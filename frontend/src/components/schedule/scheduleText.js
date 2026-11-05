// Display text for the schedule dialog.

import { getErrorHint } from '../renderers/errorHints.js';

// Codes whose chat hint doesn't fit the schedule. The rest fall back to
// getErrorHint().
const SCHEDULE_HINTS = {
  BAD_REQUEST: 'Pick between 1 and 6 courses per term, then try again.',
  NOT_FOUND:
    'We couldn\'t find a student record for your account. Your advisor ' +
    'can help get you set up.',
  NOT_IMPLEMENTED: 'The schedule builder isn\'t available right now.',
};

/**
 * @param {string|undefined} code Error code, e.g. 'NOT_FOUND'.
 * @returns {string} A hint the student can act on.
 */
export function getScheduleErrorHint(code) {
  return SCHEDULE_HINTS[code] ?? getErrorHint(code);
}

/**
 * @param {number} count Number of credits.
 * @returns {string} For example '1 credit' or '6 credits'.
 */
export function creditLabel(count) {
  return `${count} ${count === 1 ? 'credit' : 'credits'}`;
}

/**
 * @param {Array<{credits: number}>} items Courses in one term.
 * @returns {number} Total credits.
 */
export function totalCredits(items) {
  return items.reduce((sum, item) => sum + (Number(item.credits) || 0), 0);
}

const dateFormat = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
  timeZone: 'UTC',
});

/**
 * @param {?string} startDate 'YYYY-MM-DD'.
 * @param {?string} endDate 'YYYY-MM-DD'.
 * @returns {string} For example 'Jan 11 – Mar 7, 2027', or '' when
 *     either date is missing or invalid.
 */
export function formatTermDates(startDate, endDate) {
  const start = new Date(`${startDate?.slice(0, 10)}T00:00:00Z`);
  const end = new Date(`${endDate?.slice(0, 10)}T00:00:00Z`);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
    return '';
  }
  return dateFormat.formatRange(start, end);
}
