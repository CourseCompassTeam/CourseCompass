import { describe, expect, it } from 'vitest';

import { summarizeAudit } from './auditSummary.js';

describe('summarizeAudit', () => {
  it('computes progress and adds course titles', () => {
    const summary = summarizeAudit({
      creditsCompleted: 30,
      creditsRemaining: 6,
      creditsRequired: 36,
      requirementsMet: false,
      missingCourses: ['SE 692'],
      requiredCourses: [
        { code: 'SE 692', title: 'Practicum I', credits: 3 },
        { code: 'SE 601', title: 'Fundamentals', credits: 3 },
      ],
    });

    expect(summary.percent).toBe(83);
    expect(summary.missing).toEqual([
      { code: 'SE 692', title: 'Practicum I', credits: 3 },
    ]);
  });

  it('derives the required total when it is missing', () => {
    const summary = summarizeAudit({ creditsCompleted: 3, creditsRemaining: 33 });
    expect(summary.required).toBe(36);
    expect(summary.percent).toBe(8);
  });

  it('keeps bare codes when course details are missing', () => {
    const summary = summarizeAudit({ missingCourses: ['SE 699'] });
    expect(summary.missing).toEqual([
      { code: 'SE 699', title: null, credits: null },
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
