# HiringOS ATS Monorepo

Production-ready ATS platform with local AI parsing/interviewing, strict backend RBAC, and Docker Compose orchestration.

## Repository Structure

```text
repo/
├── backend/
├── frontend/
├── ai/
├── infra/
├── docker-compose.yml
├── .env.example
├── Makefile
└── README.md
```

## Core Guarantees

1. No seed/demo/mock database data.
2. Backend is the source of truth for RBAC and business rules.
3. Frontend works only via API (`/api/v1/...`).
4. AI models are local Hugging Face models with fallback paths.
5. Training pipeline is preserved but never auto-runs on startup.

## Product Feature Matrix

Detailed 15+ killer-feature analysis is in:

- `docs/killer-features.md`

## Services (Docker Compose)

- `frontend` (Next.js 16)
- `backend` (FastAPI)
- `worker` (Celery background worker)
- `ai-service` (FastAPI local AI inference)
- `postgres` (pgvector)
- `redis`
- `minio`
- `nginx` (reverse proxy, profile: `prod`)
- `prometheus` / `grafana` / `loki` / `promtail` (profile: `monitoring`)

All services include healthchecks and persistent volumes where needed.

## Quick Start

1. Copy environment file:

```bash
cp .env.example .env
```

2. Start stack:

```bash
make up
```

Windows one-command startup (build + health wait + optional account registration):

```powershell
./start-hiringos.ps1
# with candidate registration:
./start-hiringos.ps1 -RegisterCandidate -RegisterEmail "you@example.com" -RegisterPassword "StrongPass123!" -RegisterFullName "Your Name"
```

If Docker daemon is unavailable, `start-hiringos.ps1` now auto-falls back to a local non-Docker MVP stack.
You can also run the fallback directly:

```powershell
./start-hiringos-local.ps1
```

3. Open:
- Frontend: `http://localhost:3000`
- Backend docs: `http://localhost:8000/docs`
- MinIO console: `http://localhost:9001`
- AI service health: `http://localhost:8001/healthz`

## Authentication and RBAC

Roles:
- `candidate`
- `hr`
- `manager`
- `admin`

JWT access + refresh token flow is implemented in backend.

Registration rules:
- public `/auth/register` creates only `candidate`
- bootstrap owner flow is enabled only on first clean launch
- `hr` and `manager` are invite-only via organization invites
- role and organization scope are enforced only by backend (frontend is never source of truth)
- access/refresh are delivered by HttpOnly cookies, CSRF token is required for refresh/logout mutation flow

## AI Modules

`ai/` contains:
- `resume_parser/`
- `interview_ai/`
- `embeddings/`
- `training_pipeline/`

### Default Local Models (HF)

- Resume parser LLM: `Qwen/Qwen2.5-1.5B-Instruct`
- Interview LLM: `Qwen/Qwen2.5-1.5B-Instruct`
- Embeddings: `sentence-transformers/all-MiniLM-L6-v2`
- STT: `openai/whisper-small`
- TTS (female-targeted): `microsoft/speecht5_tts` + `microsoft/speecht5_hifigan`
- Video analysis: `openai/clip-vit-base-patch32`

Default combined footprint is configured to stay below 12 GB (depending on precision/cache metadata).

Validate and optionally pre-download configured models:

```bash
make ai-models-check
make ai-models-download
```

### AI Fallbacks

- Resume parse fallback: regex and heuristic extraction.
- Interview/chat/test generation: no canned fallback. If model is unavailable, API returns explicit `ai_unavailable`.
- Voice fallback: if TTS/STT is unavailable, UI switches to text response mode and exposes diagnostics.

## Training Pipeline

The training workflow is stored in `ai/training_pipeline/scripts`:

1. dataset discovery from Hugging Face
2. dataset download
3. preprocessing
4. optional LoRA training

Run:

```bash
make train-ai
```

This command is manual and does not block platform startup.

## Backend API Domains

- `auth`
- `candidates`
- `resumes`
- `documents`
- `interviews`
- `tests`
- `feedback`
- `notifications`
- `admin`

## Security Notes

- Password hashing with bcrypt.
- JWT access/refresh token rotation.
- Server-side RBAC checks.
- File extension and size validation.
- HTML sanitization to reduce XSS vectors.
- SQLAlchemy + parameterized SQL patterns for SQL injection mitigation.
- Rate limiting for auth/interview-critical endpoints via `slowapi`.
- DB-backed audit log for all API actions.

## Resume Flow

`upload -> MinIO -> AI service -> structured JSON -> DB`

Frontend `Resume Editor` supports:
- AI autofill indicator
- editable JSON
- manual save override

## Interview Flow

- strict state machine:
  - `draft -> scheduled -> in_progress -> intro_done -> theory_done -> ide_in_progress -> awaiting_ai_analysis -> completed -> reviewed`
- zero-wait answering:
  - answer is validated/saved immediately
  - next question is returned instantly
  - heavy AI analysis runs in Celery background
- anti-cheat telemetry is ingested as signals and aggregated into risk level
- video frames can be ingested and analyzed asynchronously for anti-cheat risk signals
- report generation is asynchronous with degraded fallback (`partial`) if AI components fail
- notifications are emitted when report is ready
- HR/manager viewers can monitor interview progress live via WebSocket + WebRTC signaling

Core interview API:
- `POST /api/v1/interviews`
- `GET /api/v1/interviews/{id}`
- `POST /api/v1/interviews/{id}/start`
- `POST /api/v1/interviews/{id}/answer`
- `POST /api/v1/interviews/{id}/finish`
- `GET /api/v1/interviews/{id}/report`
- `GET /api/v1/interviews/{id}/questions`
- `POST /api/v1/interviews/{id}/ide/submit`
- `POST /api/v1/interviews/{id}/events`
- `GET /api/v1/interviews/{id}/signals`
- `POST /api/v1/interviews/{id}/video/frame`
- `GET /api/v1/interviews/{id}/live`
- `POST /api/v1/interviews/question-bank`
- `GET /api/v1/interviews/question-bank`
- WebSocket: `/api/v1/ws/interviews/{id}?token=<JWT>`

Knowledge tests API:
- `POST /api/v1/tests`
- `POST /api/v1/tests/generate`
- `GET /api/v1/tests`
- `GET /api/v1/tests/{id}`
- `POST /api/v1/tests/{id}/start`
- `POST /api/v1/tests/attempts/{id}/answer`
- `POST /api/v1/tests/attempts/{id}/finish`
- `GET /api/v1/tests/attempts/list`
- `POST /api/v1/tests/question-bank`
- `GET /api/v1/tests/question-bank`

Run backend tests:

```bash
cd backend
python -m pytest -q
```

Run live API smoke tests against the running Docker stack:

```bash
docker run --rm --network hiringos_default \
  -e HIRE_TEST_BASE_URL=http://backend:8000/api/v1 \
  -e HIRE_RUN_LIVE_SMOKE=true \
  -v "${PWD}/backend:/app" -w /app hiringos-backend \
  pytest -q tests/integration/test_smoke_live_api.py
```

Run frontend quality checks:

```bash
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

Run Playwright e2e:

```bash
cd tests/e2e
npm install
npm run install:browsers
npm test
```

Run load tests:

```bash
k6 run tests/load/k6-smoke.js
```

## Notes

- Database starts empty by design.
- No seed scripts or demo accounts are included.
- Legacy frontend scaffold was removed from active repository path to satisfy no-mock-data constraints.
