# Filesystem

This guide walks you through preparing your filesystem environment for MCPMark.

## 1 · Configure Environment Variables

Set the `FILESYSTEM_TEST_ROOT` environment variable in your `.mcp_env` file:

```env
## Filesystem
FILESYSTEM_TEST_ROOT=./test_environments
```

**Recommended**: Use `FILESYSTEM_TEST_ROOT=./test_environments` (relative to project root)

---

## 2 · Automatic Test Environment Download

Our code automatically downloads test folders to your specified `FILESYSTEM_TEST_ROOT` directory when the pipeline starts running.

**Downloaded Structure**:

```
./test_environments/
├── desktop/               # Desktop environment 
├── desktop_template/      # Template files for desktop
├── file_context/          # File content understanding tasks
├── file_property/         # File metadata and properties related tasks
├── folder_structure/      # Directory organization tasks
├── legal_document/        # Legal document processing
├── papers/                # Academic paper tasks
├── student_database/      # Database management tasks
├── threestudio/           # 3D Generation codebase
└── votenet/               # 3D Object Detection codebase
```

---

## 3 · Running Filesystem Tasks

**Basic Command**:

```bash
python -m pipeline --mcp filesystem --k 4 --models gpt-5 --exp-name test_run_1
```

**Parameters**:

- `--mcp filesystem`: Specifies the filesystem MCP service
- `--k 4`: Number of parallel task executions
- `--models gpt-5`: AI model to use
- `--exp-name test_run_1`: Custom experiment name

---

## 4 · Docker Usage (Recommended)

Use Docker to avoid library version conflicts:

**Build and Run**:

```bash
# Build
./build-docker.sh

# Run
docker run --rm -it \
  -v $(pwd):/workspace \
  -v $(pwd)/.mcp_env:/workspace/.mcp_env \
  -w /workspace \
  mcpmark:latest \
  python -m pipeline --mcp filesystem --k 4 --models gpt-5 --exp-name test_run_1
```

---

## 5 · Troubleshooting

**Common Issues**:

- **Test Environment Not Found**: Ensure `FILESYSTEM_TEST_ROOT` is set correctly

- **Prerequisites**: Make sure your terminal has `wget` and `unzip` commands available

- **Best Practice**: Use Docker to prevent library version conflicts
