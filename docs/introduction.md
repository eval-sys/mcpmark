# MCPMark
MCPMark is a comprehensive evaluation suite for evaluating the agentic ability of frontier models.

MCPMark includes Model Context Protocol (MCP) service in following environments
- Notion
- Github
- Filesystem
- Postgres
- Playwright

### General Procedure
MCPMark is designed to run agentic tasks in complex environment **safely**. Specifically, it sets up an isolated environment for the experiment, completing the task, and then destroy the environment without affecting existing user profile or information.

### How to Use MCPMark
1. MCPMark Installation.
2. Authorize service (for Github and Notion).
3. Configure the environment variables in `.mcp_env`.
4. Run MCPMark experiment.

Please refer to [Quick Start](./quickstart.md) for details regarding how to start experiment properly, and [Task Page](./datasets/task.md) for task details.

### Running MCPMark

MCPMark supports the following mode to run experiments (suppose the experiment is named as new_exp, and the model used are o3 and gpt-4.1 and the environment is notion)

#### MCPMark in Pip Installation
```bash
# Evaluate ALL tasks
python -m pipeline --exp-name new_exp --mcp notion --tasks all --models o3

# Evaluate a single task group (online_resume)
python -m pipeline --exp-name new_exp --mcp notion --tasks online_resume --models o3

# Evaluate one specific task (task_1 in online_resume)
python -m pipeline --exp-name new_exp --mcp notion --tasks online_resume/task_1 --models o3

# Evaluate multiple models
python -m pipeline --exp-name new_exp --mcp notion --tasks all --models o3,gpt-4.1
```

#### MCPMark in Docker Installation
```bash
# Run all tasks for one service
./run-task.sh --mcp notion --models o3 --exp-name new_exp --tasks all

# Run comprehensive benchmark across all services
./run-benchmark.sh --models o3,gpt-4.1 --exp-name new_exp --docker
```

#### Experiment Auto-Resume
For re-run experiments, only unfinished tasks will be executed. Tasks that previously failed due to pipeline errors (such as State Duplication Error or MCP Network Error) will also be retried automatically.

### Results
The experiment results are written to `./results/` (JSON + CSV).

#### Visualization
Quickly get to know model success rate and token comsumption through one line of command

```bash
python -m examples.results_parser --exp-name exp_name --mcp SERVICE
```

This command scans `./results/{args.exp_name}/` for all model folders that start with the given service prefix.

Only models that finished all tasks without pipeline errors are visualized. Incomplete models are listed with a resume command so you can easily continue evaluation.

The generated plot is saved next to the experiment folder, e.g. `./results/{args.exp_name}/summary_{SERVICE}.png`.

### Model Support
MCPMark supports frontier models from various organizations, specifically
```env
# OpenAI
gpt-4o
gpt-4.1
gpt-4.1-mini
gpt-5
gpt-5-mini
gpt-5-nano
o3
o4-mini

# xAI
grok-4

# Google
gemini-2.5-pro
gemini-2.5-flash

# Anthropic
claude-3-7-sonnet
claude-4-sonnet
calude-4-opus

# DeepSeek
deepseek-chat
deepseek-reasoner

# Moonshot
k2
```

### Want to contribute?
Visit [Contributing Page](./contributing) to learn how to make contribution to MCPMark.
