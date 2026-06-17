# 07 — agent-container-service：容器化全生命周期运维

> **前置知识**：读完 01-06
> **阅读目标**：理解 Docker、K8s、CI/CD 是什么、为什么需要它们、它们怎么协同工作

---

## 第一部分：是什么

### 1.1 生活类比：把快餐店升级成连锁店

你开了一家快餐店。一开始只有一个店面、一个厨师、一个服务员。你亲自管理一切——这叫做**"单机部署"**。

生意火了，你开了 10 家分店。现在你需要：
- **标准化**：每家店的后厨布局、食材供应商完全一样（= Docker 镜像）
- **调配**：A 店忙不过来时，从 B 店调人手（= 负载均衡）
- **监控**：哪家店出餐慢了、食材快过期了（= Prometheus + Grafana）
- **自动化**：不需要你亲自盯着每家店（= CI/CD 自动部署）

agent-container-service 就是做"连锁店管理"的——它保证 7 个项目在生产环境中稳定运行。

### 1.2 大白话解释

**Docker 是什么？**

Docker 是一个"打包神器"。你的程序需要的所有东西（代码 + Python 运行环境 + 依赖库 + 配置文件）打包成一个"镜像"（Image）。这个镜像可以在任何有 Docker 的机器上运行，**不需要"在我机器上先装 Python 3.12"**。

```
没有 Docker：  "把 Python 3.12 装上，再 pip install 这些依赖，然后设置环境变量..."
有 Docker：    docker compose up -d    ← 一句话搞定
```

**Kubernetes（K8s）是什么？**

Docker 解决了"单个程序怎么跑"的问题。K8s 解决了"100 个程序在 10 台服务器上怎么管"的问题。

K8s 做的事情：
- **自动扩缩**：访问量突然翻倍 → 自动启动更多容器
- **自愈**：某个容器挂了 → 自动重启
- **滚动更新**：更新程序不中断服务 → 先启动新版，等新版 Ready 了再关旧版
- **负载均衡**：自动把请求分配到空闲的容器上

**类比**：Docker = 标准集装箱（让货物可以方便地装车卸车），K8s = 整个港口调度系统（管理几千个集装箱怎么装船、怎么卸船、怎么运输）。

**CI/CD 是什么？**

CI（持续集成）= 每次提交代码，自动跑一遍测试（检查有没有搞坏）
CD（持续部署）= 测试通过后，自动部署到服务器上

```
你写代码 → git push → GitHub Actions 自动：
    1. 跑 lint（代码格式检查）
    2. 跑 test（自动化测试）
    3. Trivy 安全扫描（有没有已知漏洞）
    4. docker build（打包镜像）
    5. docker push（推到镜像仓库）
    6. helm upgrade（部署到 K8s 集群）
```

---

## 第二部分：为什么

### 2.1 为什么需要 Docker？手动部署不行吗？

手动部署的问题（亲历过的都知道）：

| 问题 | 场景 |
|------|------|
| 环境不一致 | "我本地 Python 3.12 能跑啊" → 服务器上是 Python 3.10 → 报错 |
| 依赖冲突 | 项目 A 需要 numpy 1.24，项目 B 需要 numpy 2.0 → 打起来了 |
| 部署时间长 | 每次部署：手动 scp 文件、pip install、改配置 → 半小时 |
| 回滚困难 | 新版出了问题 → 不知道怎么快速回到旧版 |

Docker 解决所有这些问题：**一次打包，到处运行**。

### 2.2 为什么本地开发用 7GB 就够了？

生产环境需要 43GB（多副本、高可用、监控全开），但本地开发只有一台 7GB 的电脑。

**优化策略**：

| 生产 | 开发 | 节省 |
|------|------|------|
| 3 个 API 副本 | 1 个 | 省 66% |
| 5 个 Worker | 1 个（串行执行） | 省 80% |
| Prometheus+Grafana+Loki | 去掉 | 省 3GB |
| PostgreSQL 2GB | 256MB（轻量配置） | 省 87% |
| RabbitMQ 集群 | Redis 做 broker | 省 128MB |

**类比**：生产环境 = 超市营业，所有收银台全开。开发环境 = 超市关门后，只开一个员工通道。

### 2.3 为什么用 Helm 而不是直接用 kubectl？

kubectl 是 K8s 的命令行工具，可以直接 `kubectl apply -f deployment.yaml` 来部署。但问题是：

- 多环境（dev/staging/prod）需要维护多份几乎一样的 YAML → Helm 用 values 文件区分
- 部署时需要知道部署顺序（先部署数据库再部署应用）→ Helm 有 hook 机制
- 需要回滚 → Helm 有一键回滚 `helm rollback`

**类比**：kubectl = 手动拧螺丝，Helm = 电动扳手（更快、更标准、可回退）。

### 2.4 如何实现硬性要求

**高可用**：K8s 的 Deployment 保证指定数量的副本始终在线。Health Probe 三件套：Liveness（还活着吗？挂了自动重启）、Readiness（能接客吗？不能就暂时不给流量）、Startup（启动好了吗？给足启动时间）。滚动更新零停机——先起新 Pod，等它 Ready 了再停旧 Pod。

**可扩展**：HPA（水平自动扩缩容）根据 CPU 使用率自动增减副本。Cluster Autoscaler 在节点不够时自动加机器。

**安全**：Trivy 镜像漏洞扫描——Critical/High 漏洞直接阻断构建。非 root 用户运行容器。只读文件系统（`readOnlyRootFilesystem: true`）。NetworkPolicy 默认拒绝所有流量，只开放必要端口。Secrets 用 Sealed Secrets 加密后入库 Git。

**灾难恢复**：万一服务真的挂了 → Prometheus 检测 → Alertmanager 发送告警通知 → 运维人员处理。Kill 容器 → K8s 自动重启。节点故障 → Pod 调度到其他健康节点。

---

## 第三部分：怎么做

### 3.1 部署流程图

```
开发环境（7GB 电脑）：
  docker compose -f docker-compose.dev.yml up -d → 一行启动全部 7 个项目

测试环境（CI）：
  GitHub Actions 自动：
    → docker compose -f test.yml up -d → 跑 e2e 测试 → docker compose down

生产环境（K8s 集群）：
  helm install agent-platform ./helm-chart -f values-prod.yaml
    → 创建 Deployment、Service、Ingress、HPA、NetworkPolicy...
    → 服务上线，外部用户可访问
```

### 3.2 监控是怎么工作的

```
每个容器暴露 /metrics 端点 （Prometheus 格式）
         ↓
Prometheus 每 15 秒来"拉"一次数据
         ↓
Grafana 从 Prometheus 读数据，画成图表
         ↓
Alertmanager 检测到异常 → 发通知（钉钉/邮件/Slack）
```

**类比**：Prometheus = 体温计（持续测量），Grafana = 体温曲线图（可视化），Alertmanager = 发烧警报器（超过 38℃ 就报警）。

---

## 第四部分：面试指南

### Q1: Docker 和虚拟机有什么区别？

虚拟机虚拟整个操作系统（有独立的内核），启动要几十秒、占几 GB 内存。Docker 只虚拟应用层（共享宿主机的内核），启动秒级、占几十 MB 内存。Docker 更轻量，适合微服务架构。

### Q2: 你的 CI/CD 流水线有哪些步骤？

lint（格式检查）→ test（单元测试）→ security-scan（Trivy 漏洞扫描）→ build（Docker 构建）→ push（推到镜像仓库）→ deploy-staging（部署测试环境）→ e2e-test（端到端测试）→ deploy-prod（生产环境，需人工审批）。

### Q3: 怎么做到零停机部署？

K8s 滚动更新策略：`maxSurge: 1, maxUnavailable: 0`。意思是——先额外启动 1 个新版本 Pod，等它健康检查通过后，再停掉 1 个旧版本 Pod。任何时候都有至少 `replicas` 个 Pod 在线。整个过程中用户无感知。

### Q4: 容器被攻击了怎么办？

第一道防线：Trivy 扫描镜像漏洞（CI 阶段就阻断有漏洞的镜像）。第二道防线：容器非 root 运行 + 只读文件系统（攻击者即使打进容器也无法写入恶意文件）。第三道防线：NetworkPolicy 限制容器能访问的网络范围（比如 token-core 不需要外网就不要给）。第四道防线：即使容器被攻破了，K8s 自动重启一个新的干净容器。

### Q5: 你怎么知道服务出问题了？

Prometheus 持续采集指标（QPS、延迟、错误率、CPU、内存）。Grafana 预设面板让你一眼看出异常。Alertmanager 定义告警规则——比如"错误率超过 5% 持续 5 分钟"就发通知。因为是人都会忽视面板，但告警消息是推送到脸上的。
