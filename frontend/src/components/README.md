# Components

The chat UI is built in **SCRUM-9**. The Detailed Design describes it as:

- `ChatContainer` re-renders when ChatService's message list changes (Observer).
- `ChatService` orchestrates the query flow through `APIClient`.
- One `MessageRenderer` per response type: `audit`, `recommendation`, and
  `redirect` (Strategy). A new response type means adding a renderer without
  changing ChatContainer or ChatService.
