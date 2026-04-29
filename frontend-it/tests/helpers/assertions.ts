import { expect, type Locator, type Page, type Request } from '@playwright/test';
import { env, selector } from './env';

export function collectRequests(page: Page): Request[] {
  const requests: Request[] = [];
  page.on('request', (request) => requests.push(request));
  return requests;
}

export function collectPageErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(String(error.message || error)));
  return errors;
}

export async function expectToastVisible(page: Page, text: string): Promise<void> {
  const toast = page.locator(selector('TOAST_SELECTOR', `.ant-message-notice:has-text("${text}"), .el-message:has-text("${text}")`)).first();
  await expect(toast).toBeVisible();
}

export async function expectToastNotVisible(page: Page, text: string): Promise<void> {
  const toast = page.locator(selector('TOAST_SELECTOR', `.ant-message-notice:has-text("${text}"), .el-message:has-text("${text}")`)).first();
  await expect(toast).toHaveCount(0);
}

export async function optionalClick(locator: Locator): Promise<void> {
  if (await locator.count()) {
    await locator.first().click();
  }
}

export function apiFragment(name: string, fallback: string): string {
  return env(name, fallback);
}
