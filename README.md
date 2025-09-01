<div align="center">

# MCPMark: Stress-Testing Comprehensive MCP Use

[![Website](https://img.shields.io/badge/Website-mcpmark.ai-4285F4?style=for-the-badge&logo=google-chrome&logoColor=white)](https://mcpmark.ai)
[![Discord](https://img.shields.io/badge/Join_our_discord-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/HrKkJAxDnA)
[![Docs](https://img.shields.io/badge/Docs-000000?style=for-the-badge&logo=mdbook&color=105864)](https://mcpmark.ai/docs)
[![Hugging Face](https://img.shields.io/badge/Trajectory_Logs-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black)](https://huggingface.co/datasets/Jakumetsu/mcpmark-trajectory-log)

</div>

An evaluation suite for agentic models in real MCP tool environments (Notion / GitHub / Filesystem / Postgres / Playwright).

MCPMark provides a reproducible, extensible benchmark for researchers and engineers: one-command tasks, isolated sandboxes, auto-resume for failures, unified metrics, and aggregated reports.

[![MCPMark](https://github.com/user-attachments/assets/dfc06a41-e387-45e3-bc98-db7097ffa3dc)](https://mcpmark.ai)

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

Results are saved to `./results/{exp_name}/{model}__{mcp}/run-*/...` (e.g., `./results/test-run/gpt-5__filesystem/run-1/...`).

---

## Run your evaluations

### Single run (k=1)
```bash
# Run ALL tasks for a service
python -m pipeline --exp-name exp --mcp notion --tasks all --models MODEL --k 1

# Run a task group
python -m pipeline --exp-name exp --mcp notion --tasks online_resume --models MODEL --k 1

# Run a specific task
python -m pipeline --exp-name exp --mcp notion --tasks online_resume/daily_itinerary_overview --models MODEL --k 1

# Evaluate multiple models
python -m pipeline --exp-name exp --mcp notion --tasks all --models MODEL1,MODEL2,MODEL3 --k 1
```

### Multiple runs (k>1) for pass@k
```bash
# Run k=4 to compute stability metrics (requires --exp-name to aggregate final results)
python -m pipeline --exp-name exp --mcp notion --tasks all --models MODEL

# Aggregate results (pass@1 / pass@k / pass^k / avg@k)
python -m src.aggregators.aggregate_results --exp-name exp
```

### Run with Docker
```bash
# Run all tasks for a service
./run-task.sh --mcp notion --models MODEL --exp-name exp --tasks all

# Cross-service benchmark
./run-benchmark.sh --models MODEL --exp-name exp --docker
```

Please visit `docs/introduction.md` for choices of *MODEL*.

Tip: MCPMark supports **auto-resume**. When re-running commands, only unfinished tasks will execute. Tasks previously failed due to pipeline errors (e.g., `State Duplication Error`, `MCP Network Error`) will be retried automatically.

---

## Service setup and authentication

- **Notion**: environment isolation (Source Hub / Eval Hub), integration creation and grants, browser login verification.
  - Guide and Setup: `docs/mcp/notion.md`

- **GitHub**: multi-account token pooling recommended; import pre-exported repo state if needed.
  - Guide and Setup: `docs/mcp/github.md`

- **Postgres**: start via Docker and import sample databases.
  - Env setup: `docs/mcp/postgres.md`

- **Playwright**: install browsers before first run; defaults to `chromium`.
  - Env setup: `docs/mcp/playwright.md`

- **Filesystem**: zero-configuration, run directly.
  - Configuration: `docs/mcp/filesystem.md`

You can also follow `docs/quickstart.md` for the shortest end-to-end path.

---

## Results and metrics

- Results are organized under `./results/{exp_name}/{model}__{mcp}/run-*/` (JSON + CSV per task).
- Generate a summary with:
```bash
python -m src.aggregators.aggregate_results --exp-name exp
```
- Includes multi-run metrics (e.g., pass@k) for stability comparisons.

---

## Model and Tasks
- **Model support**: MCPMark calls models via LiteLLM — see the LiteLLM docs: [`LiteLLM Doc`](https://docs.litellm.ai/docs/). For Anthropic (Claude) extended thinking mode (enabled via `--reasoning-effort`), we use Anthropic’s native API.
- See `docs/introduction.md` for details and configuration of supported models in MCPMark.
- To add a new model, edit `src/model_config.py`. Before adding, check LiteLLM supported models/providers. See [`LiteLLM Doc`](https://docs.litellm.ai/docs/).
- Task design principles in `docs/datasets/task.md`. Each task ships with an automated `verify.py` for objective, reproducible evaluation, see `docs/task.md` for details.

---

## Contributing

Contributions are welcome:
1. Add a new task under `tasks/<category_id>/<task_id>/` with `meta.json`, `description.md` and `verify.py`.
2. Ensure local checks pass and open a PR.
3. See `docs/contributing/make-contribution.md`.

---

## Citation

If you find our works useful for your research, please consider citing:

```bibtex
@misc{mcpmark_2025,
  title        = {MCPMark: Stress-Testing Comprehensive MCP Use},
  author       = {The MCPMark Team},
  howpublished = {\url{https://github.com/eval-sys/mcpmark}},
  year         = {2025}
}
```

## License

This project is licensed under the Apache License 2.0 — see `LICENSE`.
