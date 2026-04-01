# v12.0 Layer 4: 拓扑连续量价散度与实证微观引擎 (Sentinel)

> **状态**: PROPOSED (Industrial-Grade Topology & Empirical Falsification)
> **版本**: v12.0-L4-SENTINEL-CONTINUOUS-EMPIRICAL
> **架构层级**: Layer 4 (Micro-Structure Overlay)
> **工程准则**: 拓扑平滑 (Topological Smoothness), 实证基线 (Empirical Baselines), 严格 PiT (Point-in-Time) 隔离

---

## 1. 核心信仰：敬畏混沌与拓扑平滑 (Reverence for Chaos)

真正的工业级量化引擎不追求教科书式的“绝对无参”，而是追求系统在面对噪音和肥尾分布时的**绝对连续性 (Absolute Continuity)**。
本规格书彻底废除所有非连续的阶跃函数 (Step Functions)、符号函数 (Sign) 与硬性阻断阈值 (Hard Cutoffs)。任何风控阀门与惩罚乘数必须是 $C^1$ 连续可导的拓扑映射，以吸收而非对抗市场的不确定性。

---

## 2. 实证微观概率引擎 (Empirical Micro-Engine)

承认参数的存在，并将其显式化为系统的风控阀门。废弃对完美二元高斯的幻想，直面肥尾现实。

### 2.1 显式衰减的在线协方差 (Explicit Decay Covariance)
- **特征向量**: $X_t = [r_t, v_t]^T$ (对数收益率与超额成交量)
- **在线更新 (Online EWMA Covariance)**:
  不再走私超参数。显式引入**记忆衰减因子 $\alpha$ (例如 $\alpha=0.05$)**。它决定了系统对“暴跌放量”记忆的物理半衰期。
  $$\mu_t = (1-\alpha)\mu_{t-1} + \alpha X_t$$
  $$\Sigma_t = (1-\alpha)\Sigma_{t-1} + \alpha (X_t - \mu_t)(X_t - \mu_t)^T$$
- **马氏惊奇度 (Surprisal)**: $S_{micro, t} = \frac{1}{2} (X_t - \mu_{t-1})^T (\Sigma_{t-1})^+ (X_t - \mu_{t-1})$

### 2.2 动态实证基线 (Dynamic Empirical Baseline)
彻底废弃理论高斯分布下 $E[S_{micro}]=1.0$ 的妄想。金融市场是肥尾的。
采用滚动指数移动平均 (EMA) 提取当前市场体制下的真实惊奇度基线：
$$Baseline_t = \text{EMA}(S_{micro, t}, span=252)$$
**有效惊奇惩罚 (Effective Surprisal Penalty)**:
$$Penalty_t = \exp\left(S_{micro, t} - Baseline_t\right)$$
*系统自我适应肥尾：只有当今天的离奇程度超过了过去一年的平均离奇程度时，才触发真正的方差惩罚。*

---

## 3. 拓扑连续的散度套利 (Topologically Smooth Divergence Arbitrage)

使用 Jensen-Shannon 散度 (JSD) 提取宏微观的“共识破裂度”，并用连续可导函数消灭震荡。

### 3.1 连续方向对齐 (Continuous Directional Alignment)
废弃极度危险的 $dir = \text{sign}(\dots)$。使用 Tanh 函数进行平滑的双曲正切映射，确保在零轴附近的微小震荡不会导致乘数的剧烈翻转。
$$Delta\_Macro = \mu_{macro\_t} - \mu_{macro\_t-1}$$
$$Delta\_Micro = \mu_{micro\_t} - \mu_{micro\_t-1}$$
$$Alignment\_Score = \tanh\left( \kappa \cdot (Delta\_Macro \cdot Delta\_Micro) \right) \in [-1, 1]$$
*(注: $\kappa$ 为平滑系数，控制穿越零轴的坡度)*

### 3.2 连续散度乘数 (Smooth Edge Multiplier)
将 JSD 散度与连续方向分数结合，生成无断层的杠杆乘数：
$$M_{edge} = \exp\left( Alignment\_Score \cdot JSD(P_{macro} || P_{micro}) \right)$$
- **物理意义**: 共识破裂度越大 ($JSD \to \ln(2)$)，且方向高度一致 ($Alignment \to 1$) 时，平滑放大至最大 $\sim 2.0$ 倍；若方向背离 ($Alignment \to -1$)，平滑收缩至 $\sim 0.5$ 倍。不存在任何阶跃突变。

---

## 4. 大一统动力学方程 (The Dynamical Equation)

$$Final\_Target\_Beta = \frac{\mu_{macro} \cdot M_{edge}}{\sigma_{macro}^2 \cdot \exp(S_{micro, t} - Baseline_t)}$$

*(所有变量均保持绝对连续，任何极微小的输入扰动只会产生极微小的 Beta 变化。)*

---

## 5. 严苛审计：PiT 隔离与连续置信度权重

系统绝不能成为劣质数据和过拟合模型的放大器。

### 5.1 连续模型置信度权重 (Continuous Confidence Weight)
废弃“Brier Score > 0.25 则切断”的生硬阈值。使用 Softplus 函数将微观模型的预测能力转化为连续平滑的置信权重：
$$Weight_{micro} = \sigma\left( \gamma \cdot (0.25 - \text{Brier}(P_{micro})) \right)$$
*(此处 $\sigma$ 为 Sigmoid/Softplus 族函数。当 Brier 得分在 0.25 附近徘徊时，权重平滑过渡，而非瞬间熔断。)*
最终 JSD 乘数受权重节制：$M_{effective\_edge} = 1.0 + Weight_{micro} \cdot (M_{edge} - 1.0)$

### 5.2 宏观 PiT 时间错位隔离测试 (Look-ahead Bias Falsification)
**强制执行令**：所有的宏观免费数据源（如 FRED）必须经历严苛的 Point-in-Time (PiT) 审查。
- **审计方案**: 在全量回测中，强制将所有宏观特征矩阵 $P_{macro}$ 的时间轴向后**平移 (Lag) 45 天**（模拟最恶劣的宏观数据发布滞后与初值修正）。
- **证伪基准**: 在 45 天的 PiT 盲区下，如果 $JSD$ 引擎的 Brier Score 崩溃，或全系统的 Information Ratio (IR) 断崖式下跌，**即刻判定此前的“散度套利”完全是基于未来函数 (Look-ahead Bias) 的幻觉，必须重构乃至废除。**

---
© 2026 QQQ Entropy 拓扑与实证架构审计组.
