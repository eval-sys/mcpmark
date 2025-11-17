Use the GitHub MCP tools to add a tiny bit of automation to `mcpmark-eval/mcpmark-cicd`.

Goal: every night the repo should run the existing health check script.

Do the usual branch/PR flow with a branch named `nightly-health` and a PR titled `Add nightly health check`.

Create `.github/workflows/nightly-health.yml` with:
- workflow name `Nightly Health Check`
- triggers: `workflow_dispatch` plus a cron schedule `0 2 * * *`
- one job called `health-check` on `ubuntu-latest`
- use Node.js 18 via `actions/setup-node`
- steps in order: checkout, npm ci, `npm run health-check`

Merge the PR so the workflow lives on `main`.
