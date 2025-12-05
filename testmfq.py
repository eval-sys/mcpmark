import asyncio
import os
from loguru import logger

# Reuse WebArenaSandbox from agentgym
from agentgym.sandbox.webarena import WebArenaSandbox
from agentgym.sandbox.mcp import MCPSandbox
from agentgym.sandbox.components.mcphub_models import ServerConfig

# Fix for potential aenter issue if it exists (keeping consistent with previous file style)
class MyWebArenaSandbox(WebArenaSandbox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._session = None

    async def __aenter_long__(self):
        if self._session is None:
            await self.start()
        return self


async def main():
    # 1. Start WebArena Sandbox (Target Website Host)
    logger.info("Starting WebArena Sandbox (Target)...")
    webarena = MyWebArenaSandbox(group='label3', ttl=3600*24*5)
    await webarena.start()
    
    # 2. Start MCP Sandbox (Agent/Tool Host)
    logger.info("Starting MCP Sandbox (Tool Host)...")
    mcp_sandbox = MCPSandbox(ttl=3600*24*5)
    await mcp_sandbox.start()

    # 3. Setup Playwright MCP in MCP Sandbox
    logger.info("Setting up Playwright MCP in MCP Sandbox...")
    
    # Ensure Node.js and npx are available (if not in default image)
    # Trying to install if missing, or just proceed
    # await mcp_sandbox.shell.exec("curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && apt-get install -y nodejs")
    
    # Import the Playwright MCP server
    # npx -y @playwright/mcp@latest --headless --no-sandbox
    await mcp_sandbox.mcphub.import_servers(
        playwright=ServerConfig(
            type="stdio",
            command="npx",
            args=[
                "-y", 
                "@playwright/mcp@latest",
                "--headless",
                "--isolated",
                "--no-sandbox",
                "--browser", "chromium",
                "--viewport-size", "1280,720"
            ],
        )
    )
    
    logger.info("Waiting for MCP Servers to be ready...")
    ready = await mcp_sandbox.mcphub.wait_all_servers_ready()
    if not ready:
        logger.error("MCP Servers failed to start. Checking logs...")
        # Optional: check logs
        # logs = await mcp_sandbox.proc.get_output("playwright") # process name might be different
        raise RuntimeError("MCP Servers not ready")

    # Get the connection URL
    # MCPSandbox exposes a unified streamable HTTP endpoint for all imported servers
    # The URL pattern is usually http://<host>:<port>/sse
    # But AgentGym's MCPSandbox might expose a specific URL structure.
    # mcp_sandbox.streamable_http_url returns the endpoint.
    mcp_url = mcp_sandbox.streamable_http_url
    logger.info(f"MCP Server URL: {mcp_url}")

    logger.info(f"WebArena ID: {webarena.session_id}")
    logger.info(f"MCP Sandbox ID: {mcp_sandbox.session_id}")

    # 4. Save Endpoints
    result_file = "/home/mengfanqing/cua/zhangjin/endpoints_mfq3.txt"
    with open(result_file, "w", encoding="utf-8") as f:
        f.write(f"webarena_id: {webarena.session_id}\n")
        f.write(f"mcp_sandbox_id: {mcp_sandbox.session_id}\n")
        f.write(f"mcp_server_url: {mcp_url}\n")
        
        # WebArena Endpoints
        f.write(f"homepage: {getattr(webarena, 'endpoint_homepage', '')}\n")
        f.write(f"gitlab: {getattr(webarena, 'endpoint_gitlab', '')}\n")
        f.write(f"reddit: {getattr(webarena, 'endpoint_reddit', '')}\n")
        f.write(f"map: {getattr(webarena, 'endpoint_map', '')}\n")
        f.write(f"wiki: {getattr(webarena, 'endpoint_wiki', '')}\n")
        f.write(f"shopping: {getattr(webarena, 'endpoint_shopping', '')}\n")
        f.write(f"shopping_admin: {getattr(webarena, 'endpoint_shopping_admin', '')}\n")
    
    logger.info(f"Endpoints saved to {result_file}")
    
    # Keep alive
    logger.info("Sandboxes running. Press Ctrl+C to stop (but process will sleep).")
    await asyncio.sleep(3600*24*5)


if __name__ == "__main__":
    asyncio.run(main())
