# mcp-bridge — MCP 协议桥接 + 工具治理网关

---

| 属性 | 值 |
|------|-----|
| 项目类型 | 纯后端：server |
| 前端语言 | 无 |
| 后端语言 | Python |
| 前端框架 | 无 |
| 后端框架 | FastAPI, JSON-RPC 2.0 |
| 数据库 | 无 |

---

## 1. 项目概述

### 定位
MCP (Model Context Protocol) 协议桥接与工具治理网关。解决三层问题：
1. **协议互转**：MCP ↔ OpenAI Function Calling ↔ Anthropic Tool Use 透明双向转换
2. **工具治理**：统一权限控制(RBAC)、速率限制、调用审计、沙箱执行
3. **工具生态**：本地 MCP Server 发现、注册、测试、代理

### 被依赖关系
| 调用方 | 用途 | 调用方式 |
|--------|------|---------|
| AgentForge | Agent 工具调用代理 | HTTP API + JSON-RPC |
| claude-code-toolkit | MCP Server 注册/发现 | JSON-RPC (stdio/SSE) |

### 依赖项目
无（底层协议库，不依赖其他项目）。

---

## 2. 系统架构图

```
┌───────────────────────────────────────────────────────────────────┐
│                          mcp-bridge                                │
│                                                                   │
│  ┌─────────────────────────┐    ┌─────────────────────────────┐  │
│  │      MCP Server 框架     │    │       MCP Client SDK        │  │
│  │                         │    │                             │  │
│  │ Transport:              │    │ • Connection Pool (复用)    │  │
│  │  • stdio (本地进程)      │    │ • Tool Discovery (缓存)    │  │
│  │  • SSE (HTTP 推送)      │    │ • Invocation (同步/异步)   │  │
│  │  • WebSocket (双向)     │    └─────────────┬───────────────┘  │
│  │                         │                  │                  │
│  │ Handler: JSON-RPC 2.0   │                  │                  │
│  │ Tool Registry + Auth    │                  │                  │
│  └────────────┬────────────┘                  │                  │
│               │                               │                  │
│               └───────────┬───────────────────┘                  │
│                           │                                      │
│  ┌────────────────────────▼──────────────────────────────────┐  │
│  │                    Bridge Engine                            │  │
│  │                                                            │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │  │
│  │  │ MCP → OpenAI │  │ OpenAI → MCP │  │ MCP ↔ Anthropic│    │  │
│  │  │ FunctionCall │  │ FunctionCall │  │   Tool Use    │     │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘     │  │
│  │                                                            │  │
│  │  Schema Mapper: JSON Schema 双向映射                       │  │
│  │  (const/enum/anyOf/oneOf/allOf 兼容处理)                   │  │
│  └────────────────────────┬───────────────────────────────────┘  │
│                           │                                      │
│  ┌────────────────────────▼──────────────────────────────────┐  │
│  │                 Governance Layer (工具治理)                 │  │
│  │                                                            │  │
│  │  Access Control  │ Rate Limiter  │ Audit Log  │ Sandbox   │  │
│  │  (RBAC 工具级)   │ (滑动窗口)     │ (不可篡改) │ (Docker)  │  │
│  │                  │ per tool/user │ JSON+签名  │ 进程隔离   │  │
│  └────────────────────────┬───────────────────────────────────┘  │
│                           │                                      │
│  ┌────────────────────────▼──────────────────────────────────┐  │
│  │                  Proxy (中间人模式)                          │  │
│  │  Intercept (拦截修改)  │  Cache (结果缓存 TTL)              │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

### 三种协议互转矩阵

| 特性 | MCP | OpenAI FC | Anthropic Tool Use |
|------|-----|-----------|-------------------|
| 传输 | stdio/SSE/WS | API 内联 | API 内联 |
| Schema | JSON Schema | JSON Schema + strict | JSON Schema |
| 发现 | tools/list | 静态配置 | 静态配置 |
| 流式 | 支持 (SSE) | 不支持 | 不支持 |
| 错误 | JSON-RPC error | content: "error" | content: "error" |

---

## 3. 核心业务流程

### 3.1 工具调用全流程（时序图）

```
AgentForge     mcp-bridge      Governance      MCP Server      External Tool
    │               │                │               │               │
    │ invoke_tool() │                │               │               │
    │──────────────▶│                │               │               │
    │               │ [Access Control]              │               │
    │               │───────────────▶│               │               │
    │               │◀── authorized ─│               │               │
    │               │ [Rate Limit]   │               │               │
    │               │───────────────▶│               │               │
    │               │◀── within_limit│               │               │
    │               │ [Input Validate]              │               │
    │               │ tool_input vs JSON Schema     │               │
    │               │                │               │               │
    │               │ (若 MCP Server 注册为本地)     │               │
    │               │──────────────────────────────▶│               │
    │               │◀────── tool_result ──────────│               │
    │               │                │               │               │
    │               │ [Output Validate]             │               │
    │               │ [Audit Log]     │               │               │
    │               │───────────────▶│ (记录不可篡改) │               │
    │               │                │               │               │
    │◀── tool_result│                │               │               │
```

### 3.2 协议转换流程

```
MCP Tool Def → Schema Mapper → OpenAI FC Def

Example:
  MCP: {
    name: "web_search",
    description: "Search the web",
    inputSchema: {
      type: "object",
      properties: {
        query: {type: "string", description: "Search query"}
      },
      required: ["query"]
    }
  }
  
  ↓ mcp_to_openai()
  
  OpenAI FC: {
    type: "function",
    function: {
      name: "web_search",
      description: "Search the web",
      parameters: {  ← 直接复用 JSON Schema
        type: "object",
        properties: {query: {type: "string", description: "Search query"}},
        required: ["query"]
      },
      strict: true
    }
  }
```

---

## 4. 技术栈选型

| 层 | 选型 | 理由 |
|----|------|------|
| 框架 | Python 3.12 + FastAPI | 异步、生态好 |
| 协议 | JSON-RPC 2.0 | MCP 标准协议 |
| Schema 验证 | jsonschema | JSON Schema 严格校验 |
| 高性能路径 | Rust (tokio) | Schema 转换等计算密集操作 |
| 传输 | stdio / SSE / WebSocket | MCP 三种标准传输 |
| 沙箱 | Docker SDK + subprocess | 工具执行隔离 |
| 审计日志 | Append-only file + HMAC | 不可篡改 |

---

## 5. 功能模块设计

### 5.1 MCP Server 框架

| 功能 | 说明 |
|------|------|
| Transport 层 | stdio (本地进程) / SSE (远程推送) / WebSocket (双向实时) |
| Handler | JSON-RPC 2.0 请求路由 (initialize/tools/list/tools/call) |
| Tool Registry | register / discover / invoke / health_check |
| Auth | Bearer Token / API Key / mTLS |

### 5.2 MCP Client SDK

| 功能 | 说明 |
|------|------|
| Connection Pool | TCP keep-alive, 最大空闲10, 最大活跃50, 自动重连 |
| Tool Discovery | 工具列表获取 + 本地缓存 (TTL 5min) |
| Invocation | 同步/异步/流式(progress token) |

### 5.3 协议桥接引擎

| 转换方向 | 说明 |
|---------|------|
| MCP → OpenAI FC | JSON Schema 直接复用, strict=true |
| OpenAI FC → MCP | JSON Schema 提取, 降级不兼容属性 |
| MCP → Anthropic | JSON Schema 直接复用（高度兼容） |
| Anthropic → MCP | Content Block 转 JSON-RPC Result |

### 5.4 工具治理

| 组件 | 功能 | 实现 |
|------|------|------|
| Access Control | RBAC (Admin/Operator/ReadOnly), 工具级+参数级 | YAML 策略文件 |
| Rate Limiter | 滑动窗口, per tool/user/IP | Redis / 内存 |
| Audit Log | 完整记录, append-only + HMAC 签名 | 结构化 JSON |
| Tool Validator | 输入/输出 JSON Schema 严格验证 | jsonschema |
| Sandbox | Docker gVisor / 进程隔离 / 网络隔离 / 只读FS | Docker SDK |

### 5.5 CLI 工具

| 命令 | 功能 |
|------|------|
| `mcp-proxy` | 启动 MCP 代理（中间人模式） |
| `mcp-inspect` | 工具调试/验证（发送测试请求） |
| `mcp-convert` | 协议格式转换（MCP→FC / FC→MCP） |

---

## 6. 数据模型设计

```python
# 工具治理策略模型
class ToolPolicy:
    tool_name: str
    access: AccessRule          # roles, users, readonly_users
    rate_limit: RateLimitRule   # max_per_minute, max_per_hour
    sandbox: SandboxConfig      # type, image, network, read_only_rootfs
    validation: ValidationRule  # forbidden_keywords, max_params_size

# 审计日志模型
class AuditEvent:
    event: str                  # "tool_call" | "tool_register" | "access_denied"
    timestamp: datetime
    user: str
    tool: str
    params_hash: str            # SHA256
    result_hash: str            # SHA256
    latency_ms: int
    status: str                 # "success" | "error" | "denied"
    sandbox_id: str | None
    trace_id: str
```

---

## 7. API 设计

```
# MCP Server 端点 (JSON-RPC 2.0)
POST /mcp                          MCP JSON-RPC 入口
    methods:
      initialize                   握手 + 能力协商
      tools/list                   列出可用工具
      tools/call                   调用工具
      resources/list               列出资源
      prompts/list                 列出提示模板

# MCP Client API (HTTP)
POST /api/v1/tools/invoke          调用外部 MCP 工具
GET  /api/v1/tools/discover        发现外部 MCP Server 的工具
POST /api/v1/tools/register        注册本地工具

# Governance API
GET  /api/v1/audit/logs            查询审计日志（分页）
POST /api/v1/policies/update       更新工具策略
GET  /api/v1/health                健康检查

# CLI
mcp-proxy --server http://localhost:9000
mcp-inspect --tool web_search --input '{"query": "test"}'
mcp-convert --from mcp --to openai --file tool_def.json
```

---

## 8. 非功能性设计

### 8.1 高并发

| 机制 | 实现 |
|------|------|
| Async 全链路 | asyncio + httpx async client |
| 连接池 | MCP Client 连接复用 (max_idle=10, max_active=50) |
| 请求合并 | 相同参数并发调用去重合并 |
| 背压保护 | 工具调用队列满 → 429 + Retry-After |

### 8.2 高可用

| 机制 | 实现 |
|------|------|
| 连接重试 | MCP Client 断开 → 指数退避重连 |
| 健康检查 | MCP Server heartbeat 探测 + 自动摘除不健康节点 |
| 优雅关闭 | 完成进行中调用 → 关闭连接 → 退出 |

### 8.3 可扩展

| 机制 | 实现 |
|------|------|
| 插件化 Transport | 新增传输方式只需实现 Transport trait |
| 自定义治理策略 | YAML 配置驱动，无需改代码 |
| 协议扩展 | 新增转换方向只需实现 ProtocolMapper trait |

### 8.4 低延迟

| 机制 | 实现 | 目标 |
|------|------|------|
| Rust Schema Mapper | 复杂 Schema 转换用 Rust | <1ms |
| 连接复用 | 长连接 + Keep-Alive | 消除握手延迟 |
| 结果缓存 | 幂等工具调用结果缓存 TTL | 命中时 <5ms |
| 本地 stdio | 本地 MCP Server 走 stdio | 无网络延迟 |

### 8.5 安全

| 层级 | 措施 |
|------|------|
| 传输安全 | stdio(本地) / SSE+TLS / WSS |
| 认证 | Bearer Token / API Key / mTLS |
| 授权 | 工具级 + 参数级 RBAC |
| 限流 | 滑动窗口 per tool/user/IP |
| 输入验证 | JSON Schema strict mode, 拒绝额外属性 |
| 输出验证 | Schema + 类型检查, 异常拒绝 |
| 审计 | Append-only + HMAC 签名, 不可篡改 |
| 沙箱 | Docker gVisor / 进程隔离 / 网络隔离 / 只读文件系统 |
| 注入防护 | 危险命令拦截 (rm/sudo/curl外连等) |

---

## 9. 项目间依赖

mcp-bridge 是底层协议库，不依赖其他项目。

| 被调用方 | 接口 | 用途 |
|---------|------|------|
| AgentForge | `POST /api/v1/tools/invoke` | Agent 工具调用代理 |
| AgentForge | `GET /api/v1/tools/discover` | 发现 MCP 工具列表 |
| claude-code-toolkit | JSON-RPC (stdio) | MCP Server 注册 |

---

## 10. 部署架构

### 开发环境

```yaml
mcp-bridge:
  deploy: {replicas: 1}
  resources: {limits: {memory: 128M, cpus: '0.3'}}
  command: uvicorn server.handler:app --workers 1
```

### 生产环境

```yaml
mcp-bridge:
  replicas: 2
  resources: {limits: {memory: 512M, cpus: 2}}
```

---

## 11. 目录结构

```
mcp-bridge/
├── server/                # MCP Server 框架
│   ├── transport/         # stdio / SSE / WebSocket
│   ├── handler.py
│   ├── tool_registry.py
│   └── auth.py
├── client/                # MCP Client SDK
│   ├── connection_pool.py
│   ├── tool_discovery.py
│   └── invocation.py
├── bridge/                # 协议桥接引擎
│   ├── mcp_to_openai.py
│   ├── openai_to_mcp.py
│   ├── anthropic_mcp.py
│   └── schema_mapper.py
├── governance/            # 工具治理
│   ├── access_control.py
│   ├── rate_limiter.py
│   ├── audit_log.py
│   ├── tool_validator.py
│   ├── sandbox.py
│   └── policy.yaml
├── proxy/                 # 中间人代理
│   ├── intercept.py
│   └── cache.py
├── cli/                   # 命令行工具
├── unit_tests/            # 单元测试（pytest）
├── API_tests/             # API + JSON-RPC 协议测试
├── run_tests.sh           # 一键执行全部测试
├── docker-compose.yml     # docker compose up 验收
├── Dockerfile
└── metadata.json
```

---

## 12. 验证标准

**功能验证：**
- [ ] MCP → OpenAI FC 转换 100% 兼容（含 strict mode）
- [ ] Anthropic Tool Use → MCP 转换 100% 兼容
- [ ] 三轮协议互转 (MCP→FC→MCP) 无信息丢失
- [ ] RBAC: ReadOnly 用户调用 write 工具 → 403
- [ ] 限流: >30req/min → 429 + Retry-After header
- [ ] 审计日志: 每次调用完整记录, HMAC 签名不可篡改

**硬性要求验证：**
- [ ] `docker compose up` 一键启动成功
- [ ] `./run_tests.sh` 一键执行，输出 "PASS: X, FAIL: 0, TOTAL: X"
- [ ] JSON-RPC 正常参数返回 `{"jsonrpc": "2.0", "result": {...}, "id": 1}`
- [ ] JSON-RPC 缺失 method → `{"jsonrpc": "2.0", "error": {"code": -32600, "message": "..."}, "id": null}`
- [ ] JSON-RPC 无权限 → `{"code": -32001, "message": "Forbidden"}`
- [ ] 沙箱: `rm -rf /` → 被拦截（只读文件系统）
- [ ] 50 并发工具调用 → 0 超时/0 数据错乱
- [ ] MCP Server 宕机 → Client 自动重连

---

## 13. 硬性要求合规方案

### 13.1 一键启动保障
- Dockerfile 包含所有 Python 依赖 `pip install -e .`
- docker-compose.yml `depends_on: []`（纯计算服务，无外部依赖）
- 端口通过 `MCP_BRIDGE_PORT` 环境变量配置
- 不依赖宿主机文件系统绝对路径

### 13.2 测试体系设计
- `unit_tests/` — pytest（Schema Mapper / Governance / Sandbox）
- `API_tests/` — httpx + pytest-asyncio（JSON-RPC 协议测试）
- `run_tests.sh` 输出汇总：
  ```
  ===========================
  Test Results Summary
  ===========================
  Unit Tests:    PASS  25  FAIL  0
  API Tests:     PASS  18  FAIL  0
  ===========================
  TOTAL: PASS  43  FAIL  0  SKIP  0
  ===========================
  ```
- 覆盖：正常调用 / 缺失 method / 无权限 / 超限流 / 协议转换正确性

### 13.3 错误处理规范
- JSON-RPC: 所有错误返回标准 `{"jsonrpc": "2.0", "error": {...}, "id": ...}`
- 错误码符合 JSON-RPC 2.0 规范 (-32700 解析错误, -32600 无效请求, -32601 方法不存在)
- 自定义错误码：-32000 工具错误, -32001 权限不足, -32002 限流

### 13.4 日志规范
- `structlog` 结构化 JSON，含 `trace_id`, `tool_name`, `user`, `latency_ms`
- 审计日志：append-only + HMAC 签名，不可篡改

### 13.5 参数校验
- 所有 JSON-RPC params 经 JSON Schema 严格验证
- 工具调用：输入/输出双重 Schema 校验

### 13.6 安全基线
- 传输：SSE/WebSocket 走 TLS，stdio 仅本地
- 鉴权：Bearer Token / API Key / mTLS
- RBAC：工具级 + 参数级权限
- 沙箱：Docker gVisor / 进程隔离 / 网络隔离 / 只读文件系统
