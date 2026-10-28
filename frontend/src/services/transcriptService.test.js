import { describe, expect, it, vi } from 'vitest';

import { ApiError } from './apiClient.js';
import { DevAuthService } from './authService.js';
import {
  TRANSCRIPT_UPLOAD_ENDPOINT,
  TranscriptService,
} from './transcriptService.js';

const pdf = new File(['%PDF'], 'Transcript.PDF', { type: 'application/pdf' });

function fakeAuth({ token = 'tok', devStudentId = '' } = {}) {
  return {
    getSessionToken: async () => token,
    getUserId: () => 'user',
    getDevStudentId: () => devStudentId,
  };
}

describe('TranscriptService.uploadTranscript', () => {
  it('uploads the file with the session token', async () => {
    const apiClient = {
      postFile: vi.fn().mockResolvedValue({
        course_count: 2,
        saved: [{ code: 'MSSE 610', status: 'completed' }],
        skipped: [{ code: 'MSSE 600', reason: 'not in course catalog' }],
      }),
    };
    const service = new TranscriptService(apiClient, fakeAuth());

    const result = await service.uploadTranscript(pdf);

    expect(apiClient.postFile).toHaveBeenCalledWith(
      TRANSCRIPT_UPLOAD_ENDPOINT, pdf, 'tok', {},
    );
    expect(result).toEqual({
      courseCount: 2,
      saved: [{ code: 'MSSE 610', status: 'completed' }],
      skipped: [{ code: 'MSSE 600', reason: 'not in course catalog' }],
    });
  });

  it('sends X-Dev-Student-Id in dev mode', async () => {
    const apiClient = { postFile: vi.fn().mockResolvedValue({}) };
    const service = new TranscriptService(
      apiClient, new DevAuthService('user_seed'),
    );

    const result = await service.uploadTranscript(pdf);

    expect(apiClient.postFile).toHaveBeenCalledWith(
      TRANSCRIPT_UPLOAD_ENDPOINT, pdf, '', { 'X-Dev-Student-Id': 'user_seed' },
    );
    expect(result).toEqual({ saved: [], skipped: [], courseCount: 0 });
  });

  it('rejects a non-PDF file without calling the backend', async () => {
    const apiClient = { postFile: vi.fn() };
    const service = new TranscriptService(apiClient, fakeAuth());

    const error = await service
      .uploadTranscript(new File(['x'], 'transcript.docx'))
      .catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error.code).toBe('BAD_REQUEST');
    expect(apiClient.postFile).not.toHaveBeenCalled();
  });

  it('passes backend errors through', async () => {
    const apiClient = {
      postFile: vi.fn().mockRejectedValue(
        new ApiError(404, 'NOT_FOUND', 'No student.'),
      ),
    };
    const service = new TranscriptService(apiClient, fakeAuth());

    const error = await service.uploadTranscript(pdf).catch((e) => e);

    expect(error.status).toBe(404);
  });
});
