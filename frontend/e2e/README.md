# End-to-end tests

Playwright drives a real browser through the whole stack:
Vite frontend → FastAPI backend → PostgreSQL.

- **No LLM calls.** The backend runs with `LLM_PROVIDER=fake`
  (`backend/app/orchestration/fake_llm_provider.py`), which picks tools by
  keyword and always replies "Scripted test reply." Everything else (tools,
  services, database, response shapes) is real. The backend refuses `fake`
  unless `APP_ENV` is `local` or `test`.
- **No Clerk.** The frontend runs in dev auth mode as the "nearly done" seed
  student (30 of 36 credits, MSSE 692 and MSSE 696 left).
- **Own database.** The tests save schedules, so they need a throwaway database,
  passed as `E2E_DATABASE_URL`. They never read `DATABASE_URL`, so a shell
  pointed at Cloud SQL can't be used by accident.

CI runs this as the `e2e` job in `.github/workflows/ci.yml`.

## Running locally

1. Start an empty PostgreSQL with pgvector. Either:
   - Docker: `docker run --rm -d -p 5433:5432 -e POSTGRES_PASSWORD=postgres pgvector/pgvector:pg18`
   - No Docker: `pip install pgserver` in a scratch venv, then
     `python -c "import pgserver; print(pgserver.get_server('pgdata', cleanup_mode=None).get_uri())"`
     prints a connection URL for a local server that includes pgvector.

2. Prepare it (bash, from the repo root, backend venv active):

   ```bash
   export E2E_DATABASE_URL=postgresql://postgres:postgres@localhost:5433/postgres
   psql "$E2E_DATABASE_URL" -c "CREATE EXTENSION IF NOT EXISTS vector"
   (cd migrations && npm ci && DATABASE_URL="$E2E_DATABASE_URL" npx node-pg-migrate up)
   DATABASE_URL="$E2E_DATABASE_URL" APP_ENV=test python seeds/seed.py
   psql "$E2E_DATABASE_URL" -f frontend/e2e/fixtures/future-terms.sql
   ```

   `future-terms.sql` adds two terms starting 30 and 90 days from today, so
   the schedule test doesn't depend on the seed's fixed 2027 dates.

3. Run the tests:

   ```bash
   cd frontend
   npx playwright install chromium   # first time only
   npm run test:e2e                  # add --ui to watch them run
   ```

   Playwright starts the backend on port 8090 and Vite on 5174, so your usual
   dev servers on 8080 and 5173 can keep running. Set `E2E_PYTHON` if `python`
   on your PATH isn't the backend venv (e.g. `E2E_PYTHON=../backend/.venv/Scripts/python`).

## Writing tests

- Assert on data the tools return (course codes, credit counts), not on
  reply wording. The scripted reply never changes.
- To steer the fake LLM, use its keywords: a course code like `MSSE 635`
  → course description; `graduate`/`credits`/`degree` → audit;
  `advisor`, `career`, `milestone` → those tools; anything else → redirect.
- Prefer role and label locators (`getByRole('button', { name: 'Send' })`).
