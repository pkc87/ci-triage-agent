import { test, expect } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.goto('/');
});

test('adding a product puts it in the cart', async ({ page }) => {
  await page.getByTestId('add-p1').click();

  await expect(page.getByTestId('cart-row-p1')).toBeVisible();
  await expect(page.getByTestId('cart-empty')).toBeHidden();
  await expect(page.getByTestId('line-total-p1')).toHaveText('$39.95');
  await expect(page.getByTestId('subtotal')).toHaveText('$39.95');
});

test('changing the quantity updates the line total', async ({ page }) => {
  await page.getByTestId('add-p3').click();
  await page.getByTestId('qty-p3').fill('4');
  await page.getByTestId('qty-p3').blur();

  await expect(page.getByTestId('line-total-p3')).toHaveText('$258.00');
  await expect(page.getByTestId('subtotal')).toHaveText('$258.00');
});

test('removing the last item zeroes the whole summary', async ({ page }) => {
  await page.getByTestId('add-p4').click();
  await expect(page.getByTestId('total')).toHaveText('$11.43');

  await page.getByTestId('remove-p4').click();

  await expect(page.getByTestId('cart-empty')).toBeVisible();
  await expect(page.getByTestId('subtotal')).toHaveText('$0.00');
  await expect(page.getByTestId('handling')).toHaveText('$0.00');
  await expect(page.getByTestId('tax')).toHaveText('$0.00');
  await expect(page.getByTestId('total')).toHaveText('$0.00');
});

test('a negative quantity is clamped to one', async ({ page }) => {
  await page.getByTestId('add-p1').click();
  await page.getByTestId('qty-p1').fill('-3');
  await page.getByTestId('qty-p1').blur();

  await expect(page.getByTestId('qty-p1')).toHaveValue('1');
  await expect(page.getByTestId('line-total-p1')).toHaveText('$39.95');
  await expect(page.getByTestId('total')).toHaveText('$45.75');
});

test('the cart badge counts units, not lines', async ({ page }) => {
  await expect(page.getByTestId('cart-badge')).toHaveText('0 items');

  await page.getByTestId('add-p1').click();
  await expect(page.getByTestId('cart-badge')).toHaveText('1 item');

  await page.getByTestId('add-p1').click();
  await page.getByTestId('add-p4').click();
  await expect(page.getByTestId('cart-badge')).toHaveText('3 items');
});
