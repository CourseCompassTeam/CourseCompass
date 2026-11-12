import { describe, expect, it } from 'vitest';

import { ClerkAuthService, DevAuthService } from './authService.js';

describe('ClerkAuthService', () => {
  it('returns the Clerk session token', async () => {
    const service = new ClerkAuthService({
      getToken: async () => 'jwt-token',
      userId: 'user_1',
    });

    expect(await service.getSessionToken()).toBe('jwt-token');
    expect(service.getUserId()).toBe('user_1');
    expect(service.getDevStudentId()).toBe('');
  });

  it('returns an empty token when Clerk has none', async () => {
    const service = new ClerkAuthService({
      getToken: async () => null,
      userId: null,
    });

    expect(await service.getSessionToken()).toBe('');
    expect(service.getUserId()).toBe('');
  });
});

describe('DevAuthService', () => {
  it('sends no bearer token and exposes the seed student', async () => {
    const service = new DevAuthService('user_seed');

    expect(await service.getSessionToken()).toBe('');
    expect(service.getUserId()).toBe('dev-user');
    expect(service.getDevStudentId()).toBe('user_seed');
  });

  it('defaults to no dev student', () => {
    expect(new DevAuthService().getDevStudentId()).toBe('');
  });
});
