import type { Page } from '@playwright/test';
import { env, joinUrl, requiredEnv } from './env';

export async function gotoFilePage(page: Page): Promise<void> {
  await page.goto(joinUrl(requiredEnv('APP_BASE_URL'), env('FILE_PAGE_PATH', '/system/backend/file')), { waitUntil: 'networkidle' });
}

export async function gotoFileUploadPage(page: Page): Promise<void> {
  await page.goto(joinUrl(requiredEnv('APP_BASE_URL'), env('FILE_UPLOAD_PAGE_PATH', '/system/backend/file')), { waitUntil: 'networkidle' });
}

export async function gotoUserImportPage(page: Page): Promise<void> {
  await page.goto(joinUrl(requiredEnv('APP_BASE_URL'), env('USER_IMPORT_PAGE_PATH', '/system/structure/user')), { waitUntil: 'networkidle' });
}

export async function gotoUserDetailPage(page: Page): Promise<void> {
  await page.goto(joinUrl(requiredEnv('APP_BASE_URL'), env('USER_DETAIL_PAGE_PATH', '/system/structure/user')), { waitUntil: 'networkidle' });
}
