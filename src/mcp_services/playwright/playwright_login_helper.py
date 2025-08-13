"""
Playwright Login Helper for MCPMark
====================================

This module provides browser session management and authentication utilities
for Playwright-based web automation tasks. Handles browser context setup,
session persistence, and state management.
"""

from pathlib import Path
from typing import Optional

from playwright.sync_api import (
    BrowserContext,
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)

from src.base.login_helper import BaseLoginHelper
from src.logger import get_logger

logger = get_logger(__name__)


class PlaywrightLoginHelper(BaseLoginHelper):
    """
    Login helper for Playwright web automation tasks.
    
    Manages browser contexts, session persistence, and authentication state
    for web automation scenarios.
    """

    SUPPORTED_BROWSERS = {"chromium", "firefox"}

    def __init__(
        self,
        *,
        browser: str = "chromium",
        headless: bool = True,
        state_path: Optional[str | Path] = None,
    ) -> None:
        """
        Initialize the Playwright login helper.

        Args:
            browser: Browser engine to use ('chromium' or 'firefox')
            headless: Whether to run browser in headless mode
            state_path: Path to save browser session state
        """
        super().__init__()
        
        if browser not in self.SUPPORTED_BROWSERS:
            raise ValueError(
                f"Unsupported browser '{browser}'. Supported: {', '.join(self.SUPPORTED_BROWSERS)}"
            )

        self.browser_name = browser
        self.headless = headless
        self.state_path = (
            Path(state_path or Path.cwd() / "playwright_state.json").expanduser().resolve()
        )
        
        # Browser management
        self._playwright = None
        self._browser = None
        self._browser_context: Optional[BrowserContext] = None
        
        logger.info(f"Initialized PlaywrightLoginHelper with {browser} browser")

    def login(self, **kwargs) -> bool:
        """
        Set up browser context and session state.
        
        For most Playwright tasks, this creates a clean browser context
        that can be used for web automation. More complex authentication
        can be handled in specific implementations.

        Returns:
            bool: True if browser setup successful
        """
        try:
            # Clean up any existing browser instances
            self.close()
            
            # Start Playwright
            self._playwright = sync_playwright().start()
            browser_type = getattr(self._playwright, self.browser_name)
            self._browser = browser_type.launch(headless=self.headless)
            
            # Create browser context
            context_options = {}
            
            # Load existing state if available
            if self.state_path.exists():
                try:
                    context_options["storage_state"] = str(self.state_path)
                    logger.info(f"Loaded browser state from {self.state_path}")
                except Exception as e:
                    logger.warning(f"Failed to load browser state: {e}")
            
            self._browser_context = self._browser.new_context(**context_options)
            
            # Save current state
            self._save_browser_state()
            
            logger.info("✅ Browser context setup successful")
            return True
            
        except Exception as e:
            logger.error(f"Browser setup failed: {e}")
            self.close()
            return False

    def get_browser_context(self) -> Optional[BrowserContext]:
        """
        Get the current browser context.
        
        Returns:
            BrowserContext or None if not initialized
        """
        return self._browser_context

    def is_authenticated(self) -> bool:
        """
        Check if browser context is ready for use.
        
        Returns:
            bool: True if browser context is available
        """
        return self._browser_context is not None

    def get_credentials(self) -> dict:
        """
        Get browser configuration for MCP integration.
        
        Returns:
            dict: Browser configuration parameters
        """
        return {
            "browser": self.browser_name,
            "headless": self.headless,
            "state_path": str(self.state_path)
        }

    def _save_browser_state(self) -> None:
        """Save current browser state to file."""
        if self._browser_context:
            try:
                self._browser_context.storage_state(path=str(self.state_path))
                logger.debug(f"Browser state saved to {self.state_path}")
            except Exception as e:
                logger.warning(f"Failed to save browser state: {e}")

    def close(self) -> None:
        """Clean up browser resources."""
        if self._browser_context:
            try:
                # Save state before closing
                self._save_browser_state()
                self._browser_context.close()
            except Exception as e:
                logger.warning(f"Error closing browser context: {e}")
            finally:
                self._browser_context = None

        if self._browser:
            try:
                self._browser.close()
            except Exception as e:
                logger.warning(f"Error closing browser: {e}")
            finally:
                self._browser = None

        if self._playwright:
            try:
                self._playwright.stop()
            except Exception as e:
                logger.warning(f"Error stopping Playwright: {e}")
            finally:
                self._playwright = None

