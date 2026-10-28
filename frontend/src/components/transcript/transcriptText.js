// Display text for the transcript upload dialog.

import { getErrorHint } from '../renderers/errorHints.js';

// Codes whose chat hint doesn't fit an upload. The rest fall back to
// getErrorHint().
const UPLOAD_HINTS = {
  BAD_REQUEST:
    'Make sure you uploaded your transcript as a PDF, other file types are not supported. ' +
    'Your stored courses were not changed.',
  NOT_FOUND:
    'We couldn\'t find a student record for your account. Your advisor ' +
    'can help get you set up.',
  NOT_IMPLEMENTED: 'Transcript upload isn\'t available right now.',
};

const STATUS_LABELS = {
  completed: 'Completed',
  in_progress: 'In progress',
  planned: 'Planned',
};

/**
 * @param {string|undefined} code Error code, e.g. 'BAD_REQUEST'.
 * @returns {string} A hint the student can act on.
 */
export function getUploadErrorHint(code) {
  return UPLOAD_HINTS[code] ?? getErrorHint(code);
}

/**
 * @param {string} status Transcript status, e.g. 'in_progress'.
 * @returns {string} The label to show, e.g. 'In progress'.
 */
export function formatCourseStatus(status) {
  return STATUS_LABELS[status] ?? status;
}

/**
 * @param {number} count Number of courses.
 * @returns {string} For example '1 course' or '3 courses'.
 */
export function courseCountLabel(count) {
  return `${count} ${count === 1 ? 'course' : 'courses'}`;
}
