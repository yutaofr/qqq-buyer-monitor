# v12.0 Layer 4: 统计学量价背离监控规格书 (Sentinel)

> **状态**: PROPOSED (Rigorous Math Revision)
> **版本**: v12.0-L4-SENTINEL-MATHEMATICAL
> **架构层级**: Layer 4 (Tactical Overlay)
> **数学核心**: Tikhonov 正则化的二元高斯离群检测与卡方概率映射

---

## 1. 核心准则：数学严谨与防过拟合 (Mathematical Rigor)

本规格书旨在解决量化交易中“量价分析”容易沦为伪科学与过拟合重灾区的问题。所有设计必须满足：**无超参 (Parameter-Free)**、**数值绝对稳定 (Determinism)**、**微观结构平稳性 (Stationarity)**。

### 1.1 微观结构平稳性特征提取
由于市场微观交易结构随时代剧变，严禁使用 Expanding Window 处理成交量。
- **目标变量**: $X = [r_t, v_t]^T$ 
  - $r_t = \ln(P_t / P_{t-1})$ （对数收益率）
  - $v_t = \ln(V_t / V_{MA21})$ （对数超额成交量）
- **平稳化窗口**: 严格使用 **252 日 (1年) 滚动窗口**计算历史均值向量 $\mu$ 和协方差矩阵 $\Sigma_{252}$。

### 1.2 工程确定性：正则化马氏距离
为防止极端行情下（如节假日）矩阵退化导致求逆崩溃，强制引入 **Tikhonov 正则化**：
$$\Sigma'_{252} = \Sigma_{252} + \epsilon I \quad (\epsilon = 10^{-6})$$
基于正则化协方差矩阵计算马氏距离：
$$D_M^2 = (X - \mu)^T (\Sigma'_{252})^{-1} (X - \mu)$$

---

## 2. 干预逻辑：无超参卡方映射 (Parameter-Free Mapping)

摒弃所有人为设定的衰减系数 $\alpha$。干预强度直接由概率分布本身的生存函数 (Survival Function) 决定。

### 2.1 统计学显著性 (Statistical Abnormality)
由于 $D_M^2$ 渐近服从自由度为 2 的卡方分布 ($\chi^2_2$)，当前量价异象的“惊悚程度”可以直接映射为概率：
$$P_{abnormal} = CDF_{\chi^2_2}(D_M^2) \in [0, 1)$$

### 2.2 象限定向与连续乘数
定义 **战术惩罚乘数 (Tactical Penalty Multiplier, $M_{tactical}$)**，默认值为 1.0。

- **D1 象限 (涨缩背离/量价衰竭)**
  - **条件**: $r_t > 0$ 且 $v_t < 0$ 且 $P_{abnormal} > 0.80$ (处于 80% 异常分位点外)
  - **无超参乘数**: $M_{tactical} = 1.0 - P_{abnormal}$ 
  - **物理含义**: 量价背离越离奇，乘数越逼近于 0。完全交给卡方分布决定，无人为参数。

- **动态干预应用**:
  最终建议仓位受限于 L4 乘数：
  `final_target_beta = min(bayesian_target_beta, base_beta * M_{tactical})`
  *为防止日频噪音导致仓位闪烁，该乘数需通过 5 日 EWMA 平滑后输出。*

---

## 3. 验收标准与白噪声证伪 (Validation & Anti-Overfitting)

为证明该模块并非“曲线拟合 (Curve Fitting)”，PR 合并前必须通过以下严格的三重测试：

| 测试阶段 | 评估标准 | 架构意义 |
| :--- | :--- | :--- |
| **Test 1: 基线提升** | 加入 L4 后，全量回测的 **信息比率 (Information Ratio)** 必须实现正增长，且 MDD 有所改善。 | 证明模块在风险调整后确实增加了价值。 |
| **Test 2: 白噪声证伪** | 将 $V_t$ 替换为同方差的**高斯白噪声**后重新回测。此时的 IR 必须**显著低于**真实数据的回测。 | **核心证伪测试**：证明系统捕获的是真实的量价规律，而非随机噪音的拟合。 |
| **Test 3: 矩阵鲁棒性** | 注入连续 10 天成交量完全一致的脏数据，测试系统是否抛出 `LinAlgError`。系统必须通过正则化平稳度过。 | 保证生产环境的绝对工程确定性。 |

---
© 2026 QQQ Entropy 统计策略组.
