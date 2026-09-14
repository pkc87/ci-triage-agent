import { defineConfig, devices } from '@playwright/test';

const PORT = Number(process.env.SHOP_PORT ?? 4173);
const BASE_URL = process.env.SHOP_BASE_URL ?? `http://127.0.0.1:${PORT}`;
const JSON_REPORT = process.env.PW_JSON_REPORT ?? 'reports/report.json';

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  retries: 2,
  reporter: [['json', { outputFile: JSON_REPORT }], ['list']],
  use: {
    baseURL: BASE_URL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'node serve.mjs',
    url: `http://127.0.0.1:${PORT}`,
    reuseExistingServer: false,
    stdout: 'ignore',
    stderr: 'pipe',
  },
});
