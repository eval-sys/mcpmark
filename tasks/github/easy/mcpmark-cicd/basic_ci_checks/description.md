Use the GitHub MCP tools to update the `mcpmark-eval/mcpmark-cicd` repository with a very small CI workflow.

## Goal
Add a GitHub Actions workflow named **Basic CI Checks** that automatically runs linting and unit tests any time work is pushed to or proposed for the `main` branch.

## Requirements
1. Create a branch called `basic-ci-checks` from `main`.
2. Add `.github/workflows/basic-ci.yml` with the following characteristics:
   - Workflow name: `Basic CI Checks`.
   - Trigger on both `push` and `pull_request`, limited to the `main` branch.
   - Single job called `quality-checks` that runs on `ubuntu-latest` and uses Node.js 18 (`actions/setup-node`).
   - Steps must include `actions/checkout`, `npm ci`, `npm run lint`, and `npm test` in that order after Node is configured.
3. Commit the workflow to your branch, open a pull request titled `Add basic CI checks`, and merge it so the workflow exists on `main`.

That's it—no caching, matrix builds, or issue automation required. Keep it lightweight and focused on verifying the existing lint/test scripts.
