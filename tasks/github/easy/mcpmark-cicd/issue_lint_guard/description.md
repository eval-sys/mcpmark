Use the GitHub MCP tools to wire up a tiny issue-triggered lint check for `mcpmark-eval/mcpmark-cicd`.

## Goal
Whenever a maintainer opens the tracking issue **Lint workflow check**, the repo should automatically run `npm run lint` via GitHub Actions. Keep it simple—just prove the workflow fires for issue events.

## Requirements
1. Create a branch called `issue-lint-workflow` from `main`.
2. Add `.github/workflows/issue-lint.yml` with:
   - Workflow name **Issue Lint Guard**.
   - Trigger: `issues` with `types: [opened]` (no push/PR triggers).
   - Single job `lint` on `ubuntu-latest` using Node.js 18 via `actions/setup-node`.
   - Steps in order: `actions/checkout`, `npm ci`, `npm run lint`.
3. Open a pull request titled `Add issue lint workflow`, get it merged so the workflow exists on `main`.
4. After the merge, open a new issue titled **Lint workflow check** to trigger the workflow and wait until the matching run finishes successfully. Leave the issue open; we only care that the run went green.
