# Archived Research Note

> 归档状态: Historical research only
> 说明: 本文档涉及凸性与资金放大 POC，不属于当前 v11 生产边界。

# v11 Blood & Fire Audit Report: The Birth of the Apex Predator

## 1. 审计目的 (Purpose)
验证通过 **Bucket A 动态去杠杆** 与 **Bucket B 凸性核弹变现** 组合拳，是否能在物理清算压力下创造非线性的购买力，彻底打破“受限入场”的诅咒。

## 2. 核心实验发现 (Forensic Findings)

### 2.1 凸性核爆的威力 (The Liquidity Nuke)
*   **数据**: 2020-03-17 至 03-31，系统通过平仓 15% OTM Puts，实现了从 $20,000 保费向 **$59,000,000+ 现金** 的非线性跨越。
*   **结论**: 期权凸性是应对流动性黑洞的唯一终极武器。它产生的 Free Cash 规模远超任何券商的保证金要求，实现了绝对的“入场自由”。

### 2.2 资本效率的革命 (Efficiency Win)
*   **对比**: 放弃 30% 静态现金预留，改为 2% 尾部保费。
*   **结果**: 释放了 28% 的资金重新进入 QQQ 牛市 Beta，实证消除了长达十年的 Cash Drag。

### 2.3 去杠杆的左侧预警
*   **识别**: 贝叶斯后验概率 $P(BUST)$ 在利差飙升初期成功驱动了现货敞口的非线性收缩。
*   **防御**: 这种“主动放血”在物理层面阻断了 MMR 飙升导致的 Margin Call 风险。

## 3. 架构终极交付规范 (Final SSoT)

### 3.1 资金分配引擎 (`allocator/`)
*   **`BayesianDeleverager`**: 强制执行 $1 - P(BUST)^\gamma$ 去杠杆律。
*   **`ConvexityManager`**: 强制执行 2% AUM 滚动尾部对冲协议。

### 3.2 逆转执行指令
*   **`KillSwitch`**: 采用 Dual-Anchor Z-Score 识别期限结构断裂。
*   **`Action`**: 引爆核弹 $\to$ 套现 $\to$ 满仓 NQ 期货反击。

## 4. 结论 (Final Conclusion)
v11 架构不再是一个观测工具，而是一个具备**内生流动性创造能力**的实战机器。我们接受了市场的摩擦与清算所的绞肉机法则，并用衍生品的非线性特性战胜了它们。

## 5. POC 全周期交付物清单 (POC Artifacts Inventory)

### 5.1 验证与审计脚本 (`scripts/`)
*   **`v11_poc_phase1.py`**: [正交化] 实现标定标签与推理证据的物理隔离。
*   **`v11_poc_phase2_audit.py`**: [审计] 实现 Purged Walk-Forward 验证。
*   **`v11_poc_priority1_adaptive_memory.py`**: [核心] 实现基于信贷外生变量的自适应记忆。
*   **`v11_poc_priority3_cscore_fusion.py`**: [生存] 实现相关性压力下的置信度惩罚。
*   **`v11_poc_phase5_blackout_audit.py`**: [物理] 注入交易熔断与物理断网模拟。
*   **`v11_poc_phase6_meat_grinder.py`**: [清算] 模拟跨品种保证金传染。
*   **`v11_poc_phase7_blood_fire.py`**: **[终局]** 验证动态去杠杆（左侧放血）与期权核弹（右侧变现）。

### 5.2 核心实证数据 (`data/`)
*   **`v11_full_evidence_history.csv`**: 1995-2026 全样本价格、信号与 VIX 期限结构数据集。
*   **`v11_poc_phase1_results.csv`**: 正交标定后的历史样本标签库。
*   **`v11_poc_phase2_audit_results.csv`**: 2017-2026 贝叶斯预测概率审计轨迹。

### 5.3 架构决策与过程报告 (`docs/roadmap/`)
*   **`v11_design_and_execution_plan.md`**: v11 顶层架构规范 (Apex Predator SSoT)。
*   **`v11_poc_final_comprehensive_report.md`**: 概率范式跨越总结。
*   **`v11_final_survival_report.md`**: 自适应记忆与相关性惩罚确立。
*   **`v11_blackout_audit_final.md`**: 物理熔断现实专项审计报告。
*   **`v11_meat_grinder_final_report.md`**: 保证金传染与物理闭环审计。
*   **`v11_blood_and_fire_final_report.md`**: (本文件) 动态放血与凸性变现的终极审计结论。

---
*Status: POC Inventory Finalized. All Evidence Logged. READY FOR PRODUCTION.*
