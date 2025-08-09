# Minimal MCPBench Docker image with multi-stage build
FROM python:3.11-slim as builder

# Install only build essentials for compiling Python packages
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

# Final minimal stage
FROM python:3.11-slim

# Install only absolutely essential runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # PostgreSQL runtime library (required for psycopg2)
    libpq5 \
    # Git (required for version control tasks)
    git \
    # Curl (required for downloading)
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js from NodeSource (smaller than Debian's nodejs package)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

WORKDIR /app

# Copy application code
COPY . .

# Create results directory
RUN mkdir -p /app/results

# Set environment
ENV PATH="/root/.local/bin:${PATH}"
ENV PYTHONPATH="/app:${PYTHONPATH}"

# Default command
CMD ["python3", "-m", "pipeline", "--help"]