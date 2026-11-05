import { describe, expect, it, vi } from 'vitest';

import { ApiError } from './apiClient.js';
import { DevAuthService } from './authService.js';
import {
  SCHEDULE_BUILD_ENDPOINT,
  ScheduleService,
  normalizeSchedule,
} from './scheduleService.js';

function fakeAuth({ token = 'tok', devStudentId = '' } = {}) {
  return {
    getSessionToken: async () => token,
    getUserId: () => 'user',
    getDevStudentId: () => devStudentId,
  };
}

const RAW_SCHEDULE = {
  terms: [
    {
      term_name: '2027 SPR 8W2',
      term_order: 2,
      items: [],
    },
    {
      term_name: '2027 SPR 8W1',
      term_order: 1,
      start_date: '2027-01-11',
      end_date: '2027-03-07',
      items: [{
        course_id: 'c1',
        code: 'MSSE 601',
        title: 'Software Engineering Fundamentals',
        credits: 3,
      }],
    },
  ],
};

describe('ScheduleService.buildSchedule', () => {
  it('posts courses_per_term with the session token', async () => {
    const apiClient = {
      post: vi.fn().mockResolvedValue({
        status: 'success',
        schedule: RAW_SCHEDULE,
        unplaced: [{
          course_id: 'c9', code: 'MSSE 696', title: 'Practicum II',
          reason: 'not offered in any available term',
        }],
      }),
    };
    const service = new ScheduleService(apiClient, fakeAuth());

    const result = await service.buildSchedule({ coursesPerTerm: 3 });

    expect(apiClient.post).toHaveBeenCalledWith(
      SCHEDULE_BUILD_ENDPOINT, { courses_per_term: 3 }, 'tok', {},
    );
    expect(result.schedule.terms).toHaveLength(2);
    expect(result.unplaced).toEqual([{
      courseId: 'c9', code: 'MSSE 696', title: 'Practicum II',
      reason: 'not offered in any available term',
    }]);
    expect(result.message).toBe('');
  });

  it('sends an empty body when no option is given', async () => {
    const apiClient = { post: vi.fn().mockResolvedValue({}) };
    const service = new ScheduleService(
      apiClient, new DevAuthService('user_seed'),
    );

    await service.buildSchedule();

    expect(apiClient.post).toHaveBeenCalledWith(
      SCHEDULE_BUILD_ENDPOINT, {}, '', { 'X-Dev-Student-Id': 'user_seed' },
    );
  });

  it('returns a null schedule and the message when nothing was placed',
    async () => {
      const apiClient = {
        post: vi.fn().mockResolvedValue({
          status: 'success',
          schedule: null,
          unplaced: [],
          message: 'No courses could be placed.',
        }),
      };
      const service = new ScheduleService(apiClient, fakeAuth());

      const result = await service.buildSchedule();

      expect(result).toEqual({
        schedule: null,
        unplaced: [],
        message: 'No courses could be placed.',
      });
    });

  it('passes backend errors through', async () => {
    const apiClient = {
      post: vi.fn().mockRejectedValue(
        new ApiError(400, 'BAD_REQUEST', 'Bad courses_per_term.'),
      ),
    };
    const service = new ScheduleService(apiClient, fakeAuth());

    const error = await service.buildSchedule({ coursesPerTerm: 9 })
      .catch((e) => e);

    expect(error.code).toBe('BAD_REQUEST');
  });
});

describe('normalizeSchedule', () => {
  it('sorts terms and defaults missing dates to null', () => {
    const schedule = normalizeSchedule(RAW_SCHEDULE);

    expect(schedule.terms.map((term) => term.termName))
      .toEqual(['2027 SPR 8W1', '2027 SPR 8W2']);
    expect(schedule.terms[0]).toMatchObject({
      startDate: '2027-01-11', endDate: '2027-03-07',
    });
    expect(schedule.terms[1]).toMatchObject({
      startDate: null, endDate: null,
    });
    expect(schedule.terms[0].items[0]).toEqual({
      courseId: 'c1',
      code: 'MSSE 601',
      title: 'Software Engineering Fundamentals',
      credits: 3,
    });
  });
});
