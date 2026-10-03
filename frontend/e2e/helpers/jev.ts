import type { Page } from '@playwright/test';

export function jevEnabled(): boolean {
  return Boolean(process.env.OPENROUTER_API_KEY || process.env.TYPESAFE_API_KEY);
}

export async function createOptionalJev(page: Page) {
  if (!jevEnabled()) {
    return null;
  }
  try {
    const mod = await import('playwright-jev');
    return mod.createJev(page);
  } catch {
    return null;
  }
}
