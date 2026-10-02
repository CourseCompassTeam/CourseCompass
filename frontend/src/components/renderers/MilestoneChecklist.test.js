import { describe, expect, it } from 'vitest';

import { formatCreditBand } from './MilestoneChecklist.jsx';

describe('formatCreditBand', () => {
  it('shows a closed range', () => {
    expect(formatCreditBand(0, 12)).toBe('0–12 credits');
  });

  it('shows an open-ended range', () => {
    expect(formatCreditBand(25, null)).toBe('25+ credits');
  });

  it('returns nothing when the band is unknown', () => {
    expect(formatCreditBand(null, undefined)).toBe('');
  });
});
