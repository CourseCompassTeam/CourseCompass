// Builds an iCalendar (.ics) file from a schedule, so the student can
// import it into Google Calendar or any other calendar app. Each planned
// course becomes an all-day event spanning its term.
//
// The file is made in the browser, since schedules aren't saved on the
// backend. Terms without start and end dates are left out, since an event
// needs real dates.

export const CALENDAR_FILE_NAME = 'coursecompass-schedule.ics';

const MAX_LINE_OCTETS = 75;
const encoder = new TextEncoder();

/**
 * @param {import('../../services/scheduleService.js').Schedule} schedule
 * @param {{now?: Date}} options now is the DTSTAMP time (for tests).
 * @returns {{ics: ?string, skippedTerms: string[]}} ics is null when no
 *     term has usable dates. skippedTerms names the terms left out.
 */
export function buildScheduleCalendar(schedule, { now = new Date() } = {}) {
  const events = [];
  const skippedTerms = [];

  for (const term of schedule.terms) {
    const start = parseDate(term.startDate);
    const end = parseDate(term.endDate);
    if (!start || !end || end < start) {
      if (term.items.length > 0) {
        skippedTerms.push(term.termName);
      }
      continue;
    }
    // DTEND is exclusive for all-day events, so end the day after.
    const endExclusive = new Date(end.getTime() + 24 * 60 * 60 * 1000);
    for (const item of term.items) {
      events.push(courseEvent(item, term, start, endExclusive, now));
    }
  }

  if (events.length === 0) {
    return { ics: null, skippedTerms };
  }

  const lines = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//CourseCompass//Schedule Export//EN',
    'CALSCALE:GREGORIAN',
    'METHOD:PUBLISH',
    'X-WR-CALNAME:CourseCompass schedule',
    ...events.flat(),
    'END:VCALENDAR',
  ];
  return {
    ics: lines.map(foldLine).join('\r\n') + '\r\n',
    skippedTerms,
  };
}

/**
 * @param {import('../../services/scheduleService.js').Schedule} schedule
 * @returns {boolean} True if at least one term with courses has dates.
 */
export function hasCalendarDates(schedule) {
  return schedule.terms.some((term) => term.items.length > 0
    && parseDate(term.startDate) && parseDate(term.endDate));
}

function courseEvent(item, term, start, endExclusive, now) {
  const credits = `${item.credits} ${item.credits === 1 ? 'credit' : 'credits'}`;
  // Schedules aren't saved, so the UID comes from the term and course. The
  // same course in the same term keeps its UID across rebuilds, so calendar
  // apps update the event on re-import instead of adding a duplicate.
  const uid = `${term.termName}-${item.code}`.replace(/\s+/g, '-');
  return [
    'BEGIN:VEVENT',
    `UID:${escapeText(uid)}@coursecompass`,
    `DTSTAMP:${formatTimestamp(now)}`,
    `DTSTART;VALUE=DATE:${formatDate(start)}`,
    `DTEND;VALUE=DATE:${formatDate(endExclusive)}`,
    `SUMMARY:${escapeText(`${item.code} ${item.title}`.trim())}`,
    `DESCRIPTION:${escapeText(
      `Planned for ${term.termName}, ${credits}.\n` +
      'Planned by CourseCompass. Course offerings can change, so ' +
      'confirm with your advisor before you register.',
    )}`,
    // An 8-week course shouldn't show the student as busy all day.
    'TRANSP:TRANSPARENT',
    'END:VEVENT',
  ];
}

/**
 * @param {?string} value 'YYYY-MM-DD', optionally followed by a time.
 * @returns {?Date} Midnight UTC on that day, or null if unusable.
 */
function parseDate(value) {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value ?? '');
  if (!match) {
    return null;
  }
  const [, year, month, day] = match.map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  // Rejects dates like 2027-02-30, which Date.UTC rolls into March.
  return date.getUTCDate() === day ? date : null;
}

function formatDate(date) {
  return date.toISOString().slice(0, 10).replaceAll('-', '');
}

function formatTimestamp(date) {
  return date.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '');
}

/** Escapes a TEXT value (RFC 5545 section 3.3.11). */
function escapeText(text) {
  return text
    .replace(/\\/g, '\\\\')
    .replace(/;/g, '\\;')
    .replace(/,/g, '\\,')
    .replace(/\r?\n/g, '\\n');
}

/** Folds a content line at 75 octets (RFC 5545 section 3.1). */
function foldLine(line) {
  const parts = [];
  let current = '';
  let octets = 0;
  // Continuation lines start with a space, which counts toward the limit.
  let limit = MAX_LINE_OCTETS;
  for (const char of line) {
    const size = encoder.encode(char).length;
    if (octets + size > limit) {
      parts.push(current);
      current = '';
      octets = 0;
      limit = MAX_LINE_OCTETS - 1;
    }
    current += char;
    octets += size;
  }
  parts.push(current);
  return parts.join('\r\n ');
}
