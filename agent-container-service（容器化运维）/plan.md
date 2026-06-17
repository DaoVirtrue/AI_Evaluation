# agent-container-service — Agent 服务容器化全生命周期运维

---

| 属性 | 值 |
|------|-----|
| 项目类型 | 纯后端：server |
| 前端语言 | 无 |
| 后端语言 | Python, Shell, YAML |
| 前端框架 | 无 |
| 后端框架 | Docker, Kubernetes, Helm, Traefik |
| 数据库 | 无（编排层，不直接使用数据库） |

---

## 1. 项目概述

### 定位
Agent 服务的"基础设施层"。确保 7 个项目能在任何环境运行：本地 Docker Desktop (7GB) → CI 测试 → K8s 生产集群 — 一键部署、自动扩缩、故障自愈、安全合规。

### 被依赖关系
| 调用方 | 用途 |
|--------|------|
| 全部 6 个业务项目 | Docker Compose / K8s Helm 部署编排 |

---

## 2. 系统架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                     agent-container-service                          │
│                                                                     │
│  ┌─────────────────────────┐  ┌─────────────────────────┐          │
│  │   Docker Compose 编排    │  │    K8s Helm Chart        │          │
│  │                         │  │                          │          │
│  │ • full-stack.yml (生产)  │  │ • deployments/          │          │
│  │ • dev.yml (7GB开发机)   │  │ • services/             │          │
│  │ • test.yml (CI)         │  │ • ingress/ (Traefik)    │          │
│  │                         │  │ • hpa/ (自动扩缩)       │          │
│  │ 管理 7 个业务服务 +      │  │ • pdb/ (中断预算)       │          │
│  │ 4 个基础设施 + 监控栈   │  │ • networkpolicy/        │          │
│  └───────────┬─────────────┘  │ • secrets/ (Sealed)     │          │
│              │                └───────────┬─────────────┘          │
│              │                            │                        │
│  ┌───────────▼────────────────────────────▼───────────────────┐    │
│  │                    运维工具集                               │    │
│  │                                                            │    │
│  │  agent-sync     dep-check      health-check               │    │
│  │  (版本同步CLI)   (依赖冲突检测)  (全栈健康检查)              │    │
│  └──────────────────────────┬─────────────────────────────────┘    │
│                             │                                      │
│  ┌──────────────────────────▼─────────────────────────────────┐    │
│  │                    可观测性栈                                │    │
│  │                                                            │    │
│  │  Prometheus ──▶ Grafana ──▶ Alertmanager                  │    │
│  │  (指标采集)     (可视化)     (告警通知)                      │    │
│  │                                                            │    │
│  │  Loki + Promtail ──▶ 结构化日志检索                        │    │
│  └──────────────────────────┬─────────────────────────────────┘    │
│                             │                                      │
│  ┌──────────────────────────▼─────────────────────────────────┐    │
│  │                    安全扫描                                  │    │
│  │  Trivy (镜像漏洞) │ Network Policy Audit │ Secret Leak Detect│    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. 核心业务流程

### 3.1 部署流水线

```
Git Push → GitHub Actions
  │
  ├─ lint (ruff + clippy + eslint)
  ├─ test (pytest + cargo test + npm test)
  ├─ security-scan (bandit + cargo audit + trivy)
  │
  ├─ [main分支] build-and-push:
  │   docker build → trivy image scan → push to GHCR
  │
  ├─ deploy-staging:
  │   helm upgrade --install agent-platform ./helm-chart -f values-staging.yaml
  │
  ├─ e2e-test (playwright / cypress)
  │
  └─ deploy-prod (manual approval):
      helm upgrade --install agent-platform ./helm-chart -f values-prod.yaml
```

### 3.2 本地开发流程

```
开发者 PC (Docker Desktop 7GB)
  │
  ├─ docker compose -f dev.yml up -d        (~2.0GB)
  │   启动: postgres + redis + api + forge + token-core + mcp-bridge + frontend
  │
  ├─ docker compose -f dev.yml --profile full up -d  (~3.2GB)
  │   额外启动: worker + storybook
  │
  └─ docker stats 实时查看内存/CPU
```

---

## 4. 技术栈选型

| 层 | 选型 | 理由 |
|----|------|------|
| 本地编排 | Docker Compose v3.9+ | 简单、声明式、支持 profiles |
| 生产编排 | Kubernetes 1.30+ | 业界标准、自动扩缩 |
| K8s 部署 | Helm 3 + Kustomize | 模板化 + 环境差异 |
| 网关 | Traefik v3 | 自动服务发现、TLS、WAF |
| 监控 | Prometheus + Grafana + Loki | 指标 + 日志 + 可视化 |
| 镜像扫描 | Trivy | 开源、CI 集成、低误报 |
| CI/CD | GitHub Actions | 免费、生态好 |
| Secrets | Docker Secrets / Sealed Secrets | 加密存储、Git 安全 |

---

## 5. 功能模块设计

### 5.1 Docker Compose 编排

| 文件 | 用途 | 内存 |
|------|------|------|
| `docker-compose.full-stack.yml` | 生产级全栈部署（多副本） | ~43GB |
| `docker-compose.dev.yml` | 本地开发（7GB 适配） | ~2.0-3.2GB |
| `docker-compose.test.yml` | CI 测试环境（最小化） | ~1.5GB |

### 5.2 K8s Helm Chart

```
templates/
├── deployments/        # Deployment (7个业务服务 + 4个基础设施)
├── services/           # ClusterIP / LoadBalancer
├── ingress/            # Traefik IngressRoute + TLS
├── hpa/                # 水平自动扩缩 (min=3, max=20, CPU 70%)
├── pdb/                # Pod 中断预算 (maxUnavailable=1)
├── networkpolicy/      # 默认拒绝 + 显式允许
├── secrets/            # Sealed Secrets 加密
├── configmaps/         # 环境配置
└── serviceaccounts/    # RBAC
```

### 5.3 运维 CLI 工具

| 命令 | 功能 |
|------|------|
| `agent-sync check` | 检查所有 Agent 框架版本 |
| `agent-sync upgrade` | 交互式升级框架依赖 |
| `agent-sync lock` | 生成兼容 lock 文件 |
| `dep-check scan` | 扫描 Python/Rust/JS 依赖冲突 |
| `dep-check resolve` | 自动解析兼容版本 |
| `health-check all` | 检查全部服务健康状态 |
| `health-check api` | 仅检查 API 服务 |

### 5.4 可观测性

| 组件 | 功能 |
|------|------|
| Prometheus | 采集各服务指标 (QPS/延迟/错误率/资源) |
| Grafana | 预设 Dashboard（Overview + 各服务详情） |
| Loki + Promtail | 结构化日志收集 + 全文检索 |
| Alertmanager | 服务宕机 / 高错误率 / 资源不足 告警 |

### 5.5 安全扫描

| 工具 | 功能 | 阻断条件 |
|------|------|---------|
| Trivy image scan | 镜像漏洞扫描 | Critical/High → 阻断 |
| Trivy fs scan | 代码仓库漏洞 | Critical/High → 阻断 |
| bandit | Python 安全 lint | High → 阻断 |
| cargo audit | Rust 依赖审计 | 有漏洞 → 阻断 |
| npm audit | JS 依赖审计 | High → 阻断 |

---

## 6. 部署配置示例

### 6.1 开发环境（7GB Docker Desktop）

```yaml
# docker-compose.dev.yml (片段)
services:
  postgres:
    resources: {limits: {memory: 256M, cpus: '0.3'}}
  redis:
    resources: {limits: {memory: 64M, cpus: '0.2'}}
  agent-eval-api:
    deploy: {replicas: 1}
    resources: {limits: {memory: 256M, cpus: '0.5'}}
  agent-forge:
    deploy: {replicas: 1}
    resources: {limits: {memory: 256M, cpus: '0.5'}}
  token-core:
    deploy: {replicas: 1}
    resources: {limits: {memory: 128M, cpus: '1.0'}}  # Rust 省内存
  # 不包含: Prometheus + Grafana + Loki (省 3GB)
  # 不包含: RabbitMQ (Redis 做 broker)
  # 不包含: MinIO (本地文件系统)
```

### 6.2 生产环境（K8s）

```yaml
# helm-chart/values-prod.yaml (片段)
agentForge:
  replicas: 3
  resources:
    requests: {memory: "1Gi", cpu: "1"}
    limits: {memory: "2Gi", cpu: "2"}
  hpa:
    enabled: true
    minReplicas: 3
    maxReplicas: 20
    targetCPU: 70

securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  readOnlyRootFilesystem: true
  capabilities: {drop: ["ALL"]}
```

### 6.3 本地 Docker 容量分布

```
Docker Desktop (7GB Total)
├── Docker Engine 自身  ~1.0-1.5 GB
├── 业务容器 (dev模式)  ~2.0-2.5 GB
│   ├── postgres  256MB
│   ├── redis      64MB
│   ├── api       256MB
│   ├── forge     256MB
│   ├── token     128MB  ← Rust 最省
│   ├── mcp       128MB
│   └── frontend  128MB
├── 可选 (profile full)
│   ├── worker    512MB
│   └── storybook 128MB
└── 剩余可用       ~1.8-3.0 GB
```

---

## 7. 监控面板设计

```
Grafana Dashboards:
├── Overview
│   ├── 各服务 QPS / P50-P99 延迟 / 错误率
│   └── 在线容器数 + 资源使用率
├── AgentForge (详细)
│   ├── 模型调用次数 (按模型) + 延迟分布
│   ├── Token 消耗趋势 + 成本累计 ($/hour)
│   └── 中间件耗时分布
├── Token Core
│   ├── 计数请求 QPS / 平均延迟
│   ├── 截断触发率 / 缓存命中率
│   └── 定价表版本
├── MCP Bridge
│   ├── 工具调用 QPS + 延迟
│   ├── 审计事件计数 + 拒绝调用数
│   └── 沙箱执行次数
├── Infrastructure
│   ├── PostgreSQL: 连接数 / QPS / 慢查询 / 复制延迟
│   ├── Redis: 内存使用 / 命中率 / 连接数
│   └── RabbitMQ: 队列深度 / 消费速率 / 死信队列
└── Alerts
    ├── 服务宕机 >30s
    ├── 错误率 >5%
    ├── P99 延迟 >5s
    └── 磁盘使用 >80%
```

---

## 8. 非功能性设计

### 8.1 高可用（K8s 生产）

| 机制 | 实现 |
|------|------|
| 多副本 | 每个服务 ≥3 副本 |
| Pod 反亲和 | 同服务 Pod 分散到不同节点 |
| 滚动更新 | maxSurge=1, maxUnavailable=0（零停机） |
| Health Probe | liveness(30s) + readiness(10s) + startup(60s) |
| PDB | maxUnavailable: 1（保证至少 2 副本运行） |
| 资源 QoS | requests=limits → Guaranteed 级别 |

### 8.2 可扩展

| 机制 | 实现 |
|------|------|
| HPA | CPU >70% → 自动扩容, <50% → 缩容 (5min 稳定窗口) |
| Cluster Autoscaler | 节点资源不足 → 自动加节点 |
| 读写分离 | PostgreSQL 主从 + PgBouncer 连接池 |

### 8.3 安全

| 层级 | 措施 |
|------|------|
| 镜像 | CI Trivy 扫描, Critical/High → 阻断 |
| 运行时 | 非 root, 只读根文件系统, 丢弃所有 Capabilities |
| 网络 | NetworkPolicy default-deny + 显式白名单 |
| Secrets | Sealed Secrets 加密, Git 安全 |
| 更新 | 滚动更新, 失败自动回滚 |

---

## 9. CI/CD Pipeline

```
Git Push
  │
  ├─ lint (ruff + clippy + eslint)          [并行]
  ├─ test (pytest + cargo test + npm test)   [并行]
  └─ security-scan (bandit + cargo audit + trivy) [并行]
       │
       ▼
  build-and-push (main分支)
       │
       ▼
  deploy-staging (自动)
       │
       ▼
  e2e-test (Playwright)
       │
       ▼
  deploy-prod (手动审批)
```

---

## 10. 目录结构

```
agent-container-service/
├── docker-compose/
│   ├── docker-compose.full-stack.yml    # 生产全栈 (~43GB)
│   ├── docker-compose.dev.yml           # 本地开发 (7GB适配)
│   └── docker-compose.test.yml          # CI 测试 (~1.5GB)
├── k8s/
│   ├── helm-chart/                      # Helm Chart
│   │   ├── Chart.yaml, values*.yaml
│   │   └── templates/                   # K8s 资源模板
│   └── kustomize/                       # 环境差异
├── scripts/                             # 运维 CLI
├── monitoring/
│   ├── prometheus/prometheus.yml
│   ├── grafana/dashboards/
│   ├── loki/promtail-config.yml
│   └── alertmanager/rules.yml
├── security/
│   ├── trivy-scan.sh
│   ├── network-policy-check.sh
│   └── secret-audit.sh
├── .github/workflows/ci-cd.yml
├── secrets/.env.example
└── metadata.json
```

---

## 11. 验证标准

**功能验证：**
- [ ] `docker compose -f dev.yml up -d` 在 7GB 机器成功启动全部 7 个项目
- [ ] `helm install agent-platform ./helm-chart -f values-prod.yaml` 部署到 K8s
- [ ] Kill 任意容器 → Auto Restart (Docker) / 自动重建 (K8s)
- [ ] HPA: CPU >70% → 自动扩容, <50% → 缩容
- [ ] 滚动更新: 新 Pod Ready 后才下线旧 Pod (零停机)

**硬性要求验证：**
- [ ] `docker compose up` 一键启动，无报错、无端口冲突、无依赖缺失
- [ ] `./run_tests.sh` 一键执行，输出 "PASS: X, FAIL: 0, TOTAL: X"
- [ ] Trivy 镜像扫描: 0 Critical / 0 High 漏洞
- [ ] NetworkPolicy: 默认拒绝 + 显式白名单
- [ ] 所有容器非 root 运行、只读根文件系统
- [ ] Secrets 无明文硬编码在 YAML/源码中
- [ ] Grafana: 所有服务指标 + 日志可检索
- [ ] Alertmanager: 服务宕机 <30s 发送通知
- [ ] CI/CD: Push → lint/test/scan → build → deploy → e2e 全自动

---

## 12. 硬性要求合规方案

### 12.1 一键启动保障
- 提供 `docker-compose.dev.yml`（7GB 适配版）和 `docker-compose.full-stack.yml`（生产版）
- 所有服务端口通过 `.env` 文件统一管理
- README 启动命令 `docker compose -f docker-compose.dev.yml up -d` 经实际验证
- 不依赖宿主机文件路径、系统级环境变量

### 12.2 测试体系设计
- `unit_tests/` — Shell 脚本测试（agent-sync, dep-check, health-check）
- `API_tests/` — K8s dry-run 验证（helm template / kustomize build）
- `run_tests.sh` 输出汇总：
  ```
  ===========================
  Test Results Summary
  ===========================
  Shell Tests:   PASS   8  FAIL  0
  K8s Dry-Run:   PASS   7  FAIL  0
  Trivy Scan:    PASS   7  FAIL  0
  ===========================
  TOTAL: PASS  22  FAIL  0  SKIP  0
  ===========================
  ```
- 覆盖：Docker Compose 语法校验 / Helm dry-run / Trivy 扫描 / NetworkPolicy 审计

### 12.3 错误处理规范
- Shell 脚本：`set -euo pipefail`，失败时输出清晰错误信息 + 退出码
- CI Pipeline：任何步骤失败 → 停止 + 输出失败日志
- Helm: `--atomic --timeout 5m`，失败自动回滚

### 12.4 日志规范
- 所有容器日志 → `json-file` driver → Promtail → Loki
- 结构化 JSON 日志：`timestamp`, `level`, `service`, `trace_id`

### 12.5 参数校验
- Helm values.yaml 所有字段有类型定义 + 描述 + 默认值
- `helm lint` 在 CI 中验证

### 12.6 安全基线
- 镜像：CI Trivy 扫描 Critical/High → 阻断构建
- 运行时：非 root、只读根文件系统、丢弃所有 Capabilities
- 网络：NetworkPolicy default-deny + 显式白名单
- Secrets：Sealed Secrets 加密，Git 安全
- 更新：滚动更新，失败自动回滚
