import { defineConfig } from 'vite';
import { configDefaults } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    // e2e/ holds Playwright specs, which run with `npm run test:e2e`.
    exclude: [...configDefaults.exclude, 'e2e/**'],
  },
});
