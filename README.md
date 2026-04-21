# guns-qa

Minimal QA repository used to verify the baseline workflow for:

- `pytest`
- GitHub Actions CI
- Jira issue based branch / commit / pull request linking

## CI

The workflow is defined in `.github/workflows/ci.yml`.

- Push to `main` triggers CI
- Opening or updating a pull request triggers CI
- The test command is `pytest -q`

## Standard Jira-driven Git Flow

Use a normal Jira task to carry development work instead of reusing Xray issue types.

Example flow:

1. Create or choose a Jira task such as `GUNSQA-30`
2. Create a branch like `GUNSQA-30-add-ci-jira-guide`
3. Commit with a message like `GUNSQA-30 add CI and Jira workflow note`
4. Open a pull request with a title like `GUNSQA-30 add CI and Jira workflow note`
5. Check the Jira issue Development panel for branch, commit, and PR activity

## Current Test Baseline

The repository currently includes a smoke test in `tests/test_smoke.py` to confirm that the CI pipeline runs successfully before real GUNS test cases are added.
