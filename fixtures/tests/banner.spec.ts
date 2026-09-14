import { test, expect } from '@playwright/test';

const MESSAGES = [
  'Free shipping on orders over $50',
  'Roasted to order, shipped same day',
  'Use code WELCOME10 for 10% off',
];

test('the promo banner cycles through every message', async ({ page }) => {
  await page.goto('/');

  const banner = page.getByTestId('banner');
  await expect(banner).toBeVisible();

  // The banner starts on a random message and rotates every 400 ms, so sample
  // it for longer than one full cycle instead of assuming a starting point.
  const seen = await page.evaluate(
    (durationMs) =>
      new Promise<string[]>((resolve) => {
        const element = document.querySelector('[data-testid="banner"]')!;
        const collected = new Set<string>();
        const sampler = setInterval(() => {
          collected.add((element.textContent ?? '').trim());
        }, 50);
        setTimeout(() => {
          clearInterval(sampler);
          resolve([...collected]);
        }, durationMs);
      }),
    1600,
  );

  expect(seen.sort()).toEqual([...MESSAGES].sort());
});
