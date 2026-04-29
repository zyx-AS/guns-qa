import { expect, test } from '@playwright/test';
import { collectPageErrors } from '../helpers/assertions';
import { selector } from '../helpers/env';
import { login } from '../helpers/auth';
import { gotoUserDetailPage } from '../helpers/navigation';

test('GUNSQA-85 @GUNSQA-85 user certificate attachment preview should not crash on undefined router', async ({ page }) => {
  const errors = collectPageErrors(page);
  let stage = 'login';

  await login(page);
  await gotoUserDetailPage(page);

  const userNameLinks = page.locator(
    selector('USER_NAME_LINK_SELECTOR', '.table-content .ant-table-tbody a:visible, .table-content .vxe-body--row a:visible')
  );
  const totalUsers = Math.min(await userNameLinks.count(), 12);

  let foundAttachment = false;
  let popupOpened = false;
  let sameTabPreview = false;

  for (let index = 0; index < totalUsers; index += 1) {
    stage = `open detail drawer for row ${index + 1}`;
    await expect(userNameLinks.nth(index), `User link missing during stage: ${stage}`).toBeVisible();
    await userNameLinks.nth(index).click();

    const detailDrawer = page.locator(selector('USER_DETAIL_MODAL_SELECTOR', 'text=用户信息')).first();
    await expect(detailDrawer, `Detail drawer was not visible during stage: ${stage}`).toBeVisible();

    stage = `switch certificate tab for row ${index + 1}`;
    await page.getByText('用户证书', { exact: false }).first().click();

    stage = `search attachment for row ${index + 1}`;
    const attachmentLinks = page.locator(selector('CERT_ATTACHMENT_SELECTOR', '.filename a:visible'));
    if (await attachmentLinks.count()) {
      foundAttachment = true;
      stage = `click attachment preview for row ${index + 1}`;
      const popupPromise = page.waitForEvent('popup', { timeout: 3000 }).catch(() => null);
      const beforeUrl = page.url();
      await attachmentLinks.first().click();
      const popup = await popupPromise;
      await page.waitForTimeout(800);

      popupOpened = popup !== null;
      sameTabPreview = page.url() !== beforeUrl;
      if (popup) {
        await popup.waitForLoadState('domcontentloaded').catch(() => null);
      }
      break;
    }

    stage = `close detail drawer for row ${index + 1}`;
    const closeButton = page.locator(
      selector('USER_DETAIL_CLOSE_SELECTOR', '.ant-drawer-close:visible, .ant-modal-close:visible, [aria-label="Close"]:visible')
    ).first();
    if (await closeButton.count()) {
      await closeButton.click();
    } else {
      await page.keyboard.press('Escape');
    }
    await expect(detailDrawer).toHaveCount(0);
    await page.waitForTimeout(300);
  }

  expect(foundAttachment, 'No existing user with a certificate attachment was found in the scanned rows.').toBeTruthy();
  expect(errors.some((item) => item.includes('router is not defined')), `router error detected during stage: ${stage}; errors=${errors.join(' | ')}`).toBeFalsy();
  expect(popupOpened || sameTabPreview, `Preview did not open during stage: ${stage}`).toBeTruthy();
});
