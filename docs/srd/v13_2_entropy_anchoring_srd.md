# SRD-v13.2: QQQ Bayesian Orthogonal Factor Monitor - Entropy Anchoring & ML Optimization

**Version**: 13.2  
**Status**: Ready for Implementation  
**Architect**: Gemini CLI / Senior Systems Architect  
**Reviewers**: Tech Leader, Senior Data Scientist, UI/UX Engineer  
**Date**: 2026-04-03

---

## 1. 引言 (Introduction)
本 SRD 定义了 v13.2 架构，旨在通过 2018 深度预热解决冷启动高熵问题，并结合贝叶斯校准、血统归一化及去漂移预处理，提升系统在长周期宏观转向中的识别精度与数值稳定性。

---

## 2. 架构原则 (Architectural Principles)
*   **Sequential Causality**: 严禁偷看未来，模拟 T+0 决策。
*   **Anti-Overfitting**: 权重由周期传导路径决定，严禁通过回测参数寻优。
*   **Numerical Stability**: 引入分层调和平均与温度校准，防止虚假自信。
*   **PIT Consistency**: 所有输入必须经过 Point-in-Time 滚动去中心化处理。

---

## 3. 功能性需求 (Functional Requirements)

### 3.1 FR-1: 2018 锚定深度回放 (Sequential Replay)
*   从 2018-01-01 起回放数据。
*   **仅更新** `PriorKnowledgeBase.counts` 与 `transition_counts`。
*   **严禁更新** `GaussianNB` 的 $\theta$ 与 $\sigma$。

### 3.2 FR-2: 周期传导加权与血统归一化
*   **Level 1 (2.5x)**: `credit_spread_bps` (原动机)。
*   **Level 2 (2.0x)**: `net_liquidity_usd_bn`, `real_yield_10y_pct` (定价引力)。
*   **Level 3 (1.5x)**: `treasury_vol_21d`, `move_21d` (系统压力)。
*   **Level 4 (1.0x)**: `DEFAULT_FALLBACK` (默认/市场代理)。
*   **Level 5 (0.5x)**: `breakeven_10y`, `macro_long_lag` (滞后性指标)。
*   **FR-2.1 血统归一化**: 同一原始因子衍生的特征，其实际总投票权恒定为 $w_{root}$。计算似然度时采用加权平均法（见 4.2）。

### 3.3 FR-3: 分层调和平均质量评分 (Tiered Quality)
*   **Level 1 (Core)**: 采用调和平均计算 $Q_{core}$。若任一核心因子缺失，$Q_{core} \to 0$。
*   **Level 2-5**: 采用加权算术平均计算 $Q_{support}$。
*   **Total**: $Q_{score} = Q_{core} \times Q_{support}$。

### 3.4 FR-4: 物理参与度底线 (Beta Floor)
*   `target_beta` 逻辑底线恒定为 **0.5**。
*   **FR-4.1 条件跳变**: 若 Execution Overlay 识别到 `CRASH` 或 `LIQUIDITY_SHOCK`（基于 v13 高频信号），允许底线临时降至 0.0。

### 3.5 FR-5: PIT 去漂移预处理 (Anti-Drift)
*   所有因子输入模型前，必须经过 252 日滚动窗口的 **Z-Score 归一化**。
*   此过程必须是 PIT 的，严禁泄漏未来窗口的统计量。

### 3.6 FR-6: 存储效率策略
*   回演期间采用本地缓冲。
*   只有在任务全部结束后，执行单次原子级云同步。

---

## 4. 技术规范 (Technical Specifications)

### 4.1 特征-权重注册表 (Technical Registry)
系统必须内置硬编码的 `FEATURE_WEIGHT_REGISTRY`，匹配逻辑采用“最长前缀匹配”。

### 4.2 温度校准似然度公式 (Calibrated Weighted Likelihood)
$$P(R|X) \propto P(R) \cdot \exp\left( \frac{1}{\tau} \cdot \frac{\sum w_i \cdot \ln P(x_i|R)}{\sum w_i} \right)$$
*   $\tau$ 为校准温度（默认 1.0，根据验证集调整）。
*   分母 $\sum w_i$ 实现了血统归一化。

### 4.3 质量传递函数
*   Direct: 1.0 | Proxy: 0.7 | Synthetic: 0.5 | Default: 0.3 | Missing: 0.0。

### 4.4 Beta 控制流
`Entropy Haircut` -> `Beta Floor (0.5/0.0)` -> `InertialBetaMapper (Smoothing)`。

---

## 5. UI/UX 规范 (Output)
*   **Discord**: 显示 `Prior: v13.2 Hydrated` 标签。若触发底线，标记 `⚠️ FLOOR_ACTIVE`。
*   **Web**: 增加权重分布展示与 Beta 锁定态（Amber-400）视觉反馈。
*   **Hydrating Feedback**: 回演期间接口返回 `system_status: HYDRATING`。

---

## 6. 验证协议
*   **Entropy Delta < 0.05**。
*   **Cycle Parity**: 2022 转向识别延迟 $\le 15$d。
*   **Hash Check**: 模型参数在预热前后保持一致。

---
**核准**: Gemini CLI (Architect)
