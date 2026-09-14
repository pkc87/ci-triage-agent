import { test, expect } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.goto('/');
});

test('a mixed cart adds up to subtotal, handling, tax and total', async ({ page }) => {
  // 2 x Aeropress Go (39.95) + 3 x Filter Papers (8.25) = 104.65 in goods.
  await page.getByTestId('add-p1').click();
  await page.getByTestId('qty-p1').fill('2');
  await page.getByTestId('qty-p1').blur();

  await page.getByTestId('add-p4').click();
  await page.getByTestId('qty-p4').fill('3');
  await page.getByTestId('qty-p4').blur();

  await expect(page.getByTestId('subtotal')).toHaveText('$104.65');
  await expect(page.getByTestId('handling')).toHaveText('$2.50');
  await expect(page.getByTestId('tax')).toHaveText('$8.63');
  await expect(page.getByTestId('total')).toHaveText('$115.78');
});

test('a promo code discounts the gross amount, after tax', async ({ page }) => {
  await page.getByTestId('add-p1').click();
  await expect(page.getByTestId('total')).toHaveText('$45.75');

  await page.getByTestId('discount-code').fill('WELCOME10');
  await page.getByTestId('apply-discount').click();

  // 10% of the gross 45.75 is 4.58, not 10% of the 39.95 in goods.
  await expect(page.getByTestId('discount-status')).toHaveText('Code WELCOME10 applied');
  await expect(page.getByTestId('discount')).toHaveText('-$4.58');
  await expect(page.getByTestId('total')).toHaveText('$41.17');
});

test('an unknown promo code changes nothing', async ({ page }) => {
  await page.getByTestId('add-p1').click();
  await page.getByTestId('discount-code').fill('NOPE99');
  await page.getByTestId('apply-discount').click();

  await expect(page.getByTestId('discount-status')).toHaveText('Unknown promo code');
  await expect(page.getByTestId('discount')).toHaveText('-$0.00');
  await expect(page.getByTestId('total')).toHaveText('$45.75');
});

test('applying the same promo code twice does not stack it', async ({ page }) => {
  await page.getByTestId('add-p1').click();
  await page.getByTestId('discount-code').fill('SAVE20');

  await page.getByTestId('apply-discount').click();
  await expect(page.getByTestId('total')).toHaveText('$36.60');

  await page.getByTestId('apply-discount').click();
  await expect(page.getByTestId('discount')).toHaveText('-$9.15');
  await expect(page.getByTestId('total')).toHaveText('$36.60');
});
