# AgentViz — Agent 轨迹可视化组件库

---

| 属性 | 值 |
|------|-----|
| 项目类型 | 纯前端：web |
| 前端语言 | TypeScript |
| 后端语言 | 无 |
| 前端框架 | React 18, Canvas API, D3.js, Storybook 8 |
| 后端框架 | 无 |
| 数据库 | 无 |

---

## 1. 项目概述

### 定位
独立的可视化组件库（npm 包），可嵌入 AgentEval-Platform 或任何第三方 Agent 工具。解决核心痛点：**Agent 推理过程是黑盒 → 可视化打开黑盒 → 定位问题 → 优化 Agent**。

### 被依赖关系
| 调用方 | 用途 |
|--------|------|
| AgentEval-Platform | 轨迹回放、Token 图表、对比视图 |
| claude-code-toolkit | VS Code 插件内嵌轨迹预览 |
| 第三方 Agent 工具 | npm 安装 `@agent-viz/react` 直接使用 |

### 依赖项目
| 依赖项目 | 用途 |
|---------|------|
| token-core (WASM) | 浏览器端实时 Token 计数 |

---

## 2. 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      AgentViz (Monorepo)                     │
│                                                             │
│  ┌───────────────────┐  ┌───────────────────┐              │
│  │  @agent-viz/core   │  │ @agent-viz/transform│             │
│  │  (渲染引擎)        │  │ (数据处理层)       │              │
│  │                    │  │                    │              │
│  │ Canvas / SVG 混合  │  │ • 轨迹标准化       │              │
│  │ 虚拟滚动           │  │ • 统计聚合         │              │
│  │ requestAnimation   │  │ • Web Worker       │              │
│  │ LOD (细节层次)     │  │ • Schema 定义      │              │
│  └────────┬──────────┘  └────────┬──────────┘              │
│           │                      │                          │
│           └──────────┬───────────┘                          │
│                      │                                      │
│  ┌───────────────────┴───────────────────┐                  │
│  │          组件层 (8个可视化组件)         │                  │
│  │                                       │                  │
│  │ TrajectoryTimeline  ToolCallGraph     │                  │
│  │ ContextWindowViewer TokenUsageChart   │                  │
│  │ AgentDiffView       ThinkingStreamPlayer│                │
│  │ LatencyWaterfall    ErrorTraceView    │                  │
│  └───────────────────┬───────────────────┘                  │
│                      │                                      │
│  ┌───────────────────┴───────────────────┐                  │
│  │         封装层 (多框架输出)             │                  │
│  │                                       │                  │
│  │ @agent-viz/react    @agent-viz/vanilla│                  │
│  │ (React 18 组件)     (Web Components)  │                  │
│  └───────────────────────────────────────┘                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
     ┌────────▼────────┐           ┌─────────▼────────┐
     │ Storybook 8      │           │ token-core WASM  │
     │ (组件文档/调试)   │           │ (浏览器端Token)  │
     └─────────────────┘           └──────────────────┘
```

---

## 3. 核心业务流程

### 3.1 轨迹数据渲染流程

```
AgentForge → 轨迹 JSON → @agent-viz/transform (标准化)
  │
  │  Web Worker 线程:
  │  ├── 轨迹格式标准化 (多框架统一)
  │  ├── 统计聚合 (按步骤类型/按模型/按Token)
  │  └── token-core WASM 实时 Token 计数
  │
  ▼
  主线程 (React):
  ├── 判断数据量 → <1000步骤 = DOM模式, >1000 = Canvas模式
  ├── 虚拟滚动 (react-window VariableSizeList)
  ├── LOD: 缩放级别 → 调整渲染精度
  └── requestAnimationFrame 增量渲染
```

### 3.2 组件交互关系

```
TrajectoryTimeline ──── 点击步骤 ────▶ ContextWindowViewer (显示该步Context状态)
       │                                    │
       │ 点击ToolCall                       │ Token信息
       ▼                                    ▼
ToolCallGraph (DAG)                 TokenUsageChart (消耗趋势)
       │
       │ 对比两个版本
       ▼
AgentDiffView ──── 差异步骤 ────▶ ErrorTraceView (错误根因)
                                       │
                                       ▼
                               ThinkingStreamPlayer (逐字回放)
```

---

## 4. 技术栈选型

| 层 | 选型 | 理由 |
|----|------|------|
| 框架 | React 18 + TypeScript | 主流、生态好 |
| 构建 | Vite + tsup | 快、支持库模式 |
| 渲染(大量) | Canvas 2D API | DOM 在 1000+ 节点时性能差 |
| 渲染(少量) | SVG + React | SVG 支持交互、React 方便绑定 |
| 图布局 | dagre (DAG) + D3 force | 工具调用依赖图 |
| 虚拟滚动 | react-window | 10w+ 步骤流畅 |
| 数据处理 | Web Worker | 不阻塞主线程 |
| 文档 | Storybook 8 | 组件开发/调试/演示 |
| 发布 | npm | 标准前端包分发 |
| Token计算 | token-core WASM | 浏览器端高性能计数 |

---

## 5. 功能模块设计

| 组件 | 功能 | 渲染模式 | 性能目标 |
|------|------|---------|---------|
| **TrajectoryTimeline** | 推理步骤时间线，展开详情 | DOM(<1000) / Canvas(>1000) | 10w步 60fps |
| **ToolCallGraph** | 工具调用 DAG，失败+重试路径 | SVG + dagre | 500节点流畅 |
| **ContextWindowViewer** | Token 填充进度条(按角色分色)，截断高亮 | DOM | 实时刷新 30fps |
| **TokenUsageChart** | 每步 Token 柱状图 + 累积成本曲线 | Canvas(ECharts) | 1w数据点 |
| **AgentDiffView** | 并排对比 + 差异高亮 + 决策分叉点 | DOM | 对比 2×1w步 <3s |
| **ThinkingStreamPlayer** | 打字机效果 + 速度控制(0.5x-8x) | DOM + CSS动画 | 60fps |
| **LatencyWaterfall** | 步骤延迟瀑布图 + P50/P95/P99 | SVG | 无上限 |
| **ErrorTraceView** | 错误快照 + 调用栈 + 重试序列 | DOM | — |

---

## 6. 数据模型设计

```typescript
// 统一轨迹 Schema (供所有组件消费)
interface TrajectoryStep {
  index: number;
  type: 'llm_call' | 'tool_call' | 'thinking' | 'output' | 'error';
  timestamp: string;
  model?: string;
  
  // LLM Call
  llmInput?: Message[];
  llmOutput?: string;
  
  // Tool Call
  toolName?: string;
  toolInput?: Record<string, unknown>;
  toolOutput?: unknown;
  toolError?: string;
  
  // Token (来自 token-core WASM)
  tokenUsage?: {
    promptTokens: number;
    completionTokens: number;
    thinkingTokens?: number;
    cacheHitTokens?: number;
    cost: number;
  };
  
  latencyMs?: number;
}

// 数据转换层
interface TrajectoryTransformer {
  normalize(input: unknown, source: 'agentforge' | 'langchain' | 'openai'): TrajectoryStep[];
  aggregate(steps: TrajectoryStep[]): TrajectoryStats;
}
```

---

## 7. API 设计

```typescript
// 组件 props 接口（以 TrajectoryTimeline 为例）
interface TrajectoryTimelineProps {
  steps: TrajectoryStep[];
  height?: number;
  width?: number;
  onStepClick?: (step: TrajectoryStep, index: number) => void;
  onStepHover?: (step: TrajectoryStep) => void;
  highlightRange?: [number, number];    // 高亮范围
  renderMode?: 'auto' | 'dom' | 'canvas';
}

// 导出
import { TrajectoryTimeline, TokenUsageChart, ... } from '@agent-viz/react';
import { normalizeTrajectory } from '@agent-viz/transform';
```

---

## 8. 非功能性设计

### 8.1 低延迟

| 机制 | 实现 | 目标 |
|------|------|------|
| Canvas 渲染 | 1000+ 步骤自动切换 Canvas | 10w步 60fps |
| 虚拟滚动 | react-window VariableSizeList, overscan=5 | 可见区域渲染 <16ms |
| Web Worker | 数据转换 + Token 计数 + 聚合 | 主线程 0 阻塞 |
| LOD | 缩放级别 >50% 显示概览, <50% 显示详情 | 低缩放不卡顿 |
| Ring Buffer | 实时数据只保留最近 1w 条 | 内存 <50MB |

### 8.2 高并发（前端多实例）

| 机制 | 实现 |
|------|------|
| 实例隔离 | 每个组件实例独立 Web Worker |
| 共享 Worker | token-core WASM 使用 SharedWorker 单例 |
| 内存管理 | 组件卸载 → Worker terminate → 释放内存 |

### 8.3 可扩展

| 机制 | 实现 |
|------|------|
| 插件化组件 | 每个组件独立 npm 包，按需导入 |
| 数据标准化 | `@agent-viz/transform` 支持自定义 Transformer |
| 多框架输出 | React + Web Components，未来可加 Vue/Svelte |
| 主题系统 | CSS Variables 驱动，可自定义配色 |

### 8.4 高可用

| 机制 | 实现 |
|------|------|
| 错误边界 | React ErrorBoundary 包裹，组件崩溃不影响页面 |
| 降级渲染 | WASM 加载失败 → 退化为 char/4 估算 Token |
| Progressive Enhancement | 不支持 Canvas → 降级为 DOM 渲染 |

### 8.5 安全

| 层级 | 措施 |
|------|------|
| 无 eval | 100% 静态渲染，不使用 `eval()` / `new Function()` |
| CSP 兼容 | 无内联样式/脚本，CSS-in-JS(runtime:false) |
| XSS | DOMPurify 处理轨迹文本后渲染 |
| 依赖安全 | `npm audit` CI 阻断，最小化依赖 |
| 供应链 | npm publish 前完整性检查 |

---

## 9. 项目间依赖

| 依赖项目 | 接口 | 用途 | 降级 |
|---------|------|------|------|
| **token-core** | WASM `count_tokens()` | 浏览器端 Token 计数 | char/4 估算 |
| **token-core** | WASM `estimate_cost()` | 成本估算 | 离线价格表兜底 |

---

## 10. 部署架构

### 开发环境

```yaml
agent-viz:
  deploy: {replicas: 1}
  resources: {limits: {memory: 128M, cpus: '0.2'}}
  command: npx storybook dev -p 6006 --no-open
  profiles: [full]   # 不看组件文档时可关
```

### 生产环境（npm 发布 + CDN）

```
npm publish → @agent-viz/core, @agent-viz/react, @agent-viz/transform
CDN: unpkg / jsDelivr / 自建 CDN
Storybook 静态站点 → GitHub Pages / Vercel
```

---

## 11. 目录结构

```
AgentViz/
├── packages/
│   ├── core/              # @agent-viz/core (Canvas 渲染引擎)
│   ├── react/             # @agent-viz/react (React 封装)
│   ├── vanilla/           # @agent-viz/vanilla (Web Components)
│   └── transform/         # @agent-viz/transform (数据处理)
├── unit_tests/            # 单元测试（Vitest）
├── stories/               # Storybook 示例 + 视觉回归测试
├── run_tests.sh           # 一键执行全部测试
├── package.json           # monorepo root (pnpm workspaces)
├── Dockerfile             # Storybook 部署
└── metadata.json
```

---

## 12. 验证标准

**功能验证：**
- [ ] TrajectoryTimeline: 10w 步骤初始化 <2s, 滚动 60fps
- [ ] ContextWindowViewer: 集成 token-core WASM, Token 计数组件内完成
- [ ] AgentDiffView: 准确标记两次运行的决策分叉点
- [ ] Storybook 8 个组件完整文档 + 交互示例
- [ ] npm publish: `import { TrajectoryTimeline } from '@agent-viz/react'` 可用

**硬性要求验证：**
- [ ] `docker compose up` 启动 Storybook 成功，可访问 :6006
- [ ] `./run_tests.sh` 一键执行，输出 "PASS: X, FAIL: 0, TOTAL: X"
- [ ] 组件渲染测试：每个组件至少 1 个 render test
- [ ] 组件 Props 缺失/错误：不崩溃，渲染 fallback
- [ ] XSS: `<script>alert(1)</script>` 在轨迹文本中不执行
- [ ] Canvas 降级: 不支持 Canvas → 自动切换 DOM 渲染
- [ ] 无 `dangerouslySetInnerHTML` / `eval()` 使用
- [ ] 界面：按钮有 hover/active 态，Storybook 导航流畅

---

## 13. 硬性要求合规方案

### 13.1 一键启动保障
- `docker compose up` 启动 Storybook，无需手动 `npm install`
- 所有依赖在 `package.json` 锁定版本，`pnpm-lock.yaml` 提交到仓库
- 不依赖宿主机的全局 `node_modules` 或绝对路径

### 13.2 测试体系设计
- `unit_tests/` — Vitest + Testing Library（组件渲染、数据转换、Web Worker）
- `stories/` — Storybook 交互测试 + Chromatic 视觉回归（可选）
- `run_tests.sh` 输出汇总：
  ```
  ===========================
  Test Results Summary
  ===========================
  Unit Tests:    PASS  30  FAIL  0
  ===========================
  TOTAL: PASS  30  FAIL  0  SKIP  0
  ===========================
  ```
- 覆盖：正常渲染 / Props 缺失 / 大数据量(10w+) / XSS 数据

### 13.3 错误处理规范
- React ErrorBoundary 包裹每个组件，内部错误不白屏
- Props 类型校验：TypeScript strict mode + PropTypes 运行时警告(dev)
- 数据格式不匹配：`@agent-viz/transform` 返回 `{error: "Invalid format"}` 而非崩溃

### 13.4 日志规范
- 仅 `console.warn`（Props 兼容警告）和 `console.error`（不可恢复错误）
- 禁止 `console.log("111")` 类无意义日志
- 生产构建移除所有 `console.log`

### 13.5 安全基线
- 无 `eval()` / `new Function()` / `dangerouslySetInnerHTML`
- DOMPurify 处理所有用户轨迹文本后渲染
- CSP 兼容：无内联样式/脚本，CSS-in-JS `runtime: false`
- npm publish 前 `npm audit --audit-level=high` 阻断

### 13.6 美观度（纯前端项目）
- UI 框架：TailwindCSS（组件内） + CSS Variables（主题）
- 交互：Canvas hover 高亮、拖拽缩放、键盘导航（←→ 步骤跳转）
- 空状态：`<EmptyState icon={...} title="暂无轨迹数据" />`
- Storybook: 每个组件有 Light/Dark 双主题示例
