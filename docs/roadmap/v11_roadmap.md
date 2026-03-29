# QQQ Monitor V11.0 架构演进路线图

## 1. 核心状态机优化 (Cycle State Machine Refinement)

### 1.1 `BUST` 与 `CAPITULATION` 的冲突解决机制
*   **背景**：当前 v10.0 实现中，`BUST` 拥有绝对优先级。虽然确保了安全性，但在极端恐慌（Capitulation）阶段可能错过 VIX 坍塌引发的暴力反弹。
*   **研究目标**：引入“美联储干预”探测器。若 `Spread >= 650` (BUST) 但同时检测到 `Liquidity_ROC > 0` 且 `Credit_Acceleration < 0`，则允许系统降级切换至 `CAPITULATION` 抢筹模式。

### 1.2 动态 ERP 阈值 (Adaptive ERP Thresholds)
*   **背景**：2021 年这类“长尾泡沫期”，由于利率极低，2.5% 的 ERP 阈值可能在长时间内不被触发，导致逻辑钝化。
*   **研究目标**：建立基于 10 年移动窗口的 ERP 分位点动态计算模型，而非硬编码 2.5%。

---

## 2. 流动性层级重组 (Liquidity Re-integration)

### 2.1 Net Liquidity (SSoT) 重回 Tier-0
*   **背景**：v10.0 过于强调定价周期（ERP），削弱了流动性指标。但历史证明 Net Liquidity 是纳指波动的先行同步指标。
*   **研究目标**：将 `WALCL - WDTGAL - RRPONTSYD` 重新作为系统全局的“环境水位线”，与 ERP 共同决定 Beta 上限。

### 2.2 离散化映射保护
*   **背景**：为防止 Alpha 策略被逆向工程，研究更复杂的信号离散化逻辑。

---

## 3. 自动化审计与保真度 (AC-4 Fidelity)

### 3.1 实时 Beta 偏差实时监控
*   **目标**：开发 Grafana/Web 插件，实时展示“目标 Beta vs 实际敞口”的偏离曲线，超过 0.05 自动触发警报。

---

## 4. 特种资产支持 (Exotic Assets Support)

### 4.1 TMF/USD 对冲模块
*   **背景**：在 `BUST` 周期中，现金虽安全但丧失了部分防御性 Alpha。
*   **研究目标**：研究在 BUST 阶段引入 20% 權重的長債（TMF）作為風險對沖。
