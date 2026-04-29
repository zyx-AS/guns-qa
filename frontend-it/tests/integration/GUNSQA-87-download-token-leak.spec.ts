import { expect, test } from '@playwright/test';
import { login } from '../helpers/auth';
import { selector } from '../helpers/env';
import { gotoFilePage } from '../helpers/navigation';

test('GUNSQA-87 @GUNSQA-87 download flow should not expose token in the URL', async ({ page }) => {
  const downloadUrls: string[] = [];
  await page.route('**/sysFileInfo/*Download**', async (route) => {
    downloadUrls.push(route.request().url());
    await route.fulfill({
      status: 200,
      contentType: 'application/octet-stream',
      body: 'mock-download',
    });
  });

  await login(page);
  await gotoFilePage(page);

  await page.locator(selector('FILE_DOWNLOAD_SELECTOR', '.table-content [title="下载"]:visible, .table-content .icon-opt-xiazai:visible')).first().click();
  await expect.poll(() => downloadUrls.length).toBeGreaterThan(0);
  expect(downloadUrls.some((url) => /[?&]token=/.test(url))).toBeFalsy();
});
