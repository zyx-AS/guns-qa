import type { Page } from '@playwright/test';
import { expect } from '@playwright/test';
import { env, joinUrl, requiredEnv } from './env';

type LoginResponse = {
  success: boolean;
  code: string;
  message: string;
  data?: {
    token?: string;
  };
};

export async function login(page: Page): Promise<void> {
  const baseURL = requiredEnv('APP_BASE_URL');
  const username = requiredEnv('APP_USERNAME');
  const password = requiredEnv('APP_PASSWORD');
  const loginApiPath = env('LOGIN_API_PATH', '/api/loginApi');

  const response = await page.request.post(joinUrl(baseURL, loginApiPath), {
    data: {
      account: username,
      password,
    },
  });

  const payload = (await response.json()) as LoginResponse;
  if (!response.ok() || !payload.success || !payload.data?.token) {
    throw new Error(`Login API failed: ${response.status()} ${JSON.stringify(payload)}`);
  }

  const token = payload.data.token;
  await page.context().setExtraHTTPHeaders({ Authorization: token });
  await page.addInitScript((value: string) => {
    window.localStorage.setItem('access_token', value);
  }, token);

  await page.goto(baseURL, { waitUntil: 'networkidle' });
  await expect(page.locator('#app')).toBeVisible();
}
