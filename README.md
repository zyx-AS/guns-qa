# guns-qa

`guns-qa` stores reusable GUNS test assets plus the GitHub/Jira/Xray automation that runs them.

## Standard flow

The standard path starts from `main`, then uses a Jira Test issue as the source of truth:

1. Create or update a Jira `Test` issue such as `GUNSQA-51`.
2. Put the test design in Jira, not in a per-case repository README.
3. Register the Jira Test issue in `config/xray-test-executions.json`.
4. Create a branch from `main` named `GUNSQA-xx-...`.
5. Add or update the Java test under `guns-tests/src/test/...`.
6. Push the branch and let GitHub Actions resolve the Jira key, test class, and stable Xray Test Execution from the mapping file.
7. Review the execution result in Jira/Xray. If the run reveals a defect, create a Jira `Bug` for the human-readable analysis.

## Source of truth

- Jira `Test` issues hold the test design.
- `config/xray-test-executions.json` is the only automation mapping file.
- Jira `Test Execution` issues hold execution history.
- Jira `Bug` issues hold readable failure analysis.
- Per-case README files under `guns-tests/docs/` are deprecated and intentionally removed.

## Mapping rules

Each managed `GUNSQA-*` Test issue must define:

- `testClass`
- `testExecutionKey`

Optional fields:

- `gunsRef`
- `note`

The Jira issue key itself is treated as the Xray `Test` issue key. The workflow does not fall back to a default test class, does not create a new Xray Test Execution automatically, and does not allow Xray to auto-create method-named Test issues for the managed path.

## GitHub Actions behavior

`.github/workflows/ci.yml` now enforces the generic managed flow:

- Runs automatically for `GUNSQA-*` branches.
- Resolves the Jira key and mapped test class before execution.
- Fails fast if a managed Jira Test issue is missing required mapping fields.
- Reuses the mapped stable Xray Test Execution instead of creating a new one.
- Imports the result back into the existing Jira Test and Test Execution.
- Posts short Jira comments as machine-written execution breadcrumbs.

## Local reproduction

Use an explicit test class. There is no default fallback test anymore.

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_guns_unit_test.ps1 -TestClass "fully.qualified.TestClass"
```

Linux or macOS:

```bash
bash scripts/run_guns_unit_test.sh --test-class fully.qualified.TestClass
```

## Current managed examples

- `GUNSQA-51` -> `SysUserServiceDetailTest` -> stable execution `GUNSQA-50`
- `GUNSQA-52` -> `SysUserServiceEditPasswordTrimRepeatTest` -> stable execution `GUNSQA-50`
