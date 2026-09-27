// Picks the APIClient implementation from configuration.

import { config } from '../config.js';
import { RestAPIClient } from './apiClient.js';
import { MockAPIClient } from './mockApiClient.js';

export function createApiClient() {
  return config.useMockApi
    ? new MockAPIClient()
    : new RestAPIClient(config.apiBaseUrl);
}
