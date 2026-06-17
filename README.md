# Agent 全栈开发工程师 — 能力展示项目集

> **目标岗位**：Agent 全栈开发工程师（RL基础设施 + 评测平台 + 集成框架 + 容器运维）
> **基线日期**：2026-06-16
> **项目总数**：7 个 GitHub 仓库，Docker 一键启动完整 Agent 研发生态

---

## 项目总览

| # | 项目 | 一句话定位 | 语言 | 端口 |
|---|------|-----------|------|------|
| 1 | **AgentEval-Platform** | 旗舰全栈 Agent 评测平台 | TS + Python | 8000/3000 |
| 2 | **AgentForge** | 可插拔 Agent 集成框架 + RL 训练桥接 | Python | 8001/9001 |
| 3 | **AgentViz** | 轨迹回放可视化组件库 (npm 包) | TypeScript | 6006 |
| 4 | **token-core** | 高性能 Token 引擎 (计数/截断/计费) | Rust + PyO3 + WASM | 8003 |
| 5 | **mcp-bridge** | MCP 协议实现 + 工具治理网关 | Python + Rust | 8004 |
| 6 | **agent-container-service** | Agent 服务全生命周期容器运维 | YAML + Python + Shell | — |
| 7 | **claude-code-toolkit** | AI 编程工具深度集成扩展包 | TS + Python | — |

---

## 快速开始

### 前置要求

- Docker Desktop 4.30+
- Docker Compose v3.9+
- Rust 1.82+ (仅 token-core/mcp-bridge 本地开发)
- Node.js 22+ (前端项目)
- Python 3.12+ (后端项目)

### 一键启动全部服务（硬性验收标准）

> **⚠️ 硬性要求**：`docker compose up` 必须一次成功，不允许"在我本地能跑"的情况。

```bash
# 1. 克隆主仓库
git clone https://github.com/yourname/agent-fullstack.git
cd agent-fullstack

# 2. 初始化 secrets
cp secrets/.env.example secrets/.env
# 编辑 secrets/.env，填入你的 API Keys

# 3. 开发环境一键启动（7GB Docker Desktop 适配版）
docker compose -f agent-container-service/docker-compose.dev.yml up -d

# 4. 验证所有服务健康状态
docker compose ps
curl http://localhost:8000/health     # AgentEval API
curl http://localhost:8001/health     # AgentForge
curl http://localhost:8003/health     # token-core
curl http://localhost:8004/health     # mcp-bridge
curl http://localhost:3000            # AgentEval Frontend
curl http://localhost:3000            # AgentEval Frontend (React)

# 5. 开始评测
# 打开浏览器 http://localhost:3000
# 点击"创建评测" → 填写表单 → 提交
# Worker 自动处理 → 查看结果和统计

# 6. 一键执行全部测试
./run_tests.sh
# 或浏览器端到端测试:
cd e2e_tests && node playwright_e2e.js
# 预期输出:
# ===========================
# TOTAL: PASS  XXX  FAIL  0  SKIP  0
# ===========================
```

### 验收检查清单

| 检查项 | 命令 | 预期 |
|--------|------|------|
| 一键启动 | `docker compose up -d` | 无报错，所有容器 healthy |
| 健康检查 | `curl :8000/health` 等 | 全部返回 200 |
| 测试执行 | `./run_tests.sh` | PASS X, FAIL 0, TOTAL X |
| 错误格式 | `curl -X POST :8000/api/... -d '{}'` | `{"code": 422, "msg": "..."}` |
| 无白屏 | 浏览器打开 `:3000` | 页面正常渲染 |

### 单独启动某个项目

```bash
# 每个项目都有独立的 docker-compose.yml
cd AgentEval-Platform && docker compose up -d
cd AgentForge && docker compose up -d
cd token-core && docker compose up -d
# ...
```

---

## 系统架构

```
                          ┌──────────────────────┐
                          │   Traefik API Gateway │
                          │  (TLS/RateLimit/WAF) │
                          └──────┬───────┬───────┘
                                 │       │
         ┌───────────────────────┼───────┼───────────────────────┐
         │                       │       │                       │
         ▼                       ▼       ▼                       ▼
┌─────────────────┐   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ AgentEval       │   │  AgentForge  │  │  mcp-bridge  │  │  token-core  │
│ Platform        │──▶│  (Agent框架)  │◀─│  (MCP协议)   │  │  (Token引擎) │
│ FastAPI + React │   │  Python+gRPC │  │  Python+Rust │  │  Rust+PyO3   │
└────────┬────────┘   └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
         │                   │                  │                  │
         └───────────────────┼──────────────────┼──────────────────┘
                             │                  │
                    ┌────────▼────────┐  ┌──────▼───────┐
                    │    PostgreSQL   │  │    Redis     │
                    │    (持久化)      │  │  (缓存/队列)  │
                    └─────────────────┘  └──────────────┘
```

**数据流**：用户创建评测 → AgentEval 调动 AgentForge 执行 Agent → token-core 实时计量 Token → mcp-bridge 代理工具调用 → 轨迹返回到 AgentViz 可视化 → 评测报告生成

---

## 岗位要求覆盖矩阵

| 岗位要求 | 对应项目 | 体现方式 |
|---------|---------|---------|
| **前端 JS/TS 复杂页面** | AgentEval-Platform + AgentViz | React 18 + TS 全栈前端 + 独立组件库 |
| **Python + Rust 双语言** | token-core + AgentForge + mcp-bridge | Rust 核心引擎 + Python 服务层 + PyO3 绑定 |
| **Docker/K8s 运维** | agent-container-service | 完整 Docker Compose + K8s Helm + 监控面板 |
| **AI 编程工具二次开发** | claude-code-toolkit | Slash Commands + MCP Server + VS Code 插件 |
| **Git/CI/CD 工程实践** | 全部 7 个项目 | GitHub Actions + 自动化测试 + 代码审查 |
| **Agent 评测平台** | AgentEval-Platform | 从零搭建，含轨迹回放 + 对比分析 + 报告 |
| **LLM 底层认知** | token-core | Context Window / Token 计费 / 截断 / 缓存 |
| **MCP/工具调用协议** | mcp-bridge | MCP ↔ OpenAI FC ↔ Anthropic Tool Use 互转 |
| **Prompt 工程** | claude-code-toolkit | 结构化 Prompt 模板库 + 最佳实践文档 |

---

## 开发路线图

```
Phase 1: 底层能力 (2-3周)
  token-core ──► mcp-bridge
  (Rust引擎)     (协议标准)

Phase 2: 核心框架 (3-4周)
  AgentForge ◄── token-core + mcp-bridge
  AgentViz   (并行开发)

Phase 3: 平台集成 (3-4周)
  AgentEval-Platform ◄── 集成 Phase1+2 全部能力

Phase 4: 运维+工具 (2-3周)
  agent-container-service + claude-code-toolkit
```

---

## 技术亮点

- **全链路 Async I/O**：FastAPI + SQLAlchemy asyncpg + Redis async + Celery
- **Rust 热路径**：Token 批量计数 <1ms/1000条消息（Python 实现需 ~50ms）
- **智能模型路由**：根据任务复杂度 + 成本预算自动选择最优模型（DeepSeek V4 Flash $0.14 vs Fable 5 $50）
- **分层 Context Window 截断**：System必保 → 工具结果优先 → 语义相关保留
- **2026 年模型全量定价**：20+ 模型实时价格 + 缓存折扣 + 长上下文溢价 + 思考模式计量
- **纵深安全防御**：Traefik WAF + JWT + RBAC + Rate Limit + Pydantic + SQLAlchemy + CSP + 非root容器

---

## 资源估算

### 生产环境（K8s 高可用多副本）

| 项目 | Docker 内存 | CPU | 备注 |
|------|-----------|-----|------|
| AgentEval API (×3) | 3GB | 3核 | 生产3副本 |
| AgentEval Worker (×5) | 20GB | 10核 | 评测任务执行 |
| AgentEval Frontend (×2) | 1GB | 1核 | SSR |
| AgentForge (×3) | 6GB | 6核 | Agent执行引擎 |
| token-core (×2) | 2GB | 8核 | CPU密集型 |
| mcp-bridge (×2) | 2GB | 2核 | 协议转换 |
| 基础设施 (PG+Redis+RabbitMQ+MinIO) | 6GB | 4核 | 共享服务 |
| 监控 (Prometheus+Grafana+Loki) | 3GB | 2核 | 可观测性 |
| Traefik 网关 | 512MB | 1核 | API 网关 |
| **合计** | **~43GB** | **~36核** | 生产集群 (云服务器 / 裸金属) |

### 本地开发环境（个人电脑 Docker Desktop 7GB）

> **关键策略**：副本全砍为 1、监控移除、基础设施瘦身、MinIO 换本地文件系统、Worker 串行执行。

| 项目 | Docker 内存 | CPU | 与生产差异 |
|------|-----------|-----|-----------|
| AgentEval API (×1) | 256MB | 0.5核 | 3副本→1, uvicorn 单 worker |
| AgentEval Worker (×1) | 512MB | 1核 | 5副本→1, 并发1, 串行执行 |
| AgentEval Frontend (×1) | 128MB | 0.3核 | dev server, 无 SSR |
| AgentForge (×1) | 256MB | 0.5核 | 3副本→1 |
| token-core (×1) | 128MB | 1核 | 2副本→1, Rust 本身极轻 |
| mcp-bridge (×1) | 128MB | 0.3核 | 2副本→1 |
| PostgreSQL 16 (×1) | 256MB | 0.3核 | 轻量配置, shared_buffers=64MB |
| Redis 7 (×1) | 64MB | 0.2核 | maxmemory 64MB |
| RabbitMQ (×1) | 128MB | 0.2核 | 单节点 |
| AgentViz Storybook | 128MB | 0.2核 | 组件文档, 可选关闭 |
| Traefik 网关 | 64MB | 0.1核 | 轻量路由 |
| Docker Desktop 自身开销 | ~1.5GB | — | Windows 宿主机固定消耗 |
| **实际可用** | **~3.7GB** | **~4.6核** | **7GB 总内存, 使用率约 53%** |

### 更精简方案（如内存不足 7GB）

| 进一步优化 | 省内存 | 代价 |
|-----------|--------|------|
| Celery Broker 改用 Redis（去 RabbitMQ） | 128MB | 无, Redis 做 broker 完全够用 |
| 不用时关 Worker | 512MB | 不跑评测时无影响 |
| 不用时关 Storybook | 128MB | 不看组件文档时无影响 |
| SQLite 替代 PostgreSQL | 200MB | 无并发/JSON字段受限, 仅极限情况 |
| **极限精简** | **~2.0GB** | 功能完整, 仅并发能力降低 |

### Docker Desktop 内存分配建议

```
Docker Desktop Settings → Resources:
  Memory: 7GB (全部分配给 Docker)
  CPU: 4 核 (宿主机留 2-4 核给 Windows)
  Swap: 2GB
  Disk: 64GB
```

> **结论**：本地 7GB Docker 完全够用。开发模式 ~3.7GB + Docker 自身 ~1.5GB = ~5.2GB，还剩 ~1.8GB 余量。如果关掉不用的 Worker 和 Storybook → ~2.6GB，非常轻松。

---

## License

MIT — 所有 7 个项目开源，可自由使用、修改、分发。
