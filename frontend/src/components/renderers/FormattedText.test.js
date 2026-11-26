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
      { kind: 'list', ordered: false, items: ['Week 1: Intro', 'Week 2: Patterns'] },
    ]);
  });

  it('turns "1." lines into a numbered list', () => {
    const text = 'Still required:\n1. MSSE 692 Practicum I\n2. MSSE 696 Practicum II';
    expect(toBlocks(text)).toEqual([
      { kind: 'paragraph', text: 'Still required:' },
      {
        kind: 'list',
        ordered: true,
        start: 1,
        items: ['MSSE 692 Practicum I', 'MSSE 696 Practicum II'],
      },
    ]);
  });

  it('keeps the first number and splits numbered from bulleted lines', () => {
    const text = '3) Third\n4) Fourth\n* Note';
    expect(toBlocks(text)).toEqual([
      { kind: 'list', ordered: true, start: 3, items: ['Third', 'Fourth'] },
      { kind: 'list', ordered: false, items: ['Note'] },
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
