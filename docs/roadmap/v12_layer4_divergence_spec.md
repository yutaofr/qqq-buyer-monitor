# v12.0 Layer 4: 量价背离战术监控规格书 (Sentinel)

> **状态**: PROPOSED (Roadmap Approved)
> **版本**: v12.0-L4-SENTINEL-SPEC
> **架构层级**: Layer 4 (Tactical Overlay)
> **核心目标**: 探测趋势衰竭 (Exhaustion) 与 恐慌出清 (Climax)，优化入场 Timing。

---

## 1. 核心逻辑：设计与推断的分离

Layer 4 不参与 **Regime Inference (制度推断)**。它只在 **Execution Pacing (执行节奏)** 阶段生效。

### 1.1 核心传感器 (Sensors)
- **Price Action**: QQQ 21d/252d 价格偏离度与新高/新低。
- **Volume Pulse**: QQQ 21d 滚动成交量均值偏离 (V-Zscore)。
- **Short Volume Proxy**: `src/collector/macro_v3.py` 提供的空头成交量占比。

### 1.2 三大背离模型 (The Triad)

| 模型 ID | 现象 (Phenomena) | 物理含义 | 决策干预 (Intervention) |
| :--- | :--- | :--- | :--- |
| **D1: Exhaustion** | **涨缩背离**：价格创 21d 新高，但 21d 滚动成交量均值持续萎缩。 | **趋势衰竭**：缺乏买盘支撑，非理性繁荣末端。 | **触发 Beta Ceiling**：强制将 `target_beta` 封顶于 1.0x，严禁杠杆追高。 |
| **D2: Climax** | **放量恐慌**：价格剧烈下跌，成交量激增至 2.5$\sigma$ 以上。 | **情绪高潮**：筹码大换手，飞刀落地的物理特征。 | **触发 Settlement Buffer**：延长入场冷却期，直至波动率回落或缩量出现。 |
| **D3: Accumulation** | **底背离**：价格创 21d 新低，但成交量显著收缩且 RSI/ROC 向上背离。 | **缩量洗盘**：抛压枯竭，潜在的左侧试探机会。 | **触发 Readiness Multiplier**：将 `deployment_readiness` 乘以 1.2x - 1.5x。 |

---

## 2. 算法实现路径 (The Sentinel Engine)

### 2.1 引入 `src/engine/v12/signal/divergence_monitor.py`
该模块将作为 `InertialBetaMapper` 的同级组件，负责输出 `tactical_bias`：

```python
class DivergenceMonitor:
    """
    v12.0 Sentinel Engine.
    Responsibility: Calculate Price-Volume Divergence and output tactical multipliers.
    """
    def calculate_bias(self, price_df: pd.DataFrame) -> dict:
        # 1. 涨缩背离检测 (Exhaustion)
        price_new_high = price_df['close'].tail(1).max() >= price_df['close'].rolling(21).max()
        vol_decay = price_df['volume'].rolling(5).mean() < price_df['volume'].rolling(21).mean()
        
        # 2. 量能高潮检测 (Climax)
        vol_spike = price_df['volume'].tail(1).iloc[0] > (price_df['volume'].mean() + 2.5 * price_df['volume'].std())
        
        # 3. 输出策略修正量
        return {
            "beta_ceiling": 1.0 if (price_new_high and vol_decay) else 1.2,
            "readiness_mod": 1.5 if (not vol_spike and price_df['close'].diff() < 0) else 1.0,
            "settlement_delay": 5 if vol_spike else 0
        }
```

---

## 3. 对 `Target Beta` 的具体影响

Layer 4 的干预是**限制性**而非**驱动性**的：

1.  **Beta 封顶 (Ceiling)**：如果 L1-L3 建议 1.2x，但 L4 探测到涨缩背离，最终 `target_beta` 将被封顶在 1.0x。
2.  **就绪度加成 (Readiness Bonus)**：如果 L1-L3 具备正向期望，L4 探测到缩量洗盘，`Kelly 就绪度` 将被放大，从而加速增量资金的 tranche 入场。

---

## 4. 验收标准与回测 (Gate 4)

- **AC-11 先行性审计**：在 2000 年、2008 年、2021 年末的牛市末端，L4 是否能先于宏观 BUST 信号触发 `Beta Ceiling`。
- **AC-12 飞刀审计**：在 2020 年 3 月的恐慌抛售中，L4 是否能通过 `Settlement Buffer` 成功避开最激烈的放量下跌时段。
- **AC-13 无噪音干扰**：在日常波动的震荡市中，L4 不应频繁触发，误导 `InertialBetaMapper`。

---
© 2026 QQQ Entropy 战术策略组.
