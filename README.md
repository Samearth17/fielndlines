# FieldLens AI

FieldLens AI is an offline-first urban nature explorer. It turns a few preferences into a short outdoor observation mission, then encourages the user to put the screen away. Mission generation runs locally with the open-source `google/flan-t5-small` model; a deterministic, clearly labeled fallback keeps the app useful when the model is disabled or unavailable.

Built for the 2026 **Hacktoberfest Open-Source AI Challenge — Week 1: Touch Grass**.

## Why it exists

Nature apps often add more feeds, maps, accounts, and notifications. FieldLens does less: choose a duration, place, and interest; take one safe mission outdoors; return to a private field journal. It collects no location, account, analytics, or journal data.

## Features

- Responsive, keyboard-friendly HTML/CSS/JavaScript interface.
- Missions for 15, 30, or 60 minutes in a park, neighborhood, garden, or woodland.
- Interests covering plants, birds, insects, trees, and general biodiversity.
- Lazy, cached local inference with Hugging Face Transformers.
- Strict model-output validation and safety filtering.
- Deterministic fallback missions labeled `fallback` (never presented as AI output).
- Health status exposing disabled, not-loaded, loading, ready, or error model state.
- Screen-free mission mode with a timer and completion flow.
- Browser-local journal with create, view, edit, delete, timestamps, and mission context.
- No accounts, GPS, analytics, cloud inference, or external data collection.

## Demo evidence

These screenshots were captured from the running application in fallback-only mode; the label in the UI is intentionally explicit about that status.

![FieldLens AI homepage](docs/assets/01-homepage.png)
![Mission planner](docs/assets/02-mission-planner.png)
![Generated mission](docs/assets/03-generated-mission.png)
![Field journal](docs/assets/04-field-journal.png)
![Screen-free mode](docs/assets/05-screen-free-mode.png)

The live-interaction recording is [docs/demo.mp4](docs/demo.mp4), when present. If the local machine cannot grant screen-recording permission, follow [the recording script](docs/DEMO_SCRIPT.md) to make the final capture without presenting still images as a video.

## Architecture

```text
Browser (HTML / CSS / vanilla JS)
  ├── mission preferences ──POST /api/missions/generate──┐
  ├── model status ─────────GET /api/health──────────────┤
  └── journal CRUD ─────────localStorage only            │
                                                         ▼
FastAPI + Pydantic validation
  ├── lazy cached Transformers pipeline → google/flan-t5-small
  ├── bounded prompt and generation → validated safe mission
  └── failure / timeout / malformed output → deterministic fallback
```

The model is never loaded during application startup. The first generation request initializes the pipeline; subsequent requests reuse the cached tokenizer and weights for that process. Ordinary tests mock inference and never download model files.

## Prerequisites

- Python 3.10 or newer.
- Internet access on the first model-backed request so Transformers can download model files.
- Disk space for Python packages and the model cache, plus enough RAM to load a 77M-parameter model. Exact usage varies by platform and package build, so this project does not claim a fixed requirement.
- No API key or paid service.

## Install

From the `week 2/fieldlens-ai` directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

## Run

### Reliable demo / fallback-only mode

```bash
FIELDLENS_DISABLE_MODEL=1 uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000>.

### Local Transformers inference

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

On the first mission request, Transformers downloads `google/flan-t5-small` from Hugging Face. A network connection is required until every required model file is cached. Later runs use the Hugging Face cache and can perform inference without network access; do not claim a machine is offline-ready until one successful download has completed.

Optional settings:

```bash
export FIELDLENS_MODEL_NAME=google/flan-t5-small
export FIELDLENS_MODEL_TIMEOUT_SECONDS=45
export FIELDLENS_DISABLE_MODEL=1
```

If a download, dependency import, model load, inference, memory allocation, timeout, or output-validation step fails, the API returns a safe curated mission with `"source": "fallback"`. The process remains healthy.

## API

### `GET /`

Serves the application.

### `GET /api/health`

```json
{
  "status": "ok",
  "model": {
    "name": "google/flan-t5-small",
    "enabled": true,
    "state": "not_loaded",
    "cached": false,
    "last_error": null
  }
}
```

### `POST /api/missions/generate`

```bash
curl -X POST http://127.0.0.1:8000/api/missions/generate \
  -H 'Content-Type: application/json' \
  -d '{"duration":30,"environment":"park","interests":["birds","trees"]}'
```

Allowed durations are `15`, `30`, and `60`. Allowed environments are `park`, `neighborhood`, `garden`, and `woodland`. At least one unique supported interest is required. Unknown or extra fields return HTTP 422.

Every successful response includes `source: "local_model"` or `source: "fallback"`, plus the title, steps, duration, environment, interests, difficulty, and safety notes.

Interactive OpenAPI documentation is at <http://127.0.0.1:8000/docs>.

## Test and verify

```bash
pytest -q
python -m compileall -q app tests
node --check app/static/app.js
```

Server smoke test:

```bash
FIELDLENS_DISABLE_MODEL=1 uvicorn app.main:app --host 127.0.0.1 --port 8000
curl http://127.0.0.1:8000/api/health
curl -X POST http://127.0.0.1:8000/api/missions/generate \
  -H 'Content-Type: application/json' \
  -d '{"duration":15,"environment":"garden","interests":["plants"]}'
```

## Privacy

- Journal entries never leave the browser and no journal endpoint exists.
- `localStorage` persists across reloads but is **not encrypted**. Anyone with access to the browser profile may be able to read it. Clearing site data removes the journal.
- Mission preferences go only to the local FastAPI process.
- Model inference is in-process. Model download is the only intended external model interaction.
- The app has no accounts, analytics, telemetry, GPS, or advertising.

## Safety and responsible use

Every mission includes fixed safety guidance. Observe without touching, feeding, collecting, chasing, or disturbing wildlife. Stay on marked, permitted routes; check weather, light, footing, accessibility, and local guidance. FieldLens does not establish species identity or scientific certainty and is not a substitute for local safety advice.

## Model license and limitations

`google/flan-t5-small` is listed by its official Hugging Face model card as **Apache 2.0** and currently contains 77M parameters: <https://huggingface.co/google/flan-t5-small>. The model card also warns that its training data was not filtered for all harmful content or fully assessed for bias, and says it was not tested in real-world applications.

FieldLens therefore constrains the prompt, bounds token lengths, validates structure and length, rejects unsafe instructions, adds deterministic safety notes, and falls back on any questionable output. These guardrails reduce risk; they do not make model output infallible. Small instruction-tuned models may produce repetitive, generic, malformed, or preference-insensitive text.

Project source code is under the license in [LICENSE](LICENSE). The model remains under its own Apache 2.0 license.

## Manual demo checklist

- [ ] Start in fallback mode and confirm the health badge says fallback-only.
- [ ] Generate one 15-, 30-, and 60-minute mission.
- [ ] Confirm the mission card labels curated fallback output as not AI-generated.
- [ ] Tab through all inputs and actions without a mouse.
- [ ] Start screen-free mode, confirm the timer updates, then complete the mission.
- [ ] Save, reload, edit, and delete a journal observation.
- [ ] Confirm no request is sent when journal entries change.
- [ ] Check the layout at phone and desktop widths.
- [ ] Start without fallback mode, allow the first download, and generate a `local_model` mission.
- [ ] Stop the network after caching, restart, and verify cached local inference.
- [ ] Re-run tests and capture final screenshots for the DEV post.

## Challenge submission notes

The active Week 1 prompt requires a new project with open-source AI at its core that gets people off-screen and outdoors. The required DEV tag is `#hf26challenge`; submissions close **October 11, 2026 at 11:59 PM PDT** (October 12 at 06:59 UTC). Writing quality is weighted most heavily, followed by prompt relevance, creativity, and technical execution.

See [SUBMISSION.md](SUBMISSION.md) for a local, unpublished article/demo draft.

The submission-ready DEV Community draft is [docs/DEV_ARTICLE.md](docs/DEV_ARTICLE.md).
