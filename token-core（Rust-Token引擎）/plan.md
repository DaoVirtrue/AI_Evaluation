# token-core — 高性能 Rust Token 引擎

---

| 属性 | 值 |
|------|-----|
| 项目类型 | 纯后端：server |
| 前端语言 | 无 |
| 后端语言 | Python |
| 前端框架 | 无 |
| 后端框架 | FastAPI |
| 数据库 | 无 |
| 备注 | Rust 核心引擎（src/）为生产版，Docker 部署使用纯 Python（api/main.py） |

---

## 1. 项目概述

### 定位
整个 Agent 平台的"计量引擎"。所有 Token 计算（精确计数、批量处理、流式估算、Context Window 截断、多模型实时成本计算）统一由此库完成。必须用 Rust 实现：处理 1M token 消息列表时 Python GIL 是瓶颈，且需编译为 PyO3/WASM 供多种环境调用。

### 被依赖关系
| 调用方 | 用途 | 调用方式 |
|--------|------|---------|
| AgentForge | 中间件 Token 检查/截断/成本 | **PyO3**（直接函数调用，无网络开销） |
| AgentEval-Platform | 评测报告成本聚合 | HTTP API |
| AgentViz | 浏览器端实时 Token 计数 | **WASM** (npm 包) |
| claude-code-toolkit | Token 估算 MCP Server | HTTP API |

### 支持的模型（2026年6月最新定价）

| 厂商 | 模型 | Context | Input/1M | Output/1M | Cache Hit | 长上下文溢价 |
|------|------|---------|----------|-----------|-----------|------------|
| Anthropic | Fable 5 | 1M | $10.00 | $50.00 | — | 无 |
| Anthropic | Opus 4.8 | 1M | $5.00 | $25.00 | $0.50 | 无 |
| Anthropic | Sonnet 4.6 | 1M | $3.00 | $15.00 | $0.30 | 无 |
| Anthropic | Haiku 4.5 | 200K | $1.00 | $5.00 | $0.10 | 无 |
| OpenAI | GPT-5.5 | 1M | $5.00 | $30.00 | $0.50 | >272K: 2×/1.5× |
| OpenAI | GPT-5.4 | 1M | $2.50 | $15.00 | — | 无 |
| OpenAI | GPT-4.1 | 1M | $2.00 | $8.00 | $0.50 | 无 |
| OpenAI | GPT-4.1 Mini | 1M | $0.40 | $1.60 | — | 无 |
| OpenAI | GPT-4.1 Nano | 1M | $0.10 | $0.40 | — | 无 |
| DeepSeek | V4 Pro (promo) | 1M | $0.435 | $0.87 | $0.0036 | 无 |
| DeepSeek | V4 Flash | 1M | $0.14 | $0.28 | $0.0028 | 无 |
| Google | Gemini 3.1 Pro | 2M | $2.00 | $12.00 | $0.20 | >200K: 2×/1.5× |
| Google | Gemini 3.5 Flash | 1M | $1.50 | $9.00 | — | — |
| Google | Gemini 3.1 Flash-Lite | 1M | $0.25 | $1.50 | — | — |
| Alibaba | Qwen3-235B | 128K | $0.10 | $0.10 | — | — |
| Meta | Llama 4 Maverick | 1M | $0.20 | $0.80 | — | — |

---

## 2. 系统架构图

```
                              ┌──────────────────────────────┐
                              │      token-core HTTP API      │
                              │       FastAPI :8003           │
                              │  POST /count, /cost, /truncate│
                              └──────────────┬───────────────┘
                                             │
                              ┌──────────────▼───────────────┐
                              │         Rust Core             │
                              │                               │
                              │  ┌─────────────────────────┐  │
                              │  │     Tokenizer 模块       │  │
                              │  │  • claude / openai      │  │
                              │  │  • deepseek / gemini    │  │
                              │  │  • qwen / llama         │  │
                              │  │  • Registry (自动检测)   │  │
                              │  └───────────┬─────────────┘  │
                              │              │                │
                              │  ┌───────────▼─────────────┐  │
                              │  │     Counter 模块         │  │
                              │  │  • precise (encode)     │  │
                              │  │  • estimated (char/N)   │  │
                              │  │  • batch (rayon并行)    │  │
                              │  │  • streaming (增量)     │  │
                              │  └───────────┬─────────────┘  │
                              │              │                │
                              │  ┌───────────▼─────────────┐  │
                              │  │    Context 模块          │  │
                              │  │  • Window 状态机         │  │
                              │  │    (128K→1M→2M→10M)     │  │
                              │  │  • Truncation 引擎       │  │
                              │  │    (分层/语义/滑动窗口)   │  │
                              │  │  • Compression (摘要化)  │  │
                              │  │  • Needle-in-Haystack   │  │
                              │  └───────────┬─────────────┘  │
                              │              │                │
                              │  ┌───────────▼─────────────┐  │
                              │  │    Billing 模块          │  │
                              │  │  • Pricing (16+模型)    │  │
                              │  │  • Calculator (含溢价)  │  │
                              │  │  • Optimizer (建议引擎) │  │
                              │  │  • Alert (预算告警)     │  │
                              │  └─────────────────────────┘  │
                              │                               │
                              └──────┬────────────┬───────────┘
                                     │            │
                          ┌──────────▼──┐  ┌──────▼──────────┐
                          │ PyO3 绑定    │  │ WASM 绑定       │
                          │ (Python调用) │  │ (浏览器调用)    │
                          │ import token │  │ import * as wasm│
                          │ _core        │  │ from '...'      │
                          └──────────────┘  └─────────────────┘
```

---

## 3. 核心业务流程

### 3.1 Context Window 分层截断流程

```
输入: messages[], max_tokens, model
  │
  ▼
[预检] System Prompt Token → 如果超限 → 报错返回
  │
  ▼
[分层排序] 按优先级排列非System消息:
  1. Tool Results     (最高) — Agent 依赖工具结果
  2. Recent User (4轮) — 最近用户消息
  3. Recent Assistant (6轮)
  4. Older User
  5. Older Assistant  (最低) — 优先丢弃
  │
  ▼
[贪心分配] budget = max_tokens - system_tokens
  从高优先级开始，Token 够则保留，不够则跳过
  │
  ▼
[重排序] 按原始 index 恢复消息顺序
  │
  ▼
输出: TruncationResult {
  messages, tokens_kept, tokens_lost,
  truncated_count, warning (if >90% lost)
}
```

### 3.2 成本计算流程

```
输入: TokenUsage {prompt, completion, cache_hit, thinking}, model, opts
  │
  ▼
[查价] pricing = PRICING_TABLE[model]
  │
  ├─[基础成本] prompt × input_price + completion × output_price
  ├─[缓存节省] cache_hit × (input_price - cache_price) → 负值=省钱
  ├─[长上下文溢价] if prompt > threshold:
  │    (prompt - threshold) × input_price × (multiplier - 1)
  ├─[思考Token] max(0, thinking - free_tokens) × input_price
  └─[Batch折扣] if mode == 'batch': × 0.5
  │
  ▼
输出: CostBreakdown {base, cache_savings, surcharge, thinking, total, items}
```

---

## 4. 技术栈选型

| 层 | 选型 | 理由 |
|----|------|------|
| 核心 | Rust 1.82+ | 内存安全、零成本抽象、SIMD |
| Python 绑定 | PyO3 0.22+ | 直接调用 Rust，无序列化开销 |
| WASM | wasm-pack | 浏览器端运行 |
| 并行 | rayon | 批量 Token 计数并行加速 |
| 序列化 | serde + serde_json | 高性能 JSON |
| 金融精度 | rust_decimal | 避免 IEEE 754 浮点误差 |
| HTTP服务 | FastAPI (Python侧) | Rust 通过 PyO3 注入 |
| 基准测试 | Criterion | 统计显著性测试 |

---

## 5. 功能模块设计

| 模块 | 功能 | 性能目标 |
|------|------|---------|
| Tokenizer | 16+ 模型精确分词器 + 自动检测 | <100μs/条 |
| Counter/Batch | rayon 并行批量计数 | 1000条 <10ms |
| Counter/Streaming | SSE 流式字符估算 | <10μs/次 |
| Context/Truncation | 分层截断（System→Tool→Recent→Old） | 1M token <100ms |
| Context/Compression | 历史摘要压缩（调用小模型） | — |
| Billing/Calculator | 含溢价+缓存+思考Token+输出效率 | <1μs |
| Billing/Optimizer | 调用模式分析 + 省钱建议 | — |
| Billing/Alert | 预算阈值告警 + 异常检测 | — |
| Models/Capabilities | 多维能力评分（coding/reasoning/long_ctxt/speed） | — |

---

## 6. 数据模型设计

```rust
// 核心数据结构（Rust）
struct Message {
    role: Role,           // System / User / Assistant / Tool
    content: String,
    index: usize,
}

struct TokenUsage {
    prompt_tokens: usize,
    completion_tokens: usize,
    cache_hit_tokens: usize,
    thinking_tokens: usize,
    effective_output_tokens: usize,  // GPT-5.5 输出效率
}

struct CostBreakdown {
    base_input_cost: Decimal,
    base_output_cost: Decimal,
    cache_savings: Decimal,           // 负值=省钱
    long_context_surcharge: Decimal,
    thinking_cost: Decimal,
    total: Decimal,
    items: CostLineItems,
}

struct TruncationResult {
    messages: Vec<Message>,
    tokens_kept: usize,
    tokens_lost: usize,
    truncated_count: usize,
    warning: Option<String>,          // >90%截断时警告
}
```

---

## 7. API 设计

```python
# === Python API (PyO3) ===
import token_core

# Token 计数
count = token_core.count_tokens("Hello, world!", model="claude-opus-4-8")
counts = token_core.count_batch(messages, model="gpt-5.5")

# Context Window
result = token_core.truncate(messages, max_tokens=900_000, model="claude-opus-4-8")

# 成本计算
cost = token_core.calculate_cost(usage, model="deepseek-v4-pro", mode="online")

# 多模型对比
comparisons = token_core.compare_models(input_tokens=100_000, estimated_output=20_000,
    candidates=["claude-opus-4-8", "deepseek-v4-pro", "gpt-4.1-nano"])

# 优化建议
suggestions = token_core.analyze_spending(history)

# === HTTP API (FastAPI :8003) ===
POST /api/v1/count        # Token 计数
POST /api/v1/count/batch   # 批量计数
POST /api/v1/truncate      # Context Window 截断
POST /api/v1/cost          # 成本计算
POST /api/v1/compare       # 多模型成本对比
GET  /api/v1/pricing       # 获取最新定价表
GET  /api/v1/health        # 健康检查

# === WASM API (浏览器) ===
import init, { count_tokens, calculate_cost } from '@agent-viz/token-core-wasm';
await init();
count_tokens("Hello", "claude-sonnet-4-6");
```

---

## 8. 非功能性设计

### 8.1 低延迟（核心优势）

| 机制 | 实现 | 目标 |
|------|------|------|
| Rust 原生 | 零成本抽象 + 编译优化 | 比 Python 快 10-50× |
| rayon 并行 | 批量计数 work-stealing 并行 | 1000条 <10ms |
| 无锁读取 | Arc<RwLock<Tokenizer>>, 读路径无锁 | 高并发读不阻塞 |
| 零拷贝 | &str 传递，避免 String clone | 减少内存分配 |
| 内存映射 | tokenizer 词表 mmap 加载 | 启动 <50ms, 内存 <10MB |

### 8.2 高并发

| 机制 | 实现 |
|------|------|
| 连接池 | HTTP 连接池 pool_maxsize=50 |
| 无状态服务 | 纯计算，无本地状态，可无限水平扩展 |
| 请求合并 | 相同参数并发请求自动去重 |

### 8.3 高可用

| 机制 | 实现 |
|------|------|
| 健康检查 | /health (liveness) + /ready (readiness) |
| 定价降级 | HTTP 更新失败 → 使用本地缓存定价表 |
| 优雅关闭 | 完成进行中计算 → 退出 |

### 8.4 可扩展

| 机制 | 实现 |
|------|------|
| 新增模型 | 只需在 PRICING_TABLE 添加一条记录 + 注册 Tokenizer |
| 新增截断策略 | 实现 TruncationStrategy trait 即可 |
| 定价更新 | HTTP 定期拉取 / 手动更新 / CI 自动更新 |

### 8.5 安全

| 层级 | 措施 |
|------|------|
| 内存安全 | Rust 编译时保证 (no segfault/use-after-free/buffer overflow) |
| DoS 防护 | 输入长度预检查（拒接 >10M 字符的单条消息） |
| FFI 边界 | PyO3 / wasm-bindgen 边界严格类型校验 |
| 金融精度 | Decimal 类型，避免浮点误差累积 |
| unsafe 控制 | `#![forbid(unsafe_code)]`（仅 FFI 块例外） |

---

## 9. 项目间依赖

token-core 是**被依赖方**，不依赖其他项目（纯底层库）：

| 被调用方 | 接口 | 调用方式 |
|---------|------|---------|
| AgentForge | `count_tokens`, `truncate`, `calculate_cost` | **PyO3** |
| AgentEval-Platform | `POST /api/v1/count`, `/cost` | HTTP |
| AgentViz | `count_tokens`, `calculate_cost` | **WASM** |
| claude-code-toolkit | `POST /api/v1/count`, `/compare` | HTTP |

---

## 10. 部署架构

### 开发环境

```yaml
token-core:
  deploy: {replicas: 1}
  resources: {limits: {memory: 128M, cpus: '1.0'}}  # Rust 极省内存
  command: uvicorn token_core.api:app --workers 1
```

### 生产环境

```yaml
token-core:
  replicas: 2   # CPU密集型，少量副本即可
  resources: {limits: {memory: 512M, cpus: 4}}
```

---

## 11. 目录结构

```
token-core/
├── Cargo.toml
├── src/
│   ├── lib.rs
│   ├── tokenizer/         # 16+ 模型分词器
│   ├── counter/           # 精确/估算/批量/流式
│   ├── context/           # Window + Truncation + Compression
│   ├── billing/           # Pricing + Calculator + Optimizer + Alert
│   └── models/            # 能力矩阵
├── unit_tests/            # Rust 单元测试（cargo test）
├── integration_tests/     # PyO3 + WASM 集成测试
├── API_tests/             # HTTP API 测试（httpx）
├── benches/               # Criterion 基准
├── run_tests.sh           # cargo test + pytest + wasm-pack test
├── Dockerfile
└── metadata.json
```

---

## 12. 验证标准

**功能验证：**
- [ ] 16+ 模型 Token 计数与官方 API 误差 <1%
- [ ] 1000 条消息批量计数 <10ms（Criterion bench）
- [ ] 成本计算与官方账单误差 <0.01%（Decimal 精度）
- [ ] 分层截断：System必保 → Tool结果保留 → 旧消息舍弃
- [ ] GPT-5.5 >272K / Gemini >200K 长上下文溢价自动触发
- [ ] `import token_core` Python 可用，API 与 Rust 一致

**硬性要求验证：**
- [ ] `docker compose up` 一键启动成功
- [ ] `./run_tests.sh` 一键执行，输出 "PASS: X, FAIL: 0, TOTAL: X"
- [ ] HTTP API 正常参数返回 200 + 正确 Token 计数
- [ ] HTTP API 缺失 model 参数返回 400 + `{"code": 400, "msg": "Missing 'model'"}`
- [ ] HTTP API 超大输入(>10M chars)返回 413 + `{"code": 413, "msg": "..."}`
- [ ] PyO3 异常不导致 Python 进程崩溃
- [ ] WASM 编译 <1MB，浏览器加载 <500ms
- [ ] 无 `unsafe` 代码崩溃（`#![forbid(unsafe_code)]`）

---

## 13. 硬性要求合规方案

### 13.1 一键启动保障
- Dockerfile 多阶段：`rust:1.82-slim` build → `python:3.12-slim` runtime
- 所有 Rust 依赖在 `Cargo.toml` 锁定，Python 依赖在 `requirements.txt`
- docker-compose.yml 包含 `healthcheck: curl :8003/health`
- 不依赖宿主机 Rust/Cargo 全局安装

### 13.2 测试体系设计
- `unit_tests/` — `cargo test`（每个模块的单元测试 + proptest 属性测试）
- `integration_tests/` — PyO3 集成测试（pytest）+ WASM 测试（wasm-pack test）
- `API_tests/` — httpx（HTTP 端点测试）
- `run_tests.sh` 输出汇总：
  ```
  ===========================
  Test Results Summary
  ===========================
  Rust Unit:     PASS  45  FAIL  0
  Python Integ:  PASS  12  FAIL  0
  WASM Tests:    PASS   8  FAIL  0
  API Tests:     PASS  10  FAIL  0
  ===========================
  TOTAL: PASS  75  FAIL  0  SKIP  0
  ===========================
  ```
- 覆盖：正常参数 / 缺失参数(400) / 超大输入(413) / 并发请求 / 精度验证

### 13.3 错误处理规范
- Rust：`Result<T, TokenError>` 全链路，异常不 panic
- Python：PyO3 → `PyErr` 翻译为 Python 异常，含清晰错误信息
- HTTP：FastAPI → `{"code": XXX, "msg": "...", "detail": null}`
- 严禁 FFI 边界 crash

### 13.4 日志规范
- Rust: `tracing` crate → `INFO`(请求进入) / `DEBUG`(计算细节) / `ERROR`(异常)
- Python: `structlog` → 结构化 JSON

### 13.5 参数校验
- Rust: `#![forbid(unsafe_code)]` + 输入长度预检查（>10M chars → 拒绝）
- Python: Pydantic v2 strict mode（HTTP API 层）
- FFI 边界：PyO3/wasm-bindgen 严格校验所有输入类型

### 13.6 安全基线
- 内存安全：Rust 编译时保证（无 segfault / use-after-free / buffer overflow）
- DoS 防护：输入长度上限、批量接口数组长度上限
- 金融精度：`rust_decimal`，避免 IEEE 754 浮点误差
- 定价表：本地硬编码 + HTTP 定期拉取，不依赖外部服务启动
