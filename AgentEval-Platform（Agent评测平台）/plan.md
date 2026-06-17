# AgentEval-Platform — 旗舰全栈 Agent 评测平台

---

| 属性 | 值 |
|------|-----|
| 项目类型 | 全栈：fullstack |
| 前端语言 | TypeScript |
| 后端语言 | Python |
| 前端框架 | React 18, Vite, TailwindCSS, D3.js, ECharts |
| 后端框架 | FastAPI, SQLAlchemy 2.0 |
| 数据库 | SQLite（开发）/ PostgreSQL 16（生产） |

---

## 1. 项目概述

### 定位
从零搭建的 Agent 评测平台。算法工程师在此完成：创建评测任务 → 实时监控进度 → 回放 Agent 轨迹 → 对比版本差异 → 导出评测报告。

### 依赖项目
| 依赖项目 | 用途 | 调用方式 |
|---------|------|---------|
| AgentForge | 执行 Agent 评测 | HTTP API (`POST /run`) |
| token-core | Token 计数 + 成本计算 | HTTP API (`POST /count`, `POST /cost`) |
| AgentViz | 轨迹可视化渲染 | npm 包 (`@agent-viz/react`) |
| agent-container-service | 容器化部署编排 | Docker Compose / K8s Helm |

---

## 2. 系统架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                         AgentEval-Platform                          │
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │   Frontend    │    │   Backend     │    │      Worker          │  │
│  │  React 18+TS  │◀──▶│  FastAPI      │    │  Celery × N          │  │
│  │  :3000        │ WS │  :8000        │    │  (评测任务执行)       │  │
│  │               │    │               │    │                      │  │
│  │ ┌───────────┐ │    │ ┌───────────┐ │    │ ┌─────────────────┐  │  │
│  │ │Zustand    │ │    │ │API Router │ │    │ │evaluation_task │  │  │
│  │ │React Query│ │    │ │/api/v1/*  │ │    │ │ ├─ load_dataset │  │  │
│  │ │AgentViz   │ │    │ └─────┬─────┘ │    │ │ ├─ call_forge   │  │  │
│  │ └───────────┘ │    │       │       │    │ │ ├─ collect_traj │  │  │
│  └──────────────┘    │ ┌─────▼─────┐ │    │ │ └─ calc_metrics │  │  │
│                      │ │Repository │ │    │ └─────────────────┘  │  │
│                      │ │(SQLAlchemy│ │    └──────────┬───────────┘  │
│                      │ │ async)    │ │               │              │
│                      │ └─────┬─────┘ │               │              │
│                      └───────┼───────┘               │              │
│                              │                       │              │
└──────────────────────────────┼───────────────────────┼──────────────┘
                               │                       │
                    ┌──────────▼──────────┐  ┌─────────▼──────────┐
                    │   PostgreSQL 16     │  │  Redis 7           │
                    │   (持久化存储)       │  │  (缓存 / Pub/Sub)   │
                    └─────────────────────┘  └────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   MinIO             │
                    │   (测试集文件存储)    │
                    └─────────────────────┘
```

---

## 3. 核心业务流程

### 3.1 评测任务执行流程（时序图）

```
用户        Frontend      API         Worker      AgentForge    token-core   PostgreSQL
 │              │           │            │             │             │            │
 │  点击"开始评测"│           │            │             │             │            │
 │─────────────▶│           │            │             │             │            │
 │              │ POST /eval│            │             │             │            │
 │              │──────────▶│            │             │             │            │
 │              │           │ INSERT eval│             │             │            │
 │              │           │───────────────────────────────────────────────────▶│
 │              │           │            │             │             │            │
 │              │           │ enqueue task│            │             │            │
 │              │           │───────────▶│             │             │            │
 │              │  WebSocket: progress   │             │             │            │
 │              │◀──────────────────────▶│             │             │            │
 │              │           │            │  loop cases │             │            │
 │              │           │            │────────────▶│             │            │
 │              │           │            │             │ POST /run   │            │
 │              │           │            │             │────────────▶│            │
 │              │           │            │             │             │ POST /count│
 │              │           │            │             │             │───────────▶│
 │              │           │            │             │◀────────────│            │
 │              │           │            │             │  Agent执行   │            │
 │              │           │            │             │  (含ToolCall) │           │
 │              │           │            │◀────────────│             │            │
 │              │           │            │───save────▶│             │            │
 │              │           │            │  trajectory │             │            │
 │              │           │  pub progress             │             │            │
 │              │           │───────────▶│ Redis Pub/Sub              │            │
 │              │◀──WS推送──│            │             │             │            │
 │              │           │            │ (所有case完成)             │             │
 │              │           │            │───UPDATE──▶│             │            │
 │              │           │            │   status=done             │            │
 │              │◀──刷新页面│            │             │             │            │
```

### 3.2 数据流

```
[测试集文件] → MinIO → Worker加载
[Agent执行]  → AgentForge API → 返回轨迹 + Token用量
[Token计量]  → token-core API → 实时成本计算
[进度推送]   → Redis Pub/Sub → WebSocket → Frontend
[轨迹渲染]   → AgentViz 组件库 ← API 拉取轨迹JSON
[报告生成]   → Worker异步 → Markdown/PDF → MinIO存储
```

---

## 4. 技术栈选型

| 层 | 选型 | 理由 |
|----|------|------|
| 前端框架 | React 18 + TypeScript + Vite | 主流、生态丰富、HMR 快 |
| 状态管理 | Zustand + React Query | 轻量、支持缓存/重试/乐观更新 |
| 可视化 | D3.js + ECharts + Canvas API | 定制渲染 + 开箱即用图表 |
| UI 组件 | TailwindCSS + Radix UI | 快速开发 + 无障碍 |
| 代码编辑 | Monaco Editor | JSON/YAML/Python 语法高亮 |
| 后端框架 | Python 3.12 + FastAPI | 异步、自动 OpenAPI 文档 |
| ORM | SQLAlchemy 2.0 (async) | 类型安全、参数化查询 |
| 任务队列 | Celery + RabbitMQ | 异步评测、可靠投递 |
| 实时通信 | WebSocket + Redis Pub/Sub | 低延迟进度推送 |
| 数据库 | PostgreSQL 16 + Redis 7 | 持久化 + 高速缓存 |
| 对象存储 | MinIO (S3 兼容) | 测试集文件、报告存储 |

---

## 5. 功能模块设计

| 模块 | 功能 | 优先级 |
|------|------|--------|
| 评测任务管理 | CRUD + 批量 + 状态机(queued→running→done/failed) | P0 |
| 实时监控 | WebSocket 进度推送 + 实时指标 + 中止/暂停 | P0 |
| 轨迹回放 | 逐步播放 + 每步详情(Token/Tool/Latency) + 速度控制 | P0 |
| 对比分析 | A/B 并排对比 + 差异高亮 + 决策分叉点标记 | P1 |
| Token 分析 | 按维度聚合 + 成本计算(集成token-core) + 异常检测 | P1 |
| 评测报告 | Markdown/PDF 导出 + 可分享链接 | P1 |
| 系统管理 | JWT+RBAC + API Key + 系统配置 | P2 |

---

## 6. 数据模型设计

```
┌──────────┐     ┌──────────────┐     ┌───────────────────┐
│ projects  │────▶│ evaluations  │────▶│ evaluation_results │
│ id        │     │ id           │     │ id                 │
│ name      │     │ project_id FK│     │ evaluation_id FK   │
│ owner_id  │     │ agent_config │     │ case_id            │
│ settings  │     │ dataset_id FK│     │ passed / score     │
└──────────┘     │ status       │     │ trajectory (JSONB) │
                 │ metrics      │     │ token_usage (JSONB)│
                 └──────┬───────┘     └─────────┬──────────┘
                        │                       │
                 ┌──────▼───────┐     ┌─────────▼──────────┐
                 │  datasets    │     │ trajectory_steps    │
                 │ id           │     │ id (BIGSERIAL)      │
                 │ project_id FK│     │ result_id FK        │
                 │ format       │     │ step_index / type   │
                 │ case_count   │     │ model / tool_name   │
                 │ file_path    │     │ input / output JSONB│
                 └──────────────┘     │ token_usage / latency│
                                      └─────────────────────┘
```

核心 SQL 建表语句参考 plan.md v1（保持不变）。

---

## 7. API 设计

```
评测任务
  POST   /api/v1/projects/{pid}/evaluations     创建评测
  GET    /api/v1/evaluations/{eid}              获取详情
  GET    /api/v1/evaluations/{eid}/status        获取进度（轻量）
  DELETE /api/v1/evaluations/{eid}               取消/删除
  WS     /api/v1/evaluations/{eid}/stream         WebSocket 进度推送

结果查询
  GET    /api/v1/evaluations/{eid}/results        结果列表（分页）
  GET    /api/v1/evaluations/{eid}/results/{rid}/trajectory  轨迹数据
  GET    /api/v1/evaluations/{eid}/metrics        聚合指标

对比分析
  POST   /api/v1/compare                          创建对比
  GET    /api/v1/compare/{cid}                    对比结果

报告
  POST   /api/v1/evaluations/{eid}/report         生成报告
  GET    /api/v1/reports/{rid}/download           下载报告

数据集
  POST   /api/v1/projects/{pid}/datasets          上传测试集
  GET    /api/v1/datasets/{did}                   查看测试集
```

---

## 8. 非功能性设计

### 8.1 高并发

| 机制 | 实现 |
|------|------|
| Async I/O | FastAPI async/await + uvicorn workers = CPU核数×2 |
| 数据库连接池 | SQLAlchemy pool_size=20, max_overflow=40, pool_pre_ping=True |
| Redis 连接池 | max_connections=50, socket_keepalive, retry_on_timeout |
| 任务队列 | RabbitMQ + Celery, worker_concurrency=4, prefetch=1, task_acks_late |
| WebSocket | Redis Pub/Sub 广播进度，避免客户端轮询 |
| 缓存策略 | L1(应用内存) → L2(Redis TTL=5min) → L3(PostgreSQL)；分页游标 |

### 8.2 高可用

| 机制 | 实现 |
|------|------|
| 无状态服务 | API 无本地状态，水平扩展多副本 |
| 数据库 | PostgreSQL 主从复制 + 读写分离 |
| 缓存 | Redis Sentinel 自动故障转移 |
| 熔断器 | AgentForge 调用失败率 >50% → 熔断 30s → 半开探测 |
| 优雅关闭 | SIGTERM → 停止接受新请求 → 完成进行中任务 → 退出 |
| 健康检查 | /health (liveness) + /ready (readiness) |

### 8.3 可扩展

| 机制 | 实现 |
|------|------|
| 水平扩展 | API/Worker 无状态，增加副本即可提升吞吐 |
| 数据库分片 | 按 project_id 分片（未来 100+ 项目时启用） |
| 插件化评测器 | 新增评测类型只需实现 Evaluator 接口 |
| CDN | 前端静态资源 CDN 分发，减轻源站压力 |

### 8.4 低延迟

| 机制 | 实现 | 目标 |
|------|------|------|
| WebSocket 推送 | 替代 HTTP 轮询，Redis Pub/Sub 广播 | 进度推送 <500ms |
| 游标分页 | 替代 OFFSET，结果列表查询 | <100ms |
| 轨迹数据压缩 | JSONB 存储 + 选择性字段返回 | 传输体积 -60% |
| AgentViz 虚拟滚动 | Canvas 渲染 + react-window | 10w+ 步骤 60fps |
| 热数据缓存 | 评测结果 Redis 缓存 | 命中时 <10ms |

### 8.5 安全

| 层级 | 措施 | 实现 |
|------|------|------|
| 传输 | TLS 1.3 | Traefik 终结 |
| 认证 | JWT access(15min) + refresh(7d) | HTTP-only cookie |
| 授权 | RBAC (Admin/Evaluator/Viewer) | 装饰器 `@require_role` |
| 限流 | 100req/min per user | slowapi + Redis |
| 输入验证 | Pydantic v2 strict, `extra='forbid'` | 所有 API 入参 |
| SQL注入 | 100% ORM 参数化 | 禁用 raw SQL |
| XSS | CSP header + React 转义 + DOMPurify | 三重防护 |
| CSRF | Double Submit Cookie | fastapi-csrf |
| 文件安全 | 类型白名单 + 预签名URL + ClamAV | MinIO |

---

## 9. 项目间依赖

| 依赖项目 | 接口 | 用途 | 失败降级 |
|---------|------|------|---------|
| **AgentForge** | `POST :8001/api/v1/run` | 执行 Agent | 熔断 + 重试3次 + 标记失败 |
| **token-core** | `POST :8003/api/v1/count` | Token 计数 | 使用本地估算兜底 |
| **token-core** | `POST :8003/api/v1/cost` | 成本计算 | 使用上次价格表兜底 |
| **AgentViz** | npm `@agent-viz/react` | 轨迹可视化渲染 | 降级为纯文本展示 |
| **agent-container-service** | docker-compose | 容器编排 | — |

---

## 10. 部署架构

### 开发环境（Docker Desktop 7GB 适配）

```yaml
services:
  agent-eval-api:
    deploy: {replicas: 1}
    resources: {limits: {memory: 256M, cpus: '0.5'}}
    command: uvicorn app.main:app --workers 1

  agent-eval-worker:
    deploy: {replicas: 1}
    resources: {limits: {memory: 512M, cpus: '1.0'}}
    command: celery -A tasks worker --concurrency=1
    profiles: [full]   # 不跑评测时可关

  agent-eval-frontend:
    deploy: {replicas: 1}
    resources: {limits: {memory: 128M, cpus: '0.3'}}
    command: npm run dev
```

### 生产环境（K8s 高可用）

```yaml
agent-eval-api:
  replicas: 3
  resources: {requests: {memory: 1Gi, cpu: 1}, limits: {memory: 2Gi, cpu: 2}}
  hpa: {min: 3, max: 20, cpu: 70%}
  strategy: RollingUpdate (maxSurge:1, maxUnavailable:0)
```

---

## 11. 目录结构

```
AgentEval-Platform/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # API 路由
│   │   ├── models/          # SQLAlchemy ORM 模型
│   │   ├── schemas/         # Pydantic 验证模型
│   │   ├── services/        # 业务逻辑层
│   │   ├── core/            # 配置 / 安全(JWT) / 依赖注入
│   │   └── main.py          # FastAPI 入口
│   ├── alembic/             # 数据库迁移
│   ├── unit_tests/          # 单元测试（pytest）
│   ├── API_tests/           # API 接口测试（httpx）
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── features/
│   │   ├── hooks/
│   │   ├── stores/
│   │   └── lib/
│   ├── unit_tests/          # 前端单元测试（Vitest）
│   ├── Dockerfile
│   └── package.json
├── worker/
│   ├── tasks/               # Celery 任务定义
│   ├── Dockerfile
│   └── pyproject.toml
├── run_tests.sh             # 一键执行全部测试
├── docker-compose.yml       # 开发环境（docker compose up 验收）
└── metadata.json
```

---

## 12. 验证标准

**功能验证：**
- [ ] 创建评测 → Worker 领取 → 调用 AgentForge → 结果入库 → WebSocket 推送 <500ms
- [ ] 轨迹回放：10w+ 步骤流畅播放（Canvas 模式 60fps）
- [ ] A/B 对比：两个版本并排显示，差异步骤高亮
- [ ] 报告导出：Markdown/PDF 包含完整指标图表

**硬性要求验证：**
- [ ] `docker compose up` 一键启动成功，无报错、无端口冲突
- [ ] `./run_tests.sh` 一键执行，输出 "PASS: X, FAIL: 0, TOTAL: X"
- [ ] 接口正常参数返回 200 + 正确数据
- [ ] 接口缺失参数返回 400 + `{"code": 400, "msg": "..."}`
- [ ] 接口格式错误返回 422 + `{"code": 422, "msg": "..."}`
- [ ] 接口权限不足返回 403 + `{"code": 403, "msg": "Forbidden"}`
- [ ] 数据变更接口：调用前后数据库状态正确
- [ ] 前端接口失败：Toast 提示，不白屏、不崩溃
- [ ] SQL注入 / XSS / CSRF / 未认证访问 → 全部拦截
- [ ] 日志输出：关键操作有结构化日志，无 `print("here")` 类无意义日志
- [ ] 界面：TailwindCSS 风格统一，按钮有 Loading/Disabled 态，无死链

---

## 13. 硬性要求合规方案

### 13.1 一键启动保障
- Dockerfile 多阶段构建，`pip install -r requirements.txt` 在镜像内完成
- docker-compose.yml 包含 `depends_on` + `healthcheck` + 环境变量注入
- 所有端口通过 `.env` 配置，无硬编码；`127.0.0.1` 绑定仅限开发
- README 启动命令 `docker compose up -d` 经实际验证，验证者无需改源码

### 13.2 测试体系设计
- `backend/unit_tests/` — pytest 单元测试（模型、服务层、工具函数）
- `backend/API_tests/` — httpx + pytest-asyncio（所有 API 端点）
- `frontend/unit_tests/` — Vitest + Testing Library（组件渲染、Hook 行为）
- `run_tests.sh` 一键执行，输出格式：
  ```
  ===========================
  Test Results Summary
  ===========================
  Backend Unit:   PASS  12  FAIL  0
  Backend API:    PASS  25  FAIL  0
  Frontend Unit:  PASS  18  FAIL  0
  ===========================
  TOTAL: PASS  55  FAIL  0  SKIP  0
  ===========================
  ```
- 覆盖：正常参数(200) / 缺失参数(400) / 格式错误(422) / 权限不足(403) / 数据变更验证

### 13.3 错误处理规范
- **后端**：FastAPI exception_handler 统一拦截 → `{"code": XXX, "msg": "...", "detail": null}`
- **前端**：axios interceptor → `response.error` → Toast 通知；网络断开 → 缺省页
- 严禁直接抛出 Stack Trace 或导致 500 无响应

### 13.4 日志规范
- Python: `structlog` 结构化 JSON，含 `timestamp`, `level`, `logger`, `event`, `trace_id`
- 关键节点必记：请求进入(INFO) / DB 操作(DEBUG) / 外部 API 调用(INFO) / 异常(ERROR)
- 禁止 `print("here")` / `console.log("111")` 类无意义日志

### 13.5 参数校验
- 后端：Pydantic v2 `model_config = {'extra': 'forbid'}`，所有入参有 schema
- 前端：React Hook Form + Zod 客户端校验 + 服务端错误映射双重保障

### 13.6 安全基线
- SQL：100% SQLAlchemy ORM 参数化，`echo=DEBUG` 仅开发环境
- 密码：bcrypt + salt rounds=12；JWT secret 来自环境变量
- API Key：`os.environ.get("MODEL_API_KEY")`，不硬编码在源码中
- 前端：Token 存 httpOnly cookie，不在 localStorage 暴露

### 13.7 美观度（全栈项目）
- UI 框架：TailwindCSS + Radix UI + Lucide Icons
- 按钮状态：`variant` (primary/secondary/ghost) + `size` + `loading` + `disabled`
- 空状态：`<EmptyState icon={...} title="暂无数据" action="创建评测" />` 组件
- 错误边界：`<ErrorBoundary fallback={...}>` 包裹路由页面
- 路由：React Router，无 404 死链
