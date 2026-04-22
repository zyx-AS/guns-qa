# GitHub Copilot Instructions

When adding or updating tests in this repository:

- Always create or update a matching teacher-readable README under `guns-tests/docs/<type>/<test-id>/README.md`.
- Valid documentation categories are `unit`, `integration`, `system`, and `performance`.
- Use the canonical template in `docs/testing/test-readme-template.md`.
- Review the examples in `docs/testing/examples/` before writing a new README.
- Prefer scaffolding with `scripts/new-test-doc.ps1` or `scripts/new-test-doc.sh`.
- Keep the README concise and readable for teachers. Summarize the result in natural language instead of pasting raw XML or long logs.
- Update `guns-tests/docs/README.md` and the relevant category index when a new documented test is added.
