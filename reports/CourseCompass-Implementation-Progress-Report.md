# Implementation Progress Report

**Team Production Ready**  
Euan Canoy, Nhi La, Preston Davis

MSSE692_X40_Software Engineering Practicum I  
Professor Morgan Worrell  
September 27, 2026

---

## Table of Contents

1. [I. Executive Summary](#i-executive-summary)
2. [II. Infrastructure & Development Environment](#ii-infrastructure--development-environment)
3. [III. Implementation Status](#iii-implementation-status)
4. [IV. Testing & Quality](#iv-testing--quality)
5. [V. Velocity & Week 6 Planning](#v-velocity--week-6-planning)
6. [VI. AI Usage](#vi-ai-usage)

---

## I. Executive Summary

### What was completed this week?

Our team completed the full database layer for CourseCompass: all 13 tables migrated, a working Cloud SQL connection, and real seed data pulled from the official Regis MSSE course catalog. On the deployment side, both CI/CD pipelines are fully operational. Cloud Run for the backend and Vercel for the frontend, the latter auto-deploying on every push to `dev` / `main`. Core frontend functionality and its deployment pipeline are also complete.

### What's working vs. what's not?

**Working well:** both deployment pipelines are stable and automatic, the full database schema is live with real catalog data, core frontend features are functional, and the team's ticket → branch → PR → Vercel review → two teammate approvals → merge workflow is being followed consistently.

**Not yet working:** end-to-end integration has not been attempted because each team member has been building their own section independently, so frontend, backend, and database have not yet been exercised together as a full system. The repository layer connecting the database to business logic hasn't been started, which is currently blocking the LLM recommendation and toolset from moving past early-stage work.

### Are you on track for Week 6 goals?

We are on track for Week 6 goals. The team's velocity has matched expectations since Week 1, and integration is already planned as a Week 6 priority.

### Any scope adjustments needed?

US-04 (schedule export) is postponed to keep focus on core audit, recommendation, and auth ahead of integration. No other scope changes are planned at this time.

---

## II. Infrastructure & Development Environment

### Version control setup and branching strategy

We currently use GitHub and manage tickets through Jira. We outline the work and ticket, then create a branch based on that specific Jira ticket number. From there, we merge all work into `dev` once the feature is complete. Once we verify our code behavior in `dev`, we then create a PR to push to `main`.

### CI/CD status (even if basic)

- Backend Deployment is done manually through the Google Cloud Platform (GCP) command-line interface (CLI).
- Frontend deployment is done through Vercel's CI/CD pipeline. Whenever changes are committed to our GitHub repository, Vercel automatically builds and deploys the updated codebase. This is split across two branches, where the production deployment is pulled from the `main` branch, and the development branch is pulled from the `dev` branch.

### Development environment (all team members can code?)

All team members can access the code and development environment across multiple platforms and stages. The development environment is split across two different platforms:

- Frontend can be viewed and deployed on Vercel.
- The backend can be viewed and deployed on GCP.

The team has been focusing on completing their own section and has not worked on the integration stage. We will be working on connecting the frontend, backend, and database code next week and configuring the environment and secrets as needed.

### Build system and dependency management

Listed below are the various build tools and dependency managers used throughout the project:

**Frontend**

- Npm
- Vite

**Backend**

- pip

---

## III. Implementation Status

| Feature | Status | Team Member | Completion Percentage | Blockers |
| --- | --- | --- | --- | --- |
| Cloud Run deployment pipeline | Complete | Euan | 100% | None |
| LLM recommendation | In Progress | Euan | 30% | Waiting for data to verify business logic |
| LLM Tool set | In Progress | Euan | 30% | Waiting on the rest of the data to complete tools |
| Cloud SQL setup & local dev connection | Complete | Nhi | 100% | None |
| Core academic tables (programs, students, courses, prerequisites, requirements, transcript_entries) | Complete | Nhi | 100% | None |
| Syllabus search table (syllabus_chunks and pgvector index) | Complete | Nhi | 100% | Needs confirmation on Vertex AI embedding model |
| Scheduling & reference table (schedules, schedules_terms, schedules_items, advisor_contacts, data_ingestion_logs, milestones) | Complete | Nhi | 100% | None |
| Wire migrations into CI | Not Started | Nhi | 10% | None |
| Seed / sample data | In progress | Nhi | 20% | Real MSSE course catalog (12 courses) and requirements manually inserted for testing; no automated, versioned seed script yet |
| Repository layer | Not started | Nhi | 0% | None |
| Core frontend functionality | Completed | Preston | 100% | None |
| Vercel deployment pipeline | Completed | Preston | 100% | None |
| Authentication using Clerk | In progress | Preston & Euan | 75% | Backend needs token verification set up |
| UI/UX fine-tuning | In progress | Preston | 25% | None |

---

## IV. Testing & Quality

- **Unit test coverage (percentage and key areas tested)**
  - 68% on the backend business logic layer
  - Frontend:
    - Overall: 34.6% line coverage
    - Service layer: 83% of lines
    - React components: 0%
  - 0% on database layer
- **Integration test status**
  - 0% on integration testing
- **Code review process**
  - Defined and used correctly (ticket → branch → PR → Vercel review → two teammate approvals → merge).
- **Known bugs/issues and plans to address**
  - Unconfirmed embedding dimension for `syllabus_chunks`
  - Seed data covers real courses/requirements only; no sample students or transcripts yet
  - The repository layer connecting the database to business logic hasn't been started, which is currently blocking the LLM recommendation and toolset from moving past early-stage work.

---

## V. Velocity & Week 6 Planning

### Velocity calculation

Our overall velocity has matched what we expected and planned for. Given our expedited timeline and current team skills, we did a good job at calculating how much we could actually accomplish. Our team velocity during weeks 1–4 really helped start off week 5 implementation strong and with a sound plan to build off of.

### Lessons learned

Setting up all of the external service accounts was more of a hassle than we thought. We are still struggling to figure out the best way to get around the limitations of Vercel's free plan. We're currently restricted to one person who can preview all deployments. This will prove challenging as we get closer to end-to-end testing, where developers will want to test their branch with the frontend before merging it with the `dev` or `main` branch.

### Week 6 plan — Things to complete

- All API calls between the frontend, backend, and database fully functioning and testable
- Seed/sample data inputted into database
- LLM Recommendation/Tool set implemented
- Start and complete repository layer
- Fine-tune UI/UX
- Finish authentication process

### Scope changes

US-04 (schedule export) will be implemented this cycle only if time allows; most likely it will be deferred to the next implementation sprint.

---

## VI. AI Usage

**Backend:** Agents were used to generate backend skeleton, tooling, unit tests, and connections to both LLMs and database tables.

**Frontend:** Claude was used to generate frontend scaffold, CSS styling for UI, unit tests, and commit/push code to GitHub + generate documentation for PRs.
