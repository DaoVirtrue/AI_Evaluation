# CodeSandbox — 多语言代码安全执行沙箱

## 定位
代码评测平台的基石服务。为上层评测系统提供安全、隔离、可限制资源的代码执行环境。

## 核心能力
1. **多语言支持**: Python / JavaScript / Go / Java / C++ / Rust
2. **Docker 容器隔离**: 每次执行使用独立容器，执行完毕立即销毁
3. **安全防护**: 网络隔离、只读文件系统、资源硬限制、危险代码扫描
4. **统一执行接口**: ExecutionSpec 跨语言统一抽象
5. **预热池**: 预启动容器池，消除冷启动延迟（Phase 2）

## API 设计
- `POST /api/v1/execute` — 单次代码执行
- `POST /api/v1/execute/batch` — 批量执行
- `GET /api/v1/runtimes` — 可用运行时列表
- `GET /api/v1/health` — 健康检查

## 安全措施
- Docker `--network=none` 禁止网络
- `--read-only` 只读文件系统 + tmpfs /tmp
- `--memory` / `--cpus` 资源硬限制
- `--security-opt=no-new-privileges` 禁止提权
- 静态代码扫描拦截危险调用
- 超时后 docker kill 进程树
