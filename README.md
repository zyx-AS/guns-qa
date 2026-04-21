# guns-qa

Public QA repository used to verify that GitHub-hosted runners can execute a
real unit test against the open-source GUNS codebase.

## What This Repo Does

- Stores the workflow and helper scripts for GUNS-based test execution
- Stores the GUNS-specific test assets under `guns-tests/`
- Uses GitHub-hosted runners instead of a weak shared server
- Pulls the upstream open-source GUNS source code at run time
- Keeps Jira issue based branch / commit / pull request linking

## Current CI Workflow

The workflow is defined in `.github/workflows/ci.yml`.

By default it will:

1. Start a GitHub-hosted Ubuntu runner
2. Set up Java 17 automatically
3. Clone the upstream GUNS repository from Gitee, with GitCode as a fallback
4. Check out the pinned GUNS revision
5. Copy the repo's test assets into the cloned GUNS workspace
6. Run one real GUNS unit test:
   `cn.stylefeng.guns.core.security.BlackWhiteInterceptorTest`
7. Upload surefire reports and run metadata as artifacts

The default pinned upstream revision is:

`84272f5a324e0d7890d241d7ae9afa7398da49fa`

## Standard Jira-driven Git Flow

Use a normal Jira task to carry development work instead of reusing Xray issue types.

Example flow:

1. Create or choose a Jira task such as `GUNSQA-32`
2. Create a branch like `GUNSQA-32-guns-runner-workflow`
3. Commit with a message like `GUNSQA-32 configure GUNS unit test workflow`
4. Open a pull request with a title like `GUNSQA-32 configure GUNS unit test workflow`
5. Check the Jira issue Development panel for branch, commit, PR, and workflow activity

## Local Reproduction

Windows users can run the same test flow locally with PowerShell. The script
will use Docker when it is available, and fall back to a portable Maven
download when Docker is unavailable.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_guns_unit_test.ps1
```

Linux or macOS users can run:

```bash
bash scripts/run_guns_unit_test.sh
```

Both scripts clone GUNS into a temporary workspace, execute the selected test,
inject the test assets from `guns-tests/`, and collect surefire reports under
`.artifacts/guns/`.
