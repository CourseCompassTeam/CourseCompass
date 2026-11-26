// End-to-end tests: real browser -> Vite frontend -> FastAPI backend -> Postgres.
// The backend uses the scripted LLM (LLM_PROVIDER=fake), and the frontend runs in
// dev auth mode as a seed student, so no Clerk or Vertex AI is needed.
// See e2e/README.md for running locally.

import { defineConfig, devices } from '@playwright/test';

// Ports chosen so they don't collide with the usual dev servers (5173 and 8080).
const FRONTEND_URL = 'http://localhost:5174';
const BACKEND_PORT = 8090;
const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`;

// "Nearly done" seed student: 30 of 36 credits, MSSE 692 and MSSE 696 left.
const E2E_STUDENT_ID = 'user_3K1pC0YksFOD8HW1dIiz4ITDt90';

// A separate variable from DATABASE_URL on purpose, so a shell that points at
// the dev Cloud SQL database can't be picked up by accident. The tests write
// rows (saved schedules), so use a throwaway database.
const databaseUrl = process.env.E2E_DATABASE_URL;
if (!databaseUrl) {
  throw new Error(
    'Set E2E_DATABASE_URL to a throwaway, migrated and seeded database. '
    + 'See frontend/e2e/README.md.',
  );
}

const isCI = Boolean(process.env.CI);

export default defineConfig({
  testDir: './e2e',
  // Tests share one database, so run them one at a time.
  workers: 1,
  forbidOnly: isCI,
  retries: isCI ? 1 : 0,
  reporter: isCI ? [['github'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: FRONTEND_URL,
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: `${process.env.E2E_PYTHON || 'python'} -m uvicorn app.main:app `
        + `--host 127.0.0.1 --port ${BACKEND_PORT}`,
      cwd: '../backend',
      url: `${BACKEND_URL}/health`,
      reuseExistingServer: false,
      env: {
        ...process.env,
        APP_ENV: 'test',
        LLM_PROVIDER: 'fake',
        DATABASE_URL: databaseUrl,
        CORS_ORIGINS: FRONTEND_URL,
        // Keep Vertex embeddings off even if the shell has a GCP project set.
        GCP_PROJECT_ID: '',
        GOOGLE_CLOUD_PROJECT: '',
      },
    },
    {
      command: 'npm run dev -- --port 5174 --strictPort',
      url: FRONTEND_URL,
      reuseExistingServer: false,
      // Shell variables win over frontend/.env.local in Vite.
      env: {
        ...process.env,
        VITE_API_BASE_URL: BACKEND_URL,
        VITE_USE_MOCK_API: 'false',
        VITE_CLERK_PUBLISHABLE_KEY: '',
        VITE_DEV_STUDENT_ID: E2E_STUDENT_ID,
      },
    },
  ],
});
