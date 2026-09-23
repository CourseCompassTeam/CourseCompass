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
| Auth       | Clerk (`@clerk/clerk-react`)                |
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
frontend/           React + Vite app (chat UI: SCRUM-9)
migrations/         node-pg-migrate schema migrations
seeds/              dev/test-only seed data
docs/               open questions for the team
```

## Configuration

All configuration comes from environment variables. Copy `.env.example` to
`.env` and fill in the values. Never commit `.env`.

## Local setup

TBD. Local database setup is an open question. The dependency versions in the
`package.json` files are set to `latest` until the team pins them.

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
