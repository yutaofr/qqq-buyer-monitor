# V11.5 核心开发指南 (Developer Guide)

本指南面向 QQQ Monitor 的核心开发者，旨在详细说明如何维护、扩展和审计贝叶斯全概率引擎。

---

## 1. 特征工程 (Feature Engineering)

系统的特征播种由 `ProbabilitySeeder` 负责。

*   **新增特征流程**：
    1.  在 `src/collector/` 中实现新的采集逻辑。
    2.  在 `src/research/historical_macro_builder.py` 中将新指标整合进 DNA 库。
    3.  **关键**：确保新指标在 CSV 中采用 **小数归一化** 单位（AC-2）。
    4.  在 `ProbabilitySeeder.generate_features` 中实现**因果自校准标准化**，严禁人工 anchor 或离散阈值。
*   **注意事项**：避免引入具有强烈前瞻性（Look-ahead）的特征。

## 2. 似然标定与 JIT 训练 (Likelihood & Training)

系统不再使用静态模型，而是通过 `V11Conductor` 执行 **GaussianNB JIT 训练**。

*   **模型参数**：`GaussianNB(var_smoothing=1e-2)`。增加平滑度是为了防止在某些极端制度（如 CAPITULATION）样本量过少时导致概率坍塌。
*   **基准标签**：由 `data/v11_poc_phase1_results.csv` 提供。这是系统的“老师”，定义了历史上哪些时段属于哪种制度。

## 3. 风险逻辑调试 (Debugging Inference)

当系统输出意外的 Beta 或 Regime 时，应按以下顺序排查：

1.  **特征向量审计**：运行 `scripts/diagnostic_v11_model.py`。它会输出当前特征相对于模型均值的 Z-score 和概率密度。
2.  **熵值溯源**：检查 `SignalResult.logic_trace`。查看是否存在多种制度概率接近的情况，导致 `EntropyController` 触发了大比例 Haircut。
3.  **先验干扰**：检查 `v11_prior_state.json`。确认是否是由于前一笔交易的强惯性阻碍了制度切换。

## 4. 回测审计标准 (Audit Protocol)

任何核心算法的变更，必须通过 `src.backtest` 的全样本审计。

*   **通过准则**：
    *   **Accuracy > 95%** (对齐基准标签)。
    *   **Brier Score < 0.06** (概率质量可靠)。
    *   **Bit-identical Parity**：连续运行三次回测，结果必须完全一致。
*   **实现约束**：回测必须是 walk-forward daily re-fit，不允许一次静态 train/test 代替生产同构审计。

## 5. 云端同步开发

由于 GHA 是无状态的，本地开发时请务必注意：
*   **禁止物理修改 `prod/` 数据**。
*   进行云端测试时，修改 `CloudPersistenceBridge` 的 `branch` 为你的 feature 分支名，确保同步至 `staging/`。
*   **禁止在生产/审计主路径引入 synthetic baseline**；若 canonical DNA 缺失，应直接修复数据，而不是让代码偷偷补世界观。

---
© 2026 QQQ Entropy 技术委员会.
