# CourseCompass

An AI advising chatbot for graduate students. Students can ask about degree
progress, course descriptions, and recommendations, and get routed to
advising or career services when a question is out of scope.

Built by Team Production Ready.

> **Status:** project scaffold only. The files contain structure, signatures,
> and docstrings, not working logic. Decisions the team hasn't made yet are
> listed in [docs/OPEN_QUESTIONS.md](docs/OPEN_QUESTIONS.md).

## Stack

| Layer      | Technology                                  |
|------------|---------------------------------------------|
| Frontend   | JavaScript, React, Vite, Vitest (ADR-005)   |
| Auth       | Clerk (`@clerk/react`)                      |
| Backend    | Python, FastAPI, pytest (ADR-006)           |
| Database   | PostgreSQL + pgvector (ADR-002)             |
| Migrations | node-pg-migrate                             |
| LLM        | Provider TBD (Gemini, OpenAI, or Claude)    |
| Hosting    | Vercel (frontend), Google Cloud Run + Cloud SQL (backend) (ADR-003) |

## Architecture

The backend is a modular monolith (ADR-001) with these layers:

```
API  ->  orchestration  ->  tools  ->  domain services  ->  repositories  ->  PostgreSQL
```

- The frontend talks to the backend over REST (ADR-004).
- The LLM never touches data directly. It can only pick from a fixed set of
  tools in `MCPTools`.
- Repositories are the only code that reaches the database.

## Folder map

```
backend/
  app/
    api/            REST endpoints (/api/v1/...) and the error envelope
    schemas/        request/response models
    orchestration/  intent router, tool dispatcher, response assembler, LLM provider interface
    tools/          MCPTools: the fixed tool set the LLM may call
    services/       domain logic (audit, course catalog, campus directory, milestones)
    repositories/   data access interfaces
    ingestion/      data source ingestion interface (QA-04)
  tests/            pytest
  Dockerfile        Cloud Run container image (SCRUM-11)
frontend/           React + Vite app (chat UI: SCRUM-9)
migrations/         node-pg-migrate schema migrations
seeds/              dev/test-only seed data
scripts/            gcloud auth + Cloud Run deploy helpers
docs/               open questions for the team
```

## Configuration

All configuration comes from environment variables. Copy `.env.example` to
`.env` and fill in the values. Never commit `.env`.

## Local setup

### Frontend

```
cd frontend
npm install
npm run dev      # http://localhost:5173
```

Copy `frontend/.env.example` to `frontend/.env.local`, which git ignores:

- **`VITE_USE_MOCK_API=true`** returns sample responses, so the chat works
  without the backend. Type "simulate error" in a question to see the error
  state.
- **No `VITE_CLERK_PUBLISHABLE_KEY`** runs in dev mode with a fake signed-in
  user. Add the key to turn on real Clerk sign-in.

Other commands: `npm test` (Vitest), `npm run build`, and `npm run preview`.

The chat follows the Detailed Design's Chat component. `ChatContainer`
renders each message through a `MessageRenderer` picked by message type
(`src/components/renderers/`). `ChatService` talks to the backend through
the `APIClient` and `AuthService` interfaces (`src/services/`).

### Backend (FastAPI)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

Smoke checks:

```bash
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/api/info
pytest
```

Domain routes such as `POST /api/v1/query` are still stubs and return
`501 NOT_IMPLEMENTED` with the standard error envelope.

### Deploy backend to Cloud Run

Requires `gcloud` authenticated to a project with billing enabled.

```bash
chmod +x scripts/*.sh
export GCP_PROJECT_ID="your-gcp-project-id"
# Optional: GCP_REGION=us-central1 SERVICE_NAME=coursecompass-api
./scripts/auth-gcp.sh          # or: ./scripts/auth-gcp.sh --login
./scripts/deploy-backend.sh
```

The deploy script builds `backend/Dockerfile` with Cloud Build and deploys
the image to Cloud Run (`--allow-unauthenticated` for staging smoke tests).

Local database setup is still an open question. Frontend `package.json`
dependency versions remain `latest` until the team pins them.

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
