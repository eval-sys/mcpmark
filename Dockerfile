# Multi-stage build for MCPBench
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir --user -r requirements.txt && \
    pip install --no-cache-dir --user -e .

# Final stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    # PostgreSQL client libraries
    libpq5 \
    postgresql-client \
    # Node.js and npm for MCP servers
    nodejs \
    npm \
    # Git for version control
    git \
    # Curl and wget for downloads
    curl \
    wget \
    # Graphics libraries for matplotlib
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libglu1-mesa \
    # Fonts for matplotlib
    fonts-liberation \
    # Process management
    procps \
    # Certificate handling
    ca-certificates \
    # Required for Playwright
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libatspi2.0-0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libdrm2 \
    libxcb1 \
    libxkbcommon0 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Install pipx for Python tools
RUN pip install --no-cache-dir pipx && \
    pipx ensurepath

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Set working directory
WORKDIR /app

# Copy application code
COPY . .

# Install Playwright browsers
RUN python3 -m playwright install chromium firefox

# Install global npm packages for MCP servers (cached for faster runs)
RUN npm install -g \
    @notionhq/notion-mcp-server \
    @modelcontextprotocol/server-filesystem \
    @playwright/mcp

# Install postgres-mcp via pipx
RUN /root/.local/bin/pipx install postgres-mcp

# Create results directory
RUN mkdir -p /app/results

# Add Python packages to PATH
ENV PATH="/root/.local/bin:${PATH}"
ENV PYTHONPATH="/app:${PYTHONPATH}"

# Set environment variables for Playwright
ENV PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0

# Create a non-root user (optional but recommended for security)
# RUN useradd -m -s /bin/bash mcpuser && \
#     chown -R mcpuser:mcpuser /app
# USER mcpuser

# Default command
CMD ["python3", "-m", "pipeline", "--help"]