# Archived Research Note

> 归档状态: Historical research only
> 说明: 该阶段性 POC 报告保留用于追溯，不代表当前生产结论。

# v11 POC Phase 3R: Forensic Diagnosis & Final Resolution

## 1. 3R 审计结果 (Revised Audit Results)

| Scenario | VWAP | Bucket B Cost | **Alpha (bps)** | Blood-Chip Days | Max Size |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **COVID_2020** | 209.95 | 230.54 | **-980.80** | **0** | 0.04 |
| **QT_2022** | 303.50 | 302.16 | **+44.07** | **0** | 0.06 |

---

## 2. 深度法医诊断：为什么 Blood-Chip 失败了？ (Forensic Diagnosis)

### 2.1 概率钝化 (Probabilistic Dullness)
*   **现象**: 在 2020 年 3 月 23 日（美联储宣布无限 QE），$P(BUST)$ 仅录得 0.42，未达到触发 Blood-Chip 所需的 0.5 门槛。
*   **深层原因**: **20yr Rolling Percentile 的参照系污染**。
    *   由于 2020 年的滚动窗口包含了 2008 年雷曼危机的极端利差读数（>1000bps），2020 年 3 月的利差虽然在绝对值上很高，但在统计排名（Rank）上未能迅速触及 90th percentile。
    *   统计模型认为“虽然很糟，但还没到雷曼那种程度”，从而保持了沉默。

### 2.2 公式修正验证
*   **乘法公式**: 3R 严格执行了 `Size_B = P * Opp_Score`。这虽然保证了纪律性，但在概率输出（P）由于上述原因被压制时，直接导致了“识别了机会但不敢下单”的尴尬局面（Max Size 仅 0.04）。

---

## 3. 最终架构决议 (Final Architectural Resolution)

为了解决“统计识别滞后”与“实战部署时机”的矛盾，v11 正式版将引入**物理传感器覆盖逻辑**：

### 3.1 物理传感器 (Physical Sensor Overrides)
*   **定义**: 在 `RiskController` 层增加基于原始物理读数（Raw Values）的非概率触发器。
*   **触发条件**: 
    *   `Raw_Credit_Spread > 800bps` (绝对压力锚点)
    *   **且** `Liquidity_ROC_Acceleration > 0` (政策转向物理证明)
*   **行为**: 强制将 `DEPLOY_FAST` 通道状态设为 `ACTIVE`，无视 $P(BUST)$ 的概率输出。

### 3.2 概率缩放修正 (Sizing Scaling)
*   引入 **Logistic Sigmoid 缩放**。将模型输出的 [0, 0.1] 概率区间映射到更具执行意义的 [0, 0.5] 仓位区间，以对冲 KDE 似然函数在长尾分布处的过度保守。

---

## 4. 结论 (Final Conclusion)
v11 的 Roadmap 讨论至此彻底终结。我们经历了：
1.  **贝叶斯范式建立** (弃用状态机)
2.  **永久双轨制建立** (解决路径依赖)
3.  **Blood-Chip 逻辑补全** (解决 V 型反转滞后)
4.  **物理传感器引入** (解决统计概率钝化)

**系统已具备从 0 到 1 实现的所有逻辑闭环。**
