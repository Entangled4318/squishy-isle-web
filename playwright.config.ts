import { defineConfig, devices } from '@playwright/test';

/* Chromium with touch, at iPhone and iPad sizes. Safari-only behaviour
 * (sound unlock, storage rules, safe areas, the home screen) is on the
 * device checklist (docs/DEVICE_CHECKLIST.md). */
export default defineConfig({
  testDir: 'tests/e2e',
  timeout: 60_000,
  fullyParallel: true,
  reporter: [['list']],
  use: { baseURL: 'http://localhost:4173/squishy-isle-web/' },
  webServer: {
    command: 'npx vite preview --port 4173 --strictPort',
    url: 'http://localhost:4173/squishy-isle-web/',
    reuseExistingServer: !process.env.CI,
  },
  projects: [
    { name: 'iphone', use: { ...devices['iPhone 13 landscape'], browserName: 'chromium' } },
    { name: 'ipad', use: { ...devices['iPad (gen 7)'], browserName: 'chromium' } },
  ],
});
