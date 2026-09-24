// MockAPIClient: an APIClient that returns sample responses, for building
// the UI before the backend exists. Turn it on with VITE_USE_MOCK_API=true.
//
// All data here is made up. Only the 'audit' content shape is documented
// in the API spec. The 'message' field and the recommendation and redirect
// content shapes are tentative (see docs/OPEN_QUESTIONS.md).

import { ApiError } from './apiClient.js';

const SAMPLE_RESPONSES = {
  audit: {
    message:
      'You have completed 27 of 36 credits. Three required courses remain.',
    creditsRemaining: 9,
    requirementsMet: false,
    missingCourses: ['SE 640', 'SE 660', 'SE 699'],
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
  redirect: {
    message: 'That question is outside what I can answer reliably. ' +
      'An academic advisor can help with this.',
    resourceName: 'Book an advising appointment',
    url: 'https://example.com/advising',
  },
};

const INTENT_KEYWORDS = [
  ['audit', /graduat|credit|remaining|left|audit|progress/i],
  ['recommendation', /recommend|interest|elective|suggest|next term/i],
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

    const match = INTENT_KEYWORDS.find(([, pattern]) => pattern.test(query));
    const type = match ? match[0] : 'redirect';
    return {
      id: crypto.randomUUID(),
      type,
      content: SAMPLE_RESPONSES[type],
      timestamp: new Date().toISOString(),
    };
  }
}
