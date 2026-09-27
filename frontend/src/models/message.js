// Message model from the Chat Class Diagram:
// { id: string, type: MessageType, content: object, timestamp: Date }

export const MessageType = Object.freeze({
  // Response types returned by POST /api/v1/query.
  AUDIT: 'audit',
  RECOMMENDATION: 'recommendation',
  REDIRECT: 'redirect',

  // Frontend-only types, so every chat bubble goes through a renderer.
  QUERY: 'query', // The student's own question.
  ERROR: 'error', // The request failed (network, auth, server error).
});

/**
 * Creates a Message, filling in a missing id or timestamp.
 * @param {{id?: string, type: string, content?: object,
 *     timestamp?: string|Date}} fields
 * @returns {{id: string, type: string, content: object, timestamp: Date}}
 */
export function createMessage({ id, type, content = {}, timestamp }) {
  return {
    id: id ?? crypto.randomUUID(),
    type,
    content,
    timestamp: timestamp ? new Date(timestamp) : new Date(),
  };
}
