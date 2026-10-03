import { test, expect } from '@playwright/test';

const backendUrl = process.env.E2E_BACKEND_URL || 'http://127.0.0.1:8000';

test.describe('App smoke', () => {
  test('home page loads', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('heading', { level: 1 }).first()).toBeVisible();
  });

  test('live lab page loads', async ({ page }) => {
    test.setTimeout(90_000);
    await page.goto('/live-lab');
    await expect(page.getByRole('heading', { name: /AI Testing Lab/i })).toBeVisible();
    await expect(page.getByTestId('run-analysis')).toBeVisible({ timeout: 60_000 });
  });

  test('backend health when server is running', async () => {
    test.skip(!process.env.E2E_BACKEND_URL && !process.env.CI_WITH_BACKEND, 'Set E2E_BACKEND_URL to run API smoke tests.');
    const res = await fetch(`${backendUrl}/api/health`);
    expect(res.ok).toBeTruthy();
    const body = await res.json();
    expect(body.status).toBe('ok');
  });
});
