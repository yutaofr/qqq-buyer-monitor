# 技术深潜：基于决策状态单子 (Decision State Monad) 的白盒化架构

## 1. 架构动机 (Motivation)
在 v5.0 版本中，系统的聚合逻辑分布在复杂的嵌套 `if-else` 中。这导致了两个主要痛点：
1.  **逻辑黑盒**：很难向用户解释为什么在得分很高的情况下系统依然维持 `WATCH`。
2.  **不可审计**：代码执行路径随内存销毁而丢失，无法复盘架构设计中的“跨层压制”逻辑是否被正确执行。

v6.2 引入了函数式编程中的 **State Monad** 思想，将决策过程转化为透明的、可追溯的流水线。

---

## 2. 核心模式：Decision State Monad (DSM)

### 2.1 Monadic Container: `DecisionContext`
`DecisionContext` 是流水线的核心容器，承载了所有输入、中间状态以及最重要的 `trace` 证据链。

```python
@dataclass(frozen=True)
class DecisionContext:
    # 输入快照
    tier1: Tier1Result
    tier2: Tier2Result
    # 中间状态
    structural_regime: str
    tactical_state: str
    allocation_state: AllocationState
    # 证据链 (The Accumulated State)
    trace: list[dict]
```

### 2.2 流水线步骤 (The Pipeline)
`aggregator.py` 被重构为一系列纯函数步骤，每个步骤的签名均为 `(Context) -> Context`：

1.  **`_step_structural_regime`**: 判定宏观季节。
2.  **`_step_tactical_state`**: 识别战术体感。
3.  **`_step_allocation_policy`**: 执行核心跨层决策。
4.  **`_step_overlay_refinement`**: 应用期权墙二阶约束。
5.  **`_step_finalize`**: 信号定案与特殊逻辑（如 Greedy）覆盖。

---

## 3. 白盒追踪机制 (White-box Tracing)

每一处逻辑分叉都会向 `trace` 中追加一个节点。一个典型的追踪节点如下：

```json
{
    "step": "allocation_policy",
    "decision": "SLOW_ACCUMULATE",
    "reason": "Tactical CAPITULATION capped by RICH_TIGHTENING regime",
    "evidence": {"regime": "RICH_TIGHTENING", "tactical": "CAPITULATION"}
}
```

### 3.1 跨层压制验证 (Constraint Enforcement)
这是架构中最关键的逻辑。通过 `trace`，我们可以证实：
*   如果 `structural_regime == RICH_TIGHTENING`，那么即便 `tactical_state == CAPITULATION`，最终的 `allocation_state` 也必须被截断为 `SLOW_ACCUMULATE`。

---

## 4. 叙事引擎 (The Narrative Engine)

`interpreter.py` 扮演了“状态消费者”的角色。它遍历 `trace`，并根据 `decision` 枚举和 `reason` 话术标签，动态生成面向投资者的解读文本。

*   **状态驱动**：不再依赖正则表达式匹配日志，而是基于严谨的决策状态进行分叉。
*   **诚实性**：确保在防御场景下（如 RISK_CONTAINMENT）给出警告，而非误导。

---

## 5. 持久化与审计 (Persistence)

通过更新 `src/store/db.py` 的序列化逻辑，`logic_trace` 现已随信号结果一同存入 SQLite 的 `json_blob` 字段。这使得我们可以执行以下审计查询：

```sql
-- 查询所有因为宏观压制而“减速”的交易日
SELECT date, json_extract(json_blob, '$.logic_trace') 
FROM signals 
WHERE json_blob LIKE '%capped by%';
```

---

## 6. 总结
v6.2 的重构标志着系统从“单纯的代码实现”转向了“可观测的架构表达”。通过 Monad 模式，我们实现了代码即文档、执行即审计的最高工程标准。
