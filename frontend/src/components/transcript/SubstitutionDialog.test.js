import { describe, expect, it } from 'vitest';

import { diffSubstitutions } from './SubstitutionDialog.jsx';

const declared = [
  { substitutionId: 's1', requirementCode: 'MSSE 635', substituteCode: 'MSSE 610' },
];

describe('diffSubstitutions', () => {
  it('reports nothing when the matcher matches what is saved', () => {
    expect(diffSubstitutions(declared, { 'MSSE 635': 'MSSE 610' })).toEqual({
      removals: [],
      declarations: [],
    });
  });

  it('removes a declaration the student cleared', () => {
    expect(diffSubstitutions(declared, {})).toEqual({
      removals: ['s1'],
      declarations: [],
    });
  });

  it('declares a new substitute for an open requirement', () => {
    expect(diffSubstitutions([], { 'MSSE 696': 'MSSE 615' })).toEqual({
      removals: [],
      declarations: [{ requirementCode: 'MSSE 696', substituteCode: 'MSSE 615' }],
    });
  });

  it('redeclares when the substitute changes', () => {
    expect(diffSubstitutions(declared, { 'MSSE 635': 'MSSE 615' })).toEqual({
      removals: [],
      declarations: [{ requirementCode: 'MSSE 635', substituteCode: 'MSSE 615' }],
    });
  });
});
