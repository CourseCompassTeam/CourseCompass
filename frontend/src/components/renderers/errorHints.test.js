import { describe, expect, it } from 'vitest';

import { getErrorHint } from './errorHints.js';

describe('getErrorHint', () => {
  it('does not suggest retrying when a course is not found', () => {
    const hint = getErrorHint('NOT_FOUND');
    expect(hint).toMatch(/course code/);
    expect(hint).not.toMatch(/try again in a moment/);
  });

  it('asks the student to sign in again on UNAUTHORIZED', () => {
    expect(getErrorHint('UNAUTHORIZED')).toMatch(/sign in again/);
  });

  it('points to the connection on NETWORK_ERROR', () => {
    expect(getErrorHint('NETWORK_ERROR')).toMatch(/internet connection/);
  });

  it.each([undefined, 'INTERNAL_ERROR', 'SOMETHING_NEW'])(
    'falls back to a retry hint for %s',
    (code) => {
      expect(getErrorHint(code)).toMatch(/try again in a moment/);
    },
  );
});
