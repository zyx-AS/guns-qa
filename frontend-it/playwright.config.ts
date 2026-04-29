import { defineConfig } from '@playwright/test';

const baseURL = process.env.APP_BASE_URL || 'http://101.200.163.141';
const junitOutput = process.env.PLAYWRIGHT_JUNIT_OUTPUT || '.artifacts/guns/playwright/junit.xml';
const htmlOutput = process.env.PLAYWRIGHT_HTML_OUTPUT || '.artifacts/guns/playwright/html-report';

export default defineConfig({
  testDir: './tests/integration',
  timeout: 60_000,
  expect: {
    timeout: 10_000,
  },
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: [
    ['list'],
    ['junit', { outputFile: junitOutput }],
    ['html', { outputFolder: htmlOutput, open: 'never' }],
  ],
  use: {
    baseURL,
    headless: true,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 15000,
    navigationTimeout: 30000,
  },
});
