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
python -m pipeline --exp-name EXPNAME --mcp filesystem --tasks FILESYSTEMTASK --models MODEL --k K
```

**Docker Usage (Recommended)**

Docker is recommended to avoid library version conflicts:

```bash
# Build Docker image
./build-docker.sh

# Run with Docker
./run-task.sh --mcp filesystem --models MODEL --exp-name EXPNAME --tasks FILESYSTEMTASK --k K
```

Here *EXPNAME* refers to customized experiment name, *FILESYSTEMTASK* refers to the github task or task group selected (see [Task Page](../datasets/task.md) for specific task information), *MODEL* refers to the selected model (see [Introduction Page](../introduction.md) for model supported), *K* refers to the time of independent experiments.

---

## 5 · Troubleshooting

**Common Issues**:

- **Test Environment Not Found**: Ensure `FILESYSTEM_TEST_ROOT` is set correctly
- **Prerequisites**: Make sure your terminal has `wget` and `unzip` commands available
- **Recommended**: Use Docker to prevent library version conflicts
