# MCPBench Docker image with multi-stage build
FROM python:3.12-slim AS builder

# Install build essentials for compiling Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy and install Python dependencies
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir --user -r requirements.txt && \
    pip install --no-cache-dir --user -e .

# Final stage
FROM python:3.12-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # PostgreSQL runtime library (only for postgres service, ~200KB)
    libpq5 \
    # Git (required for version control tasks)
    git \
    ca-certificates \
    # Minimal Playwright dependencies
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

# Install Node.js from NodeSource (curl is required temporarily)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get remove -y curl && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

WORKDIR /app

# Copy application code
COPY . .

# Install Playwright with chromium only (smaller than installing all browsers)
# Install for both Python and Node.js versions
RUN python3 -m playwright install chromium && \
    npx -y playwright install chromium

# Install pipx (for running Python-based MCP servers)
RUN pip install --no-cache-dir pipx && \
    pipx ensurepath

# Create results directory
RUN mkdir -p /app/results

# Set environment
# Include both Python user packages and pipx binaries in PATH
ENV PATH="/root/.local/bin:/root/.local/pipx/venvs/*/bin:${PATH}"
ENV PYTHONPATH="/app"
ENV PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright
ENV PIPX_HOME=/root/.local/pipx
ENV PIPX_BIN_DIR=/root/.local/bin

# Default command (shows help, override when running)
CMD ["python3", "-m", "pipeline", "--help"]