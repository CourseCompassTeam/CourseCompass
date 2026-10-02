import { describe, expect, it } from 'vitest';

import { toBlocks } from './FormattedText.jsx';

describe('toBlocks', () => {
  it('keeps paragraphs separated by blank lines', () => {
    expect(toBlocks('First paragraph.\n\nSecond paragraph.')).toEqual([
      { kind: 'paragraph', text: 'First paragraph.' },
      { kind: 'paragraph', text: 'Second paragraph.' },
    ]);
  });

  it('turns "*" lines into a list', () => {
    const text = 'The weekly topics are:\n*   Week 1: Intro\n*   Week 2: Patterns';
    expect(toBlocks(text)).toEqual([
      { kind: 'paragraph', text: 'The weekly topics are:' },
      { kind: 'list', items: ['Week 1: Intro', 'Week 2: Patterns'] },
    ]);
  });

  it('treats plain text as one paragraph', () => {
    expect(toBlocks('Just one sentence.')).toEqual([
      { kind: 'paragraph', text: 'Just one sentence.' },
    ]);
  });

  it('handles missing text', () => {
    expect(toBlocks(undefined)).toEqual([]);
  });
});
