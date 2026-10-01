// MockAPIClient: an APIClient that returns sample responses, for building
// the UI before the backend exists. Turn it on with VITE_USE_MOCK_API=true.
//
// All data here is made up. Only the 'audit' content shape is documented
// in the API spec. The 'message' field and the recommendation and redirect
// content shapes are tentative (see docs/OPEN_QUESTIONS.md).

import { ApiError } from './apiClient.js';

const SAMPLE_RESPONSES = {
  audit: {
    message: 'You have completed 15 of 36 credits. Seven required courses ' +
      'remain, starting with Software Requirements and Processes.',
    programName: 'Software Engineering (M.S.)',
    creditsCompleted: 15,
    creditsRemaining: 21,
    creditsRequired: 36,
    requirementsMet: false,
    missingCourses: [
      'SE 610', 'SE 613', 'SE 635', 'SE 640', 'SE 642', 'SE 692', 'SE 696',
    ],
    requiredCourses: [
      ['SE 601', 'Software Engineering Fundamentals'],
      ['SE 603', 'Software Engineering Leadership'],
      ['SE 610', 'Software Requirements and Processes'],
      ['SE 613', 'Software Project Management'],
      ['SE 615', 'Software Engineering and Society'],
      ['SE 635', 'Software Architecture and Design'],
      ['SE 640', 'Software Quality and Test'],
      ['SE 642', 'Software Assurance'],
      ['SE 692', 'Software Engineering Practicum I'],
      ['SE 696', 'Software Engineering Practicum II'],
    ].map(([code, title]) => ({ code, title, credits: 3, category: 'core' })),
  },
  recommendation: {
    message: 'Based on your interest, these courses fit your open ' +
      'requirements:',
    courses: [
      {
        code: 'SE 615',
        title: 'Software Project Management',
        description: 'Planning, estimating, and tracking software projects.',
      },
      {
        code: 'SE 635',
        title: 'Cloud Application Architecture',
        description: 'Designing and deploying scalable cloud services.',
      },
    ],
  },
  milestones: {
    message: 'You are at the Foundations stage. Here are a few things to ' +
      'work on outside of class:',
    milestones: [
      {
        label: 'Foundations',
        creditMin: 0,
        creditMax: 12,
        nextActions: [
          'Review your degree plan with your advisor',
          'Start a portfolio repository on GitHub',
        ],
      },
    ],
    resourceName: 'Career Services',
    url: 'https://example.com/career-services',
  },
  redirect: {
    message: 'That question is outside what I can answer reliably. ' +
      'An academic advisor can help with this.',
    resourceName: 'Book an advising appointment',
    url: 'https://example.com/advising',
  },
};

// [sample, response type, pattern]. The first match wins.
const INTENT_KEYWORDS = [
  ['milestones', 'recommendation', /next steps|milestone|outside of class/i],
  ['audit', 'audit', /graduat|credit|remaining|left|audit|progress/i],
  ['recommendation', 'recommendation',
    /recommend|interest|elective|suggest|next term/i],
];

export class MockAPIClient {
  /**
   * @param {{delayMs?: number}} options Simulated network delay.
   */
  constructor({ delayMs = 800 } = {}) {
    this.delayMs = delayMs;
  }

  /**
   * Returns a sample response picked by keywords in the query.
   * Include "simulate error" in a query to test the error state.
   * @param {string} endpoint Ignored.
   * @param {{query: string}} body The request body.
   * @param {string} token Ignored.
   * @returns {Promise<object>} A response shaped like POST /api/v1/query.
   */
  async post(endpoint, body, token) {
    await new Promise((resolve) => setTimeout(resolve, this.delayMs));

    const query = body?.query ?? '';
    if (/simulate error/i.test(query)) {
      throw new ApiError(500, 'INTERNAL_ERROR', 'Simulated server error.');
    }

    const match = INTENT_KEYWORDS.find(([, , pattern]) => pattern.test(query));
    const [sample, type] = match ?? ['redirect', 'redirect'];
    return {
      id: crypto.randomUUID(),
      type,
      content: SAMPLE_RESPONSES[sample],
      timestamp: new Date().toISOString(),
    };
  }
}
