"""
Playwright State Manager for MCPBench
======================================

This module manages browser contexts and test environments for Playwright-based
web automation tasks. Handles browser isolation, test page setup, and cleanup.
"""

import time
from pathlib import Path
from typing import Optional, Dict, Any, List

from playwright.sync_api import (
    BrowserContext,
    Page,
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)

from src.base.state_manager import BaseStateManager, InitialStateInfo
from src.base.task_manager import BaseTask
from src.logger import get_logger

logger = get_logger(__name__)


class PlaywrightStateManager(BaseStateManager):
    """
    Manages browser state and test environments for Playwright tasks.
    
    Provides browser context isolation, test page setup, and resource cleanup
    for web automation evaluation.
    """

    # Keep a reference to the most recently created instance so that other
    # components (e.g. TaskManager instantiated later) can reuse the same
    # browser/context and avoid launching a separate one.
    _GLOBAL_INSTANCE: Optional["PlaywrightStateManager"] = None

    def __init__(
        self,
        browser: str = "chromium",
        headless: bool = True,
        state_path: Optional[Path] = None,
        network_origins: str = "*",
        user_profile: str = "isolated", 
        viewport_width: int = 1280,
        viewport_height: int = 720,
    ):
        """
        Initialize Playwright state manager.

        Args:
            browser: Browser engine to use ('chromium' or 'firefox')
            headless: Whether to run browser in headless mode  
            state_path: Path to browser state file
            network_origins: Allowed network origins (comma-separated or *)
            user_profile: User profile type (isolated or persistent)
            viewport_width: Browser viewport width
            viewport_height: Browser viewport height
        """
        super().__init__(service_name="playwright")
        
        self.browser_name = browser
        # self.headless = headless
        self.headless = False
        self.state_path = state_path or Path.cwd() / "playwright_state.json"
        self.network_origins = network_origins
        self.user_profile = user_profile
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        
        # Browser management
        self._playwright = None
        self._browser = None
        self._browser_server = None
        self._current_context: Optional[BrowserContext] = None
        
        # Task-specific tracking
        self._current_task_pages: List[Page] = []
        # Track the most recently active Playwright page so that verification can
        # reuse the exact same browser instance / DOM state created during task
        # execution. This avoids launching a brand-new browser for verification
        # which would miss in-memory changes (e.g. form submission results).
        self._last_active_page: Optional[Page] = None
        
        # Test environment URLs for different task categories
        self.test_environments = {
            "element_extraction": "https://mcp-eval-website.vercel.app/extraction",
            "form_interaction": "https://mcp-eval-website.vercel.app/forms/",
            "web_navigation": "https://mcp-eval-website.vercel.app/navigation",
        }
        
        logger.info("Playwright state manager initialized")

        # Register global singleton reference (best-effort)
        PlaywrightStateManager._GLOBAL_INSTANCE = self

    # ------------------------------------------------------------------
    # Singleton helper
    # ------------------------------------------------------------------

    @classmethod
    def get_global_instance(cls) -> Optional["PlaywrightStateManager"]:
        """Return the last instantiated PlaywrightStateManager (if any)."""
        return cls._GLOBAL_INSTANCE

    def _create_initial_state(self, task: BaseTask) -> Optional[InitialStateInfo]:
        """
        Create isolated browser context for task execution.
        
        Args:
            task: Task for which to create browser state
            
        Returns:
            InitialStateInfo with browser context details
        """
        try:
            logger.info(f"Setting up browser context for task: {task.name}")
            
            # NOTE: We no longer launch a local Playwright browser during Stage 1.
            # The actual browser session will be started by the Playwright MCP
            # server in Stage 2. Here we only resolve the test URL so the agent
            # knows which page to work with.

            test_url = self.test_environments.get(task.category)
            if not test_url:
                logger.warning(f"No test environment defined for category: {task.category}")
                test_url = None
            
            # We intentionally do NOT launch or connect to any browser here.
            # All browser operations happen inside the Playwright MCP server
            # during Stage 2.
            
            # Track the context for cleanup
            context_id = f"context_{task.category}_{task.task_id}_{int(time.time())}"
            self.track_resource('browser_context', context_id, {
                'task_name': task.name,
                'task_category': task.category,
                'test_url': test_url
            })
            
            return InitialStateInfo(
                state_id=context_id,
                state_url=test_url,
                metadata={
                    'browser': self.browser_name,
                    'headless': self.headless,
                    'test_url': test_url,
                    'task_category': task.category
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to create browser state for {task.name}: {e}")
            return None

    def _store_initial_state_info(self, task: BaseTask, state_info: InitialStateInfo) -> None:
        """Store browser context information in task object."""
        if hasattr(task, '__dict__'):
            task.browser_context_id = state_info.state_id
            task.test_url = state_info.state_url
            task.browser_config = state_info.metadata

    def _cleanup_task_initial_state(self, task: BaseTask) -> bool:
        """Clean up browser context for specific task."""
        try:
            success = True
            
            # Close any open pages
            if self._current_task_pages:
                for page in self._current_task_pages:
                    try:
                        page.close()
                    except Exception as e:
                        logger.warning(f"Failed to close page: {e}")
                        success = False
                self._current_task_pages.clear()
            
            # Close browser context
            if self._current_context:
                try:
                    self._current_context.close()
                    logger.info("Closed browser context")
                except Exception as e:
                    logger.error(f"Failed to close browser context: {e}")
                    success = False
                finally:
                    self._current_context = None
            
            return success
            
        except Exception as e:
            logger.error(f"Error during browser cleanup for {task.name}: {e}")
            return False

    def _cleanup_single_resource(self, resource: Dict[str, Any]) -> bool:
        """Clean up a single browser resource."""
        try:
            if resource['type'] == 'browser_context':
                # Context cleanup is handled in _cleanup_task_initial_state
                logger.debug(f"Browser context {resource['id']} marked for cleanup")
                return True
            
            logger.warning(f"Unknown resource type for cleanup: {resource['type']}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to cleanup resource {resource}: {e}")
            return False

    # =========================================================================
    # Page tracking helpers
    # =========================================================================

    def _remember_page(self, page: Page) -> None:
        """Record Page object for later verification and mark it as last active."""
        if page not in self._current_task_pages:
            self._current_task_pages.append(page)
        self._last_active_page = page
        try:
            print(
                f"[PlaywrightStateManager] Remember page id={id(page)} url={page.url if page else '<no url>'} "
                f"(total tracked={len(self._current_task_pages)})"
            )
        except Exception:
            pass

    def get_last_page(self) -> Optional[Page]:
        """Return the most recently used Playwright Page (if any)."""
        if self._last_active_page and not self._last_active_page.is_closed():
            return self._last_active_page

        # Fallback: try to pick the last page from any existing context – this
        # helps when the MCP server (connected over CDP) created new pages that
        # we didn't explicitly track via _remember_page.
        try:
            if self._browser:
                for context in self._browser.contexts:
                    if context.pages:
                        return context.pages[-1]
        except Exception:
            pass

        # ---------------------------------------------------------------
        # If we haven't connected to any browser yet, but Stage 2 (MCP
        # server) has written its wsEndpoint to a well-known file, attempt to
        # connect now so that verification can reuse the same session.
        # ---------------------------------------------------------------
        import os
        from pathlib import Path
        try:
            ws_file = os.environ.get("MCP_PW_WS_FILE")
            if ws_file:
                ws_path = Path(ws_file)

                # ------------------------------------------------------------------
                # 1. Legacy path – server wrote plain text wsEndpoint to file.
                # ------------------------------------------------------------------
                if ws_path.exists():
                    try:
                        endpoint = ws_path.read_text().strip()
                        if endpoint:
                            if not self._playwright:
                                from playwright.sync_api import sync_playwright
                                self._playwright = sync_playwright().start()
                            self._browser = self._playwright.chromium.connect(endpoint)
                    except Exception:
                        pass

                # ------------------------------------------------------------------
                # 2. Newer @playwright/mcp path – session information is stored in
                #    a JSON file inside the output directory (specified via
                #    --save-session).  Try to locate and parse that file to obtain
                #    "wsEndpoint" / "cdpEndpoint" value.
                # ------------------------------------------------------------------
                if not self._browser:
                    try:
                        from json import loads
                        base_dir = ws_path.parent
                        # 2a. Direct session.json inside output_dir
                        candidates: List[Path] = [base_dir / "session.json"]
                        # 2b. Any session-*/session.json created by Playwright MCP
                        candidates.extend(base_dir.glob("session-*/session.json"))

                        for session_json_path in candidates:
                            if not session_json_path.exists():
                                continue
                            try:
                                data = loads(session_json_path.read_text())
                            except Exception:
                                continue
                            endpoint = (
                                data.get("wsEndpoint")
                                or data.get("cdpEndpoint")
                                or data.get("browserServerEndpoint")
                            )
                            if endpoint:
                                if not self._playwright:
                                    from playwright.sync_api import sync_playwright
                                    self._playwright = sync_playwright().start()
                                self._browser = self._playwright.chromium.connect(endpoint)
                                break
                    except Exception:
                        pass

                if self._browser and self._browser.contexts and self._browser.contexts[0].pages:
                    try:
                        page = self._browser.contexts[0].pages[-1]
                        self._remember_page(page)
                        return page
                    except Exception:
                        pass
        except Exception:
            pass

        return None

    def _get_context_options(self, task: BaseTask) -> Dict[str, Any]:
        """Get browser context options based on task requirements."""
        options = {
            "viewport": {"width": self.viewport_width, "height": self.viewport_height}
        }
        
        # Load browser state if available
        if self.state_path.exists():
            try:
                options["storage_state"] = str(self.state_path)
            except Exception as e:
                logger.warning(f"Failed to load browser state: {e}")
        
        # Task-specific context options
        if task.category == "form_interaction":
            # Enable form interactions
            options["permissions"] = ["geolocation"]
        elif task.category == "web_navigation":
            # Allow navigation between pages
            options["accept_downloads"] = False
        
        return options

    def _setup_test_environment(self, task: BaseTask) -> Optional[str]:
        """Set up test environment for task category."""
        try:
            test_url = self.test_environments.get(task.category)
            if not test_url:
                logger.warning(f"No test environment defined for category: {task.category}")
                return None
            
            # Create a page and navigate to test environment
            if self._current_context:
                page = self._current_context.new_page()
                
                # Navigate to test URL to ensure it's accessible
                page.goto(test_url, wait_until="networkidle", timeout=30000)
                logger.info(f"Test environment ready: {test_url}")
                
                # Track the page and mark it as active
                self._remember_page(page)
                
                # Verify page loaded correctly
                title = page.title()
                if title:
                    logger.debug(f"Page loaded with title: {title}")
                
                return test_url
            
        except PlaywrightTimeoutError:
            logger.error(f"Timeout loading test environment: {test_url}")
        except Exception as e:
            logger.error(f"Failed to setup test environment: {e}")
        
        return None

    def get_current_context(self) -> Optional[BrowserContext]:
        """Get the current browser context."""
        return self._current_context

    def get_test_page(self) -> Optional[Page]:
        """Get a page for testing (creates new one if needed)."""
        # First, try to reuse the most recently active page so that automation
        # and verification share EXACTLY the same browser tab (maintains
        # in-memory form state for pure-frontend pages).
        if self._last_active_page and not self._last_active_page.is_closed():
            return self._last_active_page

        # If no page was recorded yet (or the previous one was closed), fall
        # back to creating a new tab within the *same* browser context so we
        # still stay inside the current browser/session.
        if self._current_context:
            try:
                page = self._current_context.new_page()
                self._remember_page(page)
                return page
            except Exception as e:
                logger.error(f"Failed to create test page: {e}")

        # No browser context available – caller should make sure set_up() has
        # been invoked before requesting a page.
        return None

    def navigate_to_test_url(self, task: BaseTask) -> Optional[Page]:
        """Navigate to the test URL for a specific task."""
        test_url = self.test_environments.get(task.category)
        if not test_url:
            logger.error(f"No test URL defined for category: {task.category}")
            return None
            
        page = self.get_test_page()
        if page:
            try:
                page.goto(test_url, wait_until="networkidle", timeout=30000)
                logger.info(f"Navigated to test URL: {test_url}")
                return page
            except Exception as e:
                logger.error(f"Failed to navigate to {test_url}: {e}")
        
        return None

    def get_service_config_for_agent(self) -> dict:
        """
        Get service-specific configuration for agent execution.
        
        Returns:
            Dictionary containing browser configuration for MCP server
        """
        config = {
            "browser": self.browser_name,
            "headless": self.headless,
        }

        # If we already launched a browser, expose its CDP endpoint so that the
        # MCP server can connect to the SAME browser instead of launching a new
        # one. This requires @playwright/mcp to be started with --cdp-endpoint …
        try:
            if self._browser_server and hasattr(self._browser_server, "ws_endpoint"):
                config["cdp_endpoint"] = self._browser_server.ws_endpoint
        except Exception:
            pass
        
        # Add browser state file if it exists
        if self.state_path.exists():
            config["browser_state"] = str(self.state_path)
        
        # Add test environment URLs
        config["test_environments"] = self.test_environments
        
        return config

    def close_all(self) -> None:
        """Close all browser resources."""
        try:
            # Close all pages
            for page in self._current_task_pages:
                try:
                    page.close()
                except Exception:
                    pass
            self._current_task_pages.clear()
            
            # Close context
            if self._current_context:
                self._current_context.close()
                self._current_context = None
            
            # Close browser
            if self._browser:
                self._browser.close()
                self._browser = None
            
            # Stop Playwright
            if self._playwright:
                self._playwright.stop()
                self._playwright = None
                
            logger.info("All browser resources closed")
            
        except Exception as e:
            logger.error(f"Error closing browser resources: {e}")

    def __del__(self):
        """Ensure cleanup on deletion."""
        self.close_all()