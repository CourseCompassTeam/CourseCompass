import { describe, expect, it } from 'vitest';

import { summarizeAudit, summarizeSubstitution } from './auditSummary.js';

describe('summarizeAudit', () => {
  it('computes progress and adds course titles', () => {
    const summary = summarizeAudit({
      creditsCompleted: 30,
      creditsRemaining: 6,
      creditsRequired: 36,
      requirementsMet: false,
      missingCourses: ['MSSE 692'],
      requiredCourses: [
        { code: 'MSSE 692', title: 'Software Engineering Practicum I', credits: 3 },
        { code: 'MSSE 601', title: 'Software Engineer Fundamentals', credits: 3 },
      ],
    });

    expect(summary.percent).toBe(83);
    expect(summary.missing).toEqual([
      { code: 'MSSE 692', title: 'Software Engineering Practicum I', credits: 3 },
    ]);
  });

  it('derives the required total when it is missing', () => {
    const summary = summarizeAudit({ creditsCompleted: 3, creditsRemaining: 33 });
    expect(summary.required).toBe(36);
    expect(summary.percent).toBe(8);
  });

  it('keeps bare codes when course details are missing', () => {
    const summary = summarizeAudit({ missingCourses: ['MSSE 696'] });
    expect(summary.missing).toEqual([
      { code: 'MSSE 696', title: null, credits: null },
    ]);
    expect(summary.percent).toBeNull();
  });

  it('reports a completed degree', () => {
    const summary = summarizeAudit({
      creditsCompleted: 36,
      creditsRemaining: 0,
      requirementsMet: true,
    });
    expect(summary.met).toBe(true);
    expect(summary.percent).toBe(100);
  });
});

describe('summarizeSubstitution', () => {
  it('reads as substitute for requirement when counted', () => {
    expect(summarizeSubstitution({
      requirementCode: 'MSSE 613',
      substituteCode: 'MSSE 600',
      counted: true,
      reason: 'counted',
    })).toEqual({
      substitute: 'MSSE 600',
      requirement: 'MSSE 613',
      counted: true,
      note: '',
    });
  });

  it('explains why a declaration is not counted', () => {
    expect(summarizeSubstitution({
      requirementCode: 'MSSE 601',
      substituteCode: 'MSSE 600',
      counted: false,
      reason: 'already_completed',
    }).note).toMatch(/already completed/);
  });
});
