import { describe, expect, it } from 'vitest';

import { getErrorHint } from '../renderers/errorHints.js';
import {
  creditLabel,
  formatTermDates,
  getScheduleErrorHint,
  totalCredits,
} from './scheduleText.js';

describe('getScheduleErrorHint', () => {
  it('explains the courses-per-term range on BAD_REQUEST', () => {
    expect(getScheduleErrorHint('BAD_REQUEST')).toMatch(/1 and 6/);
  });

  it('points to the advisor on NOT_FOUND', () => {
    expect(getScheduleErrorHint('NOT_FOUND')).toMatch(/student record/);
  });

  it('falls back to the chat hints', () => {
    expect(getScheduleErrorHint('UNAUTHORIZED'))
      .toBe(getErrorHint('UNAUTHORIZED'));
  });
});

describe('creditLabel', () => {
  it.each([[1, '1 credit'], [6, '6 credits'], [0, '0 credits']])(
    '%i -> %s', (count, label) => {
      expect(creditLabel(count)).toBe(label);
    },
  );
});

describe('totalCredits', () => {
  it('adds credits and ignores missing values', () => {
    expect(totalCredits([{ credits: 3 }, { credits: 3 }, {}])).toBe(6);
  });
});

describe('formatTermDates', () => {
  it('formats a date range in UTC', () => {
    expect(formatTermDates('2027-01-11', '2027-03-07'))
      .toMatch(/^Jan 11\s*–\s*Mar 7, 2027$/);
  });

  it('is empty when a date is missing', () => {
    expect(formatTermDates(null, '2027-03-07')).toBe('');
    expect(formatTermDates('2027-01-11', undefined)).toBe('');
  });
});
