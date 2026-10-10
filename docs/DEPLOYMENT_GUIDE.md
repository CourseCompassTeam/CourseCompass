# Deployment Guide

- [1. Dependencies and prerequisites](#1-dependencies-and-prerequisites)
- [2. Environment configuration](#2-environment-configuration)
- [3. Production deployment steps](#3-production-deployment-steps)
- [4. Post-deployment verification](#4-post-deployment-verification)

---

## 1. Dependencies and prerequisites

- **Access:**
  - A Google Cloud project with billing or credits and the gcloud CLI signed in (`gcloud auth login`)
  - A Clerk application (publishable key and JWKS URL)
  - A Vercel project linked to the GitHub repository
- **Tools:**
  - Python 3.11
  - Node.js LTS (needed only for migrations)
  - git
  - Repo's virtual environment (`pip install -r backend/requirements.txt`).
- **Backend packages** (pinned in `backend/requirements.txt`):
  - FastAPI
  - Uvicorn
  - Pydantic
  - psycopg 3 with pgvector and python-dotenv
  - Google-genai for Vertex AI.
  - The Clerk token check also uses PyJWT.
- **Frontend and migrations:**
  - React
  - Vite
  - @clerk/clerk-react (`npm install` in `frontend/`)
  - node-pg-migrate (`npm install` in `migrations/`).
- **Google Cloud APIs:**
  - Cloud Run, Artifact Registry, and Cloud Build (the deploy script enables these)
  - Cloud SQL Admin and Compute Engine for the database
  - Vertex AI for Gemini and embeddings.

---

## 2. Environment configuration

For local work, create a `.env` file at the repository root (git-ignored; never commit it). On Cloud Run, the deploy script sets some variables, and the rest must be added after it runs.

#### `DATABASE_URL`

- `postgresql://postgres:<password>@34.67.68.21:5432/postgres?sslmode=require` for local work
- If missing, the API still starts and answers from hardcoded mock facts

#### `LLM_PROVIDER`, `LLM_MODEL`, `GCP_PROJECT_ID`, `GCP_LOCATION`

- Set by script
- `vertex`, `gemini-2.5-flash`, the project ID, and `us-central1`
- If `LLM_PROVIDER` is missing, queries return 501

#### `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS`

- Set by script
- `gemini-embedding-001` at 768 dimensions, which must match the `vector(768)` column

#### `APP_NAME`, `APP_ENV`

- Set by script
- `coursecompass-api` and `staging`
- Set `APP_ENV=production` for real students: only local, staging, and test accept `X-Dev-Student-Id`.
- The seed script refuses to run when `APP_ENV` is prod or production, in any letter case

#### `CLERK_PUBLISHABLE_KEY`, `CLERK_AUTHORIZED_PARTIES`

- Set on the live service
- The publishable key lets the server find Clerk's signing keys (`CLERK_JWKS_URL` or `CLERK_JWT_KEY` are alternatives)
- `CLERK_SECRET_KEY` and `LLM_API_KEY` appear in the settings, but the token code reviewed and the Vertex deployment do not use them

#### `CORS_ORIGINS`

- Comma-separated browser origins allowed to call the API

#### `VITE_CLERK_PUBLISHABLE_KEY`, `VITE_API_BASE_URL`

- Vercel
- The publishable Clerk key and the Cloud Run URL, set in Vercel for the frontend

---

## 3. Production deployment steps

### Database

1. In the Cloud Console, open Cloud SQL, Create instance, PostgreSQL. Choose Enterprise edition, PostgreSQL 18, us-central1, Single zone, and General purpose - Shared core, 1 vCPU / 1.7 GB (db-g1-small). Edition and machine family cannot be changed between dedicated and shared core later. Use only letters, numbers, and `- _ . ~` in the Postgres password and store it in the password manager
2. In Cloud SQL Studio (user postgres), run: `CREATE EXTENSION IF NOT EXISTS vector`
3. Under Connections, add each administrator's laptop public IPv4 as `x.x.x.x/32` (IPv6 is not accepted). Never add `0.0.0.0/0`. The deployed service connects through step 8, not this list
4. Run the migrations from the migrations folder in one terminal, then check `SELECT name FROM pgmigrations` (16 rows):

   ```bash
   cd migrations && npm install && set -a; source ../.env; set +a
   DATABASE_URL="${DATABASE_URL}&uselibpqcompat=true" npx node-pg-migrate up
   ```

5. Load data. Real student data comes from the application, not from the seed script, which is for development and testing only: `python seeds/seed.py` (safe to run twice)

### Backend

6. Run `gcloud config set project YOUR_PROJECT_ID`, then `bash scripts/deploy-backend.sh` from the repository root. It enables the Cloud Run, Artifact Registry, and Cloud Build APIs; creates the repository coursecompass if needed; builds the image from `backend/` with Cloud Build; deploys coursecompass-api to us-central1 (512 MiB, 1 CPU, 0 to 3 instances, unauthenticated invocation); and prints the URL
7. Add what the script does not set, with `--update-env-vars`, which keeps other variables:

   ```bash
   gcloud run services update coursecompass-api --region us-central1 --update-env-vars APP_ENV=production,CORS_ORIGINS=http://localhost:5173,https://course-compass-six.vercel.app,CLERK_PUBLISHABLE_KEY=pk_test_bW9kZXJuLW1vbmFyY2gtNjc1OS5jbGVyay5hY2NvdW50cy5kZXYk,CLERK_AUTHORIZED_PARTIES=http://localhost:5173,https://course-compass-six.vercel.app
   ```

8. Connect to Cloud SQL:

   ```bash
   gcloud run services update coursecompass-api --region us-central1 --add-cloudsql-instances PROJECT:us-central1:INSTANCE
   ```

   Give the service's runtime service account the Cloud SQL Client role, then set `DATABASE_URL` to `postgresql://postgres:<password>@/postgres?host=/cloudsql/coursecompass-509519:us-central1:coursecompass-db-small`. Use a role limited to the application tables rather than postgres. The live service already has its instance attached (checked in the console on October 9); the deploy script does not add it.
9. Repeat steps 7 to 8 after every redeploy. The script uses `--set-env-vars`, which Google documents as destructive: it deletes plain environment variables that are not in its list. Better still, add them to the script or switch it to `--update-env-vars`

### Frontend

- In Vercel set `VITE_API_BASE_URL` (the Cloud Run URL) and `VITE_CLERK_PUBLISHABLE_KEY`. Vercel deploys automatically on every push: main is production and dev is the development deployment.

---

## 4. Post-deployment verification

| Check | How | Expected result |
| --- | --- | --- |
| Service is up | `curl $API_URL/health` | A healthy response |
| Model routing works | `POST /api/v1/orchestration/route` with `{"query":"What courses should I take?"}` | A tool choice, not a 501 |
| Real data, not mock | Ask which courses are offered in 2026 FALL 8W2 | MSSE 610, 615, 635, 696. CS501 means `DATABASE_URL` is missing |
| Invalid tokens are rejected | Send `Authorization: Bearer aaa.bbb.ccc` | `401 UNAUTHORIZED` |
| Development header is off | Send `X-Dev-Student-Id` with a seeded ID and ask what is left to graduate | A generic answer, not the student's 6 credits |
| Browser access works | Open the Vercel site and ask a question | An answer, with no CORS error in the console |
| Database is healthy | `RUN_DB_TESTS=1 python -m pytest backend/tests/db/test_database_qa.py` | 87 passed (on seeded dev data only) |
| No errors in logs | Cloud Run, coursecompass-api, Logs | No 500s after the checks above |
