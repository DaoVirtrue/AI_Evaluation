FROM python:3.12-slim-bookworm
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml /app/
COPY server/ /app/server/
COPY bridge/ /app/bridge/
COPY governance/ /app/governance/
COPY client/ /app/client/
COPY proxy/ /app/proxy/
COPY cli/ /app/cli/
RUN pip install --no-cache-dir fastapi uvicorn[standard] pydantic pyyaml jsonschema
EXPOSE 8004
HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD curl -f http://localhost:8004/health || exit 1
CMD ["uvicorn", "server.handler:app", "--host", "0.0.0.0", "--port", "8004", "--workers", "1"]
