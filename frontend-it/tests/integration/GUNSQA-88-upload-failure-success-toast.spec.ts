import { expect, test } from '@playwright/test';
import { login } from '../helpers/auth';
import { fixture, selector } from '../helpers/env';
import { gotoFileUploadPage } from '../helpers/navigation';

test('GUNSQA-88 @GUNSQA-88 upload failure must not be reported as success', async ({ page }) => {
  let interceptedUploadUrl = '';
  await login(page);

  await page.route('**/sysFileInfo/upload**', async (route) => {
    const requestUrl = route.request().url();
    if (!requestUrl.includes('fileLocation=5')) {
      await route.continue();
      return;
    }

    interceptedUploadUrl = requestUrl;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ code: 500, success: false, message: 'mock upload failure' }),
    });
  });

  await gotoFileUploadPage(page);

  await page.evaluate(() => {
    const key = '__gunsQaToastMessages';
    const targetSelectors = ['.ant-message', '.ant-message-notice'];
    const store = ((window as unknown as Record<string, unknown[]>)[key] = []);

    const capture = () => {
      const texts = Array.from(document.querySelectorAll(targetSelectors.join(',')))
        .map((node) => (node.textContent || '').trim())
        .filter(Boolean);
      for (const text of texts) {
        if (!store.includes(text)) {
          store.push(text);
        }
      }
    };

    capture();
    const observer = new MutationObserver(() => capture());
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
    (window as unknown as Record<string, unknown>).__gunsQaToastObserver = observer;
  });

  const uploadInputs = page.locator(selector('FILE_UPLOAD_INPUT_SELECTOR', '.header-content-right .ant-upload input[type="file"]'));
  expect(await uploadInputs.count()).toBeGreaterThan(1);
  await uploadInputs.nth(1).setInputFiles(fixture('tests/fixtures/upload-sample.txt'));
  await expect.poll(() => interceptedUploadUrl).not.toBe('');
  await page.waitForTimeout(1500);

  const toastMessages = await page.evaluate(() => {
    return ((window as unknown as Record<string, string[]>).__gunsQaToastMessages || []).slice();
  });

  expect(
    toastMessages.some((message) => message.includes('上传成功')),
    `Unexpected toast history: ${toastMessages.join(' | ') || 'no toast captured'}`
  ).toBeFalsy();
});
