import { describe, expect, it } from 'vitest';

import { getErrorHint } from '../renderers/errorHints.js';
import {
  courseCountLabel,
  formatCourseStatus,
  getUploadErrorHint,
} from './transcriptText.js';

describe('getUploadErrorHint', () => {
  it('uses upload-specific hints where the chat hint does not fit', () => {
    expect(getUploadErrorHint('BAD_REQUEST')).toMatch(/PDF/);
    expect(getUploadErrorHint('NOT_FOUND')).toMatch(/student record/);
  });

  it('falls back to the chat hints', () => {
    expect(getUploadErrorHint('UNAUTHORIZED'))
      .toBe(getErrorHint('UNAUTHORIZED'));
    expect(getUploadErrorHint(undefined)).toBe(getErrorHint(undefined));
  });
});

describe('formatCourseStatus', () => {
  it('labels known statuses', () => {
    expect(formatCourseStatus('in_progress')).toBe('In progress');
    expect(formatCourseStatus('completed')).toBe('Completed');
  });

  it('passes unknown statuses through', () => {
    expect(formatCourseStatus('withdrawn')).toBe('withdrawn');
  });
});

describe('courseCountLabel', () => {
  it.each([
    [0, '0 courses'],
    [1, '1 course'],
    [3, '3 courses'],
  ])('labels %i as "%s"', (count, label) => {
    expect(courseCountLabel(count)).toBe(label);
  });
});
