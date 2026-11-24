# Cloud AI Learning Platform — Vocab AI

A mobile-first English vocabulary and listening app for IELTS learners. Look up words in your own imported dictionaries, save them to a personal library, review them with spaced repetition, capture words from photos with OCR, practise listening with locally transcribed audio, and get help from **LLM agents that call the app's own services as tools**.

Built as a full-stack portfolio project: **Vue 3 + TypeScript** frontend (also packaged as an **Android app with Capacitor**) and a **Python FastAPI** backend organised into domain-driven layers, running in **Docker**.

[中文说明 / Chinese notes](README.zh-CN.md)

---

## Features

### AI
- **AI learning assistant (tool-calling agent)** — the user asks in natural language ("save *resilient* and *allocate* to my library"); Claude decides which tools to call (`lookup_word`, `search_my_words`, `add_word`, `get_due_reviews`), the backend executes them through the existing services, and the loop repeats (max 8 rounds) until the answer is ready. The UI shows which tools were used. See [docs/ai-agent.md](docs/ai-agent.md).
- **Study-planning agent** — reads the learner's vocabulary, due reviews and listening mistakes, then writes today's plan (review / dictation / retell / vocabulary tasks). The plan is saved only through a `save_study_plan` tool whose input is validated before storage.
- **Deep word explanations** — etymology, letter-shape memory hints and a short "movie scene" generated from a versioned prompt; each word is generated once and cached, with a per-word lock so a double tap never pays twice.
- LLM access sits behind a thin `ClaudeClient` wrapper that maps SDK errors to the app's error codes, so services are unit-tested with a fake client.

### Listening
- **Import audio, get timed sentences** — uploads are transcribed locally with **faster-whisper** (CPU, no API cost) and split into sentences with timestamps; transcripts can be corrected by hand.
- **Dictation and retell practice** — sentence-by-sentence playback; spoken retells are recorded, transcribed and scored, and missed / misheard words feed the study planner.
- **Natural example-sentence audio** — local neural TTS with **Piper** for sentences without a real recording.

### Vocabulary
- **Image-to-vocabulary (OCR)** — OpenCV preprocessing (grayscale → upscale → denoise → adaptive threshold) + Tesseract; tap a word to look it up and save it.
- **Imported MDict dictionaries** (like Eudic / GoldenDict) — upload `.mdx` / `.mdd` packages, reorder them, search with prefix suggestions and examples; the backend includes an MDict reader (incl. LZO decompression) and serves dictionary CSS / images / audio. Falls back to an online dictionary when a word is not found locally.
- **Personal word library** with per-user data isolation.
- **Spaced-repetition review** — Ebbinghaus-style schedule (0, 1, 3, 7, 15, 30 days): *Known* advances, *Fuzzy* repeats tomorrow, *Unknown* resets.
- **Word-root reference** — page snippets from root-and-affix books.

### Platform
- Auth with bcrypt + JWT; bilingual UI (English / Chinese) built with Vant.
- **Android app** via Capacitor (`npm run build:android`).

## Tech Stack

| Layer | Technologies |
|---|---|
| Frontend | Vue 3, TypeScript, Vite, Vant 4, Vue Router, Axios, Capacitor (Android) |
| Backend | Python 3, FastAPI, Pydantic v2, PyMySQL + DBUtils connection pool |
| AI / LLM | Anthropic Claude API (tool use, agent loop), prompt files under version control |
| Speech | faster-whisper (speech-to-text), Piper (text-to-speech), PyAV |
| Computer vision | OpenCV, Tesseract OCR (pytesseract), PyMuPDF |
| Database | MySQL 8 with numbered SQL migrations |
| Security | JWT (python-jose), bcrypt |
| DevOps | Docker, Docker Compose, Nginx config for server deployment |
| Testing | pytest (69 tests) |

## Architecture

```text
 Mobile browser / Android app (Vue 3 + Vant + Capacitor)
          │  /api  (JWT in Authorization header)
          ▼
 FastAPI ─ interfaces/      HTTP routes, auth dependency, unified JSON responses, error codes
         ─ application/     use cases: auth, words, reviews, dictionaries, listening,
                            agent, planner, word explainer; prompts/
         ─ domain/          entities, repository interfaces, ReviewPolicy,
                            practice analysis, sentence splitter
         ─ infrastructure/  MySQL repositories, JWT, hashing, MDict reader,
                            OCR, Whisper, Piper, Claude client
          │
          ├──▶ MySQL
          └──▶ Claude API (agent, planner, explanations only)
```

Agent loop (assistant and planner share the pattern):

```text
user message ──▶ Claude (with tool definitions)
                   │ stop_reason = tool_use
                   ▼
           backend runs the tool via existing services ──▶ result back to Claude
                   │ … up to 8 rounds
                   ▼ stop_reason = end_turn
           final answer + list of tool calls + token usage
```

- Routes never contain SQL; business rules live in the domain layer and do not depend on FastAPI.
- The model only *proposes* actions; all reads and writes go through the same validated service code as the rest of the app, scoped to the logged-in user.
- Every response uses one shape: `{ "success": bool, "code": int, "data": ..., "message": str }`.

Frontend structure:

```text
frontend/src/
├── app/        router, layouts
├── features/   auth, words, reviews, vision, dictionaries, listening, agent, planner
├── pages/      route-level pages
└── shared/     HTTP client, UI components, styles, settings
```

## Getting Started

**Prerequisite:** Docker Desktop.

```bash
git clone https://github.com/niuleo2019/cloud-ai-learning-platform.git
cd cloud-ai-learning-platform
cp backend/.env.example backend/.env   # set JWT_SECRET; ANTHROPIC_API_KEY enables the AI features
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| API health | http://localhost:3000/api/health |
| API docs (Swagger) | http://localhost:3000/docs |
| MySQL | localhost:3307 |

Create a test account:

```bash
docker compose exec backend python scripts/seed_test_user.py
```

Notes:
- Without `ANTHROPIC_API_KEY` everything except the assistant, planner and deep explanations still works.
- Large local data is not in the repo (see `.gitignore`): imported dictionaries, Whisper models (downloaded on first use) and the Piper voice (`python -m piper.download_voices en_GB-alba-medium --data-dir /app/data/tts-voices`).
- Android: copy `frontend/.env.android.example` to `frontend/.env.android`, set the backend address, then `npm run build:android` and open `frontend/android` in Android Studio.

## API Overview

| Area | Endpoints |
|---|---|
| Auth | `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me` |
| Words | `GET/POST /api/words`, `PUT/DELETE /api/words/{id}` |
| Reviews | `GET /api/reviews/today`, `POST /api/reviews/{wordId}/submit` |
| Dictionary | `GET /api/dictionary/lookup`, `/audio`, `/speak` |
| Dictionary library | `GET/POST /api/dictionaries`, `POST /scan`, `PUT /order`, `GET /lookup`, `/examples`, `/suggest`, `PATCH/DELETE /{id}` |
| Listening | `POST/GET /api/listening/materials`, `GET /materials/{id}`, `/materials/{id}/audio`, `PUT /materials/{id}/sentences/{index}`, `POST /api/listening/retell` |
| AI assistant | `POST /api/agent/chat` |
| Study planner | `POST /api/planner/attempts`, `GET /api/planner/today`, `POST /api/planner/plan`, `PUT /api/planner/today/done` |
| Explanations | `GET/POST /api/explanations/{word}` |
| Vision | `POST /api/vision/extract-words` |
| Word roots | `GET /api/pdf-roots/search` |

Full request / response schemas are in Swagger at `/docs`.

## Tests

```bash
docker compose exec backend python -m pytest -q tests
```

69 tests covering the spaced-repetition policy, OCR word extraction, MDict dictionaries, listening transcription and retell scoring, the agent and planner tool loops (with a fake model client), and the word-explanation cache.

## Roadmap

- Measure the AI features with real usage: token cost, latency and answer quality per request, plus a small eval set
- Review history and statistics dashboard
- CI with GitHub Actions and cloud deployment (HTTPS backend for the Android app)

## Author

Lifu Chen — Full-stack developer (Python / FastAPI · Vue 3 / TypeScript), Sydney.
