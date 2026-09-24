import { describe, expect, it, vi } from 'vitest';

import { MessageType } from '../models/message.js';
import { ChatService, QUERY_ENDPOINT } from './chatService.js';

function makeService(response) {
  const apiClient = { post: vi.fn().mockResolvedValue(response) };
  const authService = {
    getSessionToken: vi.fn().mockResolvedValue('token-123'),
    getUserId: () => 'user-1',
  };
  return { service: new ChatService(apiClient, authService), apiClient };
}

describe('ChatService.sendQuery', () => {
  it('posts the query with the session token', async () => {
    const { service, apiClient } = makeService({ type: 'audit', content: {} });

    await service.sendQuery('What do I need to graduate?');

    expect(apiClient.post).toHaveBeenCalledWith(
      QUERY_ENDPOINT,
      { query: 'What do I need to graduate?' },
      'token-123',
    );
  });

  it('turns the response into a Message', async () => {
    const content = { creditsRemaining: 3, requirementsMet: false };
    const { service } = makeService({
      id: 'msg-1',
      type: 'audit',
      content,
      timestamp: '2026-09-23T12:00:00Z',
    });

    const message = await service.sendQuery('audit me');

    expect(message).toEqual({
      id: 'msg-1',
      type: MessageType.AUDIT,
      content,
      timestamp: new Date('2026-09-23T12:00:00Z'),
    });
  });

  it('treats an unknown response type as a redirect (QA-02)', async () => {
    const { service } = makeService({ type: 'made-up', content: {} });

    const message = await service.sendQuery('hello');

    expect(message.type).toBe(MessageType.REDIRECT);
  });

  it('passes API errors through to the caller', async () => {
    const apiClient = { post: vi.fn().mockRejectedValue(new Error('boom')) };
    const authService = { getSessionToken: async () => 't' };
    const service = new ChatService(apiClient, authService);

    await expect(service.sendQuery('hi')).rejects.toThrow('boom');
  });
});
