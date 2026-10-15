# Architecture Decision Records

## Table of Contents

- [ADR-001: Overall Architecture Style](#adr-001-overall-architecture-style)
- [ADR-002: Database & Data Storage Strategy](#adr-002-database--data-storage-strategy)
- [ADR-003: Infrastructure and Hosting Platform](#adr-003-infrastructure-and-hosting-platform)
- [ADR-004: Integration Approach](#adr-004-integration-approach)

---

## ADR-001: Overall Architecture Style

**Status:** Accepted

**Context:**

CourseCompass must give reliable answers on prerequisites and credits (QA-02) while also supporting flexible, LLM-driven syllabus search. Prerequisite/logic must be hallucination-free given the real cost of a wrong answer, but the team has only 3 people, 2 weeks of implementation time, and a rubric that expects clear separation of concerns and modifiability.

**Decision:**

Build CourseCompass as a modular monolith.

**Consequences:**

Positive:

- Real internal separation of concerns without distributed system overhead
- Zero hallucination risk on academic answers

Negative:

- Defers the distributed-system question rather than avoiding it
- No independent scaling per component

**Alternatives Considered:**

- Full microservices: Rejected. Coordination overhead isn't worth it for 3 people / 2 weeks

---

## ADR-002: Database & Data Storage Strategy

**Status:** Accepted

**Context:**

CourseCompass needs to store and query structured academic data (courses, prerequisites, student progress, etc.) and answer questions within its scope with guaranteed accuracy (required by QA-02) and low latency (called out by QA-01). Both stakeholder interviews flagged a major risk of hallucinations by AI, so the data layer needs to support exact, auditable answers.

**Decision:**

PostgreSQL, accessed exclusively by a repository layer. Database schema and repository interface designed to allow for easy integration of pgvector, actual implementation of pgvector will be this iteration if time permits.

**Consequences:**

Positive:

- One database technology for the whole application
- Structured queries are exact and auditable
- Modifiable to allow for expansion of course catalog and new data sources

Negative:

- If usage scales significantly, a single PostgreSQL instance may eventually need read replicas or caching. Not a concern at the current expected usage, but a known limitation

**Alternatives Considered:**

- NoSQL (MongoDB) for course/student data: Rejected. This non-relational database would not work well with the inherently relational data our application will have

---

## ADR-003: Infrastructure and Hosting Platform

**Status:** Accepted

**Context:**

CourseCompass needs a hosting environment that meets our users' availability needs and enables deployability for the distributed team. In order to meet all 4 of our quality attributes - Performance, Reliability, Security, and Modifiability - we need to decide on our hosting platform, which is the foundation for achieving this within our software. We are also limited by budget and our team's skill set for managing and deploying the software.

**Decision:**

Manage containerized serverless via Google Cloud Run for our backend hosting, Cloud SQL for relational and vector persistence, and Vercel to host our frontend.

**Consequences:**

Positive:

- The free tier lets us stay within our limited budget while still getting the performance, availability, reliability, and scalability of cloud computing.
- Managed serverless computing gives us enough control without the workload of provisioning servers or installing reporting software.
- Cloud computing lets our distributed team contribute to the software no matter the location.
- Integration with other GCP services: Using Cloud Run with Cloud SQL provides a secure, native connection between the two services.

Negative:

- Cold Starts: Serverless containers scaling from zero feature a delay when starting up and introduce higher latency.
- Stateless Constraint: Because containers cold-start, memory, data, and state must be stored in our PostgreSQL database.

**Alternatives Considered:**

- Containerized orchestration: Requires too much provisioning and monitoring given our current skill set, timeline, and project scope.
- Virtual machines: Requires too much setup, and the team does not have enough experience to scale such machines as needed.

---

## ADR-004: Integration Approach

**Status:** Accepted

**Context:**

CourseCompass has a decoupled React frontend and a Python/FastAPI backend that need to communicate, plus internal communication between the orchestration/agent layer, domain services, and data access layer. The system has moderate, predictable traffic (individual students submitting one query at a time), a modular monolith architecture, and a very short timeline with limited team experience.

**Decision:**

Synchronous REST APIs (JSON over HTTP) for frontend - backend communication, direct function/method calls for internal component communication within the backend monolith.

**Consequences:**

Positive:

- REST over HTTP is simple to implement, test, and debug, and is the most well-known technology amongst the team
- A student query gets an immediate, synchronous response (expected when interacting with a chatbot), and satisfies the performance requirement (QA-01)

Negative:

- REST is not a great fit if the system later needs to support long-running or background tasks such as bulk re-ingestion of entire course catalogs
- No built-in retry/replay mechanism if a downstream call fails partway through
- Any latency in the backend reflects in the frontend while the user waits for a response

**Alternatives Considered:**

- Message queue / event-driven architecture: Rejected for this first iteration. Adds infrastructure and operational complexity that is not needed at this scale, especially when all interactions are a simple request/response
