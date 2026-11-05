import { describe, expect, it } from 'vitest';

import { buildScheduleCalendar, hasCalendarDates } from './scheduleCalendar.js';

const NOW = new Date('2026-11-04T18:30:05.123Z');

function term(name, startDate, endDate, items) {
  return { termName: name, startDate, endDate, items };
}

function item(code, title, credits = 3) {
  return { courseId: code, code, title, credits };
}

const SCHEDULE = {
  terms: [
    term('2027 SPR 8W1', '2027-01-11', '2027-03-07', [
      item('MSSE 601', 'Software Engineering Fundamentals'),
      item('MSSE 603', 'Leadership, Teams; and Ethics'),
    ]),
    term('2027 SUM 8W1', null, null, [item('MSSE 696', 'Practicum')]),
  ],
};

/** Unfolds continuation lines and splits on CRLF. */
function lines(ics) {
  return ics.replace(/\r\n /g, '').split('\r\n');
}

describe('buildScheduleCalendar', () => {
  it('makes an all-day event per course in each dated term', () => {
    const { ics, skippedTerms } = buildScheduleCalendar(SCHEDULE, { now: NOW });
    const all = lines(ics);

    expect(all[0]).toBe('BEGIN:VCALENDAR');
    expect(all.at(-2)).toBe('END:VCALENDAR');
    expect(all.at(-1)).toBe('');
    expect(all.filter((line) => line === 'BEGIN:VEVENT')).toHaveLength(2);
    expect(all).toContain('UID:2027-SPR-8W1-MSSE-601@coursecompass');
    expect(all).toContain('DTSTAMP:20261104T183005Z');
    expect(all).toContain('DTSTART;VALUE=DATE:20270111');
    // DTEND is exclusive: the day after the term's last day.
    expect(all).toContain('DTEND;VALUE=DATE:20270308');
    expect(all).toContain(
      'SUMMARY:MSSE 601 Software Engineering Fundamentals',
    );
    expect(skippedTerms).toEqual(['2027 SUM 8W1']);
  });

  it('escapes commas, semicolons, and newlines in text', () => {
    const { ics } = buildScheduleCalendar(SCHEDULE, { now: NOW });
    const all = lines(ics);

    expect(all).toContain(
      'SUMMARY:MSSE 603 Leadership\\, Teams\\; and Ethics',
    );
    expect(all.find((line) => line.startsWith('DESCRIPTION:')))
      .toMatch(/^DESCRIPTION:Planned for 2027 SPR 8W1\\, 3 credits\.\\n/);
  });

  it('folds lines longer than 75 octets', () => {
    const { ics } = buildScheduleCalendar(SCHEDULE, { now: NOW });
    const encoder = new TextEncoder();

    for (const line of ics.split('\r\n')) {
      expect(encoder.encode(line).length).toBeLessThanOrEqual(75);
    }
    expect(ics).toMatch(/\r\n /);
  });

  it('does not split a multi-byte character when folding', () => {
    const longTitle = 'Café ' + 'é'.repeat(80);
    const schedule = {
      terms: [term('T', '2027-01-11', '2027-03-07',
        [item('MSSE 601', longTitle)])],
    };
    const { ics } = buildScheduleCalendar(schedule, { now: NOW });

    expect(lines(ics)).toContain(`SUMMARY:MSSE 601 ${longTitle}`);
  });

  it('returns null when no term has usable dates', () => {
    const schedule = {
      terms: [
        term('A', null, null, [item('MSSE 601', 'X')]),
        term('B', '2027-02-30', '2027-03-07', [item('MSSE 603', 'Y')]),
        term('C', '2027-03-07', '2027-01-11', [item('MSSE 610', 'Z')]),
      ],
    };

    expect(buildScheduleCalendar(schedule, { now: NOW })).toEqual({
      ics: null,
      skippedTerms: ['A', 'B', 'C'],
    });
  });

  it('accepts dates with a time part', () => {
    const schedule = {
      terms: [term('A', '2027-01-11T00:00:00', '2027-03-07T00:00:00',
        [item('MSSE 601', 'X')])],
    };
    const { ics } = buildScheduleCalendar(schedule, { now: NOW });

    expect(lines(ics)).toContain('DTSTART;VALUE=DATE:20270111');
  });

  it('gives the same course the same UID across rebuilds', () => {
    const first = buildScheduleCalendar(SCHEDULE, { now: NOW }).ics;
    const second = buildScheduleCalendar(structuredClone(SCHEDULE),
      { now: new Date('2026-12-01T00:00:00Z') }).ics;
    const uids = (ics) => lines(ics).filter((line) => line.startsWith('UID:'));

    expect(uids(second)).toEqual(uids(first));
  });
});

describe('hasCalendarDates', () => {
  it('is true when a term with courses has dates', () => {
    expect(hasCalendarDates(SCHEDULE)).toBe(true);
  });

  it('ignores dated terms with no courses', () => {
    expect(hasCalendarDates({
      terms: [
        term('A', '2027-01-11', '2027-03-07', []),
        term('B', null, null, [item('MSSE 601', 'X')]),
      ],
    })).toBe(false);
  });
});
