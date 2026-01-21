<div align="center">

# MCPMark: Stress-Testing Comprehensive MCP Use

[![Website](https://img.shields.io/badge/Website-mcpmark.ai-4285F4?style=for-the-badge&logo=google-chrome&logoColor=white)](https://mcpmark.ai)
[![arXiv](https://img.shields.io/badge/arXiv-2509.24002-b31b1b?style=for-the-badge&logo=arxiv&logoColor=white)](https://arxiv.org/abs/2509.24002)
[![Discord](https://img.shields.io/badge/Join_our_discord-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/HrKkJAxDnA)
[![Docs](https://img.shields.io/badge/Docs-000000?style=for-the-badge&logo=mdbook&color=105864)](https://mcpmark.ai/docs)
[![Hugging Face](https://img.shields.io/badge/Trajectory_Logs-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black)](https://huggingface.co/datasets/Jakumetsu/mcpmark-trajectory-log)

</div>

An evaluation suite for agentic models in real MCP tool environments (Notion / GitHub / Filesystem / Postgres / Playwright).

MCPMark provides a reproducible, extensible benchmark for researchers and engineers: one-command tasks, isolated sandboxes, auto-resume for failures, unified metrics, and aggregated reports.

[![MCPMark](https://github.com/user-attachments/assets/dfc06a41-e387-45e3-bc98-db7097ffa3dc)](https://mcpmark.ai)

## News

- 📌 **21 Jan** — Pinned MCP server versions for reproducible benchmarks: GitHub MCP Server `v0.15.0` (switched to Docker for version control), Notion MCP Server `@1.9.1` (Notion released 2.0 but it has many bugs, not recommended). See [#246](https://github.com/eval-sys/mcpmark/pull/246).
- 🔥 **13 Dec** — Added auto-compaction support (`--compaction-token`) to summarize long conversations and avoid context overflow during evaluation ([#236](https://github.com/eval-sys/mcpmark/pull/236])).
- 🏅 **02 Dec** — Evaluated `gemini-3-pro-preview` (thinking: low): **Pass@1 50.6%** ± 2.3% — so close to `gpt-5-high` (51.6%)! Also `deepseek-v3.2-thinking` 36.8% and `deepseek-v3.2-chat` 29.7%
- 🔥 **02 Dec** — Obfuscate GitHub @mentions to prevent notification spam during evaluation ([#229](https://github.com/eval-sys/mcpmark/pull/229))
- 🏅 **01 Dec** — DeepSeek v3.2 uses MCPMark! Kudos on securing the best open-source model. [X Post](https://x.com/deepseek_ai/status/1995452650557763728) | [Technical Report](https://huggingface.co/deepseek-ai/DeepSeek-V3.2/resolve/main/assets/paper.pdf)
- 🔥 **17 Nov** — Added 50 easy tasks (10 per MCP server) for smaller open-source models ([#225](https://github.com/eval-sys/mcpmark/pull/225))
- 🤝 **31 Oct** — Community PR from insforge: better MCP servers achieve better results with fewer tokens! ([#214](https://github.com/eval-sys/mcpmark/pull/214))
- 🔥 **13 Oct** — Added ReAct agent support. PRs for new agent scaffolds welcome! ([#209](https://github.com/eval-sys/mcpmark/pull/209))
- 🏅 **10 Sep** — `qwen-3-coder-plus` is the best open-source model! Kudos to Qwen team. [X Post](https://x.com/Alibaba_Qwen/status/1965457023438651532)

---

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

MCPMark defaults to the built-in orchestration agent (`MCPMarkAgent`). To experiment with the ReAct-style agent, pass `--agent react` to `pipeline.py` (other settings stay the same).

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
# Add --task-suite easy to run the lightweight dataset (where available)
```

Results are saved to `./results/{exp_name}/{model}__{mcp}/run-*/...` for the standard suite and `./results/{exp_name}/{model}__{mcp}-easy/run-*/...` when you run `--task-suite easy` (e.g., `./results/test-run/gpt-5__filesystem/run-1/...` or `./results/test-run/gpt-5__github-easy/run-1/...`).

---

## Run your evaluations

### Task suites (standard vs easy)

- Each MCP service now stores tasks under `tasks/<mcp>/<task_suite>/<category>/<task>/`.
- `standard` (default) covers the full benchmark (127 tasks today).
- `easy` hosts 10 lightweight tasks per MCP, ideal for smoke tests and CI (GitHub’s are already available under `tasks/github/easy`).
- Switch suites with `--task-suite easy` (defaults to `--task-suite standard`).

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

Tip: MCPMark supports **auto-resume**. When re-running, only unfinished tasks will execute. Failures matching our retryable patterns (see [RETRYABLE_PATTERNS](src/errors.py)) are retried automatically. Models may emit different error strings—if you encounter a new resumable error, please open a PR or issue.

Tip: MCPMark supports **auto-compaction**; pass `--compaction-token N` to enable automatic context summarization when prompt tokens reach `N` (use `999999999` to disable).

---

## Service setup and authentication

| Service     | Setup summary                                                                                                  | Docs                                  |
|-------------|-----------------------------------------------------------------------------------------------------------------|---------------------------------------|
| Notion      | Environment isolation (Source Hub / Eval Hub), integration creation and grants, browser login verification.     | [Guide](docs/mcp/notion.md)           |
| GitHub      | Multi-account token pooling recommended; import pre-exported repo state if needed.                              | [Guide](docs/mcp/github.md)           |
| Postgres    | Start via Docker and import sample databases.                                                                   | [Setup](docs/mcp/postgres.md)         |
| Playwright  | Install browsers before first run; defaults to `chromium`.                                                      | [Setup](docs/mcp/playwright.md)       |
| Filesystem  | Zero-configuration, run directly.                                                                               | [Config](docs/mcp/filesystem.md)      |

You can also follow [Quickstart](docs/quickstart.md) for the shortest end-to-end path.

### Important Notice: GitHub Repository Privacy

> **Please ensure your evaluation repositories are set to PRIVATE.**

GitHub state templates are now automatically downloaded from our CDN during evaluation — no manual download is required. However, because these templates contain issues and pull requests from real open-source repositories, the recreation process includes `@username` mentions of the original authors.

**We have received feedback from original GitHub authors who were inadvertently notified** when evaluation repositories were created as public. To be a responsible member of the open-source community, we urge all users to:

1. **Always keep evaluation repositories private** during the evaluation process.
2. **In the latest version**, we have added random suffixes to all `@username` mentions (e.g., `@user` becomes `@user_x7k2`) and implemented a safety check that prevents importing templates to public repositories.
3. **If you are using an older version of MCPMark**, please either:
   - Pull the latest code immediately, or
   - Manually ensure all GitHub evaluation repositories are set to private.

Thank you for helping us maintain a respectful relationship with the open-source community.

---

## Results and metrics

- Results are organized under `./results/{exp_name}/{model}__{mcp}/run-*/` (JSON + CSV per task).
- Generate a summary with:
```bash
# Basic usage
python -m src.aggregators.aggregate_results --exp-name exp

# For k-run experiments with single-run models
python -m src.aggregators.aggregate_results --exp-name exp --k 4 --single-run-models claude-opus-4-1
```
- Only models with complete results across all tasks and runs are included in the final summary.
- Includes multi-run metrics (pass@k, pass^k) for stability comparisons when k > 1.

---

## Model and Tasks
- **Model support**: MCPMark calls models via LiteLLM — see the LiteLLM docs: [`LiteLLM Doc`](https://docs.litellm.ai/docs/). For Anthropic (Claude) extended thinking mode (enabled via `--reasoning-effort`), we use Anthropic’s native API.
- See `docs/introduction.md` for details and configuration of supported models in MCPMark.
- To add a new model, edit `src/model_config.py`. Before adding, check LiteLLM supported models/providers. See [`LiteLLM Doc`](https://docs.litellm.ai/docs/).
- Task design principles in `docs/datasets/task.md`. Each task ships with an automated `verify.py` for objective, reproducible evaluation, see `docs/task.md` for details.

---

## Contributing

Contributions are welcome:
1. Add a new task under `tasks/<mcp>/<task_suite>/<category_id>/<task_id>/` with `meta.json`, `description.md` and `verify.py`.
2. Ensure local checks pass and open a PR.
3. See `docs/contributing/make-contribution.md`.

---

## Citation

If you find our works useful for your research, please consider citing:

```bibtex
@misc{wu2025mcpmark,
      title={MCPMark: A Benchmark for Stress-Testing Realistic and Comprehensive MCP Use}, 
      author={Zijian Wu and Xiangyan Liu and Xinyuan Zhang and Lingjun Chen and Fanqing Meng and Lingxiao Du and Yiran Zhao and Fanshi Zhang and Yaoqi Ye and Jiawei Wang and Zirui Wang and Jinjie Ni and Yufan Yang and Arvin Xu and Michael Qizhe Shieh},
      year={2025},
      eprint={2509.24002},
      archivePrefix={arXiv},
      primaryClass={cs.CL},
      url={https://arxiv.org/abs/2509.24002}, 
}
```

## License

This project is licensed under the Apache License 2.0 — see `LICENSE`.
