# V12.0 架构优化计划：高熵修复与历史锚定预热 (2026-04-03)

## 1. 执行摘要 (Executive Summary)
针对 V12.0 系统冷启动阶段出现的“虚高熵（False High Entropy）”及“贝叶斯迷失”现象，本计划通过引入 **2018 锚定深度预热（Deep Hydration）** 及 **自适应质量得分算法**，将系统状态从随机混沌提升至具有 8 年历史自洽性的稳健决策态。同时，明确划定 **Regime (宏观周期)** 与 **Overlay (瞬时尾部)** 的防御职责。

## 2. 核心问题诊断 (Root Cause Analysis)
1.  **先验缺失 (Prior Vacuum)**：冷启动时系统处于均匀分布状态（Max Entropy），受限于 0.15 的固定动量锁定，收敛极慢。
2.  **质量惩罚过载 (Quality Penalty Overload)**：当前的调和平均算法（Harmonic Mean）对单一因子缺失过于敏感（10 因子中缺 1，总分即崩塌至 <0.1），导致有效熵虚高。
3.  **职责混淆 (Responsibility Overlap)**：Regime 层过度追求对黑天鹅的同步反应，导致宏观特征的正交化基准在波动期产生漂移。

## 3. 架构优化方案 (Architectural Solutions)

### A. 历史锚定预热 (Deep Hydration)
*   **强制逻辑**：系统启动时，若检测到 `PriorKnowledgeBase` 计数少于 1000（约 4 年数据），强制执行从 **2018-01-01** 起的历史回放模式。
*   **目标**：通过 2018 至今的 2000+ 个交易日迭代，构建包含“2018 缩表、2020 熔断、2022 转向”的强自洽转移矩阵（Transition Matrix）。
*   **代码实现**：引入 `src/engine/v11/prior_hydrator.py` 负责序列化预热。

### B. 质量得分重构 (Adaptive Quality Scoring)
*   **算法变更**：从调和平均数转向 **加权几何平均数 (Weighted Geometric Mean)**。
*   **核心逻辑**：
    *   核心因子（Credit Spread, Net Liquidity）拥有高权重。
    *   允许次要因子（Copper/Gold, Core Capex）在冷启动时存在短期缺失而不导致全局熔断。
*   **公式**：$Q_{score} = \prod (q_i)^{w_i / \sum w_i}$

### C. 分层防御体系 (Layered Defense Strategy)
*   **Regime 层 (气候)**：锚定结构性宏观周期（如 2022 年加息周期、科技 Capex 周期）。要求：**低频、高确定性、贝叶斯收敛**。
*   **Overlay 层 (天气)**：锚定黑天鹅及地缘政治波动。要求：**高频、瞬时、基于宽度压力 (Breadth Stress) 与量价背离**。
*   **桥接逻辑**：Regime 负责 Beta 基准，Overlay 负责 Beta 的瞬时 Haircut（0.65x 截断）。

## 4. 实施路径 (Implementation Roadmap)

1.  **Patch-01**: 修改 `src/engine/v11/conductor.py`，将 `quality_score` 改为几何平均，消除虚假高熵。
2.  **Patch-02**: 实现 `prior_hydrator.py`，并在 `V11Conductor` 初始化中注入预热流程。
3.  **Patch-03**: 引入自适应贝叶斯学习率 $m = \max(0.15, 0.5 \times e^{-N/100})$。

## 5. 验证协议 (Validation Protocol)
*   **回归测试**：运行 `scripts/run_v13_cold_warm_start.py`。
*   **验收标准 (AC-12)**：
    *   冷启动与热启动的 **Entropy Delta < 0.05**。
    *   2022 年 Q1 宏观转向的 Regime 识别延迟 **< 15 个交易日**。
    *   2020 年 3 月黑天鹅期间，Regime 可维持 `RECOVERY` 或 `MID`，但 `Overlay` 必须触发 `NEGATIVE_ONLY` 保护。

---
**架构师签名**: Gemini CLI / Senior Architect
**日期**: 2026-04-03
