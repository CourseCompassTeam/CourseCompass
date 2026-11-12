import { describe, expect, it, vi } from 'vitest';

import { RestAPIClient } from './apiClient.js';
import { MockAPIClient } from './mockApiClient.js';

vi.mock('../config.js', () => ({
  config: { useMockApi: false, apiBaseUrl: 'http://api.test' },
}));

describe('createApiClient', () => {
  it('uses the REST client when mock mode is off', async () => {
    const { createApiClient } = await import('./createApiClient.js');

    const client = createApiClient();

    expect(client).toBeInstanceOf(RestAPIClient);
  });

  it('uses the mock client when mock mode is on', async () => {
    vi.resetModules();
    vi.doMock('../config.js', () => ({
      config: { useMockApi: true, apiBaseUrl: '' },
    }));
    const { createApiClient } = await import('./createApiClient.js');
    const { MockAPIClient: FreshMockClient } = await import('./mockApiClient.js');

    expect(createApiClient()).toBeInstanceOf(FreshMockClient);
    vi.doUnmock('../config.js');
  });
});
