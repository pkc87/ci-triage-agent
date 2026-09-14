import { test, expect } from '@playwright/test';

test('the order summary panel matches the visual baseline', async ({ page }) => {
  await page.goto('/');

  await page.getByTestId('add-p1').click();
  await page.getByTestId('qty-p1').fill('2');
  await page.getByTestId('qty-p1').blur();
  await expect(page.getByTestId('total')).toHaveText('$88.99');

  await expect(page.getByTestId('summary-panel')).toHaveScreenshot('summary-panel.png');
});
