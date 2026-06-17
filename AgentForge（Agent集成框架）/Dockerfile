FROM python:3.12-slim-bookworm
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml .
COPY agentforge/ ./agentforge/
RUN pip install --no-cache-dir fastapi uvicorn[standard] pydantic structlog sqlalchemy[asyncio] asyncpg redis psycopg2-binary
EXPOSE 8001
HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD curl -f http://localhost:8001/health || exit 1
CMD ["uvicorn", "agentforge.api.http_app:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]
