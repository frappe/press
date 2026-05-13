import { defineConfig, devices } from '@playwright/test';
import dotenv from "dotenv";

dotenv.config({ path: "./tests-e2e/.env", quiet: true });

export default defineConfig({
  testDir: './tests-e2e',
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 4 : undefined,
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:8010',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure'
  },
  reporter: [['list'], ['html', { open: 'never' }]],
  projects: [
    {
      name: 'cron',
      testMatch: /.*\.cron\.spec\.ts/,
      dependencies: undefined
    },
    {
      name: 'setup',
      testMatch: /.*\.setup\.ts/
    },
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'tests-e2e/.auth/session.json' 
      },
      // must match all *.test.ts files only
      testMatch: /^(?!.*(\.cron|\.setup)\.spec\.ts$).*\.test\.ts$/,
      dependencies: ['setup']
    }
  ]
});
