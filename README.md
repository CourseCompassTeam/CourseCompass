# CourseCompass

An AI advising chatbot for graduate students. Students can ask about degree
progress, course descriptions, term offerings, interest-based recommendations,
syllabus summaries, and milestones, and get routed to advising or career
services when a question is out of scope.

Built by Team Production Ready.

## Documentation package

| What | Where |
|------|-------|
| Source code | This repository (see the [folder map](#folder-map)) |
| User guide | [docs/USER_GUIDE.md](docs/USER_GUIDE.md) |
| Developer guide | [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) |
| API docs | [docs/API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md) |
| Deployment guide | [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) |
| Architecture and design (Weeks 3-4) | [Architecture Document](docs/ARCHITECTURE_DOCUMENT.md), [Architecture Decision Records](docs/ARCHITECTURE_DECISION_RECORDS.md), [Detailed Design](docs/DETAILED_DESIGN.md) |
| QA report and test results (Week 7) | [reports/CourseCompass-Quality-Assurance-Report.md](reports/CourseCompass-Quality-Assurance-Report.md) |
| Implementation reports (Weeks 5-6) | [Progress Report](reports/CourseCompass-Implementation-Progress-Report.md), [Final Implementation Report](reports/CourseCompass-Final-Implementation-Report.md) |
| Presentation materials | [Final slides](presentations/Production%20Ready%20Final%20Presentation.pptx), [presentation video](https://youtu.be/6wGrnPYD9B4) (see [presentations/](presentations/README.md)) |
| Known issues and open questions | [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md), [docs/OPEN_QUESTIONS.md](docs/OPEN_QUESTIONS.md) |

## Stack

| Layer      | Technology                                           |
|------------|------------------------------------------------------|
| Frontend   | JavaScript, React, Vite, Vitest (ADR-005)            |
| Auth       | Clerk (`@clerk/react`)                               |
| Backend    | Python, FastAPI, pytest (ADR-006)                    |
| Database   | PostgreSQL + pgvector on Cloud SQL (ADR-002)         |
| Migrations | node-pg-migrate                                      |
| LLM        | Vertex AI Gemini 2.5 Flash + gemini-embedding-001    |
| Hosting    | Vercel (frontend), Google Cloud Run (backend) (ADR-003) |

## Architecture

The backend is a modular monolith (ADR-001):

```
API  ->  orchestration  ->  tools  ->  domain services  ->  repositories  ->  PostgreSQL
```

- The frontend talks to the backend over REST (ADR-004).
- Gemini never reads the database. It only chooses a tool and phrases verified
  tool JSON.
- The server injects `student_id` from a Clerk JWT (or `X-Dev-Student-Id` in
  local/staging/test). The model cannot supply identity (QA-03).
- Repositories are the only code that runs SQL.

### Query flow

1. The chat sends `query`, short `history`, and `questionNumber`.
2. FastAPI resolves the student id and calls `answer_query`.
3. Gemini picks one tool from the fixed catalog.
4. `ToolDispatcher` runs that tool with the server student id.
5. Domain services read Cloud SQL through repositories.
6. Gemini phrases the tool JSON into the reply the student sees.

Interest search embeds the question and each leftover course’s title,
description, and syllabus text with Vertex embeddings, then ranks by cosine
similarity in the API. Stored `syllabus_chunks.embedding` values may still be
null; the ivfflat index is unused until embeddings are persisted.

### Tools

| Tool | Purpose |
|------|---------|
| `audit_degree` | Credits remaining, required courses, what to take next |
| `get_course_description` | One course, offerings, prerequisites, syllabus text |
| `recommend_courses` | Leftover courses ranked by interest |
| `list_term_offerings` | Courses published for the next or current term |
| `get_next_milestones` | Non-course steps (resume, internships, portfolio) |
| `get_advisor_contact` | Advising booking link |
| `get_career_services` | Career Services link |
| `build_schedule` | Saved schedule lookup; advising handoff if none |
| `redirect_out_of_scope` | Financial aid, account changes, medical/legal, etc. |

## Folder map

```
backend/
  app/
    api/            REST endpoints (/api/v1/...) and the error envelope
    auth/           Clerk JWT verification and student id resolution
    schemas/        request/response models
    orchestration/  LLM provider, tool catalog, dispatcher, query pipeline
    tools/          MCPTools: the fixed tool set the LLM may call
    services/       audit, course catalog, campus directory, milestones
    repositories/   PostgreSQL data access
    embeddings/     Vertex embedding client
    ingestion/      data source ingestion interface (QA-04)
  tests/            unit tests
  tests/integration/  API integration tests (in-memory repos, scripted LLM)
  tests/db/         database QA tests, seed unit tests, and benchmark
  Dockerfile        Cloud Run container image
frontend/
  src/
    components/     ChatContainer, ChatInput, and message renderers
    models/         message types and chat history helpers
    services/       ChatService, APIClient, AuthService, MockAPIClient
    auth/           Clerk root and session wiring
    styles.css      chat UI styles
  .env.example      VITE_API_BASE_URL, Clerk, mock API flags
migrations/         node-pg-migrate schema migrations
seeds/              dev/test seed data (courses, transcripts, syllabus chunks)
scripts/            gcloud auth, Cloud Run deploy, LLM smoke helpers
docs/               user, developer, API, and deployment guides; design docs
  images/           diagrams and screenshots used by the docs
reports/            implementation and QA reports
  images/           screenshots used by the reports
presentations/      final presentation slides and demo video link
```

## Configuration

All configuration comes from environment variables. Copy `.env.example` to
`.env` for the backend and `frontend/.env.example` to `frontend/.env.local`
for the frontend. Never commit either file.

Important backend variables:

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string |
| `LLM_PROVIDER=vertex` | Enables Gemini orchestration |
| `GCP_PROJECT_ID` / `GCP_LOCATION` | Vertex project and region |
| `LLM_MODEL` | Default `gemini-2.5-flash` |
| `EMBEDDING_MODEL` / `EMBEDDING_DIMENSIONS` | Default `gemini-embedding-001` / `768` |
| `CORS_ORIGINS` | Comma-separated browser origins |
| Clerk JWKS / JWT settings | Session verification |

## Local setup

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev      # http://localhost:5173
```

In `frontend/.env.local`:

- **`VITE_USE_MOCK_API=true`** — sample responses, no backend.
- **`VITE_USE_MOCK_API=false`** and **`VITE_API_BASE_URL=http://127.0.0.1:8080`** —
  talk to the local API.
- **No `VITE_CLERK_PUBLISHABLE_KEY`** — fake signed-in user (`dev-token`).
  Add the key for real Clerk sign-in.

Other commands: `npm test` (Vitest), `npm run build`, `npm run preview`.

Each question is sent with short history and a question number
(`src/models/chatHistory.js`):

```json
{
  "query": "what are its prerequisites?",
  "history": [
    { "role": "student", "text": "what is MSSE 635?" },
    { "role": "assistant", "text": "MSSE 635 is Software Architecture and Design..." }
  ],
  "questionNumber": 2
}
```

`history` is oldest first, never includes the current `query`, and holds at
most the last 3 complete exchanges (6 messages). `questionNumber` counts every
student question still on screen so milestone nudges stay correct after the
history window clips.

### Backend (FastAPI)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Point `DATABASE_URL` at Cloud SQL through the local Auth Proxy (typical local
port `5434`), then:

```bash
export LLM_PROVIDER=vertex
export GCP_PROJECT_ID=coursecompass-509519
export GCP_LOCATION=us-central1
export LLM_MODEL=gemini-2.5-flash
export EMBEDDING_MODEL=gemini-embedding-001
export EMBEDDING_DIMENSIONS=768
export APP_ENV=local
export CORS_ORIGINS=http://localhost:5173

uvicorn app.main:app --host 127.0.0.1 --port 8080
```

Smoke checks:

```bash
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/api/info
curl -X POST http://127.0.0.1:8080/api/v1/query \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer dev-token' \
  -H 'X-Dev-Student-Id: user_3K1pC0YksFOD8HW1dIiz4ITDt90' \
  -d '{"query":"What do I still need to graduate?","history":[],"questionNumber":1}'
```

Interactive OpenAPI docs: `http://127.0.0.1:8080/docs`.

Seed data (dev/test only):

```bash
# from repo root, with DATABASE_URL set
python seeds/seed.py
```

### Vertex AI Gemini

```bash
gcloud services enable aiplatform.googleapis.com --project=coursecompass-509519
gcloud auth application-default login   # local only

./scripts/smoke_llm.sh
./scripts/smoke_embed.sh
```

Tool routing smoke (does not call tools or the database):

```bash
curl -X POST http://127.0.0.1:8080/api/v1/orchestration/route \
  -H 'Content-Type: application/json' \
  -d '{"query":"How many credits do I still need?"}'
```

## Testing

### Backend

```bash
cd backend
source .venv/bin/activate
python -m pytest tests -q                 # unit + integration
python -m pytest tests/integration -q     # API integration only
```

Unit tests cover services, auth, providers, and the query pipeline with fakes.
Integration tests under `tests/integration/` run HTTP → orchestration → tools →
services with in-memory repositories and a scripted LLM. They do not call live
Cloud SQL, Clerk JWKS, or Vertex.

### Frontend

```bash
cd frontend
npm test
```

There is no automated browser e2e suite that drives Vercel → Cloud Run → Cloud
SQL → Clerk → Vertex in one flow.

## Deploy backend to Cloud Run

Requires `gcloud` authenticated to a project with billing enabled.

```bash
chmod +x scripts/*.sh
export GCP_PROJECT_ID="coursecompass-509519"
# Optional: GCP_REGION=us-central1 SERVICE_NAME=coursecompass-api
./scripts/auth-gcp.sh          # or: ./scripts/auth-gcp.sh --login
```

**Important:** `scripts/deploy-backend.sh` uses `--set-env-vars`, which
**replaces** all Cloud Run environment variables and can drop `DATABASE_URL`
and Clerk settings. Prefer building the image, then deploying only the image
so existing env vars stay in place:

```bash
gcloud builds submit backend \
  --tag us-central1-docker.pkg.dev/${GCP_PROJECT_ID}/coursecompass/coursecompass-api:TAG \
  --project="${GCP_PROJECT_ID}"

gcloud run deploy coursecompass-api \
  --image=us-central1-docker.pkg.dev/${GCP_PROJECT_ID}/coursecompass/coursecompass-api:TAG \
  --region=us-central1 \
  --project="${GCP_PROJECT_ID}"
```

Service URL pattern:

- `https://coursecompass-api-XXXX.us-central1.run.app`

Production frontend is typically pointed at that URL via `VITE_API_BASE_URL`
at Vercel build time. CORS must include each browser origin that calls the API.

## Known gaps

- `build_schedule` (US-04) is still an advising handoff when no saved schedule
  exists; there is no `.ics` export yet.
- Syllabus embeddings are computed at query time; the pgvector column is not
  filled for similarity search in SQL.
- Production Vercel builds from `main` must include the chat-history client
  changes for follow-ups like “this class” to work against the API.

## Git workflow

- `main` holds finished, stable code.
- `dev` holds integrated changes that are being tested.
- Each Jira ticket gets its own branch (for example
  `SCRUM-10-project-scaffold`). Developers can branch off the ticket branch
  for personal work.
- PR process: GitHub Copilot reviews first, then two other developers review
  and approve before merging.

## Coding standards

Python follows the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html):

- 80-character line limit and 4-space indents
- `lower_with_under` for modules, functions, and variables
- `CapsWords` for classes and `ALL_CAPS_WITH_UNDER` for constants
- A leading underscore for internal names
- Docstrings with `Args:`, `Returns:`, and `Raises:` sections
