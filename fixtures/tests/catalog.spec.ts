import { test, expect } from '@playwright/test';

const PRODUCT_NAMES = ['Aeropress Go', 'Burr Grinder', 'Gooseneck Kettle', 'Filter Papers'];

test.beforeEach(async ({ page }) => {
  await page.goto('/');
});

test('the catalog lists every product', async ({ page }) => {
  const cards = page.getByTestId('product-grid').locator('li');
  await expect(cards).toHaveCount(4);
  for (const name of PRODUCT_NAMES) {
    await expect(page.getByRole('heading', { name, exact: true })).toBeVisible();
  }
});

test('every product card offers an add-to-cart button', async ({ page }) => {
  const button = page.getByTestId('add-p2');
  await expect(button).toBeVisible();
  await expect(button).toHaveText('Add to cart');
});

test('the recommendations strip shows three distinct products', async ({ page }) => {
  const items = page.getByTestId('rec-item');
  await expect(items).toHaveCount(3);

  const names = await items.allTextContents();
  expect(new Set(names).size).toBe(3);
  for (const name of names) {
    expect(PRODUCT_NAMES).toContain(name);
  }
});
