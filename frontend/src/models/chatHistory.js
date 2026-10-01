// Builds the short conversation history sent with each question, so the
// backend can understand follow-ups like "what are its prerequisites?".
//
// Shape agreed with the backend team:
//   history: [{ role: 'student' | 'assistant', text: string }, ...]
// Oldest first, current question not included, at most 3 exchanges.

import { MessageType } from './message.js';

export const MAX_HISTORY_EXCHANGES = 3;

// Keeps a single long reply from bloating every request.
export const MAX_HISTORY_TEXT_LENGTH = 1000;

const ANSWER_TYPES = new Set([
  MessageType.AUDIT,
  MessageType.RECOMMENDATION,
  MessageType.REDIRECT,
]);

/**
 * Turns the chat so far into the history for the next request.
 *
 * Only complete exchanges are kept: a student question followed directly by
 * an answer that has text. Questions that ended in an error are dropped, so
 * roles always alternate student, assistant, student, ...
 *
 * @param {Array<{type: string, content: object}>} messages The conversation
 *     before the new question, oldest first.
 * @returns {Array<{role: string, text: string}>}
 */
export function buildHistory(messages) {
  const exchanges = [];
  for (let i = 0; i < messages.length - 1; i += 1) {
    const question = messages[i];
    const answer = messages[i + 1];
    if (question.type !== MessageType.QUERY || !ANSWER_TYPES.has(answer.type)) {
      continue;
    }
    const questionText = clip(question.content?.text);
    const answerText = clip(answer.content?.message);
    if (questionText && answerText) {
      exchanges.push([
        { role: 'student', text: questionText },
        { role: 'assistant', text: answerText },
      ]);
    }
  }
  return exchanges.slice(-MAX_HISTORY_EXCHANGES).flat();
}

function clip(text) {
  if (typeof text !== 'string') {
    return '';
  }
  const trimmed = text.trim();
  return trimmed.length > MAX_HISTORY_TEXT_LENGTH
    ? trimmed.slice(0, MAX_HISTORY_TEXT_LENGTH)
    : trimmed;
}
