# MCPMark Docker image with optimized layer caching
# Stage 1: Builder for Python dependencies only
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy and install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Final image with all runtime dependencies
FROM python:3.12-slim

# Layer 1: Core system dependencies (very stable, rarely changes)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Layer 2: PostgreSQL runtime (stable, only changes with postgres version)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
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

# Layer 5: Node.js (changes with Node version)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get remove -y curl && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Layer 6: pipx (rarely changes)
RUN pip install --no-cache-dir pipx && \
    pipx ensurepath

# Layer 7: Copy Python packages from builder (changes with dependencies)
COPY --from=builder /root/.local /root/.local

# Layer 8: Playwright browsers (changes with browser versions)
RUN python3 -m playwright install chromium && \
    npx -y playwright install chromium

# Set working directory
WORKDIR /app

# Layer 9: Create directory structure (rarely changes)
RUN mkdir -p /app/results

# Layer 10: Application code (changes frequently)
COPY . .

# Set environment
ENV PATH="/root/.local/bin:/root/.local/pipx/venvs/*/bin:${PATH}"
ENV PYTHONPATH="/app"
ENV PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright
ENV PIPX_HOME=/root/.local/pipx
ENV PIPX_BIN_DIR=/root/.local/bin

# Default command
CMD ["python3", "-m", "pipeline", "--help"]