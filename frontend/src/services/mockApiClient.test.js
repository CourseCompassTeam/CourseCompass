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
