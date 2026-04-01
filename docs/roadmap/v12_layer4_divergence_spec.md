# v12.0 Layer 4: 信息论量价离群检测规格书 (Sentinel)

> **状态**: PROPOSED (Information-Theoretic Unification)
> **版本**: v12.0-L4-SENTINEL-INFORMATION-THEORY
> **架构层级**: Layer 4 (Micro-Structure Overlay)
> **数学核心**: Tikhonov 正则化马氏距离与 Shannon 惊奇度 (Surprisal) 同构

---

## 1. 核心准则：量纲一致性与信息论大一统 (Dimensional Harmony)

量化工程的最高美学是**量纲一致性**。本模块将微观量价数据严格映射为**信息惊奇度 (Surprisal, 单位 Nats)**，使其在数学物理上与宏观 Shannon 熵 ($H$) 完全同构，从而实现无缝融合。

### 1.1 微观惊奇度提取 (Micro Surprisal Extraction)
- **目标变量**: $X = [r_t, v_t]^T$ 
  - $r_t = \ln(P_t / P_{t-1})$
  - $v_t = \ln(V_t / V_{MA21})$
- **平稳化协方差**: 使用 252 日滚动窗口计算 $\Sigma_{252}$。
- **正则化与马氏距离**: $\Sigma'_{252} = \Sigma_{252} + 10^{-6} I$
  $$D_M^2 = (X - \mu)^T (\Sigma'_{252})^{-1} (X - \mu)$$
- **瞬时惊奇度 (Surprisal)**: 
  根据二元高斯分布性质，当前量价异动的信息含量为：
  $$S_{micro} = \frac{1}{2} D_M^2 \quad (\text{单位: Nats})$$

---

## 2. 双轨制融合方程 (The Dual-Track Unification)

### 2.1 主线一：增量入场 (Kelly Readiness)
将微观瞬时惊奇度直接并入 Kelly 公式的系统不确定性分母中。
$$Kelly\_Readiness = \max\left(0, \frac{\text{Macro\_Expected\_Edge}}{H_{macro} + S_{micro}}\right)$$
- **物理机制**: 任何破坏微观结构稳态的异动（如天量暴跌、无量空涨），都会产生巨大的 $S_{micro}$。总不确定性飙升，Kelly 分数自动坍缩，停止新增资金暴露。**完全无需人工设定安全阈值。**

### 2.2 主线二：存量防守 (Beta Penalty Multiplier)
由于 $S_{micro}$ 的理论期望值严格为 $E[S_{micro}] = 1.0 \text{ Nat}$，我们构建无超参的衰减惩罚：
$$M_{tactical} = \min\left(1.0, \exp(1.0 - S_{micro})\right)$$
- **物理机制**: 
  - 当市场量价健康 ($S_{micro} \le 1.0$)，$M_{tactical} = 1.0$，决策 100% 由宏观贝叶斯引擎主导。
  - 当市场发生罕见异动（如 $S_{micro} = 4.0$），$M_{tactical} = e^{-3} \approx 0.05$。目标 Beta 被极其平滑且剧烈地削减。
$$Final\_Target\_Beta = Bayesian\_Beta \times M_{tactical}$$

---

## 3. 工程确定性与防过拟合体系 (Validation Protocols)

本模块的上线合并（Merge）必须通过以下苛刻的数学与工程测试：

### 3.1 零参数检查 (Zero-Hyperparameter Audit)
代码中严禁出现任何未经第一性原理推导的常数（$\epsilon=10^{-6}$ 的计算机精度扰动除外）。

### 3.2 白噪声反向证伪 (White Noise Falsification)
**测试方法**: 将输入历史数据中的成交量 $V_t$ 替换为均值和方差相同的**高斯白噪声**序列，重新运行全量 16 年回测。
**通过标准**: 白噪声数据注入后的系统 **信息比率 (Information Ratio)** 必须**显著且统计上稳健地**低于真实量价数据。如果白噪声表现更好，说明模型在拟合噪音，必须永久废弃该模块。

### 3.3 奇异矩阵鲁棒测试 (Singular Matrix Survival)
注入连续 20 个交易日 $r_t=0, v_t=0$ 的极端死水数据，验证系统能够依靠 Tikhonov 正则化平稳度过，绝不抛出任何 `LinAlgError`。

---
© 2026 QQQ Entropy 统计与架构联合组.
