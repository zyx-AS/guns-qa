# GUNS frontend integration testing

This folder migrates the Playwright-based frontend integration tests for `GUNSQA-85` to `GUNSQA-88` into `zyx-AS/guns-qa` without modifying the existing Java unit-test flow.

## Isolation contract

- No existing repository files are edited.
- The current root workflow `.github/workflows/ci.yml` remains untouched.
- All frontend assets live under `frontend-it/`.
- A new workflow `.github/workflows/frontend-it.yml` runs only this isolated suite.

## Scope

- `GUNSQA-85`: certificate attachment preview should not fail because `router` is undefined
- `GUNSQA-86`: non-Excel files should be blocked before hitting the import preview API
- `GUNSQA-87`: download URLs must not expose `token=` query parameters
- `GUNSQA-88`: upload failure responses must not be shown as successful uploads

## Live target

Defaults point at the deployed GUNS instance:

- Base URL: `http://101.200.163.141`
- Login API: `POST /api/loginApi`
- Username: `admin`
- Password: `APP_PASSWORD` secret

## Workflow shape

1. Branch naming stays `GUNSQA-xx-*`.
2. `frontend-it/config/xray-test-executions.json` maps Jira Test issues to Playwright grep selectors.
3. `.github/workflows/frontend-it.yml` resolves Jira context, runs one mapped Playwright test, then reuses the same Jira/Xray/Bug comment loop.
4. Existing root unit-test automation remains untouched.

## Local run

```bash
cd frontend-it
npm install
npx playwright install chromium
APP_PASSWORD='your-password' python scripts/resolve_test_context.py --mapping-path config/xray-test-executions.json --github-ref-name GUNSQA-85-local
APP_PASSWORD='your-password' python scripts/run_frontend_it.py
```
