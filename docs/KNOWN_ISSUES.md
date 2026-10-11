# Known Issues & Limitations

- [1. Current bugs (from QA report)](#1-current-bugs-from-qa-report)
- [2. Feature limitations](#2-feature-limitations)
- [3. Workarounds if available](#3-workarounds-if-available)
- [4. Future enhancements planned](#4-future-enhancements-planned)

---

## 1. Current bugs (from QA report)

### P2

- **Limited chat history:** All chats only pass along the last 3-4 messages, but that is a feature that we limited to provide the performance needed for the system
- **Follow-up question hiding summary:** A degree audit follow-up question shows the audit again while hiding the new AI summary that answers the question
- **Stubbed resources:** As most of our student data contain mock user information, we also stubbed the advising and career services resources and contact information
- **Course found by course code only:** Courses are found only by full code. “What is the software architecture course about?” returns 404 Not Found

---

## 2. Feature limitations

- Schedule building and .ics export (US-04, a Could Have) was not built. The `build_schedule` tool reads saved schedules, but nothing creates them, so it always reports that none was found
- Courses can only be looked up by code (for example MSSE 635), not by name
- Data covers the MSSE program only. Term offerings run only through 2027 SPR 8W2 (May 2, 2027); after that, the offerings tool reports that none are loaded
- Nothing is saved between visits: the chat clears on refresh and milestone checklists cannot be ticked off
- No CI, linter, or formatter is configured, so tests run by hand
- Transcript upload and self-entered courses were not built, so only the two seeded students get real audits

---

## 3. Workarounds if available

### Limited chat history

- **Impact:** User cannot follow up on the same question as asked 3 chat messages ago due to limited history. While it will show in the user interface, not all messages are passed in the query.
- **Workaround:** Keep conversations limited or continue to follow up in 4 questions max

### Follow-up question hiding summary

- **Impact:** User does not immediately see the AI summary without an extra step of clicking on the dropdown
- **Workaround:** User can just click on the clearly labeled dropdown tab if they need a deeper explanation of the response

### Stubbed resources

- **Impact:** User cannot access true advising or career service resources
- **Workaround:** As this is a prototype, there is no workaround to direct students to the actual resources. The user can only find those resources themselves, but they can have some course questions answered by the chat if needed.

### Course found by course code only

- **Impact:** The user won’t be able to receive a response about a course unless they provide the course code
- **Workaround:** The user will have to ask about a course by code, or wait until the course code and name appear together in the chat history, then reference the course by name only since the LLM will have a reference to go off of.

---

## 4. Future enhancements planned

- Build transcript upload so any student gets a real audit
- Add CI that runs both test suites plus linting on pull request
- Replace the placeholder advising and Career Services contacts with real data
- Tune response time to meet the 5-second target
- Implement schedule building and .ics export
