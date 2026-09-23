// HTTP access to the backend REST API (/api/v1/...).
//
// ChatService depends on the APIClient interface, not on RestAPIClient,
// so tests can pass in a mock (Dependency Inversion). APIClient exposes
// only post(), the one method ChatService needs (Interface Segregation).

/**
 * @interface
 * APIClient: post(path, body) -> Promise<object>
 */

export class RestAPIClient {
  /**
   * @param {string} baseUrl Backend base URL (VITE_API_BASE_URL).
   */
  constructor(baseUrl) {
    // TODO
  }

  /**
   * Sends a JSON POST request to the backend.
   * @param {string} path For example '/api/v1/query'.
   * @param {object} body Request body.
   * @returns {Promise<object>} The parsed JSON response.
   */
  async post(path, body) {
    // TODO
  }
}
