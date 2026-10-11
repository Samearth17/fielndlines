# 🌿 FieldLens AI

> An offline-first, screen-free urban nature explorer powered by local AI.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Local AI](https://img.shields.io/badge/Model-FLAN--T5--small-orange.svg)](https://huggingface.co/google/flan-t5-small)

---

## 📖 Overview

Most outdoor and nature apps paradoxically keep you glued to your phone screen—scrolling feeds, checking leaderboards, and taking photos for likes.

**FieldLens AI** does the opposite:
1. **Choose your parameters:** Select your duration (15, 30, or 60 mins), environment (park, garden, woodland, neighborhood), and interests (birds, plants, insects, trees).
2. **Get a focused outdoor mission:** Generated on-device using a lightweight local language model (`google/flan-t5-small`), backed by smart deterministic fallbacks.
3. **Put your phone away:** Activate **Screen-Free Mode** with a countdown timer and head outside to observe real nature.
4. **Log your observations:** Return to log your thoughts in a private, browser-based field journal. No accounts, no trackers, and zero cloud sync.

---

## ✨ Features

- 🧠 **100% Local AI Inference:** Runs `google/flan-t5-small` locally via Hugging Face Transformers. No API keys, subscriptions, or remote servers required.
- ⚡ **Graceful Fallback System:** Instant deterministic mission generator ensures the app always works smoothly, even on low-spec hardware or with the model disabled.
- 📵 **Screen-Free Mode:** Built-in timer and minimalist focus mode encourages you to unplug and observe.
- 📓 **Private Field Journal:** Store, edit, and review your notes directly in your browser (`localStorage`). Your notes never leave your device.
- 🔒 **Zero Tracking & Privacy First:** No GPS tracking, no account registration, no telemetry, and no external analytics.
- 🚀 **Zero Build Step:** Lightweight vanilla HTML, CSS, and modern JavaScript frontend served by FastAPI.

---

## 🚀 Quick Start

### 1. Clone & Set Up Environment

```bash
git clone https://github.com/Samearth17/fielndlines.git
cd fielndlines
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

> **Tip:** If you plan on developing or running tests, install `requirements-dev.txt` instead.

### 3. Run the App

#### Mode A: With Local AI (Default)
Downloads `google/flan-t5-small` (~300MB) on first request and runs inference locally on your CPU:
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

#### Mode B: Fast / Low-Resource Mode (Fallback Only)
Instantly runs using curated deterministic missions without downloading or loading any AI weights:
```bash
FIELDLENS_DISABLE_MODEL=1 uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Visit **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser!

---

## 🛠️ Architecture

```text
Browser (HTML / CSS / Vanilla JS)
  ├── Mission Preferences  ──> POST /api/missions/generate
  ├── Model Health Check   ──> GET  /api/health
  └── Journal Entries      ──> Saved in browser localStorage
                                    │
                                    ▼
FastAPI Backend
  ├── Lazy Model Loader   ──> Hugging Face pipeline (google/flan-t5-small)
  ├── Output Validation   ──> Pydantic models with safety guardrails
  └── Fallback Generator  ──> Curated, deterministic missions
```

---

## ⚙️ Configuration

You can customize runtime behavior using environment variables:

| Variable | Default | Description |
| :--- | :--- | :--- |
| `FIELDLENS_DISABLE_MODEL` | `0` | Set to `1` to disable the AI model and use instant deterministic fallbacks. |
| `FIELDLENS_MODEL_NAME` | `google/flan-t5-small` | Hugging Face model identifier for text generation. |
| `FIELDLENS_MODEL_TIMEOUT_SECONDS` | `45` | Maximum seconds allowed for local model inference before falling back. |

---

## 🧪 Testing

Run unit tests and verification checks:

```bash
pytest
```

---

## 🛡️ Privacy & Safety

- **Privacy:** All journal entries remain strictly in your browser's local storage. The server never receives or logs journal data.
- **Safety:** Observation missions emphasize visual exploration on safe trails and public paths. Always respect wildlife, private property, and local outdoor guidelines.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
