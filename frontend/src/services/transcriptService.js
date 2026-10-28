// TranscriptService uploads a student's transcript PDF. The backend parses
// it and replaces that student's stored courses. No LLM is involved.
//
// The student is identified by the session token only. Never send a
// student id, email, or name in the request.

import { ApiError } from './apiClient.js';

export const TRANSCRIPT_UPLOAD_ENDPOINT = '/api/v1/transcript/upload';

export class TranscriptService {
  /**
   * @param {{postFile: Function}} apiClient Any APIClient implementation.
   * @param {{getSessionToken: Function, getDevStudentId: Function}}
   *     authService Any AuthService implementation.
   */
  constructor(apiClient, authService) {
    this._apiClient = apiClient;
    this._authService = authService;
  }

  /**
   * Uploads a transcript PDF, replacing the student's stored transcript.
   * @param {File} file The transcript PDF.
   * @returns {Promise<{
   *   saved: Array<{code: string, status: string, term: string,
   *                 grade: string}>,
   *   skipped: Array<{code: string, reason: string}>,
   *   courseCount: number,
   * }>} Courses written to the transcript, and courses that were parsed
   *     but not stored (for example, not in the course catalog).
   * @throws {ApiError} If the file isn't a PDF or the request fails.
   */
  async uploadTranscript(file) {
    if (!file || !/\.pdf$/i.test(file.name ?? '')) {
      throw new ApiError(400, 'BAD_REQUEST',
        'Only PDF transcripts are supported.');
    }

    const token = await this._authService.getSessionToken();
    // Local backends only; production ignores this header.
    const devStudentId = this._authService.getDevStudentId();
    const headers = devStudentId ? { 'X-Dev-Student-Id': devStudentId } : {};

    const raw = await this._apiClient.postFile(
      TRANSCRIPT_UPLOAD_ENDPOINT,
      file,
      token,
      headers,
    );
    return {
      saved: raw?.saved ?? [],
      skipped: raw?.skipped ?? [],
      courseCount: raw?.course_count ?? 0,
    };
  }
}
