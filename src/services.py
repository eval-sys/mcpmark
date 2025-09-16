"""
Service Definitions for MCPMark
================================

Single source of truth for all MCP service configurations.
Adding a new service only requires modifying this file.

Note: Environment variables are already loaded from .mcp_env when the app starts,
so we can reference them directly via the config system.

MCP server creation is now handled entirely within src.agent.MCPAgent; therefore,
the legacy "mcp_server" and "eval_config" entries in each service definition are
deprecated and set to None for backward-compatibility.
"""

# Service definitions
SERVICES = {
    "notion": {
        "config_schema": {
            "source_api_key": {
                "env_var": "SOURCE_NOTION_API_KEY",
                "required": True,
                "description": "Notion API key for source hub with templates",
            },
            "eval_api_key": {
                "env_var": "EVAL_NOTION_API_KEY",
                "required": True,
                "description": "Notion API key for evaluation hub",
            },
            "source_parent_page_title": {
                "env_var": "SOURCE_PARENT_PAGE_TITLE",
                "default": "MCPMark Source Hub",
                "required": False,
                "description": "Title of the source hub page that contains all initial states",
            },
            "eval_parent_page_title": {
                "env_var": "EVAL_PARENT_PAGE_TITLE",
                "required": True,
                "description": "Title of the parent page in evaluation workspace",
            },
            "playwright_headless": {
                "env_var": "PLAYWRIGHT_HEADLESS",
                "default": True,
                "required": False,
                "description": "Run browser in headless mode",
                "transform": "bool",  # Will be handled by GenericConfigSchema
            },
            "playwright_browser": {
                "env_var": "PLAYWRIGHT_BROWSER",
                "default": "firefox",
                "required": False,
                "description": "Browser to use for Playwright",
                "validator": "in:chromium,firefox,webkit",  # Simple validator syntax
            },
        },
        "components": {
            "task_manager": "src.mcp_services.notion.notion_task_manager.NotionTaskManager",
            "state_manager": "src.mcp_services.notion.notion_state_manager.NotionStateManager",
            "login_helper": "src.mcp_services.notion.notion_login_helper.NotionLoginHelper",
        },
        "config_mapping": {
            # Maps config schema keys to class constructor parameters
            "state_manager": {
                "source_notion_key": "source_api_key",
                "eval_notion_key": "eval_api_key",
                "headless": "playwright_headless",
                "browser": "playwright_browser",
                "source_parent_page_title": "source_parent_page_title",
                "eval_parent_page_title": "eval_parent_page_title",
            },
            "login_helper": {
                "headless": "playwright_headless",
                "browser": "playwright_browser",
            },
        },
        # MCP server is now instantiated dynamically in MCPAgent; kept for backward
        # compatibility but set to None to indicate deprecation.
        "mcp_server": None,
        "eval_config": None,
    },
    "github": {
        "config_schema": {
            "github_tokens": {
                "env_var": "GITHUB_TOKENS",
                "required": True,
                "description": "GitHub personal access token(s) - comma-separated for round-robin",
                "transform": "list",  # Will split by comma
            },
            # Evaluation organisation / user that hosts ephemeral test repositories
            "eval_org": {
                "env_var": "GITHUB_EVAL_ORG",
                "default": "mcpleague-eval",
                "required": False,
                "description": "Evaluation organisation or user for creating temporary test repositories",
            },
            # (source_org removed – template repos now imported from local files)
        },
        "components": {
            "task_manager": "src.mcp_services.github.github_task_manager.GitHubTaskManager",
            "state_manager": "src.mcp_services.github.github_state_manager.GitHubStateManager",
            "login_helper": "src.mcp_services.github.github_login_helper.GitHubLoginHelper",
        },
        "config_mapping": {
            "state_manager": {
                "github_token": "github_tokens",
                "eval_org": "eval_org",
            },
            "login_helper": {
                # Login helper needs a single token, we'll use the first one
                "token": "github_tokens",
            },
        },
        "mcp_server": None,
        "eval_config": None,
    },
    "filesystem": {
        "config_schema": {
            "test_root": {
                "env_var": "FILESYSTEM_TEST_ROOT",
                "default": None,
                "required": False,
                "description": "Root directory for filesystem tests",
                "transform": "path",  # Convert to Path object
            },
            "cleanup_on_exit": {
                "env_var": "FILESYSTEM_CLEANUP",
                "default": True,
                "required": False,
                "description": "Clean up test directories after tasks",
                "transform": "bool",
            },
        },
        "components": {
            "task_manager": "src.mcp_services.filesystem.filesystem_task_manager.FilesystemTaskManager",
            "state_manager": "src.mcp_services.filesystem.filesystem_state_manager.FilesystemStateManager",
            "login_helper": "src.mcp_services.filesystem.filesystem_login_helper.FilesystemLoginHelper",
        },
        "config_mapping": {
            "state_manager": {
                "test_root": "test_root",
                "cleanup_on_exit": "cleanup_on_exit",
            }
        },
        "mcp_server": None,
        "eval_config": None,
    },
    "playwright": {
        "config_schema": {
            "browser": {
                "env_var": "PLAYWRIGHT_BROWSER",
                "default": "chromium",
                "required": False,
                "description": "Browser to use (chromium, firefox, webkit)",
                "validator": "in:chromium,firefox,webkit",
            },
            "headless": {
                "env_var": "PLAYWRIGHT_HEADLESS",
                "default": True,
                "required": False,
                "description": "Run browser in headless mode",
                "transform": "bool",
            },
            "network_origins": {
                "env_var": "PLAYWRIGHT_NETWORK_ORIGINS",
                "default": "*",
                "required": False,
                "description": "Allowed network origins (comma-separated or *)",
            },
            "user_profile": {
                "env_var": "PLAYWRIGHT_USER_PROFILE",
                "default": "isolated",
                "required": False,
                "description": "User profile type (isolated or persistent)",
                "validator": "in:isolated,persistent",
            },
            "viewport_width": {
                "env_var": "PLAYWRIGHT_VIEWPORT_WIDTH",
                "default": 1280,
                "required": False,
                "description": "Browser viewport width",
                "transform": "int",
            },
            "viewport_height": {
                "env_var": "PLAYWRIGHT_VIEWPORT_HEIGHT",
                "default": 720,
                "required": False,
                "description": "Browser viewport height",
                "transform": "int",
            },
        },
        "components": {
            "task_manager": "src.mcp_services.playwright.playwright_task_manager.PlaywrightTaskManager",
            "state_manager": "src.mcp_services.playwright.playwright_state_manager.PlaywrightStateManager",
            "login_helper": "src.mcp_services.playwright.playwright_login_helper.PlaywrightLoginHelper",
        },
        "config_mapping": {
            "state_manager": {
                "browser": "browser",
                "headless": "headless",
                "network_origins": "network_origins",
                "user_profile": "user_profile",
                "viewport_width": "viewport_width",
                "viewport_height": "viewport_height",
            },
            "login_helper": {
                "browser": "browser",
                "headless": "headless",
            },
        },
        "mcp_server": None,
        "eval_config": None,
    },
    "postgres": {
        "config_schema": {
            "host": {
                "env_var": "POSTGRES_HOST",
                "default": "localhost",
                "required": False,
                "description": "PostgreSQL server host",
            },
            "port": {
                "env_var": "POSTGRES_PORT",
                "default": 5432,
                "required": False,
                "description": "PostgreSQL server port",
                "transform": "int",
                "validator": "port",  # Validates port range 1-65535
            },
            "database": {
                "env_var": "POSTGRES_DATABASE",
                "default": "postgres",
                "required": False,
                "description": "PostgreSQL database name",
            },
            "username": {
                "env_var": "POSTGRES_USERNAME",
                "default": "postgres",
                "required": False,
                "description": "PostgreSQL username",
            },
            "password": {
                "env_var": "POSTGRES_PASSWORD",
                "default": "password",
                "required": False,
                "description": "PostgreSQL password",
            },
        },
        "components": {
            "task_manager": "src.mcp_services.postgres.postgres_task_manager.PostgresTaskManager",
            "state_manager": "src.mcp_services.postgres.postgres_state_manager.PostgresStateManager",
            "login_helper": "src.mcp_services.postgres.postgres_login_helper.PostgresLoginHelper",
        },
        "config_mapping": {
            "state_manager": {
                "host": "host",
                "port": "port",
                "database": "database",
                "username": "username",
                "password": "password",
            },
            "login_helper": {
                "host": "host",
                "port": "port",
                "database": "database",
                "username": "username",
                "password": "password",
            },
        },
        "mcp_server": None,
        "eval_config": None,
    },
    "playwright_webarena": {
        "config_schema": {
            "browser": {
                "env_var": "PLAYWRIGHT_BROWSER",
                "default": "chromium",
                "required": False,
                "description": "Browser to use (chromium, firefox, webkit)",
                "validator": "in:chromium,firefox,webkit",
            },
            "headless": {
                "env_var": "PLAYWRIGHT_HEADLESS",
                "default": True,
                "required": False,
                "description": "Run browser in headless mode",
                "transform": "bool",
            },
            "network_origins": {
                "env_var": "PLAYWRIGHT_NETWORK_ORIGINS",
                "default": "*",
                "required": False,
                "description": "Allowed network origins (comma-separated or *)",
            },
            "user_profile": {
                "env_var": "PLAYWRIGHT_USER_PROFILE",
                "default": "isolated",
                "required": False,
                "description": "User profile type (isolated or persistent)",
                "validator": "in:isolated,persistent",
            },
            "viewport_width": {
                "env_var": "PLAYWRIGHT_VIEWPORT_WIDTH",
                "default": 1280,
                "required": False,
                "description": "Browser viewport width",
                "transform": "int",
            },
            "viewport_height": {
                "env_var": "PLAYWRIGHT_VIEWPORT_HEIGHT",
                "default": 720,
                "required": False,
                "description": "Browser viewport height",
                "transform": "int",
            },
            "skip_cleanup": {
                "env_var": "PLAYWRIGHT_WEBARENA_SKIP_CLEANUP",
                "default": False,
                "required": False,
                "description": "Skip Docker container cleanup for debugging",
                "transform": "bool",
            },
        },
        "components": {
            "task_manager": "src.mcp_services.playwright_webarena.playwright_task_manager.PlaywrightTaskManager",
            "state_manager": "src.mcp_services.playwright_webarena.playwright_state_manager.PlaywrightStateManager",
            "login_helper": "src.mcp_services.playwright_webarena.playwright_login_helper.PlaywrightLoginHelper",
        },
        "config_mapping": {
            "state_manager": {
                "browser": "browser",
                "headless": "headless",
                "network_origins": "network_origins",
                "user_profile": "user_profile",
                "viewport_width": "viewport_width",
                "viewport_height": "viewport_height",
                "skip_cleanup": "skip_cleanup",
            },
            "login_helper": {
                "browser": "browser",
                "headless": "headless",
            },
            "task_manager": {},
        },
        "mcp_server": None,
        "eval_config": None,
    },
}


def get_service_definition(service_name: str) -> dict:
    """Get MCP service definition by name."""
    if service_name not in SERVICES:
        raise ValueError(f"Unknown MCP service: {service_name}")
    return SERVICES[service_name]


def get_supported_mcp_services() -> list:
    """Get list of implemented MCP services."""
    return [
        name
        for name, config in SERVICES.items()
        if config["components"]["task_manager"] is not None
    ]
