import { test, expect } from '@playwright/test';

// The promo bar should read as a solid colour, not a washed out one.
test('the promo banner stays fully opaque', async ({ page }) => {
  await page.goto('/');

  // Do a little shopping first, the way a real visit would.
  await page.getByTestId('load-reviews').click();
  await expect(page.getByTestId('average-rating')).toBeVisible();

  const opacity = await page
    .getByTestId('banner')
    .evaluate((element) => Number(getComputedStyle(element).opacity));

  expect(opacity).toBeGreaterThan(0.95);
});
