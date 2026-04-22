# Repository Instructions

## Testing Documentation

- Every new test case added under `guns-tests/src/test/` must have a matching teacher-readable README under `guns-tests/docs/<type>/<test-id>/README.md`.
- Valid documentation categories are `unit`, `integration`, `system`, and `performance`.
- Numbering conventions are fixed across the repository:
  - `UT-模块-序号`
  - `IT-链路-序号`
  - `ST-场景-序号`
  - `PT-场景-序号`
- The canonical template lives in `docs/testing/test-readme-template.md`.
- Reference examples live in `docs/testing/examples/`.
- Use `scripts/new-test-doc.ps1` or `scripts/new-test-doc.sh` to scaffold a new test README before filling in project-specific details.

## Required README Structure

Every case README under `guns-tests/docs/<type>/<test-id>/README.md` must contain:

1. A metadata table with these rows:
   - `测试类型`
   - `测试编号`
   - `对应代码`
   - `Jira`
   - `GitHub 工作流`
2. These section headings in order:
   - `## 1. 测试目的`
   - `## 2. 测试方法与设计依据`
   - `## 3. 前置条件`
   - `## 4. 测试步骤`
   - `## 5. 预期结果`
   - `## 6. 实际结果`
   - `## 7. 结论`
   - `## 8. 测试过程中的差异情况`

## Writing Rules

- Keep the README teacher-readable. Summarize the result in natural language instead of pasting raw XML, full logs, or long stack traces into the正文.
- Put raw execution evidence in GitHub Actions artifacts or Jira attachments, then reference them in the README.
- Update `guns-tests/docs/README.md` and the corresponding category index when adding or removing a documented test case.
- If a test file is renamed or moved, update the `对应代码` row in the README in the same change.

## Validation

- The workflow `.github/workflows/validate-test-docs.yml` validates test documentation structure.
- Commits that add or change tests should keep the documentation check green before merge.
