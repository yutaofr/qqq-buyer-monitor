# QQQ "Entropy" 资产配置监控引擎 (v11.5)

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Audit: 27yr Passed](https://img.shields.io/badge/审计-27年全通过-green.svg)](docs/audit/v11_5_comprehensive_audit_report.md)

**QQQ Entropy** 是一款基于贝叶斯全概率架构的资产配置决策引擎。它通过对过去 25 年以上宏观 DNA 的实时学习，利用信息论模型量化市场不确定性，自动生成 `目标 Beta` 建议与 `增量资金` 入场节奏。

> “外骨骼不替你走路，但它能让你在风暴中站稳。”

---

## 🧠 核心哲学：贝叶斯决策中枢
v11.5 标志着系统从“基于规则的硬阈值”向“全概率推断”的最终收敛：
*   **即时进化 (JIT)**：生产环境不依赖预训练权重，每次运行基于最新的宏观 DNA 库实时训练高斯朴素贝叶斯模型。
*   **不确定性定价**：通过 Shannon 信息熵量化模型“怀疑度”，采用无阈值指数衰减算法自动执行敞口削减 (Haircut)。
*   **数据自愈 (DQP)**：引入**数据质量惩罚机制**，当传感器失效或使用代理数据时自动调增信息熵，实现防御性执行。
*   **特征 DNA 契约**：通过 SHA-256 配置哈希锁定特征工程逻辑，确保研究回测与生产运行的特征契约严格对齐。

## 🚀 审计表现 (2018-2026 全量回测)
通过对 **3,012 个因果隔离窗口** 的全量回归审计验证：

| 审计维度 | 核心指标 | 表现值 | 结论 |
| :--- | :--- | :--- | :--- |
| **制度识别** | Top-1 准确率 | **98.71%** | 每日 Walk-forward 验证下的极高判别力 |
| **预测保真** | Brier 分数 | **0.0225** | 概率分布极其诚实且准确 |
| **推断质量** | 平均信息熵 | **0.046** | 绝大多数时段具备清晰的决策信念 |
| **执行定力** | 结算锁发生率 | **0.4%** | 完美平衡执行灵敏度与换手稳定性 |

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

### 3. 高性能因果审计 (Backtest)
执行严格因果隔离的 **3,000+ 窗口回测**：
```bash
python -m src.backtest --evaluation-start 2018-01-01
```
*详尽审计报告参见：`docs/audit/v11_5_comprehensive_audit_report.md`*

## 🏗 系统架构

```mermaid
graph TD
    A[宏观 DNA 库] -->|JIT 拟合| B[高斯朴素贝叶斯核]
    C[实时观测值] -->|DQP 审计| D[推断矩阵]
    B --> D
    D -->|后验概率| E[信息熵控制器]
    E -->|指数 Haircut| F[连续仓位载荷]
    F -->|惯性赔率屏障| G[行为守卫 (结算锁)]
    G --> H[输出: Web UI & Discord]
```

## 📂 仓库地图
*   `src/engine/v11/` - 贝叶斯全概率引擎核心实现与状态治理。
*   `src/models/` - 统一的 V11 数据契约模型。
*   `src/store/` - 云端同步桥接器与版本化存储层。
*   `docs/audit/` - 正式的架构评审与性能审计档案。

---
© 2026 QQQ Entropy 决策系统开发组.
