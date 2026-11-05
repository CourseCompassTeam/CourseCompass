import { describe, expect, it } from 'vitest';

import { MockAPIClient } from './mockApiClient.js';

const client = new MockAPIClient({ delayMs: 0 });

describe('MockAPIClient.post', () => {
  it.each([
    ['What do I still need to graduate?', 'audit'],
    ['Recommend an elective for me', 'recommendation'],
    ['Can I get financial aid?', 'redirect'],
  ])('routes "%s" to %s', async (query, type) => {
    const response = await client.post('/api/v1/query', { query }, 'tok');
    expect(response.type).toBe(type);
  });

  it('returns milestones for next-steps questions', async () => {
    const response = await client.post(
      '/api/v1/query',
      { query: 'What are my next steps outside of class?' },
      'tok',
    );
    expect(response.type).toBe('recommendation');
    expect(response.content.milestones[0].nextActions.length).toBeGreaterThan(0);
  });

  it('simulates a server error on request', async () => {
    await expect(
      client.post('/api/v1/query', { query: 'simulate error' }, 'tok'),
    ).rejects.toMatchObject({ status: 500 });
  });
});

describe('MockAPIClient.postFile', () => {
  it('returns saved and skipped courses', async () => {
    const response = await client.postFile(
      '/api/v1/transcript/upload', new File(['%PDF'], 'transcript.pdf'), 'tok',
    );
    expect(response.saved.length).toBeGreaterThan(0);
    expect(response.skipped.length).toBeGreaterThan(0);
  });

  it('simulates a parse error on request', async () => {
    await expect(
      client.postFile('/api/v1/transcript/upload',
        new File([''], 'simulate error.pdf'), 'tok'),
    ).rejects.toMatchObject({ status: 400, code: 'BAD_REQUEST' });
  });
});

describe('MockAPIClient schedule build', () => {
  it('plans courses per term and lists the rest as unplaced', async () => {
    const built = await client.post(
      '/api/v1/schedule/build', { courses_per_term: 1 }, 'tok',
    );

    expect(built.schedule.terms.map((term) => term.items.length))
      .toEqual([1, 1, 1]);
    expect(built.unplaced.length).toBeGreaterThan(1);
  });

  it('includes a term without dates', async () => {
    const built = await client.post('/api/v1/schedule/build', {}, 'tok');

    expect(built.schedule.terms.some((term) => term.start_date === null))
      .toBe(true);
  });

  it('rejects courses_per_term outside 1 to 6', async () => {
    await expect(
      client.post('/api/v1/schedule/build', { courses_per_term: 7 }, 'tok'),
    ).rejects.toMatchObject({ status: 400, code: 'BAD_REQUEST' });
  });
});
