# Cloud AI Learning Platform — Vocab App

A mobile-first English vocabulary app: look up words, save them to a personal library, review them with spaced repetition, and **capture new words from a photo** using OpenCV preprocessing and Tesseract OCR.

Built as a full-stack portfolio project with **Vue 3 + TypeScript** on the frontend and a **Python FastAPI** backend organised into domain-driven layers, all running in **Docker**.

[中文说明 / Chinese notes](README.zh-CN.md)

---

## Features

- **Image-to-vocabulary (OCR)** — upload a screenshot, book page or sign; the backend preprocesses it with OpenCV (grayscale → upscale → denoise → adaptive threshold), runs Tesseract, and returns English word candidates. Tap a word to look it up and save it.
- **Dictionary lookup** — queries a local Longman offline dictionary first and falls back to an online dictionary API when the word is not found locally.
- **Personal word library** — add, edit and delete words with meanings, examples and source; data is isolated per user.
- **Spaced-repetition review** — Ebbinghaus-style schedule (0, 1, 3, 7, 15, 30 days). Cards flip to reveal the meaning; *Known* advances the stage, *Fuzzy* repeats tomorrow, *Unknown* resets.
- **Word-root reference** — shows page snippets from root-and-affix books for supported words.
- **Auth** — registration and login with bcrypt password hashing and JWT.
- **Bilingual UI** — English / Chinese interface, mobile-first layout built with Vant.

## Tech Stack

| Layer | Technologies |
|---|---|
| Frontend | Vue 3, TypeScript, Vite, Vant 4, Vue Router, Axios |
| Backend | Python 3, FastAPI, Pydantic, PyMySQL + DBUtils connection pool |
| Computer vision | OpenCV, Tesseract OCR (pytesseract) |
| Database | MySQL 8 |
| Security | JWT (python-jose), bcrypt |
| DevOps | Docker, Docker Compose, Nginx config for server deployment |
| Testing | pytest |

## Architecture

```text
 Mobile browser (Vue 3 + Vant)
          │  /api  (JWT in Authorization header)
          ▼
 FastAPI ─ interfaces/      HTTP routes, auth dependency, unified JSON responses, error codes
         ─ application/     use cases: auth, words, reviews
         ─ domain/          entities, repository interfaces, ReviewPolicy (spaced repetition)
         ─ infrastructure/  MySQL repositories, JWT, password hashing,
                            dictionary lookup, OpenCV + Tesseract OCR
          │
          ▼
        MySQL
```

- Routes never contain SQL; business rules (e.g. the review schedule) live in the domain layer and do not depend on FastAPI.
- Every response uses one shape: `{ "success": bool, "code": int, "data": ..., "message": str }`.

Frontend structure:

```text
frontend/src/
├── app/        router, layouts
├── features/   auth, words, reviews, vision (API calls + state)
├── pages/      route-level pages
└── shared/     HTTP client, types, styles, settings
```

## Getting Started

**Prerequisite:** Docker Desktop.

```bash
git clone https://github.com/niuleo2019/cloud-ai-learning-platform.git
cd cloud-ai-learning-platform
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

The backend Docker image installs `tesseract-ocr`, so OCR works out of the box. To run the backend without Docker, install Tesseract locally and see [README.zh-CN.md](README.zh-CN.md) for manual setup.

## API Overview

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register` | Register |
| POST | `/api/auth/login` | Log in, returns JWT |
| GET | `/api/auth/me` | Current user |
| GET / POST | `/api/words` | List / add words |
| PUT / DELETE | `/api/words/{id}` | Update / delete a word |
| GET | `/api/reviews/today` | Words due for review |
| POST | `/api/reviews/{wordId}/submit` | Submit known / fuzzy / unknown |
| GET | `/api/dictionary/lookup?word=` | Offline dictionary lookup |
| GET | `/api/pdf-roots/search` | Word-root reference snippets |
| POST | `/api/vision/extract-words` | Extract English words from an uploaded image |

## Tests

```bash
docker compose exec backend python -m pytest -q tests
```

Covers the spaced-repetition policy (stage transitions and upper bound) and OCR word extraction.

## Roadmap

- AI learning assistant: an LLM agent with tool calling over the existing services (OCR, lookup, library, reviews)
- AI-generated example sentences and quizzes based on frequently forgotten words
- Review history and statistics dashboard
- CI with GitHub Actions and cloud deployment

## Author

Lifu Chen — Full-stack developer (Python / FastAPI · Vue 3 / TypeScript), Sydney.
