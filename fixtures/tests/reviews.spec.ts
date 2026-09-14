import { test, expect } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.goto('/');
});

test('the reviews section offers a load action', async ({ page }) => {
  const button = page.getByTestId('load-reviews');
  await expect(button).toBeVisible();
  await expect(button).toHaveText('Load reviews');
  await expect(page.getByTestId('reviews-list').locator('li')).toHaveCount(0);
});

test('loading reviews renders every approved review with the average', async ({ page }) => {
  await page.getByTestId('load-reviews').click();

  await expect(page.getByTestId('review-item')).toHaveCount(4);
  await expect(page.getByTestId('average-rating')).toBeVisible();
  await expect(page.getByTestId('average-rating')).toHaveText('Average rating: 4.3 out of 5');
  await expect(page.getByTestId('reviews-spinner')).toBeHidden();
});

test('the average rating ignores reviews that are not approved', async ({ page }) => {
  await page.getByTestId('load-reviews').click();
  await expect(page.getByTestId('average-rating')).toBeVisible();

  const authors = await page.getByTestId('review-item').locator('.review-author').allTextContents();
  expect(authors).not.toContain('unverified buyer');
  await expect(page.getByTestId('average-rating')).not.toHaveText('Average rating: 3.6 out of 5');
});
