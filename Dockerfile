# =============================================================================
# Production Dockerfile for Hermes Agent & AWS Bedrock AgentCore Runtime
# =============================================================================
FROM python:3.12-slim as builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir .

# =============================================================================
# Final Minimal Runtime Stage
# =============================================================================
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Create unprivileged application user for least privilege security
RUN groupadd -r hermes && useradd -r -g hermes hermes

# Copy installed site-packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY . .

# Adjust file ownership
RUN chown -R hermes:hermes /app

USER hermes

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/ping').read()"

CMD ["python", "-m", "agentcore.app"]
