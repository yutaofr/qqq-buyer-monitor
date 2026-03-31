# QQQ "Entropy" 资产配置监控引擎 (v11.5)

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Audit: 27yr Passed](https://img.shields.io/badge/审计-27年全通过-green.svg)](docs/WIKI_V11.md)

**QQQ Entropy** 是一款基于贝叶斯推断的概率决策引擎。它通过对过去 25 年以上宏观记忆的深度学习，自动生成 `目标 Beta` 建议与 `增量资金` 入场节奏，帮助个人投资者在纳斯达克市场波动中实现逻辑化生存。

> “外骨骼不替你走路，但它能让你在风暴中站稳。”

---

## 🧠 核心哲学：贝叶斯决策中枢
v11.5 标志着系统从“基于规则的硬阈值”向“全概率推断”的最终收敛：
*   **即时进化 (JIT)**：每次运行基于最新的宏观 DNA 库 (`macro_historical_dump.csv`) 实时训练高斯朴素贝叶斯模型。
*   **不确定性定价**：通过 Shannon 信息熵量化模型“怀疑度”，当市场处于迷雾区时自动触发敞口削减 (Haircut)。
*   **比特级一致性**：统一的小数化数据契约，确保了从研究回测到生产运行的数值完全对齐。

## 🚀 审计表现 (1999-2026 全量回测)
2026 年 3 月 30 日通过高性能并行审计流水线验证：

| 审计维度 | 核心指标 | 表现值 | 结论 |
| :--- | :--- | :--- | :--- |
| **制度识别** | Top-1 准确率 | **97.04%** | 多轮运行结果比特级一致 |
| **预测保真** | Brier 分数 | **0.0487** | 概率分布高度置信且准确 |
| **推断质量** | 平均信息熵 | **0.052** | 绝大多数时段具备清晰的决策信念 |
| **执行定力** | 结算锁发生率 | **0.2%** | 有效过滤边界噪音，减少无效换手 |

## 🛠 快速开始

### 1. 环境配置
```bash
pip install -e .[dev]
```

### 2. 实时生产运行 (T+0)
获取今日贝叶斯决策建议并同步云端状态：
```bash
python -m src.main
```

### 3. 高性能因果审计
重现 **27 年因果隔离回测**：
```bash
python -m src.backtest --evaluation-start 2018-01-01
```
*审计可视化图表保存在：`artifacts/v11_5_acceptance/`*

## 🏗 系统架构

```mermaid
graph TD
    A[宏观 DNA 库] --> B[标准化特征播种]
    B --> C[JIT 模型训练]
    C --> D[递归贝叶斯更新]
    D --> E[信息熵风险控制器]
    E --> F[制度稳定器]
    F --> G[行为守卫 (结算锁)]
    G --> H[输出: status.json & Discord]
```

## 📂 仓库地图
*   `src/engine/v11/` - 贝叶斯全概率引擎核心实现。
*   `src/models/` - 统一的 V11 数据契约模型。
*   `src/store/` - 云端桥接器 (Vercel Blob) 与持久化层。
*   `scripts/v11_historical_analyzer.py` - 标准化波段分析与复现工具。

---
© 2026 QQQ Entropy 决策系统开发组.
