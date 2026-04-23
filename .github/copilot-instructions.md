# GitHub Copilot Instructions

When adding or updating tests in this repository:

- Treat Jira `Test` issues as the design source of truth.
- Update `config/xray-test-executions.json` whenever a managed `GUNSQA-*` test is added or renamed.
- Add Java test assets under `guns-tests/src/test/java/...`.
- Do not add per-case README files under `guns-tests/docs/`.
- Do not rely on a default test class or a newly created Xray Test Execution.
- Keep Jira comments short and machine-oriented. Put readable defect analysis in a Jira `Bug`.
