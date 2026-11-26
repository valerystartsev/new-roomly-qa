import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests-ts',
  outputDir: 'artifacts-ts/browser',
  reporter: [
    ['list'],
    ['junit', { outputFile: 'artifacts-ts/junit.xml' }],
  ],
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:8000/',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
