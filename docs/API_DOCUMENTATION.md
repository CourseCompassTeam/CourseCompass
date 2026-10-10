# API Documentation

- [1. Endpoint reference](#1-endpoint-reference-requestresponse-formats)
- [2. Authentication requirements](#2-authentication-requirements)
- [3. Example requests](#3-example-requests)
- [4. Error codes and meanings](#4-error-codes-and-meanings)

---

## 1. Endpoint reference (request/response formats)

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Health check |
| `GET` | `/api/info` | Service information |
| `POST` | `/api/v1/query` | Send a student’s question and recent chat history; returns one answer |
| `POST` | `/api/v1/orchestration/route` | Smoke and staging check |

### Request: `POST /api/v1/query`

| Header / field | Type | Required | Description |
| --- | --- | --- | --- |
| `Content-Type` | header | Yes | application / json |
| `Authorization` | header | No | Bearer &lt;Clerk session token&gt; |
| `X-Dev-Student_id` | header | No | Development only (local, staging, test): s seeded test student’s Clerk ID |
| `query` | string | Yes | The student’s question in natural language |
| `questionNumber` | integer | No | Which student question this is in the whole chat |

### Response: `200 OK`

| Field | Type | Description |
| --- | --- | --- |
| `id` | string | Unique message ID |
| `type` | string | Audit, recommendation, or redirect; tells the frontend |
| `content` | object | Shape depends on type |
| `timestamp` | string | ISO 8601 timestamp |

---

## 2. Authentication requirements

- The server decides who is asking, in this order:
  1. Valid Clerk Bearer token, whose `sub` claim is the Clerk user ID
  2. In local, staging, and test environments only, the `X-Dev-Student-Id` header
  3. Otherwise, the request is anonymous, with no student identity, so only program-level answers.
  - The client never names a student in the request body, and the student ID is not sent to the LLM.
- Send the token as `Authorization: Bearer <Clerk session JWT>`. It is checked with an RS256 signature and 10 seconds of clock leeway against a key from `CLERK_JWT_KEY` or the JWKS address (`CLERK_JWKS_URL`, or derived from `CLERK_PUBLISHABLE_KEY`, which the live service sets).
- A Bearer token that is present but invalid or expired is rejected with `401`. In local, staging, and test environments, a value that is not JWT-shaped (three dot-separated parts) is ignored rather than rejected; in any other environment, every Bearer value is verified.
- Browsers may only call the API from origins in `CORS_ORIGINS`, which excludes Vercel preview URLs. Cloud Run allows unauthenticated invocation, so access control is entirely the app's Clerk check.

---

## 3. Example requests

Set `API_URL` to the Cloud Run URL. Anonymous request (program-level answer):

```bash
curl -X POST $API_URL/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Which courses are offered in 2026 FALL 8W2?", "history": [], "questionNumber": 1}'
```

Signed-in student (personalized audit):

```bash
curl -X POST $API_URL/api/v1/query \
  -H "Content-Type: application/json" -H "Authorization: Bearer $CLERK_TOKEN" \
  -d '{"query": "What do I still need to graduate?", "history": [], "questionNumber": 1}'
```

Development only (local, staging, test): act as a seeded student without a token:

```bash
curl -X POST $API_URL/api/v1/query -H "Content-Type: application/json" \
  -H "X-Dev-Student-Id: <seeded student's Clerk ID>" -d '{"query": "What do I still need to graduate?"}'
```

Example response (illustrative: the structure was observed in a live test; the values come from the seeded "nearly done" test student):

```json
{
  "id": "b7f3c1e2-5a1d-4c8e-9f20-3d6a8e1b7c44",
  "type": "audit",
  "content": {
    "creditsRemaining": 6,
    "requirementsMet": false,
    "missingCourses": ["MSSE 692", "MSSE 696"],
    "message": "You have 6 credits remaining. Your degree requirements are not yet met. You are missing MSSE 692 and MSSE 696."
  },
  "timestamp": "2026-10-04T18:36:42.366462+00:00"
}
```

---

## 4. Error codes and meanings

Errors raised by the app share one envelope, for example, a model rate limit:

```json
{ "error": { "code": "TOO_MANY_REQUESTS", "message": "The advising model is temporarily busy. Try again in a moment.", "details": {} } }
```

| Status | code | Meaning and cause |
| --- | --- | --- |
| `401` | `UNAUTHORIZED` | Bearer token invalid or expired (`details.reason` names the failure), or token verification is not configured on the server |
| `422` | (FastAPI default) | The body does not match the schema, for example `query` is missing. FastAPI's own `{"detail": [...]}` format is used, not the envelope above |
| `404` | `NOT_FOUND` | The student asked about a course code that does not exist; message "Course X was not found." |
| `429` | `TOO_MANY_REQUESTS` | The LLM provider is rate-limiting; retry in a moment |
| `500` | `INTERNAL_ERROR` | Unexpected failure; message "An unexpected error occurred." and `details.type` holds the exception class name |
| `501` | `NOT_IMPLEMENTED` | The LLM provider is not configured: `LLM_PROVIDER=vertex` and `GCP_PROJECT_ID` must be set |
