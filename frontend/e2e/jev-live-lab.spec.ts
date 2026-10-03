import { test, expect } from '@playwright/test';
import { createOptionalJev, jevEnabled } from './helpers/jev';

test.describe('Live Lab with Jev semantic checks', () => {
  test.beforeEach(async () => {
    test.skip(!jevEnabled(), 'Set OPENROUTER_API_KEY or TYPESAFE_API_KEY to run Jev tests.');
  });

  test('Jev can verify the Live Lab workspace', async ({ page }) => {
    const jev = await createOptionalJev(page);
    test.skip(!jev, 'Install playwright-jev (see frontend/.env.example) to run semantic UI tests.');

    await page.goto('/live-lab');
    await jev.verify('the page title mentions AI Testing Lab');
    await jev.verify('there is a button to run analysis');
    await jev.verify('there are editable areas for source code and requirements');
  });

  test('Jev can start analysis when backend is online', async ({ page }) => {
    test.skip(!process.env.E2E_BACKEND_URL, 'Set E2E_BACKEND_URL=http://127.0.0.1:8000 with backend running.');

    const jev = await createOptionalJev(page);
    test.skip(!jev, 'Install playwright-jev to run semantic UI tests.');

    await page.goto('/live-lab');
    await jev.click('Run Analysis');
    await expect(page.getByText(/PROCESSING|COMPLETE|Source Code Analysis|failed/i).first()).toBeVisible({
      timeout: 120_000,
    });
  });
});
