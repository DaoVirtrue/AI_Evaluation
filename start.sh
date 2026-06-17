#!/bin/bash
set -euo pipefail

echo "============================================"
echo "  Agent 全栈平台 — 一键启动"
echo "  预计内存占用: ~1.2GB (Docker Desktop 7GB)"
echo "============================================"
echo ""

# Check Docker
if ! docker info > /dev/null 2>&1; then
    echo "[ERROR] Docker 未运行。请先启动 Docker Desktop。"
    exit 1
fi

# Build and start
echo "[1/3] 构建镜像..."
docker compose build --parallel 2>&1 | tail -5

echo ""
echo "[2/3] 启动服务..."
docker compose up -d

echo ""
echo "[3/3] 等待服务就绪..."
SERVICES=("localhost:8000/health" "localhost:8001/health" "localhost:8003/health" "localhost:8004/health")
for url in "${SERVICES[@]}"; do
    for i in {1..30}; do
        if curl -sf "$url" > /dev/null 2>&1; then
            echo "  [OK] $url"
            break
        fi
        sleep 1
    done
done

echo ""
echo "============================================"
echo "  全部服务已启动！"
echo "============================================"
echo ""
echo "  服务列表:"
echo "    AgentEval Platform : http://localhost:8000/health"
echo "    AgentForge         : http://localhost:8001/health"
echo "    token-core         : http://localhost:8003/health"
echo "    mcp-bridge         : http://localhost:8004/health"
echo ""
echo "  快速测试:"
echo "    curl http://localhost:8003/api/v1/models"
echo "    curl -X POST http://localhost:8004/mcp -H 'Content-Type: application/json' -d '{\"jsonrpc\":\"2.0\",\"method\":\"tools/list\",\"id\":1}'"
echo "    curl -X POST http://localhost:8001/api/v1/agents/run -H 'Content-Type: application/json' -d '{\"messages\":[{\"role\":\"user\",\"content\":\"Hello\"}],\"framework\":\"native\"}'"
echo ""
echo "  停止: docker compose down"
echo "  日志: docker compose logs -f"
echo "============================================"
