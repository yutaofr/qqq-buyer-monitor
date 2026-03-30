# Implementation Plan: v11 Entropy (Discrete Exoskeleton)

## 1. 计划综述
本计划严格遵循 v11 SRD 的“独裁式离散状态机”架构。我们将通过 TDD 流程，分阶段实现从数据防毒到独裁映射的完整链路，并同步执行对旧时代“连续优化”模块的物理大扫除。

## 2. 阶段一：架构大扫除 (The Great Purge)
**目标**: 物理删除 `src/engine/` 中所有追求“连续仓位”、“随机优化”或“马科维茨/凯利优化”的遗留逻辑，消除架构精神分裂。

### 待删除/禁用清单：
*   **`src/engine/allocation_search.py`**: 删除所有基于搜索最优 Beta 比例的连续算法。
*   **`src/engine/aggregator.py`**: 剥离多源概率加权逻辑，改为单一外生变量标定。
*   **任何 `Kelly` 相关的仓位缩放公式**: 统一替换为离散的 `[QLD, QQQ, CASH]` 映射。

---

## 3. 阶段二：核心双核实现 (TDD Cycle 1)
**目标**: 实现认知中枢与猎杀算子。

### 任务清单：
1.  **`src/engine/v11/core/adaptive_memory.py`**:
    *   [TEST] 验证信贷利差暴涨时，半衰期是否按指数级坍塌。
    *   [ACT] 实现 `ExogenousMemoryOperator`。
2.  **`src/engine/v11/core/kill_switch.py`**:
    *   [TEST] 注入 2020 年 VIX 期限结构数据，验证 Z-Score 3.0 的触发精度。
    *   [ACT] 实现 `DualAnchorKillSwitch`。

---

## 4. 阶段三：独裁映射与数据装甲 (TDD Cycle 2)
**目标**: 实现行为约束层。

### 任务清单：
1.  **`src/engine/v11/signal/data_degradation_pipeline.py`**:
    *   [TEST] 注入 `NaN` 和幽灵报价，验证 Quality Score 降级。
    *   [ACT] 实现数据防毒面具。
2.  **`src/engine/v11/signal/hysteresis_exposure_mapper.py`**:
    *   [TEST] 模拟 $P(BUST)$ 在 0.4 临界点的震荡，验证“死区”过滤效果。
    *   [TEST] 验证 T+1 结算锁对后续信号的物理拦截。
    *   [ACT] 实现独裁状态机。

---

## 5. 阶段四：2020 熔断高压审计 (Final Proof)
**目标**: 在模拟环境中，让系统经历 VIX 80 的洗礼，验证 AC-1 至 AC-4 的达标情况。

### 验收指标：
*   **不因噪音洗盘**：震荡期的无效指令数 = 0。
*   **不因脏数据崩盘**：数据断流时的信号 = SAFE_BLACKOUT。
*   **精准猎杀**：3-17 确认触发 QLD 满仓指令。

---
*Architect's Note: We are no longer quants; we are cybernetic engineers building a fortress.*
