# v12.0 Layer 4: 广义凯利微观方差规格书 (Sentinel)

> **状态**: PROPOSED (Grand Unification - Zero Constant Revision)
> **版本**: v12.0-L4-SENTINEL-GENERALIZED-KELLY
> **架构层级**: Layer 4 (Micro-Structure Overlay)
> **数学核心**: 贝叶斯在线协方差更新、广义逆矩阵与连续凯利方程

---

## 1. 核心信仰：绝对的零常数 (Zero-Constant Axiom)

量化系统的脆弱性皆源于“魔法数字”。本模块在架构上**严禁**任何形式的时间窗口（如 252 天）、正则化扰动（如 $10^{-6}$）、截断函数（如 `min/max`）以及人为的象限条件（如 `if 涨缩背离`）。

所有决策必须是连续、可导且由数据自身的概率分布驱动的。

---

## 2. 核心数学推导 (The Mathematics)

### 2.1 微观分布的无窗在线更新 (Parameter-Free Online Updating)
废弃固定窗口。量价向量 $X = [r_t, v_t]^T$ 的均值 $\mu_t$ 与协方差 $\Sigma_t$ 采用随时间流逝自适应的逆威沙特分布进行在线贝叶斯更新（Online Bayesian Updating）。
数据更新的卡尔曼增益由新观测值带来的信息增益自然决定，**时间跨度由数据自身的信噪比定义，而非人工常量。**

### 2.2 绝对确定的马氏惊奇度 (Deterministic Surprisal)
废弃 Tikhonov 扰动。使用摩尔-彭若斯广义逆 (Moore-Penrose Pseudo-Inverse, $\Sigma^+$) 来解决极端无波动日的奇异矩阵问题，利用 IEEE 754 硬件精度实现截断。
$$D_M^2 = (X_t - \mu_{t-1})^T (\Sigma_{t-1})^+ (X_t - \mu_{t-1})$$
瞬时微观惊奇度 (Surprisal)：
$$S_{micro} = \frac{1}{2} D_M^2 \quad (\text{理论期望 } E[S_{micro}] = 1.0)$$

---

## 3. 决策大一统：广义凯利方程 (Generalized Kelly Pacing)

所有的战术干预（不接飞刀、不追高、缩量加仓）统一收敛为对凯利方程方差项的连续调制。

### 3.1 有效微观方差 (Effective Variance)
将瞬时惊奇度作为宏观方差的指数乘数：
$$\sigma_{eff}^2 = \sigma_{macro}^2 \cdot \exp(S_{micro} - 1.0)$$

### 3.2 终极目标 Beta (The Ultimate Target Beta)
$$Final\_Target\_Beta = \frac{\mu_{macro}}{\sigma_{macro}^2 \cdot \exp(S_{micro} - 1.0)}$$

#### 物理自洽性推演 (Physical Self-Consistency)
1. **防范“飞刀” (Anti-Climax)**：放量暴跌引发 $S_{micro} \gg 1.0$。分母指数级膨胀，$Beta \to 0$。凯利判据自动拒绝在高方差局部接盘。
2. **防范“虚假繁荣” (Anti-Exhaustion)**：高位异动或天量滞涨，同样导致 $S_{micro} \gg 1.0$。分母膨胀迫使系统自动止盈。
3. **拥抱“静水流深” (Embrace Calmness)**：市场极度平静（如经典的无量慢牛），$S_{micro} < 1.0$。方差缩小，Beta 自动放大，资金利用率达到极致。

---

## 4. 验证与证伪标准 (Falsifiability)

- **Test A (白噪声证伪)**：将 $V_t$ 替换为高斯白噪声。由于白噪声无结构性异动，$S_{micro}$ 均值将死锁于 1.0，$Final\_Target\_Beta$ 将退化为纯宏观模型。如果加入真实 $V_t$ 的信息比率 (IR) 不能以 $p < 0.05$ 的显著性击败白噪声退化模型，则本规格书作废。
- **Test B (拓扑连续性)**：要求目标 Beta 函数在任意市场极端切片下（包括 2020.03 的六次熔断）保持 $C^1$ 连续（一阶可导），严禁出现因 `if/else` 导致的阶跃断层。

---
© 2026 QQQ Entropy 大一统架构组.
