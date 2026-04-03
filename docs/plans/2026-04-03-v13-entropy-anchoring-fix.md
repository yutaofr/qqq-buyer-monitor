# v13.1 架构优化：周期锚定预热与宏观传导权重重构 (2026-04-03)

## 1. 架构基准 (Base Architecture: v13)
遵循分层防御架构，明确 Regime 层（气候/周期）与 Overlay 层（天气/黑天鹅）的职责。

## 2. 优化准则 (Principles: KISS & Anti-Overfit)
1.  **传导权重 (Causal Weighting)**: 基于霍华德·马克斯周期论，按照因子对 QQQ/QLD 的传导路径远近分配权重，严禁通过回测参数寻优。
2.  **增量优先**: 外部注入状态，不侵入核心。
3.  **零过拟合**: 锁定权重矩阵，仅允许贝叶斯计数（Prior Counts）在回放中自然演化。
4.  **物理底线**: 任何情况下的 `target_beta` 物理底线为 0.5。

## 3. 核心修改 (Core Changes)

### A. 周期论权重矩阵 (Cycle-Logic Scoring)
*   **位置**: `src/engine/v11/conductor.py`
*   **算法**: 加权算术平均。
*   **权重矩阵 (Agnostic to Backtest)**:
    *   **Level 1 (2.5x)**: `credit_spread` (信贷周期是周期的原动机)。
    *   **Level 2 (2.0x)**: `net_liquidity`, `real_yield` (折现率决定长久期资产估值)。
    *   **Level 3 (1.5x)**: `treasury_vol` (固定收益市场的流动性前瞻)。
    *   **Level 4 (1.0x)**: `usdjpy`, `copper_gold` (风险偏好代理)。
    *   **Level 5 (0.5x)**: `core_capex`, `breakeven` (滞后性周期现状)。

### B. Beta 参与度底线 (Beta Floor Protection)
*   **逻辑**: 最终 `target_beta` >= 0.5。防止在 QQQ 这种具有长期多头溢价的资产中因模型噪音而彻底空仓。

### C. 2018 深度回放 (Deep Hydration)
*   **逻辑**: 强制回放 2018 至今的完整周期 DNA。
*   **目标**: 构建具有“历史自洽性”的贝叶斯先验，使系统在冷启动首日即具备“老兵”直觉。

## 4. 验证指标 (Validation)
1.  **Entropy Convergence**: 冷启动熵从混沌 (>0.9) 下降到洞察 (<0.3)。
2.  **Cycle Parity**: 2022 年宏观转向识别延迟 < 15 个交易日。
3.  **No Logic Drift**: 预热前后的模型 Hash 值必须完全一致。

---
**签名**: Gemini CLI / Senior Architect (v13.1 Cycle-Engine)
