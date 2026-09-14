import { test, expect } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.goto('/');
  await page.getByTestId('add-p1').click();
});

test('checkout rejects an empty email address', async ({ page }) => {
  await page.getByTestId('name').fill('Dana Fisher');
  await page.getByTestId('email').fill('');
  await page.getByTestId('zip').fill('94110');
  await page.getByTestId('place-order').click();

  await expect(page.getByTestId('form-error')).toBeVisible();
  await expect(page.getByTestId('form-error')).toContainText('Enter a valid email address');
  await expect(page.getByTestId('order-confirmation')).toBeHidden();
});

test('checkout requires a five digit zip code', async ({ page }) => {
  await page.getByTestId('name').fill('Dana Fisher');
  await page.getByTestId('email').fill('dana@example.com');
  await page.getByTestId('zip').fill('941');
  await page.getByTestId('place-order').click();

  await expect(page.getByTestId('form-error')).toContainText('ZIP code must be 5 digits');
  await expect(page.getByTestId('order-confirmation')).toBeHidden();
});

test('a complete order shows a confirmation and empties the cart', async ({ page }) => {
  await page.getByTestId('name').fill('Dana Fisher');
  await page.getByTestId('email').fill('dana@example.com');
  await page.getByTestId('zip').fill('94110');
  await page.getByTestId('place-order').click();

  const confirmation = page.getByTestId('order-confirmation');
  await expect(confirmation).toBeVisible();
  await expect(confirmation).toHaveText(/^Order #[A-Z0-9]{6} placed on [A-Z][a-z]+ \d{1,2}, \d{4}$/);

  await expect(page.getByTestId('form-error')).toBeHidden();
  await expect(page.getByTestId('cart-empty')).toBeVisible();
  await expect(page.getByTestId('total')).toHaveText('$0.00');
});
