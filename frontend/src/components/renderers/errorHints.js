// What to tell the student after an error, based on the error code from
// the backend's error envelope (or RestAPIClient's NETWORK_ERROR).
// Only suggest retrying when retrying can actually help.

const HINTS = {
  BAD_REQUEST: 'Try rephrasing your question.',
  NOT_FOUND:
    'Check the course code or name and ask again. If it still isn\'t ' +
    'found, your advisor can help.',
  UNPROCESSABLE_CONTENT:
    'I couldn\'t confirm that against the course catalog. Please check ' +
    'with your advisor.',
  UNAUTHORIZED: 'Your session may have expired. Please sign in again.',
  FORBIDDEN: 'You don\'t have access to that information.',
  NOT_IMPLEMENTED: 'That feature isn\'t available yet.',
  TOO_MANY_REQUESTS: 'You\'re sending questions quickly. Wait a minute, ' +
    'then try again.',
  NETWORK_ERROR: 'Check your internet connection, then try again.',
};

const DEFAULT_HINT = 'Something went wrong on our end. Please try again ' +
  'in a moment.';

/**
 * @param {string|undefined} code Error code, e.g. 'NOT_FOUND'.
 * @returns {string} A hint the student can act on.
 */
export function getErrorHint(code) {
  return HINTS[code] ?? DEFAULT_HINT;
}
