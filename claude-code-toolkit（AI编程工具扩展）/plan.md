# claude-code-toolkit — AI 编程工具深度集成扩展包

---

| 属性 | 值 |
|------|-----|
| 项目类型 | 全栈：fullstack |
| 前端语言 | TypeScript |
| 后端语言 | Python, TypeScript |
| 前端框架 | VS Code Extension API, React |
| 后端框架 | FastAPI (MCP Server) |
| 数据库 | 无 |

---

## 1. 项目概述

### 定位
面向 Agent 开发者的效率工具集。深度集成 Claude Code / Cursor / VS Code，将 Agent 开发→调试→评测→部署的反馈循环从"分钟级"缩短到"秒级"。

### 依赖项目
| 依赖项目 | 用途 | 调用方式 |
|---------|------|---------|
| AgentEval-Platform | 评测触发 + 结果查询 | HTTP API |
| AgentForge | IDE 内执行 Agent | HTTP API |
| token-core | Token 估算 MCP Server 数据源 | HTTP API |
| mcp-bridge | MCP Server 注册 | JSON-RPC (stdio) |

---

## 2. 系统架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                     claude-code-toolkit                             │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                   Claude Code 集成                             │ │
│  │                                                               │ │
│  │  CLAUDE.md    Slash Commands    Hooks          MCP Servers    │ │
│  │  (项目指令)    /agent-eval       pre-tool-use   eval-server   │ │
│  │               /agent-debug      post-response   token-server  │ │
│  │               /trajectory       cost-warning    agent-server  │ │
│  │               /deploy-agent                                    │ │
│  └───────────────────────────┬───────────────────────────────────┘ │
│                              │                                     │
│  ┌───────────────────────────▼───────────────────────────────────┐ │
│  │                   VS Code 扩展                                 │ │
│  │                                                               │ │
│  │  Commands              Views              Providers           │ │
│  │  runEvaluation         AgentDashboard     TrajectoryPreview   │ │
│  │  estimateTokens        CostMonitor        (Custom Editor)     │ │
│  └───────────────────────────┬───────────────────────────────────┘ │
│                              │                                     │
│  ┌───────────────────────────▼───────────────────────────────────┐ │
│  │              结构化 Prompt 模板库                               │ │
│  │                                                               │ │
│  │  agent-debugging/    eval-design/    code-generation/         │ │
│  │  (调试场景)           (评测设计)      (代码生成)                │ │
│  │                                                               │ │
│  │  security-audit/     cost-optimization/                       │ │
│  │  (安全检查)           (成本优化)                                │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│AgentEval API │    │ AgentForge   │    │  token-core  │
│:8000         │    │ :8001        │    │  :8003       │
└──────────────┘    └──────────────┘    └──────────────┘
```

---

## 3. 核心业务流程

### 3.1 /agent-eval 命令执行流程

```
开发者: /agent-eval configs/my-agent.yaml dataset-001
  │
  ▼
Claude Code 读取 agent-eval.md 指令
  │
  ├─ 1. 读取 agent 配置文件
  ├─ 2. POST AgentEval-Platform API 创建评测
  │     → {evaluation_id: "ev-123"}
  ├─ 3. 轮询进度 (每 5s)
  │     或 WebSocket 推送
  ├─ 4. 评测完成 → 获取结果
  │     → {pass_rate: 87%, avg_latency: 1.2s, total_cost: $0.42}
  └─ 5. 格式化输出:
       ✅ 评测完成: ev-123
       📊 通过率: 87% (87/100)
       ⏱️ 平均延迟: 1.2s
       💰 总成本: $0.42
       🔗 轨迹: http://localhost:3000/evaluations/ev-123
```

### 3.2 成本预警 Hook 流程

```
每次 Claude Code 响应后 → post-response.sh
  │
  ├─ 获取当前会话 Token 使用量
  ├─ 调用 token-core API 估算成本
  ├─ 与预算阈值比较 ($5/会话)
  └─ 超限 → 终端红色警告:
       💰 成本警告: 当前会话 $6.23 (预算 $5.00)
       建议: /token-estimate 查看详情
```

---

## 4. 技术栈选型

| 层 | 选型 |
|----|------|
| Claude Code 扩展 | Markdown Slash Commands + Shell Hooks + Python MCP Server |
| VS Code 扩展 | TypeScript + VS Code Extension API |
| MCP Server | Python 3.12 + FastAPI (FastMCP) |
| CLI 工具 | Python + Click/Typer |
| 文档 | Markdown + YAML Frontmatter |

---

## 5. 功能模块设计

### 5.1 Claude Code Slash Commands

| 命令 | 功能 | 调用的项目 |
|------|------|-----------|
| `/agent-eval` | 一键创建并运行评测 | AgentEval-Platform |
| `/agent-debug` | 交互式调试失败的 Agent case | AgentEval-Platform |
| `/trajectory` | 查看指定评测的轨迹 | AgentEval-Platform |
| `/token-estimate` | 估算选中代码/配置的 Token | token-core |
| `/deploy-agent` | 一键部署 Agent 到 K8s | agent-container-service |
| `/agent-security` | 审计 Agent 安全性 | — |

### 5.2 Claude Code Hooks

| Hook | 触发时机 | 功能 |
|------|---------|------|
| `pre-tool-use.sh` | 工具调用前 | 拦截危险操作 (rm, drop, delete) → 需确认 |
| `post-response.sh` | 每次响应后 | 自动记录轨迹到 AgentEval-Platform |
| `cost-warning.sh` | 会话 Token 变化 | 超预算 → 终端红色警告 |

### 5.3 MCP Server 三件套

| Server | 提供的能力 | 调用的项目 |
|--------|----------|-----------|
| **eval-server** | `query_eval`, `compare_versions`, `list_datasets`, `get_report` | AgentEval-Platform |
| **token-server** | `estimate_tokens`, `estimate_cost`, `compare_models`, `optimize_prompt` | token-core |
| **agent-server** | `run_agent`, `debug_agent`, `list_models` | AgentForge |

### 5.4 VS Code 扩展

| 功能 | 说明 |
|------|------|
| `Run Evaluation` | 右键 YAML/JSON → 触发评测 |
| `Estimate Tokens` | 选中代码/文本 → 显示 Token 估算 + 成本 |
| `Agent Dashboard` | 侧栏: 最近评测列表 + Agent 状态 |
| `Cost Monitor` | 底部状态栏: 今日 Token 消耗 / 成本 |
| `Trajectory Preview` | 内联轨迹可视化 (集成 AgentViz) |

### 5.5 Prompt 模板库（5 个场景 14 个模板）

| 场景 | 模板数 | 示例模板 |
|------|--------|---------|
| agent-debugging | 3 | root-cause, tool-error, context-overflow |
| eval-design | 3 | test-case-gen, edge-case-discover, eval-metrics |
| code-generation | 3 | new-agent, add-tool, refactor-agent |
| security-audit | 3 | tool-sandbox, prompt-injection, data-leak |
| cost-optimization | 2 | model-selection, prompt-compress |

每个模板包含：场景描述、输入变量（`$1`, `$2`）、结构化的 System/User Prompt、期望输出格式。

---

## 6. Slash Command 模板设计示例

```markdown
---
description: Run agent evaluation against a test dataset
argument-hint: <agent-config-path> <dataset-id>
---

## Task
Run an agent evaluation using the AgentEval-Platform.

## Steps
1. Read the agent config from `$1`
2. Call the API:
   POST http://localhost:8000/api/v1/evaluations
   Body: {"agent_config": <config_content>, "dataset_id": "$2"}
3. Poll GET /api/v1/evaluations/{id}/status every 5s until done
4. Fetch results from GET /api/v1/evaluations/{id}/metrics
5. Output a summary with pass rate, latency, cost, and trajectory link
```

---

## 7. 非功能性设计

### 7.1 低延迟

| 场景 | 目标 |
|------|------|
| `/token-estimate` 返回 | <2s |
| `/agent-eval` 创建评测 | <5s + 等待评测完成 |
| VS Code Token 估算 | <500ms (调用 token-core WASM) |
| MCP Server 响应 | <1s |

### 7.2 高可用

| 机制 | 实现 |
|------|------|
| 降级 | 后端 API 不可用时，Slash Command 返回友好错误 + 手动操作指引 |
| MCP Server 重启 | stdio transport 断开 → Claude Code 自动重连 |

### 7.3 安全

| 层级 | 措施 |
|------|------|
| Hook 安全确认 | `pre-tool-use.sh` 拦截危险命令 → 交互式确认 |
| MCP Server 权限 | 仅读取/查询，不执行破坏性操作 |
| API Key | 通过环境变量/Secrets 注入，不硬编码在模板中 |
| 文件访问 | VS Code 扩展仅访问当前工作区 |

---

## 8. 项目间依赖

| 依赖项目 | 接口 | 用途 | 降级 |
|---------|------|------|------|
| AgentEval-Platform | `POST :8000/api/v1/evaluations` | 创建评测 | 返回"服务不可用，请手动操作" |
| AgentForge | `POST :8001/api/v1/agents/run` | 执行 Agent | 同上 |
| token-core | `POST :8003/api/v1/count` | Token 估算 | 使用本地 char/4 估算 |
| mcp-bridge | JSON-RPC (stdio) | MCP Server 注册 | — |

---

## 9. 部署架构

无需独立部署容器。本项目的产物是：
- **Claude Code**: 复制 commands/hooks/mcp-servers 到项目的 `.claude/` 目录
- **VS Code 扩展**: 通过 VS Code Marketplace / `.vsix` 安装
- **Prompt 模板**: 直接复制 `prompts/` 文件到对应项目中使用

```
安装方式:
```bash
# Claude Code 集成
cp -r claude-code-toolkit/claude-code/* .claude/

# VS Code 扩展
code --install-extension agent-toolkit.vsix

# Prompt 模板 (按需复制)
cp prompts/agent-debugging/root-cause.md my-project/prompts/
```

---

## 10. 目录结构

```
claude-code-toolkit/
├── claude-code/
│   ├── CLAUDE.md                  # 项目级 AI 指令
│   ├── settings.json             # Claude Code 配置
│   ├── commands/                 # Slash Commands (6个)
│   ├── hooks/                    # Shell Hooks (3个)
│   └── mcp-servers/              # MCP Server (3个)
├── vscode-extension/
│   ├── src/
│   │   ├── extension.ts
│   │   ├── providers/            # TrajectoryPreviewProvider
│   │   ├── commands/             # runEvaluation, estimateTokens
│   │   └── views/                # AgentDashboard, CostMonitor
│   └── package.json
├── prompts/                      # 结构化 Prompt 模板 (14个)
│   ├── agent-debugging/
│   ├── eval-design/
│   ├── code-generation/
│   ├── security-audit/
│   └── cost-optimization/
├── docs/                         # 使用指南
│   ├── prompt-engineering-guide.md
│   ├── model-selection-guide.md
│   └── agent-development-workflow.md
└── metadata.json
```

---

## 11. 验证标准

**功能验证：**
- [ ] `/agent-eval` → 创建评测 → 返回结果 + 轨迹链接
- [ ] `/agent-debug` → 加载失败 case → 定位根因 → 建议修复
- [ ] `pre-tool-use.sh` → `rm -rf` 被拦截 → 需 Y/N 确认
- [ ] `cost-warning.sh` → Token 超 $5 → 终端红色警告

**硬性要求验证：**
- [ ] `./run_tests.sh` 一键执行，输出 "PASS: X, FAIL: 0, TOTAL: X"
- [ ] MCP eval-server → 正常查询返回 JSON 结果
- [ ] MCP token-server → 估算 Token → 返回成本 + 模型对比
- [ ] MCP agent-server → 调用 AgentForge → 返回 Agent 执行结果
- [ ] VS Code: 右键"Run Evaluation" → 调用 AgentEval API → 成功创建评测
- [ ] VS Code: 选中代码 → "Estimate Tokens" → 显示 Token数 + 成本
- [ ] Slash Command 模板：每个含结构化变量 + 输出格式，可独立使用
- [ ] Prompt 工程指南：含分层设计 / 示例驱动 / 约束显式化 / 调试模式

---

## 12. 硬性要求合规方案

### 12.1 一键可用保障
- Claude Code：复制 `claude-code/` 到项目 `.claude/` 目录即生效
- VS Code：`code --install-extension agent-toolkit.vsix` 安装
- MCP Server：`pip install -e .` 或 docker compose 启动
- 不依赖特定 IDE 版本以外的全局配置

### 12.2 测试体系设计
- `unit_tests/` — pytest（MCP Server 测试）
- `API_tests/` — VS Code 扩展 E2E 测试（@vscode/test-electron）
- `run_tests.sh` 输出汇总：
  ```
  ===========================
  Test Results Summary
  ===========================
  MCP Server:    PASS   9  FAIL  0
  VS Code E2E:   PASS   5  FAIL  0
  Hook Tests:    PASS   3  FAIL  0
  ===========================
  TOTAL: PASS  17  FAIL  0  SKIP  0
  ===========================
  ```
- 覆盖：MCP Server 方法调用 / VS Code 命令执行 / Hook 拦截逻辑

### 12.3 错误处理规范
- MCP Server：JSON-RPC 标准错误响应
- Slash Command：后端 API 不可用时 → 友好提示 "AgentEval 服务不可用，请手动操作"
- VS Code：API 调用失败 → `vscode.window.showErrorMessage` 提示

### 12.4 日志规范
- MCP Server：`structlog` 结构化 JSON
- VS Code：OutputChannel 独立日志面板
- Hooks：stdout/stderr 重定向到 Claude Code 日志

### 12.5 参数校验
- Slash Command 模板：`argument-hint` 定义必填参数
- MCP Server：JSON Schema 验证工具参数
- VS Code 命令：运行时检查上下文（是否有活动编辑器、是否选中文本）

### 12.6 安全基线
- `pre-tool-use.sh`：白名单 + 黑名单双重过滤（rm/drop/delete/curl外连 → 需确认）
- MCP Server：只读查询，不执行破坏性操作
- API Key：环境变量/Secrets 注入，不硬编码在模板中
- VS Code 扩展：仅访问当前工作区文件

### 12.7 美观度（全栈项目 — VS Code 插件）
- Sidebar 面板：TreeView + 图标 + Badge 计数
- 命令面板：所有命令有 `Agent Toolkit:` 前缀
- 内联预览：Webview 加载 AgentViz 组件，暗黑主题匹配 VS Code
