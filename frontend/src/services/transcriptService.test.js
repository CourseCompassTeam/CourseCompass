import { describe, expect, it, vi } from 'vitest';

import { ApiError } from './apiClient.js';
import { DevAuthService } from './authService.js';
import {
  SUBSTITUTION_REVIEW_ENDPOINT,
  SUBSTITUTIONS_ENDPOINT,
  TRANSCRIPT_UPLOAD_ENDPOINT,
  TranscriptService,
  normalizeReview,
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
      clearedSubstitutions: [],
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
    expect(result).toEqual({
      saved: [],
      skipped: [],
      courseCount: 0,
      clearedSubstitutions: [],
    });
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

describe('TranscriptService substitutions', () => {
  it('loads the review with the session token and dev header', async () => {
    const apiClient = {
      get: vi.fn().mockResolvedValue({ requirements: [{ code: 'MSSE 635' }] }),
    };
    const service = new TranscriptService(
      apiClient,
      fakeAuth({ devStudentId: 'user_x' }),
    );

    const review = await service.getSubstitutionReview();

    expect(apiClient.get).toHaveBeenCalledWith(
      SUBSTITUTION_REVIEW_ENDPOINT,
      'tok',
      { 'X-Dev-Student-Id': 'user_x' },
    );
    expect(review).toEqual({
      requirements: [{ code: 'MSSE 635' }],
      courses: [],
      substitutions: [],
    });
  });

  it('declares a substitute with camelCase codes', async () => {
    const apiClient = { post: vi.fn().mockResolvedValue({}) };
    const service = new TranscriptService(apiClient, fakeAuth());

    await service.declareSubstitution('MSSE 635', 'MSSE 610');

    expect(apiClient.post).toHaveBeenCalledWith(
      SUBSTITUTIONS_ENDPOINT,
      { requirementCode: 'MSSE 635', substituteCode: 'MSSE 610' },
      'tok',
      {},
    );
  });

  it('removes a declaration by id', async () => {
    const apiClient = { delete: vi.fn().mockResolvedValue({}) };
    const service = new TranscriptService(apiClient, fakeAuth());

    await service.removeSubstitution('abc-123');

    expect(apiClient.delete).toHaveBeenCalledWith(
      `${SUBSTITUTIONS_ENDPOINT}/abc-123`,
      'tok',
      {},
    );
  });
});

describe('normalizeReview', () => {
  it('fills missing lists with empty arrays', () => {
    expect(normalizeReview(undefined)).toEqual({
      requirements: [],
      courses: [],
      substitutions: [],
    });
  });
});
