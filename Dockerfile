# MCPBench Docker image with multi-stage build
FROM python:3.11-slim as builder

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
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # PostgreSQL runtime library (required for psycopg2)
    libpq5 \
    # Git (required for version control tasks)
    git \
    # Curl (required for downloading)
    curl \
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

# Install Node.js from NodeSource
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

WORKDIR /app

# Copy application code
COPY . .

# Install Playwright with chromium only (smaller than installing all browsers)
RUN python3 -m playwright install chromium

# Create results directory
RUN mkdir -p /app/results

# Set environment
ENV PATH="/root/.local/bin:${PATH}"
ENV PYTHONPATH="/app:${PYTHONPATH}"
ENV PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright

# Default command
CMD ["python3", "-m", "pipeline", "--help"]