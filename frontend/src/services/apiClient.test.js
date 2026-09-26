import { afterEach, describe, expect, it, vi } from 'vitest';

import { ApiError, RestAPIClient } from './apiClient.js';

function mockFetch(status, body) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('RestAPIClient.post', () => {
  it('sends JSON with a Bearer token and returns the body', async () => {
    const fetchMock = mockFetch(200, { type: 'audit' });
    const client = new RestAPIClient('http://api.test/');

    const result = await client.post('/api/v1/query', { query: 'hi' }, 'tok');

    expect(result).toEqual({ type: 'audit' });
    expect(fetchMock).toHaveBeenCalledWith('http://api.test/api/v1/query', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer tok',
      },
      body: JSON.stringify({ query: 'hi' }),
    });
  });

  it('parses the standard error envelope', async () => {
    mockFetch(401, {
      error: { code: 'UNAUTHORIZED', message: 'Session expired.', details: {} },
    });
    const client = new RestAPIClient();

    const error = await client.post('/api/v1/query', {}, 'tok').catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(401);
    expect(error.code).toBe('UNAUTHORIZED');
    expect(error.message).toBe('Session expired.');
  });

  it('reports an unreachable server as a network error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('fail')));
    const client = new RestAPIClient();

    const error = await client.post('/api/v1/query', {}, 'tok').catch((e) => e);

    expect(error.code).toBe('NETWORK_ERROR');
    expect(error.status).toBe(0);
  });
});
