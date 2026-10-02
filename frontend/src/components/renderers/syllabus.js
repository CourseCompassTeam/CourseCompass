// Reads the stored syllabus text into sections for the syllabus view.
//
// The backend sends each course's syllabus as plain text in this shape:
//   MSSE-635 Software Architecture and Design. <overview sentences>
//   Course objectives: <sentence>. <sentence>.
//   Weekly topics: Week 1, <topic>. Week 2, <topic>. ...
// Building the view from this stored text (not the AI's wording) keeps the
// weekly list complete and in order.

const OBJECTIVES_PREFIX = /^course objectives:\s*/i;
const WEEKS_PREFIX = /^weekly topics:\s*/i;
const TITLE_PREFIX = /^[A-Z]{2,5}-?\s?\d{3}\s[^.]*\.\s*/;
const WEEK_PATTERN = /week\s+(\d+),\s*([^.]+)\./gi;

/**
 * @param {string} text The course's syllabusText.
 * @returns {?{overview: string, objectives: string[],
 *     weeks: Array<{week: number, topic: string}>}} The sections, or null
 *     if no weekly topics were found (the caller then falls back).
 */
export function parseSyllabus(text) {
  if (typeof text !== 'string' || !text.trim()) {
    return null;
  }

  let overview = '';
  let objectives = [];
  let weeks = [];
  for (const rawLine of text.split('\n')) {
    const line = rawLine.trim();
    if (OBJECTIVES_PREFIX.test(line)) {
      objectives = splitSentences(line.replace(OBJECTIVES_PREFIX, ''));
    } else if (WEEKS_PREFIX.test(line)) {
      weeks = [...line.matchAll(WEEK_PATTERN)].map((match) => ({
        week: Number(match[1]),
        topic: capitalize(match[2].trim()),
      }));
    } else if (line && !overview) {
      overview = line.replace(TITLE_PREFIX, '');
    }
  }

  return weeks.length > 0 ? { overview, objectives, weeks } : null;
}

function splitSentences(text) {
  return text
    .split(/\.\s+|\.$/)
    .map((sentence) => sentence.trim())
    .filter(Boolean)
    .map(capitalize);
}

function capitalize(text) {
  return text.charAt(0).toUpperCase() + text.slice(1);
}
