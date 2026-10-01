// ChatService orchestrates the query flow from the Chat Sequence Diagram:
// get a session token, POST the query, classify the response, and return
// a Message. It knows nothing about rendering.

import { MessageType, createMessage } from '../models/message.js';

export const QUERY_ENDPOINT = '/api/v1/query';

const RESPONSE_TYPES = new Set([
  MessageType.AUDIT,
  MessageType.RECOMMENDATION,
  MessageType.REDIRECT,
]);

export class ChatService {
  /**
   * @param {{post: Function}} apiClient Any APIClient implementation.
   * @param {{getSessionToken: Function, getUserId: Function}} authService
   *     Any AuthService implementation.
   */
  constructor(apiClient, authService) {
    this._apiClient = apiClient;
    this._authService = authService;
  }

  /**
   * Sends a student's question to the backend.
   * @param {string} query The student's natural-language question.
   * @param {Array<{role: string, text: string}>} history Earlier exchanges,
   *     oldest first (see models/chatHistory.js).
   * @param {number} questionNumber This question's place in the chat,
   *     from 1. The backend uses it to offer milestones on the 3rd and
   *     4th question of every four.
   * @returns {Promise<object>} The response as a Message.
   * @throws {ApiError} If the request fails.
   */
  async sendQuery(query, history = [], questionNumber = 1) {
    const token = await this._authService.getSessionToken();
    const raw = await this._apiClient.post(
      QUERY_ENDPOINT,
      { query, history, questionNumber },
      token,
    );
    return createMessage({
      id: raw?.id,
      type: this.#classifyResponseType(raw),
      content: raw?.content ?? {},
      timestamp: raw?.timestamp,
    });
  }

  /**
   * Picks the MessageType for a raw backend response.
   *
   * An unrecognized type is treated as a redirect, so unexpected content is
   * never shown to the student as fact (QA-02).
   */
  #classifyResponseType(raw) {
    return RESPONSE_TYPES.has(raw?.type) ? raw.type : MessageType.REDIRECT;
  }
}
