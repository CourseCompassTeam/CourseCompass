# Open Questions

The design docs don't settle these yet. The scaffold leaves each one open on
purpose, so the team can decide together.

1. **Local database setup.** Docker, a native Postgres + pgvector install, or
   a shared dev database?
2. **Backend container build for Cloud Run.** ~~A Dockerfile, or
   `gcloud run deploy --source`?~~ **Decided (SCRUM-11):** Dockerfile in
   `backend/` + Cloud Build (`scripts/deploy-backend.sh`).
3. **CI provider and workflow.** The Detailed Design says migrations run in CI
   before the test suite, but it doesn't name a CI provider.
4. **Database driver or ORM** for the repository implementations.
5. **Rate limiting.** Which library or approach enforces the documented
   10 requests per minute?
6. **Clerk token verification on the backend.** Clerk's Python SDK, or manual
   JWT verification?
7. **MCP transport.** ADR-004 says internal components use direct function
   calls, but the Container Diagram shows an MCP server talking to the
   API Gateway over JSON-RPC. Which one?
8. **Schema gaps and typos** in the Detailed Design:
   - `courses` has no description column, but US-02 returns course descriptions.
   - There's no link from a Clerk user to a `students` row.
   - `StudentMilestoneService` needs milestone data, but there's no milestones table.
   - `GET /admin/ingest/status/{job_id}` needs a table for ingestion jobs.
   - `advisor_contacts` doesn't cover career services contacts or booking URLs
     (US-05 and US-06).
   - Typos: `courses.courses_id`, `schedule_items.student_term_id` (it should
     probably be `schedule_term_id`), and `TIMESTAMPZ` (should be `TIMESTAMPTZ`).
9. **Python linter and formatter** to enforce the Google style guide.
10. **Seed data content.** Which courses and which test students?
11. **PR template and GitHub branch protection settings.**
<<<<<<< HEAD
12. **Dependency versions.** `migrations/package.json` uses `latest` and
    `backend/requirements.txt` is unpinned. (The frontend is pinned, with a
    committed `package-lock.json`.)
13. **`POST /api/v1/query` response content.** The API spec only documents
    the `audit` content (`creditsRemaining`, `requirementsMet`,
    `missingCourses`). The frontend currently expects these tentative shapes,
    which the backend should confirm or change:
    - Every type: an optional `message` string with the natural-language reply.
    - `recommendation`: `courses: [{ code, title, description }]`
    - `redirect`: `resourceName` and `url` (advising or career services link)
    - The frontend treats any unknown `type` as a redirect.
=======
12. **Dependency versions.** The `package.json` files use `latest` until pinned.
13. **LLM provider.** ~~Gemini, OpenAI, or Claude?~~ **Decided (SCRUM-11):**
    Vertex AI Gemini via `VertexGeminiProvider` (`LLM_PROVIDER=vertex`),
    using Application Default Credentials. Model id is configurable
    (`LLM_MODEL`, default `gemini-2.5-flash`).
>>>>>>> 42b97df (SCRUM-11: Wire Vertex AI Gemini into orchestration layer)
