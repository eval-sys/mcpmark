# MCPMark

MCPMark is a comprehensive evaluation suite for testing AI models’ agentic ability.


## 1 · Environment Setup

Before running MCPMark you need to prepare the environment for the MCP service you plan to evaluate. Follow the service-specific guides below:

- **Notion** – [docs/setup/notion-env-setup.md](docs/setup/notion-env-setup.md)
- **GitHub** – [docs/setup/github-env-setup.md](docs/setup/github-env-setup.md)
- **Filesystem** – coming soon...

## 2 · Environment Variables

All environment variables **must** be set in a file named `.mcp_env` in your project root. Example:

```env
# Service Credentials
## Notion
SOURCE_NOTION_API_KEY="your-source-notion-api-key"   # For Source Hub (templates)
EVAL_NOTION_API_KEY="your-eval-notion-api-key"       # For Eval Hub (active evaluation)
EVAL_PARENT_PAGE_TITLE="MCPMark Eval Hub"           # Must match the name of the empty page you created in Eval Hub
PLAYWRIGHT_BROWSER="chromium" # default to chromium, you can also choose firefox
PLAYWRIGHT_HEADLESS="True"

## GitHub
# GitHub token(s) for round-robin usage (comma-separated for multiple tokens)
GITHUB_TOKENS="token1"
# Example with multiple tokens:
# GITHUB_TOKENS="token1,token2,token3,token4"
GITHUB_EVAL_ORG="mcpmark-eval"

## Postgres
POSTGRES_PASSWORD="your-postgres-password"
POSTGRES_HOST="localhost"
POSTGRES_PORT="5432"
POSTGRES_DATABASE="your-database-name"
POSTGRES_USERNAME="your-postgres-username"

# Model Providers (set only those you need)
## Google Gemini
GEMINI_BASE_URL="https://your-gemini-base-url.com/v1"
GEMINI_API_KEY="your-gemini-api-key"

## DeepSeek
DEEPSEEK_BASE_URL="https://your-deepseek-base-url.com/v1"
DEEPSEEK_API_KEY="your-deepseek-api-key"

## OpenAI
OPENAI_BASE_URL="https://your-openai-base-url.com/v1"
OPENAI_API_KEY="your-openai-api-key"

## Anthropic
ANTHROPIC_BASE_URL="https://your-anthropic-base-url.com/v1"
ANTHROPIC_API_KEY="your-anthropic-api-key"

## Moonshot
MOONSHOT_BASE_URL="https://your-moonshot-base-url.com/v1"
MOONSHOT_API_KEY="your-moonshot-api-key"

## xAI
XAI_BASE_URL="https://your-xai-base-url.com/v1"
XAI_API_KEY="your-xai-api-key"
```

You only need to set the variables for the model providers you plan to use. Currently supported model providers: **OpenAI, Google Gemini, DeepSeek, Anthropic, Moonshot, xAI**.

## 3 · Installation

### Option A: Local Installation
```bash
pip install -e .
```

### Option B: Docker (Recommended)
```bash
# Build Docker image
./build-docker.sh

# Run with Docker
./run-task.sh --mcp notion --models o3 --exp-name run-1 --tasks all
```

## 4 · Authenticate with Your MCP Service

Refer to the corresponding guide for authentication details:

- Notion: [docs/setup/notion-workspace-setup.md#authenticate-with-notion](docs/setup/notion-workspace-setup.md#authenticate-with-notion)
- GitHub: handled automatically via `GITHUB_TOKEN`.

The verification script will tell you which browser is working properly. The pipeline defaults to using **chromium**. Our pipeline has been **fully tested on macOS and Linux**.

## 5 · Run the Evaluation

### Using Local Installation
```bash
# Evaluate ALL 20 tasks
python -m pipeline --exp-name run-1 --mcp notion --tasks all --models o3

# Evaluate a single task group
python -m pipeline --exp-name run-1 --mcp notion --tasks online_resume --models o3

# Evaluate one specific task
python -m pipeline --exp-name run-1 --mcp notion --tasks online_resume/task_1 --models o3

# Evaluate multiple models
python -m pipeline --exp-name run-1 --mcp notion --tasks all --models o3,gpt-4.1,claude-4-sonnet
```

### Using Docker
```bash
# Run all tasks for a service
./run-task.sh --mcp notion --models o3 --exp-name run-1 --tasks all

# Run comprehensive benchmark across all services
./run-benchmark.sh --models o3,gpt-4.1 --exp-name benchmark-1 --docker
```

**Auto-resume is supported:** When you rerun an evaluation command, only unfinished tasks will be executed. Tasks that previously failed due to pipeline errors (such as `State Duplication Error` or `MCP Network Error`) will also be retried automatically.

Results are written to `./results/` (JSON + CSV).

### Visualize Results

After your evaluations are done, generate a quick dashboard of model performance (success rate + token usage) with:

```bash
python -m examples.results_parser --exp-name MCP-RUN --mcp notion
```

This command scans `./results/{args.exp_name}/` for all model folders that start with the given service prefix.

Only models that finished **all** tasks without pipeline errors are visualized. Incomplete models are listed with a resume command so you can easily continue evaluation.

The generated plot is saved next to the experiment folder, e.g. `./results/{args.exp_name}/summary_notion.png`.

---

## 6 · Contributing

1. Fork the repository and create a feature branch.
2. Add new tasks inside `tasks/<category>/<task_n>/` with a `description.md` and a `verify.py`.
3. Ensure all tests pass.
4. Submit a pull request — contributions are welcome!
