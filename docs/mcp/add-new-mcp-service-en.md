# Adding New MCP Services Guide

## Overview

This guide explains how to add a new MCP service to the MCPMark framework. With our fully consolidated service definitions architecture, adding a new service requires:
1. Add complete service definition to `src/services.py` (including config schema)
2. Implement the three service components (task_manager, state_manager, login_helper)
3. Create test tasks

No other files need to be modified!

## Prerequisites

Before starting:
1. Understand the target MCP service's API and authentication method
2. Have test tasks and verification scripts ready
3. Be familiar with the project structure (see `code-structure.md`)

## Step 1: Add Service Definition

First, add your service definition to `src/services.py`. This is the only place you need to configure your service:

```python
SERVICES = {
    # ... existing services ...
    
    "slack": {
        "config_schema": {
            # Define all configuration values and their environment variables
            "api_key": {
                "env_var": "SLACK_API_KEY",
                "required": True,
                "description": "Slack API token for bot"
            },
            "workspace_id": {
                "env_var": "SLACK_WORKSPACE_ID",
                "required": True,
                "description": "Slack workspace ID"
            },
            "default_channel": {
                "env_var": "SLACK_DEFAULT_CHANNEL",
                "default": "general",
                "required": False,
                "description": "Default channel for operations"
            }
        },
        "components": {
            "task_manager": "src.mcp_services.slack.slack_task_manager.SlackTaskManager",
            "state_manager": "src.mcp_services.slack.slack_state_manager.SlackStateManager",
            "login_helper": "src.mcp_services.slack.slack_login_helper.SlackLoginHelper",
        },
        "config_mapping": {
            # Maps config keys to constructor parameters
            "state_manager": {
                "api_token": "api_key",
                "workspace_id": "workspace_id",
            },
            "login_helper": {
                "api_token": "api_key",
                "workspace_id": "workspace_id",
            }
        },
        "mcp_server": {
            "type": "stdio",  # or "http" for HTTP-based servers
            "command": "npx",
            "args": ["-y", "@slack/mcp-server"],
            "timeout": 120,
            "cache_tools": True,
            "requires_config": {
                "env": {
                    "SLACK_API_TOKEN": "{slack_token}",
                    "SLACK_WORKSPACE_ID": "{workspace_id}"
                }
            }
        },
        "eval_config": {
            # What config to pass to the agent
            "slack_token": "api_key",
            "workspace_id": "workspace_id"
        }
    }
}
```

## Step 2: Create Service Directory Structure

Create the directory structure for your service:

```bash
mkdir -p src/mcp_services/slack/
touch src/mcp_services/slack/__init__.py
touch src/mcp_services/slack/slack_login_helper.py
touch src/mcp_services/slack/slack_state_manager.py
touch src/mcp_services/slack/slack_task_manager.py
```

## Step 3: Implement Task Manager

### 3.1 Create Task Data Class (Optional)

In `slack_task_manager.py`, create a service-specific task class if needed:

```python
from dataclasses import dataclass
from typing import Optional
from src.base.task_manager import BaseTask

@dataclass
class SlackTask(BaseTask):
    """Represents a single evaluation task for Slack service."""
    
    # Add Slack-specific fields if needed
    workspace_id: Optional[str] = None
    channel_id: Optional[str] = None
```

### 3.2 Implement Task Manager Class

```python
from pathlib import Path
from src.base.task_manager import BaseTaskManager

class SlackTaskManager(BaseTaskManager):
    """Manages task discovery and verification for Slack service."""
    
    def __init__(self, tasks_root: Path = None):
        if tasks_root is None:
            tasks_root = Path(__file__).resolve().parents[3] / "tasks"
        super().__init__(tasks_root)
    
    def _get_service_directory_name(self) -> str:
        """Return the service directory name."""
        return "slack"
    
    def _get_task_organization(self) -> str:
        """Return how tasks are organized: 'file' or 'directory'."""
        return "directory"  # Use "file" if tasks are single files
    
    def _create_task_instance(self, **kwargs) -> SlackTask:
        """Create a task instance from kwargs."""
        return SlackTask(**kwargs)
```

## Step 4: Implement State Manager

In `slack_state_manager.py`:

```python
from typing import Optional, Dict, Any
from src.base.state_manager import BaseStateManager, InitialStateInfo
from src.base.task_manager import BaseTask
from src.logger import get_logger

logger = get_logger(__name__)

class SlackStateManager(BaseStateManager):
    """Manages initial state setup and cleanup for Slack tasks."""
    
    def __init__(self, api_token: str, workspace_id: str):
        super().__init__("slack")
        self.api_token = api_token
        self.workspace_id = workspace_id
        # Initialize Slack client
        # self.slack_client = SlackClient(api_token)
    
    def _create_initial_state(self, task: BaseTask) -> Optional[InitialStateInfo]:
        """Create initial state for a Slack task."""
        try:
            # Create test channel or duplicate existing state
            # channel_id = self.slack_client.create_test_channel(...)
            
            # Track created resources
            # self.track_resource("channel", channel_id)
            
            return InitialStateInfo(
                state_id="channel_id_here",
                state_url=f"slack://channel/{self.workspace_id}/channel_id_here",
                metadata={"workspace_id": self.workspace_id}
            )
        except Exception as e:
            logger.error(f"Failed to create initial state: {e}")
            return None
    
    def _store_initial_state_info(self, task: BaseTask, state_info: InitialStateInfo) -> None:
        """Store initial state information in the task object."""
        if hasattr(task, 'channel_id'):
            task.channel_id = state_info.state_id
        if hasattr(task, 'workspace_id'):
            task.workspace_id = self.workspace_id
    
    def _cleanup_task_initial_state(self, task: BaseTask) -> bool:
        """Clean up initial state for a specific task."""
        try:
            # Clean up task-specific state
            if hasattr(task, 'channel_id') and task.channel_id:
                # self.slack_client.delete_channel(task.channel_id)
                pass
            return True
        except Exception as e:
            logger.error(f"Failed to cleanup task state: {e}")
            return False
    
    def _cleanup_single_resource(self, resource: Dict[str, Any]) -> bool:
        """Clean up a single tracked resource."""
        try:
            resource_type = resource['type']
            resource_id = resource['id']
            
            if resource_type == "channel":
                # self.slack_client.delete_channel(resource_id)
                pass
            
            return True
        except Exception as e:
            logger.error(f"Failed to cleanup resource {resource}: {e}")
            return False
```

## Step 5: Implement Login Helper

In `slack_login_helper.py`:

```python
from pathlib import Path
from typing import Optional
from src.base.login_helper import BaseLoginHelper
from src.logger import get_logger

logger = get_logger(__name__)

class SlackLoginHelper(BaseLoginHelper):
    """Handles Slack authentication and session management."""
    
    def __init__(self, api_token: str, workspace_id: str, state_path: Optional[Path] = None):
        super().__init__("slack", state_path)
        self.api_token = api_token
        self.workspace_id = workspace_id
    
    def login(self) -> bool:
        """Perform Slack authentication."""
        try:
            # Verify API token
            # response = self.slack_client.auth_test()
            # return response.get("ok", False)
            return True
        except Exception as e:
            logger.error(f"Slack login failed: {e}")
            return False
    
    def is_logged_in(self) -> bool:
        """Check if currently logged in to Slack."""
        # Check authentication status
        return True
    
    def logout(self) -> bool:
        """Logout from Slack (if applicable)."""
        # Slack API tokens typically don't need explicit logout
        return True
```

## Step 6: Configure Environment Variables

Add your service's environment variables to `.mcp_env`:

```bash
# Slack Service
SLACK_API_KEY=xoxb-your-slack-bot-token
SLACK_WORKSPACE_ID=your-workspace-id
SLACK_DEFAULT_CHANNEL=general  # Optional, has default
```

The config system automatically:
1. Loads environment variables based on your `config_schema` definition
2. Validates required values are present
3. Applies defaults for optional values
4. Uses `config_mapping` to pass values to your components with correct parameter names

### Config Schema Features

- **transform**: Convert string env vars to other types
  - `"bool"`: Converts "true", "1", "yes" to True
  - `"int"`: Converts to integer
  - `"path"`: Converts to Path object
- **validator**: Validate values
  - `"port"`: Validates port range 1-65535
  - `"in:opt1,opt2,opt3"`: Validates value is in list

## Step 7: Create Test Tasks

Create the task structure in the `tasks/` directory:

```
tasks/
└── slack/
    └── channel_management/
        └── task_1/
            ├── description.md
            └── verify.py
```

### description.md example:

```markdown
# Create New Channel Task

Use the Slack MCP tools to create a new channel named "test-channel" and invite user @john.doe to the channel.

## Requirements:
1. Channel name: test-channel
2. Channel description: This is a test channel for evaluation
3. Set as private channel
4. Invite user: @john.doe
```

### verify.py example:

```python
#!/usr/bin/env python3
import sys
import os
from slack_sdk import WebClient

def verify_task(channel_id):
    client = WebClient(token=os.getenv("SLACK_API_TOKEN"))
    
    try:
        # Verify channel exists
        response = client.conversations_info(channel=channel_id)
        if not response["ok"]:
            return False
            
        channel = response["channel"]
        
        # Verify channel name
        if channel["name"] != "test-channel":
            return False
            
        # Verify it's a private channel
        if not channel["is_private"]:
            return False
            
        # Verify members
        members_response = client.conversations_members(channel=channel_id)
        # ... more verification logic
        
        return True
    except Exception as e:
        print(f"Verification failed: {e}")
        return False

if __name__ == "__main__":
    channel_id = sys.argv[1] if len(sys.argv) > 1 else None
    success = verify_task(channel_id)
    sys.exit(0 if success else 1)
```

## That's It!

With our consolidated architecture, you don't need to:
- Modify `src/agent.py` - it uses the MCP server builder automatically
- Modify `src/factory.py` - it loads your service from definitions
- Modify `src/evaluator.py` - it uses your eval_config automatically
- Create separate factory classes - the generic factory handles everything

## Step 8: Test Your Service

### 8.1 Unit Tests

Create test files to verify your components:

```python
# tests/test_slack_service.py
import pytest
from src.mcp_services.slack.slack_task_manager import SlackTaskManager

def test_slack_task_discovery():
    manager = SlackTaskManager()
    tasks = manager.discover_all_tasks()
    assert len(tasks) > 0
```

### 8.2 Integration Test

Run the full evaluation pipeline:

```bash
python -m pipeline --mcp slack --models gpt-4o --tasks all --exp-name slack-test
```

## Key Architecture Benefits

1. **True Single Source of Truth**: ALL service configuration (including env vars) is in `src/services.py`
2. **Zero Additional Files**: No need to modify config_schema.py, agent.py, factory.py, or evaluator.py
3. **Automatic Config Loading**: GenericConfigSchema reads directly from service definitions
4. **Runtime Substitution**: Sensitive values use template substitution `{api_key}`
5. **Type Safety**: Config schema validates types and requirements
6. **No Hardcoding**: No if-elif chains or schema classes to add

## Important Notes

1. **Error Handling**: Ensure all network calls have proper error handling
2. **Resource Cleanup**: Track all created resources in StateManager
3. **Authentication**: Handle API keys securely through config system
4. **Logging**: Add sufficient logging for debugging
5. **Validation**: Service definitions are validated at startup

## Checklist

- [ ] Add complete service definition to `src/services.py` (with config_schema)
- [ ] Create service directory structure
- [ ] Implement TaskManager (only 3 required methods!)
- [ ] Implement StateManager
- [ ] Implement LoginHelper
- [ ] Add environment variables to `.mcp_env`
- [ ] Create test tasks
- [ ] Write verification scripts
- [ ] Run integration tests

That's it! No other files to modify.

By following this guide, you can add a new MCP service with minimal code changes and maximum consistency with the framework.