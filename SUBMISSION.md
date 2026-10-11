---
title: "FieldLens AI: a local field guide designed to make itself unnecessary"
published: false
tags: hf26challenge, opensource, ai, python
---

> Draft for review. Add repository URL, demo URL, screenshots, and real outdoor testing notes before publishing. Do not invent these.

## What I built

FieldLens AI creates a short nature-observation mission from three choices: available time, environment, and interests. Once the mission is ready, the interface shifts into a deliberately quiet screen-free mode. After returning, the explorer can save an observation in a browser-local journal.

The Week 1 “Touch Grass” prompt immediately suggested a design constraint: the screen should be the shortest part of the experience. FieldLens has no feed, streak, GPS route, social graph, account, or cloud AI call.

## Demo

<!-- Add a real screenshot or video. Show: preference selection → mission → screen-free mode → journal. -->

Repository: **TODO**

Live demo / setup instructions: **TODO**

## How it works

```text
Browser preferences → FastAPI /api/missions/generate
                    → lazy local google/flan-t5-small pipeline
                    → validated mission
                    ↘ deterministic fallback on any failure

Browser journal CRUD → localStorage only
```

The backend loads `google/flan-t5-small` only on the first model-backed request and caches it for later requests. Inference is bounded and deterministic. The response parser accepts only the small mission format the interface needs and rejects malformed, overlong, or unsafe output. Failures return a curated mission visibly labeled “not AI-generated.”

## Why open matters

Once the weights have been downloaded, mission generation can run on the user's computer without sending preferences or observations to a paid inference API. The model can be inspected or swapped, and a reviewer can run the whole stack locally. This matters for privacy, cost, and resilience—but “local” is not magic. First-run download still needs a network, local inference still needs memory and CPU, and an open model can still produce weak or biased output.

The official model card lists FLAN-T5 Small under Apache 2.0 and warns about bias and untested real-world use. FieldLens treats generation as creative assistance, never species identification or scientific fact.

## Reliability is part of the experience

The app stays useful when model dependencies are missing, downloads fail, memory is tight, inference times out, or generated text is malformed. FastAPI validates every input and output shape. pytest tests the HTTP surface while mocking model calls, so the test suite stays quick and does not silently download weights.

The journal has an equally strict privacy boundary: observations remain in browser `localStorage`; there is no journal API. The UI explains that localStorage persists but is not encrypted.

## Responsible exploration

Every mission says to observe without touching, feeding, collecting, chasing, or disturbing wildlife. Missions keep people on permitted paths, avoid trespassing, and describe uncertain observations without pretending to confirm a species.

## What I would test outside

<!-- Replace this section with honest results after taking the app outside. -->

- Was the setup short enough?
- Could the mission be remembered after pocketing the phone?
- Were instructions useful in a real park, street, garden, and woodland?
- Did screen-free mode reduce checking rather than create timer anxiety?
- Which generated instructions needed better safety filtering?

## What I learned

Offline-first AI needs an honest state model. “Local inference” is not available until the weights are cached. A product must expose that state, survive download and parse failures, and say clearly when the result is a non-AI fallback.

## Acknowledgements and further reading

- Google / Hugging Face, [FLAN-T5 Small model card](https://huggingface.co/google/flan-t5-small).
- Peyton Green, [Testing FastAPI Endpoints Without Spinning Up a Server](https://dev.to/peytongreen_dev/testing-fastapi-endpoints-without-spinning-up-a-server-j74).
- Maxime Rius, [Embarquer un modèle ML dans une app mobile offline-first](https://dev.to/riusmax/embarquer-un-modele-ml-dans-une-app-mobile-offline-first-architecture-et-retours-dexperience-59o3).

<!-- Required before submission: real repository/demo links, screenshots, honest outdoor test, AI disclosure, and final proofreading. -->
