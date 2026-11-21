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

  test('requirements input selector supports PDF, document, and flowchart uploads', async ({ page }) => {
    await page.route('**/api/health', (route) =>
      route.fulfill({ json: { status: 'ok' } })
    );
    await page.route('**/api/examples', (route) =>
      route.fulfill({
        json: {
          filename: 'sample_source.py',
          source_code: 'def sample():\n    return True\n',
          requirements_text: 'Default requirement.',
        },
      })
    );
    await page.route('**/api/github/status', (route) =>
      route.fulfill({ json: { connected: false } })
    );
    await page.route('**/api/requirements/extract', (route) => {
      const requestBody = route.request().postDataBuffer()?.toString('utf8') || '';
      const requirementsText = requestBody.includes('checkout_requirements.pdf')
        ? 'Requirement from PDF.'
        : 'Requirement from document.';
      return route.fulfill({ json: { requirements_text: requirementsText } });
    });
    await page.route('**/api/requirements/extract-diagram', (route) => {
      const requestBody = route.request().postDataBuffer()?.toString('utf8') || '';
      if (requestBody.includes('failed-flowchart.png')) {
        return route.fulfill({
          status: 502,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Vision service unavailable.' }),
        });
      }
      return route.fulfill({ json: { requirements_text: 'Requirement from flowchart.' } });
    });
    let submittedSessionForm = '';
    await page.route('**/api/sessions', (route) => {
      submittedSessionForm = route.request().postDataBuffer()?.toString('utf8') || '';
      return route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Mock session create failure' }),
      });
    });

    await page.goto('/');
    await page.evaluate(() => {
      document.cookie = 'bugai_token=e2e-test-token; path=/';
    });
    await page.goto('/live-lab');
    const inputType = page.getByRole('combobox', { name: 'Requirements input type' });
    const requirements = page.getByRole('textbox', { name: 'Requirements text' });

    await expect(requirements).toHaveValue('Default requirement.');
    await inputType.selectOption('pdf');
    await expect(inputType).toHaveValue('pdf');
    await page.getByRole('button', { name: 'Choose PDF' }).click();
    await page.getByLabel('Requirements upload file').setInputFiles({
      name: 'checkout_requirements.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('dummy PDF'),
    });
    await expect(requirements).toHaveValue('Requirement from PDF.');

    await inputType.selectOption('document');
    await page.getByRole('button', { name: 'Choose Document' }).click();
    await page.getByLabel('Requirements upload file').setInputFiles({
      name: 'requirements.docx',
      mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      buffer: Buffer.from('dummy document'),
    });
    await expect(requirements).toHaveValue('Requirement from document.');

    await inputType.selectOption('diagram');
    await page.getByRole('button', { name: 'Choose Image' }).click();
    await page.getByLabel('Flowchart image file').setInputFiles({
      name: 'flowchart.png',
      mimeType: 'image/png',
      buffer: Buffer.from('dummy image'),
    });
    await expect(page.getByAltText('Uploaded diagram')).toBeVisible();
    await expect(page.getByText('DIAGRAM PREVIEW · flowchart.png')).toBeVisible();
    await expect(requirements).toHaveValue(
      'Requirement from document.\nRequirement from flowchart.'
    );

    await page.getByLabel('Flowchart image file').setInputFiles({
      name: 'failed-flowchart.png',
      mimeType: 'image/png',
      buffer: Buffer.from('dummy image'),
    });
    await expect(page.getByText('Vision service unavailable.')).toBeVisible();
    await expect(page.getByAltText('Uploaded diagram')).toBeVisible();
    await expect(page.getByText('DIAGRAM PREVIEW · failed-flowchart.png')).toBeVisible();

    await inputType.selectOption('pdf');
    await page.getByRole('button', { name: 'Choose PDF' }).click();
    await page.getByLabel('Requirements upload file').setInputFiles({
      name: 'checkout_requirements.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('dummy PDF'),
    });
    await expect(requirements).toHaveValue('Requirement from PDF.');
    await page.getByTestId('run-analysis').click();
    await expect(page.getByText('Mock session create failure')).toBeVisible();
    expect(submittedSessionForm).toContain('Requirement from PDF.');
  });

  test('rapid Run Analysis activations create only one session', async ({ page }) => {
    test.setTimeout(60_000);
    let createRequests = 0;
    let notifyCreateRequest!: () => void;
    const createRequestStarted = new Promise<void>((resolve) => {
      notifyCreateRequest = resolve;
    });

    await page.route('**/api/health', (route) =>
      route.fulfill({ json: { status: 'ok' } })
    );
    await page.route('**/api/examples', (route) =>
      route.fulfill({
        json: {
          filename: 'sample_source.py',
          source_code: 'def sample():\n    return True\n',
          requirements_text: 'sample requirement',
        },
      })
    );
    await page.route('**/api/github/status', (route) =>
      route.fulfill({ json: { connected: false } })
    );
    await page.route('**/api/sessions', async (route) => {
      createRequests += 1;
      notifyCreateRequest();
      await new Promise((resolve) => setTimeout(resolve, 750));
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Mock create failure' }),
      });
    });

    await page.goto('/');
    await page.evaluate(() => {
      document.cookie = 'bugai_token=e2e-test-token; path=/';
    });
    await page.goto('/live-lab');
    const runButton = page.getByRole('button', { name: 'Run Analysis' });
    await expect(runButton).toBeEnabled({ timeout: 60_000 });
    await page.waitForTimeout(500);
    await runButton.evaluate((button: HTMLElement) => {
      button.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      button.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    await createRequestStarted;
    await page.waitForTimeout(100);
    expect(createRequests).toBe(1);
    await expect(page.getByText('Mock create failure')).toBeVisible();
  });

  test('backend health when server is running', async () => {
    test.skip(!process.env.E2E_BACKEND_URL && !process.env.CI_WITH_BACKEND, 'Set E2E_BACKEND_URL to run API smoke tests.');
    const res = await fetch(`${backendUrl}/api/health`);
    expect(res.ok).toBeTruthy();
    const body = await res.json();
    expect(body.status).toBe('ok');
  });
});
