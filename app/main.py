"""FieldLens AI FastAPI application and local mission generator."""

from __future__ import annotations

import asyncio
import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any, Literal
from uuid import uuid4

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator


BASE_DIR = Path(__file__).resolve().parent
MODEL_NAME = os.getenv("FIELDLENS_MODEL_NAME", "google/flan-t5-small")
MODEL_DISABLED = os.getenv("FIELDLENS_DISABLE_MODEL", "0").strip().lower() in {
    "1", "true", "yes", "on"
}
MODEL_TIMEOUT_SECONDS = float(os.getenv("FIELDLENS_MODEL_TIMEOUT_SECONDS", "45"))

Duration = Literal[15, 30, 60]
Environment = Literal["park", "neighborhood", "garden", "woodland"]
Interest = Literal["plants", "birds", "insects", "trees", "general biodiversity"]
Difficulty = Literal["easy", "moderate", "adventurous"]
Source = Literal["local_model", "fallback"]


class MissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    duration: Duration
    environment: Environment
    interests: list[Interest] = Field(min_length=1, max_length=5)

    @field_validator("interests")
    @classmethod
    def unique_interests(cls, values: list[Interest]) -> list[Interest]:
        if len(values) != len(set(values)):
            raise ValueError("interests must not contain duplicates")
        return values


class MissionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str = Field(min_length=4, max_length=80)
    instructions: list[str] = Field(min_length=3, max_length=6)
    duration: Duration
    environment: Environment
    interests: list[Interest]
    difficulty: Difficulty
    safety_notes: list[str] = Field(min_length=2, max_length=4)
    source: Source


class ModelStatus(BaseModel):
    name: str
    enabled: bool
    state: Literal["disabled", "not_loaded", "loading", "ready", "error"]
    cached: bool
    last_error: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok"]
    model: ModelStatus


@dataclass(frozen=True)
class MissionTemplate:
    title: str
    steps: tuple[str, ...]
    difficulty: Difficulty


FALLBACKS: dict[str, tuple[MissionTemplate, ...]] = {
    "plants": (
        MissionTemplate("Leaf Shape Safari", ("Find three plants with noticeably different leaf shapes.", "Sketch or describe one edge, vein pattern, and texture from each.", "Notice where each plant grows without picking any part of it."), "easy"),
        MissionTemplate("Tiny Plant Neighborhoods", ("Choose a small patch beside the path and count its distinct plant forms.", "Compare which plants prefer shade, cracks, or open soil.", "Record one question to investigate later without guessing a species."), "moderate"),
    ),
    "birds": (
        MissionTemplate("Listen Before You Look", ("Stand quietly for two minutes and map each bird sound by direction.", "Watch for movement and note size, color, and behavior rather than naming species.", "Move to one new listening spot and compare what changes."), "easy"),
        MissionTemplate("Bird Behavior Watch", ("Choose a comfortable viewpoint well away from nests or feeding birds.", "Observe one bird for five minutes and note how it moves, rests, or searches for food.", "Compare your notes with a second bird from the same distance."), "moderate"),
    ),
    "insects": (
        MissionTemplate("Pollinator Pause", ("Find a flowering patch beside a permitted path.", "Watch from a respectful distance and count insect visits for five minutes.", "Note color, size, movement, and flower choice without touching anything."), "easy"),
        MissionTemplate("Six-Legged Micro-Safari", ("Inspect leaves, bark, and the air above flowers without moving habitat.", "Find three different insect behaviors and describe each in plain language.", "Leave every creature and its shelter exactly as found."), "moderate"),
    ),
    "trees": (
        MissionTemplate("Bark & Canopy Trail", ("Find three trees along a public path.", "Compare bark pattern, trunk shape, and canopy silhouette without removing bark or leaves.", "Choose one tree and make a 60-second texture sketch."), "easy"),
        MissionTemplate("A Tree's Many Neighbors", ("Choose one accessible tree away from hazards.", "Look for moss, lichens, insects, fallen leaves, or birds around it without disturbing them.", "Draw a simple relationship map of what you observed."), "moderate"),
    ),
    "general biodiversity": (
        MissionTemplate("Five Senses, Lightly", ("Walk slowly and pause at three safe spots.", "At each stop record one color, sound, texture you can observe without touching, and sign of seasonal change.", "Finish by noting which stop seemed most diverse and why."), "easy"),
        MissionTemplate("Urban Habitat Mosaic", ("Find three small habitat types such as lawn, hedge, tree bed, pond edge, or wall.", "Spend equal time observing the living things in each from the path.", "Compare the habitats without claiming species identities you cannot verify."), "moderate"),
    ),
}

ENVIRONMENT_HINTS = {
    "park": "Use marked paths and a quiet public green-space edge.",
    "neighborhood": "Stay on public pavements and cross streets only at safe crossings.",
    "garden": "Observe only where you have permission and avoid treated or thorny plants.",
    "woodland": "Remain on marked trails and turn back before light or weather deteriorates.",
}
SAFETY_NOTES = (
    "Observe wildlife quietly: never touch, feed, collect, chase, or disturb it.",
    "Stay in permitted public areas, watch weather and footing, and tell someone your route for longer outings.",
    "Descriptions are observations, not confirmed species identifications.",
)


class LocalMissionGenerator:
    """Lazily loads and caches a local Transformers text2text pipeline."""

    def __init__(self) -> None:
        self.pipeline: Any | None = None
        self.state: Literal["disabled", "not_loaded", "loading", "ready", "error"] = (
            "disabled" if MODEL_DISABLED else "not_loaded"
        )
        self.last_error: str | None = None
        self._load_lock = Lock()

    def status(self) -> ModelStatus:
        state = "disabled" if MODEL_DISABLED else self.state
        return ModelStatus(name=MODEL_NAME, enabled=not MODEL_DISABLED, state=state,
                           cached=self.pipeline is not None, last_error=self.last_error)

    def _load_pipeline(self) -> Any:
        from transformers import pipeline
        return pipeline("text2text-generation", model=MODEL_NAME, tokenizer=MODEL_NAME, device=-1)

    def _ensure_pipeline(self) -> Any:
        if self.pipeline is not None:
            return self.pipeline
        with self._load_lock:
            if self.pipeline is not None:
                return self.pipeline
            self.state = "loading"
            try:
                self.pipeline = self._load_pipeline()
            except BaseException as exc:
                self.state = "error"
                self.last_error = _safe_error(exc)
                raise
            self.state = "ready"
            self.last_error = None
            return self.pipeline

    def generate(self, request: MissionRequest) -> str:
        local_pipeline = self._ensure_pipeline()
        prompt = (
            "Create one safe outdoor nature observation mission. "
            f"Duration: {request.duration} minutes. Environment: {request.environment}. "
            f"Interests: {', '.join(request.interests)}. "
            "Do not tell the explorer to touch, feed, collect, chase, climb, trespass, "
            "leave marked paths, or identify a species with certainty. "
            "Return exactly four lines: TITLE: short title; STEP: instruction; "
            "STEP: instruction; STEP: instruction."
        )
        result = local_pipeline(prompt, max_new_tokens=128, min_new_tokens=35, do_sample=False,
                                num_beams=4, repetition_penalty=1.15, truncation=True,
                                max_length=256)
        if not isinstance(result, list) or not result or not isinstance(result[0], dict):
            raise ValueError("model returned an unexpected result shape")
        text = result[0].get("generated_text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("model returned empty text")
        return text.strip()


generator = LocalMissionGenerator()


def _safe_error(exc: BaseException) -> str:
    if isinstance(exc, MemoryError):
        return "The model could not be loaded within available memory."
    if isinstance(exc, (ImportError, ModuleNotFoundError)):
        return "Transformers or its local runtime dependencies are unavailable."
    return f"{type(exc).__name__}: local model initialization or inference failed."[:180]


def _fallback(request: MissionRequest) -> MissionResponse:
    key = "|".join([str(request.duration), request.environment, *sorted(request.interests)])
    digest = hashlib.sha256(key.encode()).digest()
    interest = request.interests[digest[0] % len(request.interests)]
    template = FALLBACKS[interest][digest[1] % len(FALLBACKS[interest])]
    steps = [ENVIRONMENT_HINTS[request.environment], *template.steps]
    if request.duration == 60:
        steps.append("Repeat the observation in a second area and compare the two places.")
    elif request.duration == 30:
        steps.append("Use the final five minutes to write a short reflection in your journal.")
    return MissionResponse(id=str(uuid4()), title=template.title, instructions=steps,
                           duration=request.duration, environment=request.environment,
                           interests=request.interests,
                           difficulty=template.difficulty if request.duration < 60 else "adventurous",
                           safety_notes=list(SAFETY_NOTES), source="fallback")


UNSAFE_PATTERN = re.compile(
    r"\b(touch|feed|collect|capture|pick|chase|disturb|climb|trespass|leave the (?:path|trail))\b",
    re.IGNORECASE,
)


def _parse_model_output(raw: str, request: MissionRequest) -> MissionResponse:
    lines = [re.sub(r"^[\-*\d.)\s]+", "", line).strip() for line in raw.splitlines()]
    lines = [line for line in lines if line]
    title = ""
    steps: list[str] = []
    for line in lines:
        if re.match(r"^title\s*:", line, re.IGNORECASE):
            title = re.sub(r"^title\s*:\s*", "", line, flags=re.IGNORECASE).strip()
        elif re.match(r"^step\s*:", line, re.IGNORECASE):
            steps.append(re.sub(r"^step\s*:\s*", "", line, flags=re.IGNORECASE).strip())
    # FLAN-T5 sometimes follows the intent but drops the requested labels. Keep
    # that output usable when it contains enough bounded, sentence-like content.
    if not title and not steps and len(raw) >= 60:
        chunks = [part.strip(" -:;") for part in re.split(r"[\n;.!?]+", raw) if part.strip()]
        if len(chunks) >= 4:
            title, steps = chunks[0][:80], [part[:220] for part in chunks[1:4]]
    if not 4 <= len(title) <= 80 or not 3 <= len(steps) <= 5:
        raise ValueError("model output did not follow the required format")
    if any(not 12 <= len(step) <= 220 for step in steps):
        raise ValueError("model instruction length was invalid")
    if UNSAFE_PATTERN.search(" ".join(steps)):
        raise ValueError("model output contained an unsafe activity")
    steps.insert(0, ENVIRONMENT_HINTS[request.environment])
    return MissionResponse(id=str(uuid4()), title=title, instructions=steps,
                           duration=request.duration, environment=request.environment,
                           interests=request.interests,
                           difficulty="easy" if request.duration == 15 else "moderate" if request.duration == 30 else "adventurous",
                           safety_notes=list(SAFETY_NOTES), source="local_model")


app = FastAPI(title="FieldLens AI",
              description="Offline-first nature missions powered by local open-source AI.",
              version="1.0.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", model=generator.status())


@app.post("/api/missions/generate", response_model=MissionResponse)
async def generate_mission(request: MissionRequest) -> MissionResponse:
    if MODEL_DISABLED:
        return _fallback(request)
    try:
        raw = await asyncio.wait_for(asyncio.to_thread(generator.generate, request),
                                     timeout=MODEL_TIMEOUT_SECONDS)
        return _parse_model_output(raw, request)
    except (asyncio.TimeoutError, MemoryError, ImportError, OSError, RuntimeError, ValueError) as exc:
        generator.last_error = _safe_error(exc)
        if generator.pipeline is None:
            generator.state = "error"
        return _fallback(request)
