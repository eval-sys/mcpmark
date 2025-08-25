# MCPMark

An evaluation suite for agentic models in real MCP tool environments (Notion / GitHub / Filesystem / Postgres / Playwright).

Official website: [mcpmark.ai](https://mcpmark.ai)

MCPMark provides a reproducible, extensible benchmark for researchers and engineers: one-command tasks, isolated sandboxes, auto-resume for failures, unified metrics, and aggregated reports.

## What you can do with MCPMark

- **Evaluate real tool usage** across multiple MCP services: `Notion`, `GitHub`, `Filesystem`, `Postgres`, `Playwright`.
- **Use ready-to-run tasks** covering practical workflows, each with strict automated verification.
- **Reliable and reproducible**: isolated environments that do not pollute your accounts/data; failed tasks auto-retry and resume.
- **Unified metrics and aggregation**: single/multi-run (pass@k, avg@k, etc.) with automated results aggregation.
- **Flexible deployment**: local or Docker; fully validated on macOS and Linux.

---

## Quickstart (5 minutes)

### 1) Clone the repository
```bash
git clone https://github.com/eval-sys/mcpmark.git
cd mcpmark
```

### 2) Set environment variables (create `.mcp_env` at repo root)
Only set what you need. Add service credentials when running tasks for that service.

```env
# Example: OpenAI
OPENAI_BASE_URL="https://api.openai.com/v1"
OPENAI_API_KEY="sk-..."

# Optional: Notion (only for Notion tasks)
SOURCE_NOTION_API_KEY="your-source-notion-api-key"
EVAL_NOTION_API_KEY="your-eval-notion-api-key"
EVAL_PARENT_PAGE_TITLE="MCPMark Eval Hub"
PLAYWRIGHT_BROWSER="chromium"   # chromium | firefox
PLAYWRIGHT_HEADLESS="True"

# Optional: GitHub (only for GitHub tasks)
GITHUB_TOKENS="token1,token2"   # token pooling for rate limits
GITHUB_EVAL_ORG="your-eval-org"

# Optional: Postgres (only for Postgres tasks)
POSTGRES_HOST="localhost"
POSTGRES_PORT="5432"
POSTGRES_USERNAME="postgres"
POSTGRES_PASSWORD="password"
```

See `docs/introduction.md` and the service guides below for more details.

### 3) Install and run a minimal example

Local (Recommended)
```bash
pip install -e .
# If you'll use browser-based tasks, install Playwright browsers first
playwright install
```

Docker
```bash
./build-docker.sh
```

Run a filesystem task (no external accounts required):
```bash
python -m pipeline \
  --mcp filesystem \
  --k 1 \ # run once to quick start
  --models gpt-5  \ # or any model you configured
  --tasks file_property/size_classification
```

Results are saved to `./results/{exp_name}/{mcp}__{model}/{task}`.

---

## Run your evaluations

### Single run (k=1)
```bash
# Run ALL tasks for a service
python -m pipeline --exp-name exp --mcp notion --tasks all --models o3

# Run a task group
python -m pipeline --exp-name exp --mcp notion --tasks online_resume --models o3

# Run a specific task
python -m pipeline --exp-name exp --mcp notion --tasks online_resume/task_1 --models o3

# Evaluate multiple models
python -m pipeline --exp-name exp --mcp notion --tasks all --models o3,gpt-4.1,claude-4-sonnet
```

### Multiple runs (k>1) for pass@k
```bash
# Run k=5 to compute stability metrics (requires --exp-name)
python -m pipeline --exp-name exp --mcp notion --tasks all --models o3 --k 5

# Aggregate results (pass@1 / pass@k / pass^k / avg@k)
python -m src.aggregators.aggregate_results --exp-name exp
```

### Run with Docker
```bash
# Run all tasks for a service
./run-task.sh --mcp notion --models o3 --exp-name exp --tasks all

# Cross-service benchmark
./run-benchmark.sh --models o3,gpt-4.1 --exp-name exp --docker
```

Tip: MCPMark supports **auto-resume**. When re-running commands, only unfinished tasks will execute. Tasks previously failed due to pipeline errors (e.g., `State Duplication Error`, `MCP Network Error`) will be retried automatically.

---

## Service setup and authentication

- **Notion**: environment isolation (Source Hub / Eval Hub), integration creation and grants, browser login verification.
  - Guide: `docs/mcp/notion.md`
  - Env setup: `docs/setup/notion-env-setup.md`

- **GitHub**: multi-account token pooling recommended; import pre-exported repo state if needed.
  - Guide: `docs/mcp/github.md`
  - Env setup: `docs/setup/github-env-setup.md`

- **Postgres**: start via Docker and import sample databases.
  - Env setup: `docs/setup/postgres-env-setup.md`

- **Playwright**: install browsers before first run; defaults to `chromium`.
  - Env setup: `docs/setup/playwright-env-setup.md`

- **Filesystem**: zero-configuration, run directly.

You can also follow `docs/quickstart.md` for the shortest end-to-end path.

---

## Results and metrics

- Results are written to `./results/` (JSON + CSV).
- Generate a summary with:
```bash
python -m src.aggregators.aggregate_results --exp-name exp
```
- Includes multi-run metrics (e.g., pass@k) for stability comparisons.

---

## Models and tasks

- See supported models in `docs/introduction.md`.
- Task catalog and design principles in `docs/datasets/task.md`. Each task ships with an automated `verify.py` for objective, reproducible evaluation.

---

## Contributing

Contributions are welcome:
1. Add a new task under `tasks/<category>/<task_n>/` with `description.md` and `verify.py`.
2. Ensure local checks pass and open a PR.
3. See `docs/contributing/make-contribution.md` and `docs/contributing/add-new-mcp-service.md`.

---

## License

This project is licensed under the Apache License 2.0 — see `LICENSE`.
