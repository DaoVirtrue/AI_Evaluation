# AgentForge — 可插拔 Agent 集成框架

---

| 属性 | 值 |
|------|-----|
| 项目类型 | 纯后端：server |
| 前端语言 | 无 |
| 后端语言 | Python |
| 前端框架 | 无 |
| 后端框架 | FastAPI（当前） / gRPC（计划） / Celery（计划） |
| 数据库 | 无（当前 Demo，内存存储）/ PostgreSQL 16 + Redis 7（生产） |

---

## 1. 项目概述

### 定位
屏蔽 LangChain、OpenAI Agents SDK、自研框架的差异，提供统一的 Agent 抽象层。核心创新：中间件管道（洋葱模型）+ 智能模型路由 + RL 训练桥接。

### 被依赖关系
| 调用方 | 用途 | 接口 |
|--------|------|------|
| AgentEval-Platform | 执行评测 Agent | gRPC `RunAgent` |
| claude-code-toolkit | IDE 内执行 Agent | HTTP `POST /api/v1/run` |
| RL 训练框架 | 批量导出训练轨迹 | HTTP `POST /api/v1/export` |

### 依赖项目
| 依赖项目 | 用途 | 调用方式 |
|---------|------|---------|
| token-core | Token 计数 + 成本计算 + Context Window 截断 | PyO3 直接调用 |
| mcp-bridge | MCP 工具调用 + 工具治理 | HTTP API |

---

## 2. 系统架构图

```
                              ┌──────────────────────────────┐
                              │     AgentForge API Layer      │
                              │  ┌──────────┐ ┌───────────┐  │
                              │  │  FastAPI  │ │   gRPC    │  │
                              │  │ :8001     │ │  :9001    │  │
                              │  └─────┬─────┘ └─────┬─────┘  │
                              └────────┼─────────────┼────────┘
                                       │             │
                              ┌────────▼─────────────▼────────┐
                              │     Agent Orchestrator        │
                              │  • Agent 生命周期              │
                              │  • 多 Agent 拓扑编排           │
                              │  • 超时/取消/重试控制          │
                              │  • 并发 asyncio.Task 隔离      │
                              └──────────────┬───────────────┘
                                             │
              ┌──────────────────┬───────────┼───────────┬──────────────────┐
              │                  │           │           │                  │
     ┌────────▼──────┐  ┌───────▼──────┐ ┌──▼─────┐ ┌───▼───────┐  ┌──────▼──────┐
     │ LangChain     │  │ OpenAI Agents│ │ Native │ │ 其他      │  │ 自定义适配器 │
     │ Adapter       │  │ Adapter      │ │Adapter │ │ Adapter   │  │ (实现Base)  │
     └────────┬──────┘  └───────┬──────┘ └──┬─────┘ └───┬───────┘  └──────┬──────┘
              │                  │           │           │                  │
              └──────────────────┴───────────┼───────────┴──────────────────┘
                                             │
                              ┌──────────────▼───────────────┐
                              │    Middleware Pipeline        │
                              │    (洋葱模型，1→7→7→1)        │
                              │                               │
                              │  Request ──────────────────▶  │
                              │  ┌─────────────────────────┐  │
                              │  │ 1. ContextWindowCheck   │──┼──▶ token-core (PyO3)
                              │  │ 2. ToolCallSanitizer    │  │
                              │  │ 3. SemanticCache        │  │
                              │  │ 4. RateLimiter          │  │
                              │  │ 5. ModelRouter          │──┼──▶ token-core (pricing)
                              │  │ 6. Tracer               │  │
                              │  │ 7. CostTracker          │──┼──▶ token-core (cost)
                              │  └─────────────────────────┘  │
                              │  ◀────────────────── Response │
                              └──────────────┬───────────────┘
                                             │
                     ┌───────────────────────┼───────────────────────┐
                     │                       │                       │
            ┌────────▼──────┐     ┌─────────▼──────┐     ┌─────────▼──────┐
            │ Tool Registry │     │ Model Provider  │     │  RL Bridge     │
            │ ┌───────────┐ │     │ ┌─────────────┐ │     │ ┌────────────┐ │
            │ │ MCP Tools │─┼────▶│ │ Claude API  │ │     │ │轨迹→RL格式 │ │
            │ │ (mcp-     │ │     │ │ OpenAI API  │ │     │ │jsonl/parquet│ │
            │ │  bridge)  │ │     │ │ DeepSeek API│ │     │ │奖励信号注回 │ │
            │ ├───────────┤ │     │ │ Gemini API  │ │     │ └────────────┘ │
            │ │ Function  │ │     │ │ Qwen/Llama  │ │     └────────────────┘
            │ │ Calling   │ │     │ └─────────────┘ │
            │ └───────────┘ │     └─────────────────┘
            └───────────────┘
```

---

## 3. 核心业务流程

### 3.1 Agent 执行流程（时序图）

```
调用方       Orchestrator   Pipeline     ModelRouter   Model API   token-core   mcp-bridge
  │               │             │             │             │            │            │
  │ RunAgent()    │             │             │             │            │            │
  │──────────────▶│             │             │             │            │            │
  │               │ 构建Pipeline              │             │            │            │
  │               │────────────▶│             │             │            │            │
  │               │             │ 1.WindowCheck             │            │            │
  │               │             │──────────────────────────────────────▶│            │
  │               │             │◀───── tokens, needs_truncation ──────│            │
  │               │             │ (超限→截断)  │             │            │            │
  │               │             │ 5.ModelRouter             │            │            │
  │               │             │─────────────▶│             │            │            │
  │               │             │ (选择最优模型)│             │            │            │
  │               │             │◀─────────────│             │            │            │
  │               │             │───────────────────────────▶│            │            │
  │               │             │        LLM Call             │            │            │
  │               │             │◀────── response ───────────│            │            │
  │               │             │ (如有 Tool Call)            │            │            │
  │               │             │──────────────────────────────────────────────────▶│
  │               │             │◀──────────── tool_result ─────────────────────────│
  │               │             │ (循环直到无 Tool Call)      │            │            │
  │               │             │ 7.CostTracker              │            │            │
  │               │             │──────────────────────────────────────▶│            │
  │               │             │◀───── CostBreakdown ─────────────────│            │
  │               │             │ 6.Tracer: 记录完整轨迹     │            │            │
  │               │◀────────────│             │             │            │            │
  │◀──AgentResponse─────────────│             │             │            │            │
```

### 3.2 ModelRouter 智能路由决策

```
输入: 任务复杂度 + 预算 + 延迟目标
  │
  ▼
[分类] 简单分类/摘要?  ──Yes──▶ Haiku 4.5 ($1/$5) / GPT-4.1 Nano ($0.10/$0.40)
  │ No
  ▼
[分类] 中等推理/编码?  ──Yes──▶ DeepSeek V4 Flash ($0.14/$0.28) / Sonnet 4.6 ($3/$15)
  │ No
  ▼
[分类] 复杂 Agent?     ──Yes──▶ Opus 4.8 ($5/$25) / DeepSeek V4 Pro ($0.435/$0.87)
  │ No
  ▼
[分类] 极限推理?       ──Yes──▶ Fable 5 ($10/$50) / GPT-5.5 ($5/$30)
  
策略: cost_optimal / latency_optimal / capability_optimal
Fallback: 主模型失败 → 自动切换备选模型 → 请求不丢失
```

---

## 4. 技术栈选型

| 层 | 选型 | 理由 |
|----|------|------|
| HTTP API | FastAPI | 异步、自动文档、生态好 |
| 内部通信 | gRPC | 低延迟、强类型、流式支持 |
| 数据验证 | Pydantic v2 | 类型安全、strict mode |
| 异步 | asyncio + anyio | 全链路异步 |
| 日志 | structlog | 结构化 JSON 日志 |
| Token 计算 | token-core (PyO3) | Rust 高性能、直接调用 |
| 工具调用 | mcp-bridge (HTTP) | MCP 协议代理 + 治理 |
| 测试 | pytest + pytest-asyncio | 异步测试支持 |

---

## 5. 功能模块设计

### 5.1 Agent 适配器（插件化）

```python
class BaseAgent(ABC):
    """所有框架适配器的统一接口"""
    @abstractmethod
    async def run(self, messages, tools, config) -> AgentResponse: ...
    @abstractmethod
    async def stream(self, messages, tools, config) -> AsyncIterator: ...
    @property
    @abstractmethod
    def framework(self) -> str: ...
```

| 适配器 | 支持的框架 | 状态 |
|--------|-----------|------|
| LangChainAdapter | LangChain 0.3+, LangGraph | P0 |
| OpenAIAgentsAdapter | OpenAI Agents SDK | P0 |
| NativeAdapter | 直接使用 Anthropic/OpenAI SDK | P0 |
| CustomAdapter | 用户自定义（实现 BaseAgent） | P1 |

### 5.2 中间件管道

| # | 中间件 | 功能 | 依赖 |
|---|--------|------|------|
| 1 | ContextWindowCheck | Token 预检 + 分层截断 + 上下文压缩 | **token-core** |
| 2 | ToolCallSanitizer | 工具调用参数校验 + 危险操作拦截 | — |
| 3 | SemanticCache | 语义相似请求缓存命中 | Embedding 模型 |
| 4 | RateLimiter | Token Bucket 多维度限流 | Redis |
| 5 | ModelRouter | 智能路由（成本/延迟/能力） | **token-core** (pricing) |
| 6 | Tracer | 完整轨迹记录（每步输入/输出） | — |
| 7 | CostTracker | 实时成本累计 + 预算预警 | **token-core** (cost) |

### 5.3 工具注册中心

```python
class ToolRegistry:
    def register(self, tool: ToolDefinition) -> None: ...
    def discover(self, source: str) -> list[ToolDefinition]: ...  # MCP / FC
    def invoke(self, name: str, params: dict, ctx: ToolContext) -> ToolResult: ...
```

### 5.4 RL Training Bridge

```
Agent 轨迹 → 标准化 Schema → 导出格式选择
  ├── JSONL (通用, 小规模)
  ├── Parquet (大规模训练, 列式压缩)
  └── Apache Arrow (流式, 实时训练)

RLTrainingSample:
  observation: Context Window 状态
  action:      Tool Call / Final Answer
  reward:      基于评测结果的奖励信号
  metadata:    {model, token_usage, cost, latency}
```

---

## 6. 数据模型设计

```
┌─────────────────────────┐     ┌─────────────────────────┐
│ agent_configs           │     │ agent_sessions          │
│ id                      │     │ id                      │
│ name                    │     │ config_id FK            │
│ framework               │     │ status (active/done/err)│
│ model                   │     │ total_tokens            │
│ middleware_pipeline JSONB│    │ total_cost              │
│ tool_registry JSONB     │     │ created_at              │
│ system_prompt           │     └───────────┬─────────────┘
└─────────────────────────┘                 │
                               ┌────────────▼─────────────┐
                               │ trajectory_steps          │
                               │ id (BIGSERIAL)            │
                               │ session_id FK             │
                               │ step_index / step_type    │
                               │ model / tool_name         │
                               │ input / output (JSONB)    │
                               │ token_usage (JSONB)       │
                               │ latency_ms                │
                               └───────────────────────────┘
```

---

## 7. API 设计

```
# 外部 HTTP API (FastAPI :8001)
POST   /api/v1/agents/run              执行 Agent (同步)
POST   /api/v1/agents/run/stream       执行 Agent (流式 SSE)
GET    /api/v1/agents/{id}/status      查询 Agent 状态
DELETE /api/v1/agents/{id}/cancel      取消执行

POST   /api/v1/tools/register          注册工具
GET    /api/v1/tools/list              列出工具

POST   /api/v1/export                  导出轨迹 (RL格式)
GET    /api/v1/health                  健康检查

# 内部 gRPC API (:9001)
service AgentForge {
  rpc RunAgent(AgentRequest) returns (AgentResponse);
  rpc RunAgentStream(AgentRequest) returns (stream AgentStreamEvent);
  rpc ExportTrajectories(ExportRequest) returns (ExportResponse);
}
```

---

## 8. 非功能性设计

### 8.1 高并发

| 机制 | 实现 |
|------|------|
| Async I/O | asyncio 全链路，asyncio.Task 隔离每个 Agent 执行 |
| 连接池 | HTTP pool_maxsize=100; gRPC channel pool max_idle=10, max_active=50 |
| 并发执行 | 每个 Agent 独立 Task，可单独取消/超时，无锁竞争 |
| 请求合并 | 相同参数并发调用自动去重（SemanticCache 层） |

### 8.2 高可用

| 机制 | 实现 |
|------|------|
| 熔断器 | 模型 API 失败率 >50% → 熔断 30s → 半开探测 |
| 重试策略 | 指数退避 (1s/2s/4s/8s)，最大 3 次 |
| Fallback | 主模型失败 → 自动切换备选模型 |
| 优雅关闭 | SIGTERM → 停止新请求 → 完成进行中 Agent → 退出 |

### 8.3 可扩展

| 机制 | 实现 |
|------|------|
| 适配器插件 | 新增框架只需实现 BaseAgent 接口，注册即用 |
| 中间件可配置 | YAML/JSON 驱动管道组合，无需改代码 |
| 工具注册 | 支持 MCP / Function Calling / 自定义协议扩展 |
| gRPC 流式 | 支持 Server Streaming（实时推送 Agent 推理过程） |

### 8.4 低延迟

| 机制 | 实现 | 目标 |
|------|------|------|
| gRPC 内部通信 | Protocol Buffers + HTTP/2 多路复用 | 比 REST 快 40% |
| token-core PyO3 | Rust 直接调用，无网络开销 | <1ms |
| 语义缓存 | Embedding 相似度 >0.95 命中 | 缓存命中时 <5ms |
| 连接复用 | HTTP Keep-Alive + gRPC 长连接 | 消除握手延迟 |

### 8.5 安全

| 层级 | 措施 |
|------|------|
| 工具沙箱 | Docker 隔离 / 进程隔离 / 网络隔离 / 只读文件系统 |
| API Key | AES-256-GCM 加密存储，运行时解密 |
| 审计 | 每次 Tool Call 完整记录（时间/用户/参数/结果） |
| Prompt 注入防护 | System/User 分层 + 特殊分隔符 + 输入清洗 |
| 工具权限 | mcp-bridge RBAC 集成，工具级 + 参数级 |

---

## 9. 项目间依赖

| 依赖项目 | 接口 | 用途 | 失败降级 |
|---------|------|------|---------|
| **token-core** | PyO3 `count_tokens()` | Token 精确计数 | 本地估算 char/4 |
| **token-core** | PyO3 `calculate_cost()` | 实时成本计算 | 缓存定价表 |
| **token-core** | PyO3 `truncate_messages()` | Context Window 截断 | 简单尾部截断 |
| **mcp-bridge** | `POST :8004/invoke` | MCP 工具调用 | 返回错误给 Agent |

---

## 10. 部署架构

### 开发环境

```yaml
agent-forge:
  deploy: {replicas: 1}
  resources: {limits: {memory: 256M, cpus: '0.5'}}
  command: uvicorn agentforge.api.http_app:app --workers 1
```

### 生产环境

```yaml
agent-forge:
  replicas: 3
  resources: {requests: {memory: 1Gi, cpu: 1}, limits: {memory: 2Gi, cpu: 2}}
  hpa: {min: 3, max: 20, cpu: 70%}
```

---

## 11. 目录结构

```
AgentForge/
├── agentforge/
│   ├── agents/             # BaseAgent + 各框架适配器
│   ├── middleware/         # 中间件管道 (pipeline + 7个中间件)
│   ├── tools/              # 工具注册中心 + MCP/FC 适配
│   ├── models/             # 模型 Provider (Claude/GPT/DeepSeek/...)
│   ├── bridge/             # RL 训练桥接
│   ├── api/                # HTTP + gRPC 接口层
│   └── core/               # 配置 / 安全 / 日志
├── unit_tests/             # 单元测试（pytest）
├── API_tests/              # API 接口测试（httpx + gRPC）
├── proto/                  # .proto 定义
├── run_tests.sh            # 一键执行全部测试
├── docker-compose.yml      # docker compose up 验收
├── Dockerfile
└── metadata.json
```

---

## 12. 验证标准

**功能验证：**
- [ ] 三套适配器（LangChain/OpenAI Agents/Native）运行同一任务，输出格式一致
- [ ] 1000 条消息 Context Window 检查 <10ms（PyO3 调用 token-core）
- [ ] ModelRouter 自动选择：简单→Haiku，复杂→Opus/DeepSeek V4 Pro
- [ ] 主模型失败 → 自动 fallback → 请求不丢失
- [ ] 100 条轨迹批量导出 Parquet，RL 训练可直读

**硬性要求验证：**
- [ ] `docker compose up` 一键启动成功，无依赖缺失
- [ ] `./run_tests.sh` 一键执行，输出 "PASS: X, FAIL: 0, TOTAL: X"
- [ ] gRPC 正常参数返回正确 response
- [ ] HTTP API 缺失参数返回 400 + `{"code": 400, "msg": "..."}`
- [ ] 格式错误返回 422 + `{"code": 422, "msg": "..."}`
- [ ] Token 超限：Pydantic 拒绝，返回 422 而非 500 崩溃
- [ ] ToolCallSanitizer 拦截 `rm -rf /` 等危险操作
- [ ] 异常不抛 Stack Trace，返回 `{"code": 500, "msg": "Internal error"}`

---

## 13. 硬性要求合规方案

### 13.1 一键启动保障
- Dockerfile 多阶段构建，`pip install -e .` 在镜像内完成
- docker-compose.yml 包含 `depends_on: [token-core, mcp-bridge]` + `healthcheck`
- 端口通过环境变量 `AGENT_FORGE_PORT` 配置，默认 8001
- 不依赖宿主机的绝对路径、全局环境变量或未声明的系统库

### 13.2 测试体系设计
- `unit_tests/` — pytest（适配器、中间件、工具注册、模型路由）
- `API_tests/` — httpx + grpcio（HTTP 端点 + gRPC 方法）
- `run_tests.sh` 一键执行，输出汇总：
  ```
  ===========================
  Test Results Summary
  ===========================
  Unit Tests:    PASS  20  FAIL  0
  API Tests:     PASS  15  FAIL  0
  ===========================
  TOTAL: PASS  35  FAIL  0  SKIP  0
  ===========================
  ```
- 覆盖：正常参数 / 缺失参数(400) / 格式错误(422) / 超时 / gRPC 流式

### 13.3 错误处理规范
- FastAPI exception_handler → `{"code": XXX, "msg": "..."}`
- gRPC → `grpc.StatusCode.INVALID_ARGUMENT` + 详细描述
- 严禁泄露 Stack Trace 给客户端

### 13.4 日志规范
- `structlog` 结构化 JSON，含 `trace_id` / `agent_id` / `model` / `latency_ms`
- 关键节点：请求进入 / 模型路由选择 / 模型 API 调用 / Tool Call / 异常

### 13.5 参数校验
- Pydantic v2 strict mode，所有 API 入参有 Schema
- gRPC Protobuf 类型强制 + 业务层二次校验

### 13.6 安全基线
- API Key：`os.environ["MODEL_API_KEY"]`，AES-256-GCM 加密存储
- 工具调用：经 mcp-bridge 统一治理，沙箱隔离
- 无 SQL 拼接（不直接操作数据库，通过 AgentEval 间接存储）
