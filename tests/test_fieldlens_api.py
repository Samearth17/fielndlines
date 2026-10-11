from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import main

client = TestClient(main.app)
VALID = {"duration": 30, "environment": "park", "interests": ["birds", "trees"]}


@pytest.fixture(autouse=True)
def reset_generator(monkeypatch):
    monkeypatch.setattr(main, "MODEL_DISABLED", False)
    main.generator.pipeline = None
    main.generator.state = "not_loaded"
    main.generator.last_error = None


def test_homepage_and_static_assets() -> None:
    home = client.get("/")
    assert home.status_code == 200
    assert "FieldLens AI" in home.text
    for asset in ("app.js", "styles.css"):
        response = client.get("/static/" + asset)
        assert response.status_code == 200
        assert response.text


def test_health_reports_model_status() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["model"] == {
        "name": "google/flan-t5-small",
        "enabled": True,
        "state": "not_loaded",
        "cached": False,
        "last_error": None,
    }


def test_valid_local_model_mission(monkeypatch) -> None:
    monkeypatch.setattr(
        main.generator,
        "generate",
        lambda _: (
            "TITLE: Canopy Sound Map\n"
            "STEP: Listen quietly for layered bird calls.\n"
            "STEP: Compare the canopy at two marked-path stops.\n"
            "STEP: Record shapes and movements without naming species."
        ),
    )
    response = client.post("/api/missions/generate", json=VALID)
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "local_model"
    assert body["duration"] == 30
    assert body["environment"] == "park"
    assert body["interests"] == ["birds", "trees"]
    assert len(body["instructions"]) == 4
    assert set(body) == {
        "id", "title", "instructions", "duration", "environment", "interests",
        "difficulty", "safety_notes", "source",
    }


@pytest.mark.parametrize(
    "payload",
    [
        {"duration": 20, "environment": "park", "interests": ["birds"]},
        {"duration": 15, "environment": "beach", "interests": ["birds"]},
        {"duration": 15, "environment": "park", "interests": []},
        {"duration": 15, "environment": "park", "interests": ["fungi"]},
        {"duration": 15, "environment": "park", "interests": ["birds", "birds"]},
        {"duration": 15, "environment": "park", "interests": ["birds"], "gps": True},
    ],
)
def test_invalid_inputs_return_422(payload) -> None:
    assert client.post("/api/missions/generate", json=payload).status_code == 422


def test_disabled_model_returns_labeled_deterministic_fallback(monkeypatch) -> None:
    monkeypatch.setattr(main, "MODEL_DISABLED", True)
    first = client.post("/api/missions/generate", json=VALID).json()
    second = client.post("/api/missions/generate", json=VALID).json()
    assert first["source"] == "fallback"
    assert first["title"] == second["title"]
    assert first["instructions"] == second["instructions"]
    assert client.get("/api/health").json()["model"]["enabled"] is False


def test_model_initialization_failure_uses_fallback(monkeypatch) -> None:
    def fail(_: main.MissionRequest) -> str:
        raise OSError("download unavailable")

    monkeypatch.setattr(main.generator, "generate", fail)
    body = client.post("/api/missions/generate", json=VALID).json()
    assert body["source"] == "fallback"
    assert "failed" in main.generator.last_error.lower()


@pytest.mark.parametrize(
    "raw",
    [
        "not structured",
        "TITLE: Too short\nSTEP: only one step",
        (
            "TITLE: Unsafe outing\n"
            "STEP: Touch every leaf you see carefully.\n"
            "STEP: Walk slowly for five minutes.\n"
            "STEP: Write down what you see."
        ),
    ],
)
def test_malformed_or_unsafe_model_output_uses_fallback(monkeypatch, raw) -> None:
    monkeypatch.setattr(main.generator, "generate", lambda _: raw)
    assert client.post("/api/missions/generate", json=VALID).json()["source"] == "fallback"


def test_no_journal_api_exists() -> None:
    assert client.get("/api/journal").status_code == 404


def test_static_paths_exist() -> None:
    assert {"index.html", "styles.css", "app.js"} <= {
        path.name for path in Path(main.BASE_DIR / "static").iterdir()
    }
