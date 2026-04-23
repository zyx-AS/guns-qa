# Repository Instructions

## Standard test workflow

- Jira `Test` issues replace per-case README files.
- `config/xray-test-executions.json` is the only automation mapping file.
- Every managed `GUNSQA-*` Test issue must declare `testClass` and `testExecutionKey`.
- Branch names for managed test work should start with the Jira key, for example `GUNSQA-52-password-trim`.
- Do not rely on a default test class. The workflow now requires an explicit mapped or manual `testClass`.
- Do not create ad-hoc Xray Test Executions for the managed flow. Reuse the mapped stable execution.
- Do not reintroduce `guns-tests/docs/**` per-case documentation. Put test design in Jira and execution evidence in Jira/Xray.

## Repo change rules

- Store Java test assets under `guns-tests/src/test/java/...`.
- Update `config/xray-test-executions.json` in the same change when adding or renaming a managed Jira Test issue.
- Keep Jira Test issue keys business-readable. Do not create or preserve method-named placeholder Test issues.
- If an automated run reveals a product defect, capture the readable analysis in a Jira `Bug`, not in a long machine-written comment.
