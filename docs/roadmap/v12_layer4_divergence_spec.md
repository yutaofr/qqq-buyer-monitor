# v12.0 Layer 4: KL散度“猎杀”与广义凯利规格书 (Sentinel)

> **状态**: PROPOSED (Information-Theoretic Hunting Revision)
> **版本**: v12.0-L4-SENTINEL-KL-DIVERGENCE
> **架构层级**: Layer 4 (Micro-Structure Overlay)
> **数学核心**: Kullback-Leibler Divergence, Micro-GaussianNB, 广义凯利方程

---

## 1. 核心信仰：用信息论量化“带血的筹码”

量化系统的猎杀本能不应源于人工设定的超跌阈值，而应源于**市场定价误差的数学绝对值**。本规格书通过引入 Kelly-KL 定理，将巴菲特的“别人恐惧我贪婪”转化为严格的无参数对数方程。

---

## 2. 数学推导：上帝与乌合之众的对决

### 2.1 God Sensor (宏观真实分布 $P_{macro}$)
由 10 因子正交贝叶斯核（L1-L3）输出的真实后验概率分布：
$$P_{macro} = [p_{boom}, p_{mid}, p_{late}, p_{bust}]$$
这是基于实体经济和流动性得出的“物理真相”。

### 2.2 Crowd Sensor (微观隐含分布 $P_{micro}$)
建立一个平行的**微观特征高斯朴素贝叶斯 (Micro-GNB)**。
- **输入特征**: $X_t = [r_t, v_t]$（仅包含当日对数收益率与日频超额成交量）。
- **推断结果**: 仅依据当日量价的恐慌或贪婪程度，反推大众隐含的 Regime 概率：
  $$P_{micro} = GNB_{micro}.predict\_proba(X_t)$$

### 2.3 猎杀期望 (The Alpha): KL 散度
根据信息论，利用市场定价错误（$P_{micro}$）相对于物理真相（$P_{macro}$）进行下注的理论最大指数增长率，严格等于两者的 Kullback-Leibler 散度：
$$Edge_{KL} = D_{KL}(P_{macro} || P_{micro}) = \sum_{i \in Regimes} P_{macro}(i) \ln \left( \frac{P_{macro}(i)}{P_{micro}(i) + \epsilon_{math}} \right)$$
*(注: $\epsilon_{math}=10^{-12}$ 仅为防止对数除零的 IEEE 754 硬件护城河，非业务超参)*

---

## 3. 广义凯利大一统方程 (The Grand Unification Kelly)

所有的战术干预（猎杀错杀、规避真崩盘、平滑慢牛）收敛为单一连续方程：

$$Final\_Target\_Beta = \frac{\mu_{base\_macro} + \lambda \cdot D_{KL}(P_{macro} || P_{micro})}{H(P_{macro}) + S_{micro}(X_t)}$$

*(注: $\lambda=1.0$，单位为 Nats，物理量纲完美对齐)*

### 3.1 物理自洽性推演 (Physical Self-Consistency)

| 市场情境 | 宏观状态 | 微观量价 | 变量坍缩态 | 最终 Beta | 物理意义 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **带血的筹码 (错杀)** | **BOOM** (健康) | **暴跌放量** (恐慌) | $D_{KL} \to \infty$ <br> $S_{micro} \to Large$ | **飙升 (>1.0)** | 错杀收益率的爆发远超微观局部方差的惩罚，系统**加杠杆嗜血猎杀**。 |
| **真实的雪崩 (崩盘)** | **BUST** (恶化) | **暴跌放量** (恐慌) | $D_{KL} \to 0$ <br> $S_{micro} \to \infty$ | **坍缩 (\approx 0)** | 上帝与大众都认为是崩盘（无错杀 Alpha），微观方差无限大，系统**空仓保命**。 |
| **虚假的繁荣 (诱多)** | **BUST** (恶化) | **无量拉升** (贪婪) | $D_{KL} \to \infty$ <br> $S_{micro} \to Medium$ | **封锁 (\approx 0)** | 虽然散度大，但基础期望 $\mu_{base}$ 为负，且方差抑制，系统**拒绝追高**。 |
| **静水流深 (慢牛)** | **MID** (温和) | **缩量微涨** (平静) | $D_{KL} \to 0$ <br> $S_{micro} \to 0$ | **平稳 (1.0)** | 宏微观共识一致，方差极小，系统依靠时间价值稳定获取 Beta。 |

---

## 4. 验证与防过拟合 (Falsifiability)

- **Test A (无超参验证)**：除防止浮点溢出的系统级极小值外，禁止引入任何人为权重。KL 散度的 Nat 单位必须与 Shannon 熵的 Nat 单位在数学上等价，实现 1:1 无损相加。
- **Test B (白噪声免疫测试)**：当 $X_t$ 被注入高斯白噪声时，$P_{micro}$ 退化为历史先验（Prior），$D_{KL}$ 常态化，系统安全退化为纯宏观模型，不会引发错误猎杀。

---
© 2026 QQQ Entropy 大一统架构组.
