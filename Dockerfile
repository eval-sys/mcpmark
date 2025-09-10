# MCPMark Docker image with optimized layer caching
FROM python:3.12-slim

# Layer 1: Core system dependencies (very stable, rarely changes)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Layer 2: PostgreSQL runtime and client tools (stable, only changes with postgres version)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Layer 3: Git (stable)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Layer 4: Playwright system dependencies (changes with browser requirements)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libxcb1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Layer 5: Download tools and Node.js (changes with Node version)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl wget unzip && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Layer 6: pipx (rarely changes)
RUN pip install --no-cache-dir pipx && \
    pipx ensurepath

# Layer 9: Install PostgreSQL MCP server (Python, used via `pipx run postgres-mcp`)
RUN pipx install postgres-mcp

# Set working directory
WORKDIR /app

# Layer 9: Create directory structure (rarely changes)
RUN mkdir -p /app/results

# Layer 10: Application code (changes frequently)
COPY . .

# Install Python package and dependencies from pyproject (editable mode)
RUN pip install --no-cache-dir -e .

# Install Playwright browsers after Playwright is available
RUN python3 -m playwright install chromium && \
    npx -y playwright install chromium

# Set environment
ENV PATH="/root/.local/bin:/root/.local/pipx/venvs/*/bin:${PATH}"
ENV PYTHONPATH="/app"
ENV PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright
ENV PIPX_HOME=/root/.local/pipx
ENV PIPX_BIN_DIR=/root/.local/bin

# Default command
CMD ["python3", "-m", "pipeline", "--help"]