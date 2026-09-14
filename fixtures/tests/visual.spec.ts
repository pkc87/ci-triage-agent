import { existsSync } from 'node:fs';

import { test, expect } from '@playwright/test';

/**
 * Playwright suffixes snapshot names with the platform, so a baseline recorded
 * on Windows is not the file Linux goes looking for. Only the win32 baseline is
 * committed here, because that is the machine the corpus was generated on.
 *
 * On any other platform this test would fail for a reason that has nothing to
 * do with the code under test -- which is, with some irony, exactly one of the
 * failure classes this repository triages (see eval/cases/hist-008, and the
 * KAPUTTER_TEST definition in docs/fallformat.md). Failing red in CI to
 * demonstrate that would be cute and useless, so it skips with the reason
 * stated instead.
 *
 * To record a baseline for your platform:
 *   cd fixtures && npx playwright test visual --update-snapshots
 */
test('the order summary panel matches the visual baseline', async ({ page }, testInfo) => {
  // testInfo resolves the platform-suffixed path Playwright will actually compare
  // against, so this cannot drift from the naming scheme.
  const baseline = testInfo.snapshotPath('summary-panel.png');
  test.skip(
    !existsSync(baseline),
    `no committed baseline for platform "${process.platform}" ` +
      '(only win32 is committed; run with --update-snapshots to record one)',
  );

  await page.goto('/');

  await page.getByTestId('add-p1').click();
  await page.getByTestId('qty-p1').fill('2');
  await page.getByTestId('qty-p1').blur();
  await expect(page.getByTestId('total')).toHaveText('$88.99');

  await expect(page.getByTestId('summary-panel')).toHaveScreenshot('summary-panel.png');
});
