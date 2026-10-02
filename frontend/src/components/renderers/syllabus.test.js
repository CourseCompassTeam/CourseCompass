import { describe, expect, it } from 'vitest';

import { parseSyllabus } from './syllabus.js';

const SYLLABUS =
  'MSSE-635 Software Architecture and Design. This online course explores ' +
  'architectural patterns. Students learn to make architectural decisions.\n' +
  'Course objectives: design software architectures. Evaluate and select ' +
  'appropriate architectural patterns.\n' +
  'Weekly topics: Week 1, architectural thinking and quality attributes. ' +
  'Week 2, architectural patterns and styles. Week 7, architecture ' +
  'documentation and ADRs.';

describe('parseSyllabus', () => {
  it('splits the stored text into overview, objectives, and weeks', () => {
    const syllabus = parseSyllabus(SYLLABUS);

    expect(syllabus.overview).toBe(
      'This online course explores architectural patterns. Students learn ' +
      'to make architectural decisions.',
    );
    expect(syllabus.objectives).toEqual([
      'Design software architectures',
      'Evaluate and select appropriate architectural patterns',
    ]);
    expect(syllabus.weeks).toEqual([
      { week: 1, topic: 'Architectural thinking and quality attributes' },
      { week: 2, topic: 'Architectural patterns and styles' },
      { week: 7, topic: 'Architecture documentation and ADRs' },
    ]);
  });

  it('returns null when there are no weekly topics', () => {
    expect(parseSyllabus('MSSE-601 Fundamentals. An overview only.')).toBeNull();
  });

  it('returns null for missing text', () => {
    expect(parseSyllabus(undefined)).toBeNull();
    expect(parseSyllabus('')).toBeNull();
  });
});
