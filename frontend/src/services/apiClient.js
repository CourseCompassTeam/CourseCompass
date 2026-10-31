// HTTP access to the backend REST API (/api/v1/...).
//
// ChatService depends on the APIClient interface, not on RestAPIClient,
// so tests and local development can pass in another implementation
// (Dependency Inversion). APIClient exposes only the methods the services
// need (Interface Segregation).
//
// APIClient interface:
//   post(endpoint: string, body: object, token: string) -> Promise<object>
//   postFile(endpoint: string, file: File, token: string,
//            headers?: object) -> Promise<object>

/** An error response, parsed from the backend's standard error envelope. */
export class ApiError extends Error {
  /**
   * @param {number} status HTTP status (0 if the server was unreachable).
   * @param {string} code Error code, e.g. 'UNAUTHORIZED'.
   * @param {string} message Human-readable message.
   * @param {object} details Extra information from the backend.
   */
  constructor(status, code, message, details = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export class RestAPIClient {
  /**
   * @param {string} baseUrl Backend base URL (VITE_API_BASE_URL).
   */
  constructor(baseUrl = '') {
    this.baseUrl = baseUrl.replace(/\/+$/, '');
  }

  /**
   * Sends a JSON POST request to the backend.
   * @param {string} endpoint For example '/api/v1/query'.
   * @param {object} body Request body.
   * @param {string} token Session token, sent as a Bearer token.
   * @returns {Promise<object>} The parsed JSON response.
   * @throws {ApiError} If the request fails or returns an error status.
   */
  async post(endpoint, body, token) {
    return this.#send(endpoint, {
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }, token);
  }

  /**
   * Uploads a file as multipart/form-data, in the form field 'file'.
   * Content-Type is left unset so the browser adds the boundary.
   * @param {string} endpoint For example '/api/v1/transcript/upload'.
   * @param {File} file The file to upload.
   * @param {string} token Session token, sent as a Bearer token.
   * @param {object} headers Extra request headers.
   * @returns {Promise<object>} The parsed JSON response.
   * @throws {ApiError} If the request fails or returns an error status.
   */
  async postFile(endpoint, file, token, headers = {}) {
    const formData = new FormData();
    formData.append('file', file);
    return this.#send(endpoint, { headers: { ...headers }, body: formData },
      token);
  }

  async #send(endpoint, { headers, body }, token) {
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    let response;
    try {
      response = await fetch(this.baseUrl + endpoint, {
        method: 'POST',
        headers,
        body,
      });
    } catch {
      throw new ApiError(0, 'NETWORK_ERROR', 'Could not reach the server.');
    }

    const data = await response.json().catch(() => null);
    if (!response.ok) {
      const error = data?.error ?? {};
      throw new ApiError(
        response.status,
        error.code ?? 'INTERNAL_ERROR',
        error.message ?? `Request failed with status ${response.status}.`,
        error.details ?? {},
      );
    }
    return data;
  }
}
