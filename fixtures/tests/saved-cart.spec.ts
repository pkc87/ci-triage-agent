import { test, expect } from '@playwright/test';

test('a saved cart can be restored after a reload', async ({ page }) => {
  await page.goto('/');

  await page.getByTestId('add-p2').click();
  await page.getByTestId('add-p2').click();
  await expect(page.getByTestId('cart-badge')).toHaveText('2 items');

  await page.getByTestId('save-cart').click();
  await expect(page.getByTestId('cart-sync-status')).toHaveText('Cart saved');

  await page.reload();
  await expect(page.getByTestId('cart-badge')).toHaveText('0 items');

  await page.getByTestId('restore-cart').click();
  await expect(page.getByTestId('cart-sync-status')).toHaveText('Cart restored');
  await expect(page.getByTestId('cart-row-p2')).toBeVisible();
  await expect(page.getByTestId('cart-badge')).toHaveText('2 items');
});
