import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: false, // Run tests sequentially to avoid rate limiting
  forbidOnly: !!process.env.CI,
  retries: 2, // Retry failed tests
  workers: 1, // Single worker to avoid overwhelming the server
  reporter: 'list',
  timeout: 60000,
  use: {
    baseURL: process.env.TEST_URL || 'https://sip-dialer-263oa.ondigitalocean.app',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
