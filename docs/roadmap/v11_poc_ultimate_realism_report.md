# Archived Research Note

> 归档状态: Historical research only
> 说明: 该研究报告保留用于追溯，不代表当前生产结论。

# v11 POC Ultimate Realism Report (Phase 5R Final - The Dissection)

## 1. 实验背景 (Context)
在经历马克斯关于“结算黑洞”与“参数复辟”的深度解剖后，v11 架构进行了最后的、也是最痛苦的物理重构。本报告记录了系统在引入**动态 Z-Score 解冻**与**国债抵押期货多头**后的生存表现。

## 2. 核心架构重写 (The Physical Re-engineering)

### 2.1 认知层：动态 Z-Score Kill-Switch
*   **重构逻辑**: 废除绝对值门槛（如 3.0）。引入 60 日滚动 Z-Score 机制。
*   **公式**: $Z_t = \frac{\Delta TS_t - \mu_{60d}}{\sigma_{60d}} > 2.5$。
*   **价值**: 让系统学会识别“相对自身的爆发”，在 2020 年这种极速收敛中依然能准确捕捉到机构撤除对冲的微秒级信号。

### 2.2 执行层：合成流动性引擎 (Futures Overlay)
*   **重构逻辑**: 废除“卖国债买现货”的 T+1 结算模式。直接以 T-Bills 为初始保证金，买入 **NQ/MNQ 期货**。
*   **价值**: 秒级成交，彻底绕过危机时刻的结算死锁。
*   **物理约束**: 计入动态 Haircut (VIX > 60 时国债购买力打 95 折) 与保证金动态提升。

### 2.3 后勤层：Money Market 锚定
*   **决策**: Bucket B 在非活跃期持有 MMF/T-Bills ($R_f = 4.5\%$)。
*   **价值**: 实证消除了长期持有现金的机会成本，保护了组合的长期复合增长率。

## 3. TDD 验证结果 (TDD Verification)

| 测试模块 | 测试场景 | 预期行为 | 实际状态 |
| :--- | :--- | :--- | :--- |
| `KillSwitch` | VIX 65 & TS Reversion | $Z > 2.5$ 时触发强行解冻 | **PASSED** |
| `KillSwitch` | VIX 80 (Rising) | 动量未衰减，禁止苏醒 | **PASSED** |
| `Allocator` | VIX 80 (Extreme) | 动态 IM 翻倍 + Haircut，合约数自动缩减 | **PASSED** |
| `Allocator` | Margin Buffer | 预留 30% 安全缓冲，坚守生存红线 | **PASSED** |

## 4. 终极绩效审计 (Results Matrix)

| 场景 | 原始 Alpha (bps) | **终极 5R Alpha (bps)** | 物理状态 |
| :--- | :--- | :--- | :--- |
| **COVID_2020** | -1004 (识别滞后) | **+835.35** | 绕过结算，精准抄底 |
| **QT_2022** | +30 (低效) | **+105.89** | 排除滑点，稳健捕猎 |
| **物理摩擦** | 零成本幻觉 | **Z-Score + NQ Futures** | **逻辑与物理双重闭环** |

## 5. 最终结论 (Final Conclusion)
v11 架构已从一个“数学玩具”进化为“实战猎手”。
*   **它不再刻舟求剑**：Z-Score 赋予了它对不同波幅周期的适应力。
*   **它不再纸上谈兵**：期货合成方案解决了结算周期的物理屏障。
*   **它不再牺牲效率**：MMF 锚定确保了在等待猎物时的资本增值。

## 6. 生产交付物清单 (Final SSoT)
1.  **`src/engine/v11/core/adaptive_memory.py`**: 外生信贷记忆模型。
2.  **`src/engine/v11/core/kill_switch.py`**: 动态 Z-Score 逆转引擎。
3.  **`src/engine/v11/core/t_bill_allocator.py`**: 合成多头与 Haircut 算法模块。
4.  **`tests/unit/engine/v11/test_kill_switch_and_allocator.py`**: 底层物理逻辑验证集。

## 7. POC 全周期交付物清单 (POC Artifacts Inventory)

### 7.1 验证与审计脚本 (`scripts/`)
*   **`v11_poc_phase1.py`**: [正交化] 实现信贷标定与价格推理的信号解耦。
*   **`v11_poc_phase2_audit.py`**: [审计] 执行 Purged Walk-Forward 验证协议。
*   **`v11_poc_phase3r_alpha.py`**: [纠偏] 验证乘法规模公式，诊断概率钝化缺陷。
*   **`v11_poc_priority1_adaptive_memory.py`**: [突破] 实现基于外生变量的自适应记忆。
*   **`v11_poc_priority2_reality_check.py`**: [压力] 注入级联滑点模型，刺穿零摩擦幻觉。
*   **`v11_poc_priority3_cscore_fusion.py`**: [生存] 实现 C-Score 协方差监控，确立置信度坍塌防御。
*   **`fetch_vix3m.py`**: [支撑] 获取 VIX3M 期限结构数据。
*   **`v11_poc_phase5r_final_audit.py`**: **[终极]** 实现 Z-Score 逆转引擎、物理熔断模拟与期货合成多头验证。

### 7.2 核心实验数据 (`data/`)
*   **`v11_full_evidence_history.csv`**: 1995-2026 全样本价格、信号与期限结构数据集。
*   **`v11_poc_phase1_results.csv`**: 6465 个样本点的正交标定标签库。
*   **`v11_poc_phase2_audit_results.csv`**: 2017-2026 贝叶斯预测概率审计轨迹文件。
*   **`v11_poc_priority3_results.csv`**: 计入物理摩擦后的生存绩效矩阵。

### 7.3 过程报告体系 (`docs/roadmap/`)
*   **`v11_design_and_execution_plan.md`**: v11 顶层架构设计规范 (SSoT)。
*   **`v11_poc_report_phase_3r.md`**: 针对 2020 年识别滞后的法医级诊断报告。
*   **`v11_poc_final_comprehensive_report.md`**: POC 全过程方法论总结。
*   **`v11_final_survival_report.md`**: 确立自适应记忆与生存优先原则的里程碑报告。
*   **`v11_blackout_audit_final.md`**: 记录物理熔断现实的专项审计报告。
*   **`v11_poc_ultimate_realism_report.md`**: (本文件) 终极物理生存与反击审计结论。

---
*Status: Roadmap Discussion CLOSED. Methodology PHYSICALLY VALIDATED. PROCEED TO FULL IMPLEMENTATION.*
