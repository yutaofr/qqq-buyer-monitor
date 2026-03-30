# Archived Research Note

> 归档状态: Historical research only
> 现行验收: `docs/roadmap/v11_acceptance_report_2026-03-30.md`
> 说明: 本文档包含 POC 期的实验叙事与假设，不代表当前生产口径。

# v11 POC 综合实验与审计终审报告 (Comprehensive Final Report)

## 1. POC 核心目的 (Purpose)
验证 v11 "Entropy" 概率决策引擎在**非平稳市场（Non-stationary Market）**下的生存与盈利能力。拒绝一切硬编码补丁，通过统计结构自适应实现极端风险下的理性猎杀。

## 2. 核心方法论与逻辑 (Revised for Realism)

### 2.1 贝叶斯不确定性与 C-Score
*   **动态置信度**: 废除“独立性假设”。引入 **C-Score (Correlation Stress Score)** 监控标定层（信贷）与推理层（价格）的实时协方差。
*   **相关性惩罚**: 当全局相关性趋向 1 时（流动性危机），自动膨胀似然函数的方差项，使后验概率收缩，迫使决策回归防御性中值，避免在信心崩溃时过度交易。

### 2.2 结构自适应：自适应半衰期 (Adaptive Memory)
*   **动态遗忘**: 废除固定 5 年 EWMA。半衰期 $\lambda$ 设定为当前波动率的倒函数。在极端动荡期加速遗忘（High Decay），确保系统不被陈旧的历史排名压制；在平稳期拉长记忆，确保统计分布的稳定性。

### 2.3 物理约束：保证金与流动性摩擦
*   **全仓约束**: Bucket B 的部署逻辑受制于全账户实时维持保证金。购买力计算公式：`Available_B = Total_Cash - Bucket_A_Margin_Buffer`。
*   **级联滑点模拟**: 所有回测强制执行 $Slippage = Baseline \times e^{(VIX/20)}$ 指数级成本模型，真实模拟 VIX 80 时的流动性黑洞。

## 3. 交付物与审计表现 (Deliverables & Performance)

### 3.1 审计区间: 1995 - 2026 (7362 样本)
### 3.2 核心场景表现 (The 2020 Marks Audit)
| 策略 | 2020 场景 Alpha | 入场均代价 (Cost) | 逻辑类型 |
| :--- | :--- | :--- | :--- |
| **QQQ VWAP (Benchmark)** | 0 bps | $210.30 | 盲目定投 |
| **v11 POC 4 (进化版)** | **+671.84 bps** | **$196.17** | **贝叶斯概率合成** |
*注：上述 Alpha 尚未计入级联滑点惩罚，待 3.2 待办任务重测。*

## 6. 不足与待办 (Hard-Truth Deficiencies)

### 6.1 逻辑透明度
*   **禁止规则先验**: 彻底删除通过 IF-ELSE 伪装的先验概率。对于极稀疏事件（CAPITULATION），系统必须通过 **Maximum Entropy (最大熵)** 或跨资产代理数据进行推导，而非人工注入。

### 6.2 待办：生存压力测试 (The "Survival" Sprint)
1.  **[Stress-Test]** 重新审计 2020 场景：加入 VIX 指数滑点与全仓保证金封锁模型。
2.  **[Fuser]** 在 `bayesian_fuser.py` 中实现协方差激增时的置信度坍塌逻辑（C-Score）。
3.  **[Engine]** 实现自适应半衰期算子，消除参数过拟合风险。

## 7. 交付物列表 (Deliverables List)

### 7.1 核心决策引擎 (`src/engine/v11/core/`)
*   **`probabilistic_classifier.py`**: 实现基于 EWMA-PCA-KDE 的五状态概率分类器。
*   **`bayesian_fuser.py`**: 执行宏观先验（Prior）与战术似然（Likelihood）的数学融合逻辑。
*   **`prior_modulator.py`**: 实现“先验漂移”算子，对接物理传感器信号。

### 7.2 资金管理层 (`src/engine/v11/allocator/`)
*   **`dual_bucket_sizer.py`**: 物理隔离的桶 A（存量保护）与桶 B（增量猎杀）规模计算。
*   **`risk_aggregator.py`**: 只读汇总模块，计算合并后的 `Combined_VaR` 与总杠杆率。

## 8. POC 全周期交付物清单 (Complete POC Artifacts Inventory)

### 8.1 实验与审计脚本 (`scripts/`)
*   **`v11_poc_phase1.py`**: [基础] 实现正交标定协议与 PCA-KDE 似然模型。
*   **`v11_poc_phase2_audit.py`**: [审计] 执行 Purged Walk-Forward 验证，确立 BUST 识别增益 (+13.15%)。
*   **`v11_poc_phase3r_alpha.py`**: [纠偏] 验证乘法规模公式，诊断概率钝化缺陷。
*   **`v11_poc_priority1_adaptive_memory.py`**: [突破] 实现自适应半衰期逻辑，消除硬编码。
*   **`v11_poc_priority2_reality_check.py`**: [现实] 注入级联滑点模型，刺穿零摩擦幻觉。
*   **`v11_poc_priority3_cscore_fusion.py`**: [生存] 实现 C-Score 协方差监控，确立置信度坍塌防御。
*   **`v11_poc_phase5_blackout_audit.py`**: [终局] 引入物理熔断模拟与资金实存约束，完成生存压力测试。

### 8.2 实证数据集 (`data/`)
*   **`v11_price_vix_history.csv`**: 1995-2026 全样本价格与信号数据集。
*   **`v11_poc_phase1_results.csv`**: 6465 个样本点的正交标定标签库。
*   **`v11_poc_phase2_audit_results.csv`**: 2017-2026 贝叶斯预测概率审计轨迹。
*   **`v11_poc_priority3_results.csv`**: 计入滑点与相关性惩罚后的绩效矩阵。

### 8.3 架构决策与过程报告 (`docs/roadmap/`)
*   **`v11_design_and_execution_plan.md`**: v11 顶层架构设计规范 (SSoT)。
*   **`v11_poc_report_phase_3r.md`**: 针对 2020 年场景识别滞后的诊断报告。
*   **`v11_poc_final_comprehensive_report.md`**: (本文件) POC 全过程总结。
*   **`v11_final_survival_report.md`**: 确立生存优先原则的里程碑报告。
*   **`v11_blackout_audit_final.md`**: 终审报告，记录物理熔断下的 Alpha 真实真相。

---
*Status: POC Inventory Finalized. READY FOR IMPLEMENTATION.*
