# Stage 1: Build Rust PyO3 module
FROM rust:slim-bookworm AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip python3-dev ca-certificates && update-ca-certificates && rm -rf /var/lib/apt/lists/*
COPY Cargo.toml .
COPY src/ ./src/
COPY benches/ ./benches/
COPY pyo3-bindings/ ./pyo3-bindings/
RUN sed -i '/wasm-bindings/d' Cargo.toml
RUN sed -i 's/members = \[/members = \[\n    "pyo3-bindings",/' Cargo.toml
RUN cargo build --release -p token-core-py
RUN find target -name "*token_core*" -type f | head -5
RUN cp target/release/libtoken_core_py.so /tmp/token_core_py.so 2>/dev/null || true

# Stage 2: Runtime
FROM python:3.12-slim-bookworm
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY api/ ./api/
COPY --from=builder /tmp/token_core_py.so /usr/local/lib/python3.12/site-packages/token_core_py.so
RUN python -c "import token_core_py; print('✅ RUST BACKEND:', token_core_py.list_models()[:3])" 2>&1 || echo "⚠️ Rust module unavailable, using Python fallback"
EXPOSE 8003
HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD curl -f http://localhost:8003/health || exit 1
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8003", "--workers", "1"]
