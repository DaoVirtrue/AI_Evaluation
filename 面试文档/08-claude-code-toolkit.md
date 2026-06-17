# 08 — claude-code-toolkit：AI 编程工具深度集成扩展

> **前置知识**：读完 01-07
> **阅读目标**：理解 IDE 工具扩展、Slash Command、MCP Server、Prompt Engineering 是什么

---

## 第一部分：是什么

### 1.1 生活类比：给工人配好用的电动工具

一个建筑工人，徒手拧螺丝一天能装 50 个。给他一个电动螺丝刀，一天能装 200 个。

claude-code-toolkit 就是给 Agent 开发者配的"电动工具"——不是替代开发者，是让开发者**做同一件事快 5 倍**。

### 1.2 大白话解释

**Slash Command 是什么？**

你在 Claude Code 里输入 `/agent-eval my-config.yaml dataset-001`，Claude Code 自动：读配置 → 调 API 创建评测 → 轮询进度 → 返回结果。

不需要你手动：
- 打开浏览器
- 登录评测平台
- 找到创建评测的页面
- 填表单
- 点提交
- 刷新看进度

**一句话搞定。**

**MCP Server 是什么？**

MCP Server 是一个"能力插件"。装了一个 MCP Server，Claude Code 就能在对话中直接：
- "帮我查一下最近 3 次评测的结果" → eval-server 查数据库返回
- "估算这个 System Prompt 的 Token 数和成本" → token-server 调用 token-core 计算
- "用 Sonnet 4.6 跑一下这个测试" → agent-server 调用 AgentForge

**类比**：MCP Server = 给 Claude Code 装"技能包"。原本只会聊天，装了 eval-server 就会查评测数据了。

**Prompt 模板库是什么？**

写好 Prompt 是一个可复用的技能。模板库里存了 14 个经过验证的结构化 Prompt，覆盖调试、评测、代码生成、安全审计四大场景。拿来即用，不需要从零写。

### 1.3 模块一览

| 模块 | 是什么 | 怎么用 |
|------|--------|--------|
| Slash Commands（5个） | Claude Code 自定义命令 | `/agent-eval`、`/agent-debug` 等 |
| Hooks（3个） | 自动化触发脚本 | 调用危险操作前拦截、成本超预算告警 |
| MCP Servers（3个） | 能力扩展 | 对话中直接查询评测、估算 Token、执行 Agent |
| VS Code 插件 | IDE 集成 | 右键触发评测、选中代码估算 Token |
| Prompt 模板（14个） | 可复用的高质量 Prompt | 复制即用，每个有结构化变量 |

---

## 第二部分：为什么

### 2.1 为什么需要 Slash Command 而不是手动操作？

手动操作一个"创建评测"要：切窗口 → 打开浏览器 → 登录 → 导航 → 填表 → 提交 → 等待 → 查看结果。**单次 2-3 分钟，每天做 10 次就是半小时。**

Slash Command：在 IDE 里打一行字，回车。**5 秒。一天省 25 分钟。**

**这不仅是效率问题，更影响开发者的"心流"**——每切一次窗口，大脑的专注就被打断一次，重新进入需要 15 分钟。

### 2.2 为什么需要 Hook 机制？

Hook 是"在某个操作前后自动执行的动作"。例如：
- **pre-tool-use hook**：在 Claude Code 调用任何工具之前，检查这个操作是否危险
- **post-response hook**：在每次 Claude Code 回复后，自动记录轨迹到评测平台
- **cost-warning hook**：Token 消耗超过预算，终端显示红色警告

**类比**：Hook = 流水线上的质检站。不需要工人主动检查，物料经过自动检测。不符标准的自动拦截。

### 2.3 为什么不把 VS Code 插件的功能直接放在 Claude Code 里？

两种工具解决不同的场景：
- Claude Code（终端）= 你已经在写代码了，不想离开终端
- VS Code 插件 = 你需要图形化界面看轨迹、对比结果

**类比**：Claude Code = 命令行的 ping 命令（快、直接），VS Code 插件 = Wireshark 图形界面（直观、可探索）。

---

## 第三部分：怎么做

### 3.1 Slash Command 的工作流程

```
你输入: /agent-eval configs/my-agent.yaml dataset-001
         ↓
Claude Code 读取 agent-eval.md 中的指令
         ↓
Claude 按指令执行：读取配置文件 → 调 API → 轮询进度 → 格式化输出
         ↓
终端显示：
  ✅ 评测完成: ev-abc123
  📊 通过率: 87%
  💰 总成本: $0.42
  🔗 http://localhost:3000/evaluations/ev-abc123
```

### 3.2 MCP Server 怎么和 Claude Code 通信

MCP Server 通过 stdio（标准输入输出）和 Claude Code 通信。启动 Claude Code 时，它会按照配置启动 MCP Server 进程，然后通过 JSON-RPC 协议发送请求。

**类比**：Claude Code 是你的"老板"，MCP Server 是你新招的"员工"。老板通过内部对讲机（stdio）说"帮我查一下评测结果"，员工查完回复。

---

## 第四部分：面试指南

### Q1: MCP 和传统 API 有什么区别？

传统 API：你需要手动发 HTTP 请求、处理响应、写认证逻辑。MCP：Claude Code 自动发现可用的工具，自动填入合适的参数，自动调用。对用户而言，就是"对话中直接接入了能力"。API 是给人读文档用的，MCP 是给 AI Agent 自动用的。

### Q2: Prompt 模板为什么能提高质量？

好的 Prompt 不是随便写的，它有结构：System（角色定义）→ Context（背景信息）→ Task（具体任务）→ Constraints（约束条件）→ Output Format（输出格式要求）。模板把这种结构固化下来，变量化的部分通过 `$1`、`$2` 填入。这样每次输出的质量和格式都是一致的。

### Q3: 你的 Prompt Engineering 有什么方法论？

三个核心原则：一是分层设计——System、Context、Task 严格分开。二是示例驱动——给 AI 看 2-3 个正确的输入/输出示例，比描述 100 句话更有效。三是约束显式化——不说"不要做 X"，而是说"做 Y，如果遇到 X 情况则做 Z"。

### Q4: Hook 失败了会影响 Claude Code 正常运行吗？

不会。pre-tool-use hook 返回非 0 退出码会阻止工具执行（这是设计目的——拦截危险操作）。post-response 和 cost-warning hook 失败只会输出警告，不影响后续操作。所有 Hook 都有超时限制（5 秒），超时自动跳过。

### Q5: 这个项目为什么放在最后学？

因为它是"锦上添花"的效率工具——没有它，Agent 开发照样能做，只是慢一点。前面 6 个项目是"地基"，这个是"装修"。学完地基再学装修，你才能理解装修为什么要这样做。面试官也更看重地基的扎实程度。
