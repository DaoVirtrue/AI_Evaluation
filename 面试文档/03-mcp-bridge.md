# 03 — mcp-bridge：MCP 协议桥接 + 工具治理网关

> **前置知识**：读完 01-开篇全景、02-token-core
> **阅读目标**：理解什么是协议、MCP 是什么、为什么需要协议转换、什么是工具治理

---

## 第一部分：是什么

### 1.1 生活类比：万国插头转换器

你出国旅行，带了中国的电器（国标插头），但酒店只有欧标插座。

你怎么办？买个**万国插头转换器**。

mcp-bridge 就是这个转换器。它让使用不同"协议"的 Agent 和工具能够互相沟通。Agent 可能说"MCP 协议"，工具可能只懂"OpenAI Function Calling 协议"，mcp-bridge 在中间做翻译。

### 1.2 大白话解释

**什么是协议（Protocol）？**

协议就是"计算机之间怎么说话"的约定。

```
人类协议：   "你好" → 对方回 "你好"
HTTP 协议：  "GET /page" → 服务器回 "200 OK + 网页内容"
JSON-RPC：  {"method": "调用", "params": {...}} → 对方回 {"result": {...}}
```

**为什么需要 MCP？**

2024 年之前，每个 AI 大模型公司都有自己的"工具调用"方式：
- OpenAI 用 **Function Calling**（函数调用格式）
- Anthropic 用 **Tool Use**（工具使用格式）
- 其他公司各有各的格式

这导致一个问题：你为 OpenAI 写了一个"搜索网页"的工具，换个 Anthropic 的模型就不能用了，得重新写。

2024 年底，Anthropic 提出 **MCP（Model Context Protocol，模型上下文协议）**，想做一个"统一标准"——所有模型、所有工具都用同一套协议沟通。类似于 USB 接口统一了所有外设的连接方式。

**mcp-bridge 做三件事：**

1. **协议互转**：MCP → OpenAI FC、OpenAI FC → MCP、Anthropic Tool Use ↔ MCP
2. **工具治理**：谁可以用什么工具、一分钟最多调用几次、所有调用记录留档
3. **安全沙箱**：危险的工具调用（如 `rm -rf /`）被自动拦截

### 1.3 三种协议的关系

| 协议 | 提出者 | 格式 | 相当于 |
|------|--------|------|--------|
| MCP | Anthropic | JSON-RPC 2.0 | 国际标准 USB-C |
| Function Calling | OpenAI | API 内联 JSON | 苹果 Lightning 接口 |
| Tool Use | Anthropic | API 内联 JSON | 安卓 Micro-USB |

mcp-bridge 就是"转接头"——让 Lightning 设备能插到 USB-C 充电器上。

### 1.4 它在 7 个项目中的位置

```
AgentForge → "帮我调用 web_search 工具"
    ↓
mcp-bridge → 1. 检查权限（这个用户有权限用 web_search 吗？）
            → 2. 检查限流（这分钟调用超过 30 次了吗？）
            → 3. 格式转换（AgentForge 用 MCP → 目标工具用 OpenAI FC）
            → 4. 执行调用
            → 5. 记录审计日志
    ↓
返回结果给 AgentForge
```

---

## 第二部分：为什么

### 2.1 为什么需要协议转换层而不是直接对接？

**方案 A（不用 mcp-bridge）**：AgentForge 里写死三种协议的转换逻辑 → 每加一个新模型要改 AgentForge 代码 → AgentForge 越来越臃肿。

**方案 B（用 mcp-bridge）**：AgentForge 只和 mcp-bridge 沟通（统一用 MCP），mcp-bridge 负责所有协议转换 → 加新模型只需在 mcp-bridge 加一个转换器 → AgentForge 不用改。

**这就是"单一职责原则"**：AgentForge 专心做 Agent 执行，mcp-bridge 专心做协议转换。

### 2.2 为什么用 JSON-RPC 2.0？

JSON-RPC 是一个极其简单的远程调用协议。请求格式：

```json
{"jsonrpc": "2.0", "method": "tools/call", "params": {...}, "id": 1}
```

响应格式：

```json
{"jsonrpc": "2.0", "result": {...}, "id": 1}
```

**为什么不用 REST API？**
REST API 用"动词 + URL"描述操作（如 `POST /api/tools/search`）。但 MCP 需要支持双向通信（服务器主动推送消息给客户端），REST 是单向的（客户端请求→服务器响应）。JSON-RPC 配合 SSE/WebSocket 可以双向。

**为什么不用 gRPC？**
gRPC 性能更好，但需要 `.proto` 文件定义接口，不如 JSON-RPC 方便调试。MCP 的设计哲学是"足够简单，让人能用 curl 调试"。

### 2.3 为什么需要工具治理？

想象一个场景：你公司有 50 个 Agent 在运行，每个 Agent 都调用"删除文件"这个工具。如果没有治理：

- 一个 bug Agent 可能删掉所有文件 → **没有权限控制**
- 50 个 Agent 同时疯狂调用工具 → 工具服务器被打挂 → **没有限流**
- 出事了查不到是谁调用了什么 → **没有审计日志**

工具治理就是"给工具调用上三道锁"：

| 锁 | 作用 | 配置示例 |
|----|------|---------|
| 权限控制 | 谁能用这个工具 | readonly 用户不能用 write 工具 |
| 速率限制 | 多久能调一次 | 搜索工具：30 次/分钟 |
| 审计日志 | 谁调了什么 | 每次调用记录 + HMAC 签名防篡改 |

### 2.4 如何实现硬性要求

**高并发**：mcp-bridge 用 Python asyncio 异步处理。收到 50 个工具调用请求时，不是排队（同步），而是同时处理（异步）。连接池复用 TCP 连接，减少反复建立连接的开销。

**高可用**：无状态服务，可以启动多个实例。MCP Server 挂了会指数退避重连（等 1 秒→2 秒→4 秒→8 秒）。

**安全**：工具调用输入/输出都经 JSON Schema 严格校验。危险操作（`rm -rf`、`DROP TABLE`）在参数校验层就被拦截。Docker 沙箱模式下，工具在隔离容器中运行，只有只读文件系统和受限网络。

**可扩展**：新增协议转换方向只需实现一个函数（如 `mcp_to_openai()`），不修改核心逻辑。

---

## 第三部分：怎么做

### 3.1 白话实现路径

```
1. AgentForge 调用：POST /api/v1/tools/invoke {"tool": "web_search", "params": {"query": "AI"}}
         ↓
2. AccessController 检查权限：用户 "admin" 能用 "web_search" → 通过
         ↓
3. RateLimiter 检查限流：web_search 这分钟调了 15 次，上限 30 次 → 通过
         ↓
4. ToolValidator 校验参数：query 是 string，长度 < 100K → 通过
         ↓
5. 协议转换（如果需要）：MCP → OpenAI FC 格式
         ↓
6. 执行工具调用
         ↓
7. 输出校验 + 审计日志（HMAC 签名）
         ↓
8. 返回结果给 AgentForge
```

### 3.2 协议转换到底做了什么？

MCP 格式：
```json
{"name": "web_search", "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}}}
```

转为 OpenAI Function Calling 格式：
```json
{"type": "function", "function": {"name": "web_search", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}}, "strict": true}}
```

核心变化：加了 `strict: true`（OpenAI 要求严格模式），外层多了一层 `function` 包装。

---

## 第四部分：面试指南

### Q1: MCP 是什么？为什么需要它？

MCP 是 Anthropic 提出的模型-工具标准协议。它解决的核心问题是**碎片化**——之前每个 AI 公司有自己的工具调用格式，开发者为 OpenAI 写的工具不能在 Claude 上用。MCP 的目标是成为"AI 工具的 USB 标准"，和 USB 统一外设接口的逻辑一样。

### Q2: 你的 mcp-bridge 和直接用 MCP 有什么区别？

直接用 MCP：只支持 MCP 协议的 Agent 和工具。mcp-bridge：支持三种协议的互转——无论 Agent 用什么格式（MCP/OpenAI FC/Anthropic Tool Use），无论工具提供什么接口，mcp-bridge 都能桥接。而且它还加了工具治理（权限、限流、审计），这是原生 MCP 没有的。

### Q3: JSON-RPC 和 REST 有什么区别？

REST 用 HTTP 方法（GET/POST/DELETE）+ URL 路径来定义操作，适合 CRUD 场景。JSON-RPC 用单一端点 + method 字段来定义操作，适合远程过程调用。MCP 选 JSON-RPC 是因为工具调用本质是"远程调用一个函数"而不是"增删改查资源"。

### Q4: 如何防止恶意工具调用？

三道防线：第一道——访问控制，未授权用户直接 403。第二道——参数校验，危险字符串（`rm -rf`、`os.system`）在验证层被拦截。第三道——Docker 沙箱，即使前两道被绕过，工具在隔离容器内运行，只有只读文件系统、没有网络、到时间自动 kill。

### Q5: 50 个并发工具调用来的时候，系统会不会挂？

不会。Python asyncio 异步处理，50 个请求同时处理不需要 50 个线程。连接池复用 TCP 连接，不需要反复握手。如果下游 MCP Server 处理不过来，mcp-bridge 会返回 429（Too Many Requests）并带上 Retry-After header，告诉调用方多久后重试——这叫"背压保护"，保护下游不被打挂。
