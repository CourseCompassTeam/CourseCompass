// ScheduleService builds a student's course schedule. The backend plans
// remaining required courses by prerequisites and term offerings. No LLM
// is involved, so the same inputs give the same plan.
//
// Schedules aren't saved. The student rebuilds whenever they want a new
// one, and exports it as a calendar file made in the browser.
//
// The student is identified by the session token only. Never send a
// student id, email, or name in the request.

export const SCHEDULE_BUILD_ENDPOINT = '/api/v1/schedule/build';

export const DEFAULT_COURSES_PER_TERM = 2;
export const MAX_COURSES_PER_TERM = 6;

export class ScheduleService {
  /**
   * @param {{post: Function}} apiClient Any APIClient implementation.
   * @param {{getSessionToken: Function, getDevStudentId: Function}}
   *     authService Any AuthService implementation.
   */
  constructor(apiClient, authService) {
    this._apiClient = apiClient;
    this._authService = authService;
  }

  /**
   * Plans the student's remaining required courses.
   * @param {{coursesPerTerm?: number}} options Most courses in one term.
   * @returns {Promise<{
   *   schedule: ?Schedule,
   *   unplaced: Array<{courseId: string, code: string, title: string,
   *                    reason: string}>,
   *   message: string,
   * }>} schedule is null when no course could be placed, and message
   *     says why.
   * @throws {ApiError} If the request fails.
   */
  async buildSchedule({ coursesPerTerm } = {}) {
    const token = await this._authService.getSessionToken();
    // Local backends only; production ignores this header.
    const devStudentId = this._authService.getDevStudentId();
    const headers = devStudentId ? { 'X-Dev-Student-Id': devStudentId } : {};
    const body = coursesPerTerm === undefined
      ? {}
      : { courses_per_term: coursesPerTerm };

    const raw = await this._apiClient.post(
      SCHEDULE_BUILD_ENDPOINT,
      body,
      token,
      headers,
    );
    return {
      schedule: raw?.schedule ? normalizeSchedule(raw.schedule) : null,
      unplaced: (raw?.unplaced ?? []).map((course) => ({
        courseId: course.course_id ?? '',
        code: course.code ?? '',
        title: course.title ?? '',
        reason: course.reason ?? '',
      })),
      message: raw?.message ?? '',
    };
  }
}

/**
 * @typedef {object} Schedule
 * @property {Array<{
 *   termName: string,
 *   termOrder: number,
 *   startDate: ?string,
 *   endDate: ?string,
 *   items: Array<{courseId: string, code: string, title: string,
 *                 credits: number}>,
 * }>} terms In order. startDate and endDate are 'YYYY-MM-DD', or null
 *     when the backend doesn't send them.
 */

/**
 * @param {object} raw The schedule from the build response.
 * @returns {Schedule}
 */
export function normalizeSchedule(raw) {
  return {
    terms: (raw?.terms ?? [])
      .map((term) => ({
        termName: term.term_name ?? '',
        termOrder: term.term_order ?? 0,
        startDate: term.start_date ?? null,
        endDate: term.end_date ?? null,
        items: (term.items ?? []).map((item) => ({
          courseId: item.course_id ?? '',
          code: item.code ?? '',
          title: item.title ?? '',
          credits: item.credits ?? 0,
        })),
      }))
      .sort((a, b) => a.termOrder - b.termOrder),
  };
}
