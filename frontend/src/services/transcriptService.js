// TranscriptService uploads a student's transcript PDF. The backend parses
// it and replaces that student's stored courses. No LLM is involved.
//
// The student is identified by the session token only. Never send a
// student id, email, or name in the request.

import { ApiError } from './apiClient.js';

export const TRANSCRIPT_UPLOAD_ENDPOINT = '/api/v1/transcript/upload';
export const SUBSTITUTION_REVIEW_ENDPOINT = '/api/v1/transcript/review';
export const SUBSTITUTIONS_ENDPOINT = '/api/v1/transcript/substitutions';

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

    const { token, headers } = await this.#auth();
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
      clearedSubstitutions: raw?.clearedSubstitutions ?? [],
    };
  }

  /**
   * Loads what the substitution matcher needs for the signed-in student.
   * @returns {Promise<SubstitutionReview>}
   * @throws {ApiError} If the request fails.
   */
  async getSubstitutionReview() {
    const { token, headers } = await this.#auth();
    const raw = await this._apiClient.get(
      SUBSTITUTION_REVIEW_ENDPOINT,
      token,
      headers,
    );
    return normalizeReview(raw);
  }

  /**
   * Declares or replaces the substitute for one required course.
   * @param {string} requirementCode Required course, e.g. 'MSSE 635'.
   * @param {string} substituteCode Course the student took instead.
   * @returns {Promise<SubstitutionReview>} The updated review.
   * @throws {ApiError} If the course cannot be declared.
   */
  async declareSubstitution(requirementCode, substituteCode) {
    const { token, headers } = await this.#auth();
    const raw = await this._apiClient.post(
      SUBSTITUTIONS_ENDPOINT,
      { requirementCode, substituteCode },
      token,
      headers,
    );
    return normalizeReview(raw);
  }

  /**
   * Removes one of the student's declared substitutions.
   * @param {string} substitutionId The declaration to remove.
   * @returns {Promise<SubstitutionReview>} The updated review.
   * @throws {ApiError} If the declaration is not found.
   */
  async removeSubstitution(substitutionId) {
    const { token, headers } = await this.#auth();
    const raw = await this._apiClient.delete(
      `${SUBSTITUTIONS_ENDPOINT}/${encodeURIComponent(substitutionId)}`,
      token,
      headers,
    );
    return normalizeReview(raw);
  }

  async #auth() {
    const token = await this._authService.getSessionToken();
    // Local backends only; production ignores this header.
    const devStudentId = this._authService.getDevStudentId();
    const headers = devStudentId ? { 'X-Dev-Student-Id': devStudentId } : {};
    return { token, headers };
  }
}

/**
 * @typedef {object} SubstitutionReview
 * @property {Array<{code: string, title: string, credits: number}>}
 *     requirements Required courses not yet directly completed.
 * @property {Array<{code: string, title: string, credits: number,
 *     status: string}>} courses Transcript courses that are not required.
 * @property {Array<{substitutionId: string, requirementCode: string,
 *     substituteCode: string, substituteTitle: string, counted: boolean}>}
 *     substitutions The student's declared substitutions.
 */

/**
 * @param {object} raw The backend review payload.
 * @returns {SubstitutionReview}
 */
export function normalizeReview(raw) {
  return {
    requirements: raw?.requirements ?? [],
    courses: raw?.courses ?? [],
    substitutions: raw?.substitutions ?? [],
  };
}
