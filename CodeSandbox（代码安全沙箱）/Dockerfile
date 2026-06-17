FROM python:3.12-slim-bookworm

LABEL org.opencontainers.image.title="CodeSandbox"
LABEL org.opencontainers.image.description="Multi-language secure code execution sandbox"
LABEL org.opencontainers.image.version="0.1.0"

# Install Docker CLI (for Docker-out-of-Docker if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install runtime dependencies
COPY api/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy application code
WORKDIR /app
COPY . /app/

# Create non-root user
RUN useradd --create-home --shell /bin/bash sandbox && \
    chown -R sandbox:sandbox /app
USER sandbox

EXPOSE 8005

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -sf http://localhost:8005/health || exit 1

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8005", "--workers", "1"]
