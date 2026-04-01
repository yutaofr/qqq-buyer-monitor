# v12.0 Layer 4: 双轨制微观量价离群检测规格书 (Sentinel)

> **状态**: PROPOSED (Grand Unification Revision)
> **版本**: v12.0-L4-SENTINEL-DUAL-TRACK
> **架构层级**: Layer 4 (Micro-Structure Overlay)
> **数学核心**: Tikhonov 正则化马氏距离 ($D_M^2$) 与 卡方概率 ($P_{abnormal}$)

---

## 1. 核心准则：双轨制与绝对平稳性

本模块旨在将 QQQ 的微观量价异动（背离、高潮、衰竭）以**无超参 (Parameter-Free)**、**连续可导**的方式，分别嵌入系统的两大核心决策主线：增量资金的 Kelly 入场与存量资金的 Beta 风险管理。

### 1.1 微观结构平稳性特征提取
- **目标变量**: $X = [r_t, v_t]^T$ 
  - $r_t = \ln(P_t / P_{t-1})$ （对数收益率）
  - $v_t = \ln(V_t / V_{MA21})$ （对数超额成交量）
- **平稳化窗口**: 严格使用 **252 日 (单交易年) 滚动窗口**计算历史均值向量 $\mu$ 和协方差矩阵 $\Sigma_{252}$。
- **正则化马氏距离 ($D_M^2$)**: 
  $$\Sigma'_{252} = \Sigma_{252} + 10^{-6} I$$
  $$D_M^2 = (X - \mu)^T (\Sigma'_{252})^{-1} (X - \mu)$$
- **离群概率 ($P_{abnormal}$)**: 
  基于自由度为 2 的卡方分布：$P_{abnormal} = CDF_{\chi^2_2}(D_M^2)$

---

## 2. 主线一：增量资金入场节奏 (Kelly Pacing)

> **原则**：增量资金由 Kelly 判据主导，寻找盈亏比最优解。马氏距离 $D_M^2$ 物理上等价于“当前微观局部方差”。

### 2.1 广义 Kelly 就绪度方程
$$Kelly\_Readiness = \max\left(0, \frac{\mu_{macro} + \Delta \mu_{micro}}{\sigma_{macro}^2 + D_M^2}\right)$$

- **分子 (期望收益)**: 宏观预期夏普率加上微观底背离补偿 $\Delta \mu_{micro}$（当 $r_t < 0, v_t < 0$ 且触及超卖时激活）。
- **分母 (系统方差)**: 宏观 Shannon 熵 ($\sigma_{macro}^2$) 加上微观马氏距离 ($D_M^2$)。
- **工程表现**: 当发生“放量暴跌（接飞刀）”或“高位异动放量”时，$D_M^2$ 瞬间飙升。分母趋于无穷大，Kelly 就绪度自动坍缩至 0，严禁新增资金入场。**彻底消灭人为的 `if vol > x` 规则。**

---

## 3. 主线二：存量资金 Beta 管理 (Risk Management)

> **原则**：存量资金由贝叶斯推断与信息熵主导。微观量价离群概率 $P_{abnormal}$ 作为连续的“软约束乘数”实施动态风控。

### 3.1 战术惩罚乘数 (Tactical Penalty, $M_{tactical}$)
摒弃二元对立的“破位减仓”硬规则。当且仅当系统处于**“量价衰竭象限 (Exhaustion)”**（即 $r_t > 0$ 且 $v_t < 0$）时，激活战术乘数：
$$M_{tactical} = 1.0 - P_{abnormal}$$

### 3.2 最终 Beta 映射
$$Final\_Target\_Beta = \min\left(Bayesian\_Beta, Base\_Beta \times M_{tactical}\right)$$

- **工程表现**: 如果 QQQ 在缩量（$v_t < 0$）的情况下强行拉升（$r_t > 0$）创出新高，且这种量价组合极为罕见（如 $P_{abnormal} = 0.95$），则 $M_{tactical} = 0.05$。存量资金的目标 Beta 被极其平滑地压制，拒绝跟随“非理性繁荣”。

---

## 4. 验收与防过拟合 (Validation)

1.  **无超参证明**: $M_{tactical}$ 和 $D_M^2$ 均直接由统计分布得出，严禁在回测中加入任何缩放系数进行曲线拟合。
2.  **白噪声证伪测试**: 将输入 $V_t$ 替换为高斯白噪声。如果系统的 **信息比率 (IR)** 未显著下降，则该模块无效，必须废弃。
3.  **确定性测试**: 注入极低波动率的僵尸数据，确保 $\Sigma'_{252}$ 求逆不引发 `LinAlgError`。

---
© 2026 QQQ Entropy 双轨制架构组.
