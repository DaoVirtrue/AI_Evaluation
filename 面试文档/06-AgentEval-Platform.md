# 06 — AgentEval-Platform：旗舰全栈 Agent 评测平台

> **前置知识**：读完 01-05
> **阅读目标**：理解全栈是什么、前后端如何协作、什么是实时通信、什么是评测闭环

---

## 第一部分：是什么

### 1.1 生活类比：驾校考试系统

你考驾照：
- **科目一**（理论考试）：选择题，有标准答案 → 自动批改
- **科目二**（场地驾驶）：倒车入库、侧方停车 → 传感器自动检测撞线、压线
- **科目三**（道路驾驶）：真实路况 → 考官坐在副驾打分

Agent 评测也是这样：
- **简单题**（分类、提取）：有标准答案 → 自动评分
- **中等题**（推理、编码）：看结果对不对 → 自动判断
- **复杂题**（多步 Agent）：需要人工看轨迹 → 回放分析

AgentEval-Platform 就是 Agent 的"驾校考试系统"——创建考卷（测试集）→ 安排考试（启动评测）→ 自动阅卷（指标分析）→ 复盘讲评（轨迹回放）。

### 1.2 它在 7 个项目中的位置：整合者

```
AgentEval-Platform
    ├── 调用 AgentForge  → 执行 Agent（评测任务）
    ├── 调用 token-core   → 统计 Token 消耗和成本
    ├── 调用 AgentViz     → 渲染轨迹回放
    ├── 通过 mcp-bridge   → Agent 的工具调用被代理
    └── 通过 agent-container-service → 部署运行
```

**AgentEval-Platform 是唯一一个调用其他所有项目的项目**。它是旗舰产品。

### 1.3 前后端分离是什么

| 传统（不分离） | 现代（前后端分离） |
|-------------|----------------|
| 后端直接拼 HTML 返回 | 后端只返回 JSON 数据 |
| 前端就是模板 | 前端是独立应用 |
| 改页面样式要改后端 | 改样式只改前端 |
| 一个团队全栈 | 前端团队 + 后端团队并行开发 |

```
[浏览器] ← HTTP/WebSocket → [后端 API] ← → [数据库]
  React 应用                    FastAPI          PostgreSQL
```

---

## 第二部分：为什么

### 2.1 为什么需要评测平台？Agent 跑一下不就行了吗？

Agent 不是"跑一遍看看对不对"这么简单。真正的 Agent 开发需要：

1. **回归测试**：改了 System Prompt，怎么知道没破坏原来的能力？→ 跑评测
2. **A/B 对比**：两个版本哪个更好？→ 并排对比
3. **成本追踪**：为什么这个月的 API 账单翻了 3 倍？→ Token 分析
4. **根因定位**：Agent 在客户场景失败了，怎么复现？→ 轨迹回放

**评测不是一次性的，是持续迭代的核心流程。**

### 2.2 为什么用 WebSocket 而不是 HTTP 轮询？

评测任务可能需要 10-30 分钟（几百个 test case）。用户想实时看到进度。

| 方案 | 怎么做 | 问题 |
|------|--------|------|
| HTTP 轮询 | 前端每 2 秒发一个请求问"好了没？" | 服务器被大量无效请求打满 |
| WebSocket | 建立一个长连接，后端主动推送 | 只在有更新时发消息，节省资源 |

**类比**：HTTP 轮询 = 你每 5 分钟打电话问快递到哪了，WebSocket = 快递 App 主动推送"你的快递已到驿站"。

### 2.3 为什么用 asyncpg（异步数据库驱动）？

数据库查询通常需要 10-50 毫秒。如果用同步驱动，这 50 毫秒里整个线程都在等数据库，不能处理其他请求。

异步驱动：发请求给数据库 → 不等结果 → 先去处理下一个请求 → 数据库返回结果时再回来处理。

**类比**：同步 = 你站在微波炉前等 3 分钟什么也不做。异步 = 设定时器，3 分钟内去洗菜切菜，响了再回来。

### 2.4 如何实现硬性要求

**高并发**：API 用 FastAPI async/await + uvicorn 多 worker + SQLAlchemy asyncpg 连接池（20+40）。评测任务用 Celery + RabbitMQ 异步队列——创建评测的请求秒级返回，实际执行在后台 Worker 中进行。

**高可用**：无状态 API 服务可启动多个实例。PostgreSQL 读写分离。熔断器——AgentForge 调用失败率 >50% 触发熔断，保护系统不被雪崩。

**可扩展**：Worker 数量可独立扩缩——评测任务多时加 Worker，少时减 Worker。评测器（如何给一个 case 打分）通过接口抽象，新增评测类型不需改核心代码。

**低延迟**：WebSocket 实时推送进度（<500ms）。热点数据 Redis 缓存（TTL=5min）。数据库分页用游标替代 OFFSET（大数据量下更快）。

**安全**：JWT 认证（15 分钟超时）+ RBAC 权限。Pydantic 严格模式校验所有输入。CSP header + React 转义 + DOMPurify 三重 XSS 防护。

---

## 第三部分：怎么做

### 3.1 一次评测的完整流程

```
1. 用户在前端点击"创建评测"
         ↓
2. 前端 POST /api/v1/evaluations → 后端创建评测记录（status=queued）
         ↓
3. Celery Worker 领取任务 → status=running
         ↓
4. Worker 循环处理每个 test case：
    ├── 调用 AgentForge API 执行 Agent
    ├── 收集轨迹数据（steps, tokens, latency, cost）
    ├── 判断答案是否正确（passed=true/false, score）
    ├── Redis Pub/Sub 推送进度："完成 45/100"
    └── 结果写入 PostgreSQL
         ↓
5. 前端通过 WebSocket 实时更新进度条
         ↓
6. 全部完成 → status=completed → 用户可查看结果、轨迹回放、导出报告
```

### 3.2 数据模型设计的"为什么"

| 表 | 为什么需要 | 关键的 JSONB 字段 |
|----|----------|-----------------|
| projects | 多项目隔离 | settings |
| evaluations | 记录每次评测的元信息 | agent_config（Agent 配置） |
| evaluation_results | 每个 test case 的结果 | trajectory（完整推理过程） |
| trajectory_steps | 每步的详细信息 | input/output（LLM 调用的输入输出） |

为什么 trajectory 用 JSONB（PostgreSQL 的 JSON 二进制格式）？因为每个 Agent 的轨迹结构不同（有的 3 步、有的 20 步），传统关系型表无法灵活存储。JSONB 既能灵活存储，又能建索引查询。

---

## 第四部分：面试指南

### Q1: 你的评测平台和 LangSmith（LangChain 的评测工具）有什么区别？

回答结构：先承认竞品的存在和合理性，再说明你的差异化优势。LangSmith 是 LangChain 生态内的工具，只能评测 LangChain 写的 Agent。AgentEval-Platform 是框架无关的——通过 AgentForge 适配层，可以评测任何框架的 Agent。而且我们多了 Context Window 可视化、多模型成本对比、RL 训练数据导出等工程化功能。

### Q2: 你这个系统怎么保证数据一致性？比如评测状态显示 completed 但实际没跑完？

Worker 采用"先执行后确认"模式（task_acks_late=True）——执行成功才从队列中删除任务。如果 Worker 在执行过程中挂了，任务会重新入队，不会丢失。同时评测状态用数据库事务更新，不存在"前台显示成功、后台没存上"的情况。

### Q3: 前端怎么处理接口失败？

全局 axios/fetch 拦截器：401→跳登录页，403→提示无权操作，500→Toast"服务器错误，请重试"。数据加载中→Loading 状态（Skeleton 占位，不是白屏）。数据加载失败→"加载失败"缺省页 + 重试按钮。空数据→"暂无数据"引导页。

### Q4: 如果 100 个用户同时创建评测，系统会怎样？

API 层：FastAPI async 可以同时处理大量请求，数据库连接池（20-40 连接）保证不被撑爆。任务层：Worker 按队列顺序消费，不会因为 100 个任务同时开始而打垮 AgentForge。WebSocket：Redis Pub/Sub 广播，每个用户只收到自己评测的进度。

### Q5: 这个项目最大的技术挑战是什么？

是"把 7 个项目串成一条可验证的流水线"。每个项目单独做都不难，难的是：token-core 的计数结果能被 AgentForge 实时使用、AgentForge 的轨迹能被 AgentViz 无障碍渲染、AgentViz 的组件能在 AgentEval-Platform 中无 bug 集成。这需要统一的数据格式（Trajectory Schema）、清晰的服务契约（API 版本管理）、完善的错误处理（每个项目挂了都有降级策略）。
