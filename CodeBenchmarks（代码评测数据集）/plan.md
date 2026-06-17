# CodeBenchmarks — 代码评测数据集管理

## 定位
代码评测的"题库"层。统一管理和加载各类代码 Benchmark，提供标准化打分能力。

## 核心能力
1. 统一加载器: 一个接口加载 HumanEval/MBPP/LiveCodeBench/自定义数据集
2. pass@k 计算: 严格按照 HumanEval 论文公式实现
3. 测试用例增强: 从标准测试生成更多变体
4. 自建数据集: 支持从 JSONL/CSV/GitHub Repo 导入自定义代码题

## 支持的 Benchmark
- HumanEval: 164 道 Python 函数生成题
- HumanEval+: 80x 增强测试用例
- MBPP: 974 道 Python 编程题
- LiveCodeBench: 实时 LeetCode/Codeforces 竞赛题
- SWE-bench: GitHub issue → PR 修复评测

## pass@k 计算公式
pass@k = 1 - C(n-c, k) / C(n, k)
n = 总采样数
c = 正确样本数
k = 参数
