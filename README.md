<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://github.com/user-attachments/assets/5feb54d4-adb3-408e-9a3d-213a5897ad74">
  <img height="90" src="https://github.com/user-attachments/assets/214269f6-9ea6-43d2-b349-722c6ff32926">
</picture>

</div>

---

An evaluation suite for agentic models in real MCP tool environments (Notion / GitHub / Filesystem / Postgres / Playwright).

Official website: [mcpmark.ai](https://mcpmark.ai)

MCPMark provides a reproducible, extensible benchmark for researchers and engineers: one-command tasks, isolated sandboxes, auto-resume for failures, unified metrics, and aggregated reports.

### Affiliation: EVAL SYS

[EVAL SYS](https://github.com/eval-sys) is a living, open-source community to track and advance model agentic capabilities. We release benchmarks, datasets, toolchains, and models to push the field forward. Initiated by [LobeHub](https://github.com/lobehub), we collaborate with research labs, MCP servers, independent contributors, and more. **Join us, contribute, or reach out!**

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

> [!IMPORTANT]
> Create `.mcp_env` with the required credentials in the project root. Do not commit secrets to version control.

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

See [docs/introduction.md](docs/introduction.md) and the service guides below for more details.

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

> [!TIP]
> Prefer Docker to ensure reproducibility across environments and cleaner local setups.

Run a filesystem task (no external accounts required):

```bash
python -m pipeline \
  --exp-name quickstart \
  --mcp filesystem \
  --tasks file_property/size_classification \
  --models gpt-5   # or any model you configured
```

Results are saved to `./results/{exp_name}/{mcp}__{model}/{task}`.

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

## Run your evaluations

> [!WARNING]
> Running tasks can create or modify resources in connected services (e.g., Notion pages, GitHub repositories). Use dedicated evaluation workspaces and tokens.

> [!CAUTION]
> Avoid pointing evaluations at production databases or organizations. Tasks may write data, hit rate limits, or incur provider costs.

### Single run (k=1)

```bash
# Evaluate ALL tasks (single run)
python -m pipeline --exp-name your-exp-name --mcp notion --tasks all --models o3 --k 1

# Evaluate a single task group
python -m pipeline --exp-name your-exp-name --mcp notion --tasks online_resume --models o3 --k 1

# Evaluate one specific task
python -m pipeline --exp-name your-exp-name --mcp notion --tasks online_resume/task_1 --models o3 --k 1

# Evaluate multiple models
python -m pipeline --exp-name your-exp-name --mcp notion --tasks all --models o3,gpt-4.1,claude-4-sonnet --k 1
```

### Multiple runs (k>1) for pass@k

```bash
# Run k=5 evaluations for pass@k metrics (requires --exp-name)
python -m pipeline --exp-name your-exp-name --mcp notion --tasks all --models o3 --k 5

# Aggregate results to get pass@1, pass@k, pass^k, avg@k metrics
python -m src.aggregators.aggregate_results --exp-name your-exp-name

# Multiple models with k runs
python -m pipeline --exp-name your-exp-name --mcp github --tasks all --models gpt-4,claude-3 --k 3
```

### Run with Docker

```bash
# Run all tasks for a service
./run-task.sh --mcp notion --models o3 --exp-name your-exp-name --tasks all

# Run comprehensive benchmark across all services
./run-benchmark.sh --models o3,gpt-4.1 --exp-name your-exp-name --docker
```

**Auto-resume is supported:** When you rerun an evaluation command, only unfinished tasks will be executed. Tasks that previously failed due to pipeline errors (such as `State Duplication Error` or `MCP Network Error`) will also be retried automatically.

## Results and metrics

Results are written to `./results/` (JSON + CSV).

### Aggregate Results

After your evaluations are done, generate a comprehensive summary with:

```bash
python -m src.aggregators.aggregate_results --exp-name your-exp-name
```

This generates `./results/your-exp-name/summary.json` with detailed metrics including pass@k metrics for multiple runs.

See also: [Introduction](docs/introduction.md) for modes and examples; [Task docs](docs/datasets/task.md) for task catalog and design principles.

---

## Models and tasks

- See supported models in [docs/introduction.md](docs/introduction.md).
- Task catalog and design principles: [docs/datasets/task.md](docs/datasets/task.md). Each task ships with an automated `verify.py` for objective, reproducible evaluation.

---

## Contributing

1. Fork the repository and create a feature branch.
2. Add new tasks inside `tasks/<category>/<task_n>/` with a `description.md` and a `verify.py`.
3. Ensure all tests pass.
4. Submit a pull request — contributions are welcome!

### Community and Collaboration

We welcome contributions from research labs, MCP server maintainers, and independent developers. Open an issue to discuss ideas, or start with a small PR to improve tasks, verifiers, or documentation. **Join us, contribute, or reach out!**

---

## Acknowledgements

This work is initialized by the EVAL SYS collaboration between NUS TRAIL × LobeHub. See the project website at [mcpmark.ai](https://mcpmark.ai/).

---

## How to Cite

If you use MCPMark in your work, please cite the project:

```bibtex
@misc{wu2025mcpmark,
  title        = {MCPMark: Stress-Testing Comprehensive MCP Use},
  author       = {Zijian Wu and Xiangyan Liu and Xinyuan Zhang and Lingjun Chen and Fanqing Meng and Lingxiao Du and Yiran Zhao and Fanshi Zhang and Yaoqi Ye and Jiawei Wang and Zirui Wang and Jinjie Ni and Yufan Yang and Arvin Xu and Michael Qizhe Shieh},
  howpublished = {\url{https://github.com/eval-sys/mcpmark}},
  year         = {2025}
}
```

---

## License

This project is licensed under the Apache License 2.0 — see `LICENSE`.
