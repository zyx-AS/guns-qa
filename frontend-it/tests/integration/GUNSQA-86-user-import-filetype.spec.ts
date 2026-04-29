import { expect, test } from '@playwright/test';
import { apiFragment } from '../helpers/assertions';
import { login } from '../helpers/auth';
import { fixture, selector } from '../helpers/env';
import { gotoUserImportPage } from '../helpers/navigation';

test('GUNSQA-86 @GUNSQA-86 non-Excel files should be blocked before import preview API is called', async ({ page }) => {
  let previewCalled = false;
  const previewApi = apiFragment('USER_IMPORT_PREVIEW_API', '/userImport/uploadAndGetPreviewData');
  await page.route(`**${previewApi}**`, async (route) => {
    previewCalled = true;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ code: '500', success: false, message: 'mock preview call' }),
    });
  });

  await login(page);
  await gotoUserImportPage(page);

  await page.getByRole('button', { name: '更多' }).click();
  await page.getByText('导入导出', { exact: true }).last().click();
  await expect(page.getByText('导入导出用户', { exact: true })).toBeVisible();
  await expect(page.getByText('上传Excel', { exact: true })).toBeVisible();

  await page.locator(selector('USER_IMPORT_FILE_INPUT_SELECTOR', '.import-content .ant-upload input[type="file"]')).setInputFiles(
    fixture('tests/fixtures/not-excel.txt')
  );
  await page.waitForTimeout(1500);

  expect(previewCalled).toBeFalsy();
});
