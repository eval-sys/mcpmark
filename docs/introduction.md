# MCPMark
MCPMark is a comprehensive evaluation suite for evaluating the agentic ability of frontier models.

MCPMark includes Model Context Protocol (MCP) service in following environments
- Notion
- Github
- Filesystem
- Postgres
- Playwright
- Playwright-WebArena

### General Procedure
MCPMark is designed to run agentic tasks in complex environment **safely**. Specifically, it sets up an isolated environment for the experiment, completing the task, and then destroy the environment without affecting existing user profile or information.

### How to Use MCPMark
1. MCPMark Installation.
2. Authorize service (for Github and Notion).
3. Configure the environment variables in `.mcp_env`.
4. Run MCPMark experiment.

Please refer to [Quick Start](./quickstart.md) for details regarding how to start a sample filesystem experiment in properly, and [Task Page](./datasets/task.md) for task details. Please visit [Installation and Docker Uusage](./installation_and_docker_usage.md) information of full MCPMark setup.

### Running MCPMark

MCPMark supports the following mode to run experiments (suppose the experiment is named as new_exp, and the model used are o3 and gpt-4.1 and the environment is notion), with K repetive experiments.

#### MCPMark in Pip Installation
```bash
# Evaluate ALL tasks
python -m pipeline --exp-name new_exp --mcp notion --tasks all --models o3 --k K

# Evaluate a single task group (online_resume)
python -m pipeline --exp-name new_exp --mcp notion --tasks online_resume --models o3 --k K

# Evaluate one specific task (task_1 in online_resume)
python -m pipeline --exp-name new_exp --mcp notion --tasks online_resume/task_1 --models o3 --k K

# Evaluate multiple models
python -m pipeline --exp-name new_exp --mcp notion --tasks all --models o3,gpt-4.1 --k K
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

#### Reult Aggregation (for K > 1)
MCP supports aggreated metrics of pass@1, pass@K, $\text{pass}^{K}$, avg@K.
```bash
python -m src.aggregators.aggregate_results --exp-name new_exp
```

### Model Support
MCPMark supports the following models with according providers (model codes in the brackets).
#### OpenAI
- GPT-5 (gpt-5)
- o3 (o3)

#### Anthropic
- Claude-4.1-Opus (claude-4.1-opus)
- Claude-4-Sonnet (claude-4-sonnet)

#### Google
- Gemini-2.5-Pro (gemini-2.5-pro)

#### Grok
- Grok-4 (grok-4)

#### Deepseek
- DeepSeek-Chat (deepseek-chat)

#### Alibaba
- Qwen3-Coder (qwen-3-coder)

#### Kimi
- Kimi-K2 (k2)

### Want to contribute?
Visit [Contributing Page](./contributing) to learn how to make contribution to MCPMark.
