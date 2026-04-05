# Archived Research Note

> 归档状态: Historical research only
> 现行生产基线: `docs/versions/v11/v11_bayesian_production_baseline_2026-04-05.md`
> 说明: 本文档描述的是早期设计阶段方案，现已被执行后的生产基线替代。

# v11.0 Design and Execution Plan: The Cognitive Exoskeleton (Retail Edition)

## 1. 核心愿景 (Vision)
v11.0 "Entropy" 旨在构建一个**独裁式的决策外骨骼**。我们拒绝毫秒级交易的幻觉，专注于在 QQQ/QLD/Cash 的受限边界内，通过**迟滞映射算法**屏蔽人性噪音，并利用 **T+1 物理结算锁** 强行同步用户行为与券商物理现实。

---

## 2. 核心双核算子 (Core Signal Engines)

### 2.1 右侧猎杀：Dual-Anchor Kill-Switch
*   **逻辑**: 破解长周期熊市的波动率钝化。
*   **双轨校验**:
    1.  **战术 (20d)**: 捕捉近期斜率突变 ($Z_{fast} > 2.0$)。
    2.  **战略 (252d)**: 锚定年度宏观基线 ($Z_{slow} > 3.0$)。
*   **行为**: 强制苏醒，优先级高于贝叶斯概率，执行一键满仓 QLD。

### 2.2 独裁映射：Hysteresis Exposure Mapper
*   **死区逻辑 (Deadband)**: 
    *   **降级**: $P(BUST) > 0.40$ 时 $QLD \to QQQ$。
    *   **避险**: $P(BUST) > 0.75$ 时 $QQQ \to CASH$。
    *   **恢复**: 必须满足 $P(BUST) < 0.20$ 且经过冷却期。
*   **价值**: 物理阻断临界点上的“反复横跳”，牺牲微小的局部精度换取账户的资产完整性。

---

## 3. 物理层拦截与 UI 状态 (Behavioral Engineering)

### 3.1 结算物理锁 (Settlement Lock)
*   **锁死逻辑**: 任何调仓指令发出后，信号引擎自动进入 **T+1/T+2 锁定状态**。
*   **目的**: 强行对齐散户券商的已结算资金规则，防止 Good Faith Violation，更重要的是**强行冷却用户的调仓冲动**。

### 3.2 独裁 UI 状态机
*   **巡航 (Cruise)**: 绿色。100% QLD。隐藏所有噪音。
*   **装甲 (Shield)**: 黄色。100% QQQ。展示信贷恶化。
*   **物理断网 (Blackout)**: 黑色。100% CASH。隐藏买入按钮，展示“别人正在流血”的数据。
*   **猎杀复苏 (Resurrection)**: 红色闪烁转绿。Kill-Switch 触发。

---

## 4. 交付物列表 (Final Retail Implementation)

### 4.1 核心中枢 (`src/engine/v11/signal/`)
*   **`dual_anchor_kill_switch.py`**: 长短双轨 Z-Score 引擎。
*   **`hysteresis_exposure_mapper.py`**: 独裁状态映射器。
*   **`data_degradation_pipeline.py`**: 极端环境下的脏数据清洗与降级模块。

---
*Architect Review Note: No more futures. No more accounting games. We build the armor for the retail warrior. Ready for the data integrity final boss.*
