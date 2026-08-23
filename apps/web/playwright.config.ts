import { defineConfig, devices } from "@playwright/test";

const port = process.env.PLAYWRIGHT_PORT ?? "3000";
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? `http://127.0.0.1:${port}`;
const webServerCommand = process.env.CI
  ? "npm run start:standalone"
  : `npm run dev -- -p ${port}`;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "list",
  use: {
    baseURL,
    channel: process.env.PLAYWRIGHT_CHANNEL || undefined,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  webServer: {
    command: webServerCommand,
    url: `${baseURL}/en`,
    env: { NEXT_PUBLIC_API_URL: "", PORT: port },
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "firefox", use: { ...devices["Desktop Firefox"] } },
    { name: "webkit", use: { ...devices["Desktop Safari"] } },
  ],
});
