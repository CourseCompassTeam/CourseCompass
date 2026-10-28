// Frontend configuration, read from Vite environment variables.
// Set these in frontend/.env.local (see frontend/.env.example).

const env = import.meta.env;

export const config = {
  // Clerk publishable key. When it's empty, the app runs in dev mode
  // with a fake signed-in user.
  clerkPublishableKey: env.VITE_CLERK_PUBLISHABLE_KEY ?? '',

  // Backend base URL, e.g. http://localhost:8000. Empty = same origin.
  apiBaseUrl: env.VITE_API_BASE_URL ?? '',

  // 'true' = use MockAPIClient instead of calling the backend.
  useMockApi: env.VITE_USE_MOCK_API === 'true',

  // Dev mode only: seed student to act as, sent as X-Dev-Student-Id.
  // The backend honors it only when APP_ENV is local, staging, or test.
  devStudentId: env.VITE_DEV_STUDENT_ID ?? '',
};
