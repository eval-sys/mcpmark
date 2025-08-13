"""
WebArena (Docker) Login Helper for MCPMark
==========================================

This helper exposes basic browser configuration for agents. Authentication is
not required for the public WebArena environment; isolation is handled via
Docker containerization in the state manager.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from src.base.login_helper import BaseLoginHelper
from src.logger import get_logger

logger = get_logger(__name__)


class PlaywrightLoginHelper(BaseLoginHelper):
    """
    Minimal login helper. It does not launch browsers; that is handled by
    the Playwright MCP client. It simply exposes configuration parameters such
    as headless mode and an optional storage state file path.
    """

    def __init__(
        self,
        *,
        browser: str = "chromium",
        headless: bool = True,
        state_path: Optional[str | Path] = None,
        base_url: Optional[str] = None,
    ) -> None:
        super().__init__()
        self.browser_name = browser
        self.headless = headless
        self.state_path = Path(state_path or Path.cwd() / "playwright_state.json").expanduser().resolve()
        self.base_url = base_url
        logger.info("Initialized WebArenaLoginHelper (browser=%s, headless=%s)", browser, headless)

    def login(self, **kwargs) -> bool:
        """
        No-op login. For WebArena we don't need credentials; we only provide
        configuration for the MCP to open a browser.
        """
        logger.info("WebArenaLoginHelper login: no-op")
        return True

    def is_authenticated(self) -> bool:
        return True

    def get_credentials(self) -> dict:
        return {
            "browser": self.browser_name,
            "headless": self.headless,
            "state_path": str(self.state_path),
            "base_url": self.base_url,
        }

    def close(self) -> None:
        # No resources to release
        pass 