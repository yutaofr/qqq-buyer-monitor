# v12.1 Layer 4: Sentinel 微观量价与散度套利规格书

> **状态**: PROPOSED (Industrial-Grade Topology & Empirical Falsification)
> **版本**: v12.1-SENTINEL-FINAL
> **架构层级**: Layer 4 (Micro-Structure Overlay)
> **工程准则**: 拓扑平滑 (Topological Smoothness), 实证基线 (Empirical Baselines), ALFRED 严格 PIT 隔离, 物理风控 (Tikhonov)

---

## 1. 核心愿景：广义凯利大一统 (Grand Unification)

V12.1 架构的核心突破是将宏观贝叶斯推断（Layer 1-3）与微观市场微结构（Layer 4）在**信息论**框架下实现完美融合。系统通过感知宏观真相与微观情绪之间的散度，实现“伺机而动”的猎杀与“敬畏市场”的防御。

---

## 2. 微观概率引擎 (Empirical Micro-Engine)

### 2.1 物理全秩协方差 (Tikhonov Regularization)
承认特征高度共线性时的奇异性风险。废弃伪逆，采用吉洪诺夫正则化：
$$\Sigma_{robust} = \Sigma_t + 10^{-6} \cdot I$$
- **物理意义**: 确保矩阵全秩的同时，一旦在干涸维度发生微小异动，马氏惊奇度将暴力爆炸，从而精准触发极值风控。

### 2.2 惊奇度与动态基线 (Surprisal & EMA Baseline)
- **马氏惊奇度**: $S_{micro, t} = \frac{1}{2} (X_t - \mu_{t-1})^T (\Sigma_{robust})^{-1} (X_t - \mu_{t-1})$
- **动态基线**: $Baseline_t = \text{EMA}(S_{micro, t}, span=252)$
- **年代际水位锁**: $S_{99th, t} = \text{Percentile}(S_{micro, t-1764...t}, 99\%)$
- **惩罚项**: $Penalty_t = \exp\left( \max(S_{micro, t} - Baseline_t, \ S_{micro, t} - S_{99th, t}) \right)$

---

## 3. 散度套利引擎 (Divergence Arbitrage)

### 3.1 Jensen-Shannon 散度 (JSD)
利用 JSD 提取宏微观的“共识破裂度”，值域严格有界于 $[0, \ln(2)]$：
$$JSD(P_{macro} || P_{micro})$$

### 3.2 连续方向对齐与乘数
使用 Tanh 映射确保杠杆乘数的拓扑连续性，并引入结构波动率下限 $\epsilon_{vol\_floor}$ 防止分母坍缩。
$$Z\_Signal_t = \frac{Raw\_Signal_t - \mu_{signal}}{\max(\sigma_{signal}, \epsilon_{vol\_floor})}$$
$$M_{edge} = \exp\left( \tanh(Z\_Signal_t) \cdot JSD \right)$$

---

## 4. 大一统动力学方程 (The Dynamical Equation)

$$Final\_Target\_Beta = \frac{\mu_{macro} \cdot M_{effective\_edge}}{\sigma_{macro}^2 \cdot Penalty_t}$$

---

## 5. 铁血审计准则 (Audit Protocols)

### 5.1 ALFRED PIT 隔离定律
回测必须使用 ALFRED 数据库中**当时当刻发布且未经修正的初值 (Vintage Data)**。严禁使用事后修正数据污染散度计算。

### 5.2 相对生存约束 (Relative Survival Constraint)
寻优目标函数必须满足：
`Annual_IR(With_L4) >= Annual_IR(Base_Macro) - 0.05`
Layer 4 的使命是护航与猎杀，其叠加效果绝不允许在任何宏观周期显著拖累基础策略。

### 5.3 混沌工程与摩擦力
系统上线前必须通过：
- **Chaos Monkey**: 5% 初值丢失与 10% 发布延迟下的稳健运行。
- **动态滑点**: 在高惊奇度（$S_{micro}$）下计入指数级跳升的冲击成本。

---
© 2026 QQQ Entropy 架构实施委员会.
