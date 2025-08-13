# 添加新 MCP 服务指南

## 概述

本指南详细说明如何在 MCPMark 框架中添加新的 MCP 服务。框架采用模板方法模式和工厂模式，确保新服务能够无缝集成到现有评测流程中。

## 准备工作

在开始之前，请确保：
1. 了解目标 MCP 服务的 API 和认证方式
2. 准备好相应的测试任务和验证脚本
3. 熟悉项目的代码结构（参考 `code_structure.md`）

## 步骤一：创建服务目录结构

为新服务创建目录结构：

```bash
mkdir -p src/mcp_services/{service_name}/
touch src/mcp_services/{service_name}/__init__.py
touch src/mcp_services/{service_name}/{service_name}_login_helper.py
touch src/mcp_services/{service_name}/{service_name}_state_manager.py
touch src/mcp_services/{service_name}/{service_name}_task_manager.py
```

例如，添加 Slack 服务：
```bash
mkdir -p src/mcp_services/slack/
touch src/mcp_services/slack/__init__.py
touch src/mcp_services/slack/slack_login_helper.py
touch src/mcp_services/slack/slack_state_manager.py
touch src/mcp_services/slack/slack_task_manager.py
```

## 步骤二：实现任务管理器

### 2.1 创建任务数据类

在 `{service_name}_task_manager.py` 中创建服务特定的任务类：

```python
from dataclasses import dataclass
from typing import Optional, List
from src.base.task_manager import BaseTask

@dataclass
class SlackTask(BaseTask):
    """Represents a single evaluation task for Slack service."""
    
    # Slack-specific fields
    workspace_id: Optional[str] = None
    channel_id: Optional[str] = None
    thread_ts: Optional[str] = None
    expected_message_count: Optional[int] = None
```

### 2.2 实现任务管理器类

```python
from pathlib import Path
from typing import Any, Dict, List, Optional
from src.base.task_manager import BaseTaskManager

class SlackTaskManager(BaseTaskManager):
    """Manages task discovery, filtering, and verification for Slack-based evaluation."""
    
    def __init__(self, tasks_root: Path = None):
        if tasks_root is None:
            tasks_root = Path(__file__).resolve().parents[3] / "tasks"
        super().__init__(tasks_root, service="slack")
    
    def _get_service_directory_name(self) -> str:
        """Return the service directory name."""
        return "slack"
    
    def _find_task_files(self, category_dir: Path) -> List[Dict[str, Any]]:
        """Find task files in category directory."""
        task_files = []
        
        # 根据你的任务文件组织方式实现
        # 例如：task_X 目录包含 instruction.md 和 verify.py
        for task_dir in category_dir.iterdir():
            if not task_dir.is_dir() or not task_dir.name.startswith("task_"):
                continue
            
            try:
                task_id = int(task_dir.name.split("_")[1])
            except (IndexError, ValueError):
                continue
            
            instruction_path = task_dir / "instruction.md"
            verification_path = task_dir / "verify.py"
            
            if instruction_path.exists() and verification_path.exists():
                task_files.append({
                    "task_id": task_id,
                    "instruction_path": instruction_path,
                    "verification_path": verification_path
                })
        
        return task_files
    
    def _create_task_from_files(self, category_name: str, task_files_info: Dict[str, Any]) -> Optional[SlackTask]:
        """Create a SlackTask from file information."""
        return SlackTask(
            task_instruction_path=task_files_info["instruction_path"],
            task_verification_path=task_files_info["verification_path"],
            service="slack",
            category=category_name,
            task_id=task_files_info["task_id"],
        )
    
    def _get_verification_command(self, task: SlackTask) -> List[str]:
        """Get the verification command for Slack tasks."""
        return [
            sys.executable,
            str(task.task_verification_path),
            # 传递必要的参数，如工作区 ID 等
            task.workspace_id or "",
        ]
    
    def _format_task_instruction(self, base_instruction: str) -> str:
        """Format task instruction with Slack-specific additions."""
        return base_instruction + "\\n\\nNote: Use Slack API tools to complete this task."
```

## 步骤三：实现状态管理器

在 `{service_name}_state_manager.py` 中：

```python
from typing import Optional, Dict, Any
from src.base.state_manager import BaseStateManager, InitialStateInfo
from src.base.task_manager import BaseTask

class SlackStateManager(BaseStateManager):
    """Manages initial state setup and cleanup for Slack tasks."""
    
    def __init__(self, api_token: str, workspace_id: str):
        super().__init__("slack")
        self.api_token = api_token
        self.workspace_id = workspace_id
        # 初始化 Slack 客户端
        # self.slack_client = SlackClient(api_token)
    
    def _create_initial_state(self, task: BaseTask) -> Optional[InitialStateInfo]:
        """Create initial state for a Slack task."""
        try:
            # 创建测试频道或复制现有状态
            # channel_id = self.slack_client.create_test_channel(...)
            
            # 跟踪创建的资源
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
            # 清理特定任务的状态
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

## 步骤四：实现登录助手

在 `{service_name}_login_helper.py` 中：

```python
from pathlib import Path
from typing import Optional
from src.base.login_helper import BaseLoginHelper

class SlackLoginHelper(BaseLoginHelper):
    """Handles Slack authentication and session management."""
    
    def __init__(self, api_token: str, workspace_id: str, state_path: Optional[Path] = None):
        super().__init__("slack", state_path)
        self.api_token = api_token
        self.workspace_id = workspace_id
    
    def login(self) -> bool:
        """Perform Slack authentication."""
        try:
            # 验证 API token
            # response = self.slack_client.auth_test()
            # return response.get("ok", False)
            return True
        except Exception as e:
            logger.error(f"Slack login failed: {e}")
            return False
    
    def is_logged_in(self) -> bool:
        """Check if currently logged in to Slack."""
        # 检查认证状态
        return True
    
    def logout(self) -> bool:
        """Logout from Slack (if applicable)."""
        # Slack API tokens 通常不需要显式登出
        return True
```

## 步骤五：更新工厂配置

在 `src/factory.py` 中添加新服务的工厂和配置：

### 5.1 添加服务工厂

```python
class SlackServiceFactory(ServiceFactory):
    """Factory for creating Slack-specific managers."""

    def create_task_manager(self, config: ServiceConfig, **kwargs) -> BaseTaskManager:
        from src.mcp_services.slack.slack_task_manager import SlackTaskManager
        return SlackTaskManager(tasks_root=kwargs.get("tasks_root"))

    def create_state_manager(self, config: ServiceConfig, **kwargs) -> BaseStateManager:
        from src.mcp_services.slack.slack_state_manager import SlackStateManager
        return SlackStateManager(
            api_token=config.api_key,
            workspace_id=config.config["workspace_id"],
        )

    def create_login_helper(self, config: ServiceConfig, **kwargs) -> BaseLoginHelper:
        from src.mcp_services.slack.slack_login_helper import SlackLoginHelper
        return SlackLoginHelper(
            api_token=config.api_key,
            workspace_id=config.config["workspace_id"],
            state_path=kwargs.get("state_path"),
        )
```

### 5.2 注册服务配置

在 `MCPServiceFactory` 类中添加：

```python
SERVICE_CONFIGS = {
    # ... 现有配置 ...
    "slack": {
        "api_key_var": "SLACK_API_TOKEN",
        "additional_vars": {
            "workspace_id": "SLACK_WORKSPACE_ID",
            # 其他必需的环境变量
        },
    },
}

SERVICE_FACTORIES = {
    # ... 现有工厂 ...
    "slack": SlackServiceFactory(),
}
```

## 步骤六：更新 Agent 配置

在 `src/agent.py` 的 `_create_mcp_server` 方法中添加新服务支持：

```python
async def _create_mcp_server(self, **service_config):
    # ... 现有服务配置 ...
    
    elif self.service == "slack":
        # Slack MCP server 配置
        slack_token = service_config.get("slack_token")
        workspace_id = service_config.get("workspace_id")
        
        if not slack_token:
            raise ValueError("Slack API token (slack_token) is required for Slack MCP server")
        
        return MCPServerStdio(
            params={
                "command": "npx",
                "args": ["-y", "@slack/mcp-server"],  # 假设的包名
                "env": {
                    "SLACK_API_TOKEN": slack_token,
                    "SLACK_WORKSPACE_ID": workspace_id,
                },
            },
            client_session_timeout_seconds=120,
            cache_tools_list=True,
        )
```

## 步骤七：环境变量配置

在 `.mcp_env` 文件中添加新服务的环境变量：

```bash
# Slack 服务配置
SLACK_API_TOKEN=xoxb-your-slack-bot-token
SLACK_WORKSPACE_ID=your-workspace-id
```

## 步骤八：创建测试任务

在 `tasks/` 目录下创建服务任务结构：

```
tasks/
└── slack/
    └── channel_management/
        └── task_1/
            ├── instruction.md
            └── verify.py
```

### instruction.md 示例：
```markdown
# 创建新频道任务

请使用 Slack MCP 工具创建一个名为 "test-channel" 的新频道，并邀请用户 @john.doe 加入该频道。

## 要求：
1. 频道名称：test-channel
2. 频道描述：This is a test channel for evaluation
3. 设置为私有频道
4. 邀请用户：@john.doe
```

### verify.py 示例：
```python
#!/usr/bin/env python3
import sys
import os
from slack_sdk import WebClient

def verify_task(channel_id):
    client = WebClient(token=os.getenv("SLACK_API_TOKEN"))
    
    try:
        # 验证频道是否存在
        response = client.conversations_info(channel=channel_id)
        if not response["ok"]:
            return False
            
        channel = response["channel"]
        
        # 验证频道名称
        if channel["name"] != "test-channel":
            return False
            
        # 验证是否为私有频道
        if not channel["is_private"]:
            return False
            
        # 验证成员
        members_response = client.conversations_members(channel=channel_id)
        # ... 更多验证逻辑
        
        return True
    except Exception as e:
        print(f"Verification failed: {e}")
        return False

if __name__ == "__main__":
    channel_id = sys.argv[1] if len(sys.argv) > 1 else None
    success = verify_task(channel_id)
    sys.exit(0 if success else 1)
```

## 步骤九：参数管理

### 9.1 在 evaluator.py 中添加服务配置

更新 `_get_service_config_for_agent` 方法：

```python
def _get_service_config_for_agent(self) -> dict:
    service_config = {}
    
    # ... 现有服务配置 ...
    
    elif self.service == "slack":
        service_config["slack_token"] = MCPServiceFactory.create_service_config("slack").api_key
        service_config["workspace_id"] = MCPServiceFactory.create_service_config("slack").config["workspace_id"]
        
    return service_config
```

## 步骤十：测试和验证

### 10.1 单元测试

创建测试文件验证各组件：

```python
# tests/test_slack_service.py
import pytest
from src.mcp_services.slack.slack_task_manager import SlackTaskManager

def test_slack_task_discovery():
    manager = SlackTaskManager()
    tasks = manager.discover_all_tasks()
    assert len(tasks) > 0
```

### 10.2 集成测试

运行完整的评测流程：

```bash
python pipeline.py --service slack --models gpt-4o --tasks all --exp-name slack-test
```

## 注意事项

1. **错误处理**: 确保所有网络调用和外部 API 调用都有适当的错误处理
2. **资源清理**: 在 StateManager 中跟踪所有创建的资源，确保能够清理
3. **认证管理**: 安全地处理 API 密钥和认证信息
4. **日志记录**: 添加充分的日志记录以便调试
5. **文档更新**: 更新相关文档和 README
6. **配置验证**: 在初始化时验证必需的环境变量是否存在

## 完成检查清单

- [ ] 创建服务目录结构
- [ ] 实现 TaskManager、StateManager、LoginHelper
- [ ] 更新工厂配置
- [ ] 添加 Agent MCP server 支持
- [ ] 配置环境变量
- [ ] 创建测试任务
- [ ] 编写验证脚本
- [ ] 添加单元测试
- [ ] 运行集成测试
- [ ] 更新文档

通过遵循这个指南，你应该能够成功地将新的 MCP 服务集成到 MCPMark 框架中。