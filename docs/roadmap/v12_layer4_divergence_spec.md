# v12.0 Layer 4: 工业级散度套利与实证风控引擎 (Sentinel)

> **状态**: PROPOSED (Battle-Hardened Industrial Revision)
> **版本**: v12.0-L4-SENTINEL-ALFRED-WFO
> **架构层级**: Layer 4 (Micro-Structure Overlay)
> **工程准则**: 动态归一化 (Dynamic Normalization), 绝对水位锁 (High-Water Mark Lock), ALFRED 初值隔离, 滚动步进审计 (WFO)

---

## 1. 核心信仰：直面参数与拒绝未来函数 (The Reality Check)

放弃用纯粹的理论方程去统治市场的幻想。工业级量化系统承认超参数（衰减因子、窗口跨度）的存在，并将其纳入严格的动态归一化与样本外审计体系。绝不用带有事后修正（Revision）的宏观数据污染微观量价的真实散度。

---

## 2. 危机钝化修正：动态基线与绝对水位锁 (The Anti-Boiling-Frog Mechanism)

系统必须适应微观体制的变迁，但绝不能在连环崩盘中“习惯高波动”而解除武装。

### 2.1 动态实证基线 (Empirical Baseline)
采用滚动指数移动平均 (EMA) 提取当前市场体制下的惊奇度基线：
$$Baseline_t = \text{EMA}(S_{micro, t}, span_{base})$$

### 2.2 绝对高水位锁 (Absolute High-Water Mark Lock)
为了防止连环崩盘（Volatility Clustering）导致的基线被动抬高，必须引入基于全局历史极值的硬性风控介入：
定义超长周期（如 7 年 / 1764 个交易日）的滚动 99 分位数，确保绝对水位锁具备年代际的自适应能力，避免被“世纪末日”的极值永久绑架：
$$S_{99th, t} = \text{Percentile}(S_{micro, t-1764...t}, 99\%)$$
**修正后的有效惊奇惩罚 (Effective Surprisal Penalty)**:
$$Penalty_t = \exp\left( \max(S_{micro, t} - Baseline_t, \ S_{micro, t} - S_{99th, t}) \right)$$
- **物理意义**: 在正常的震荡市，系统依靠动态 $Baseline_t$ 吸收常规噪音；一旦惊奇度突破历史 99% 的绝对极值（真崩盘），无论短期 EMA 基线被抬得有多高，惩罚机制立即接管，系统强制降杠杆，**绝不允许在深渊中“习惯高波动”。**

---

## 3. 散度套利：废除常数缩放，强制动态归一化 (Dynamic Z-Score Normalization)

废弃使用静态常数 $\kappa$ 强行缩放 Tanh 函数的伪连续。必须让信号在当前波动率体制下自然映射。

### 3.1 动态信号归一化
定义原始方向动量积：
$$Raw\_Signal_t = (\mu_{macro\_t} - \mu_{macro\_t-1}) \cdot (\mu_{micro\_t} - \mu_{micro\_t-1})$$
计算该信号在过去 $span_{base}$ 窗口内的滚动均值 $\mu_{signal}$ 与标准差 $\sigma_{signal}$。
**Z-Score 归一化 (防分母坍缩)**:
引入长期信号波动率下限 $\epsilon_{vol}$（如过去 5 年标准差的 10 分位数），确保在极度死水的低波动率体制下，不会因为分母趋近于 0 而无限放大噪音：
$$Z\_Signal_t = \frac{Raw\_Signal_t - \mu_{signal}}{\max(\sigma_{signal}, \epsilon_{vol})}$$

### 3.2 连续散度乘数 (Smooth Edge Multiplier)
将归一化后的 Z-Score 喂给双曲正切函数，生成真正的连续方向对齐分数：
$$Alignment\_Score_t = \tanh(Z\_Signal_t) \in [-1, 1]$$
$$M_{edge} = \exp\left( Alignment\_Score_t \cdot JSD(P_{macro} || P_{micro}) \right)$$
- **物理意义**: 系统自动根据近期的信号波动率来判断当前的宏微观共振是否“显著”。只有统计学上显著的共振（Z-Score 大于 1 或 2），才能撬动 Tanh 的非线性两端，触发真正的猎杀或防守。

---

## 4. 大一统动力学方程 (The Dynamical Equation)

$$Final\_Target\_Beta = \frac{\mu_{macro} \cdot M_{effective\_edge}}{\sigma_{macro}^2 \cdot Penalty_t}$$
*(其中 $M_{effective\_edge}$ 经过微观模型 Brier Score 的 Softplus 置信度加权衰减)*

---

## 5. 铁血审计：ALFRED 初值与 WFO 滚动步进

一切脱离真实数据与样本外测试的回测都是诈骗。

### 5.1 ALFRED (ArchivaL FRED) 初值隔离定律
**严禁使用滞后的现值数据。** 宏观 $P_{macro}$ 的计算，必须严格调用美联储 ALFRED 数据库中**当时当刻 (Point-in-Time) 发布且未经任何事后修正的初值 (Vintage Data)**。
- 若当日 ALFRED 无数据发布，强制沿用前值（Forward Fill）。
- **证伪逻辑**: 如果在真实的“脏数据、初值数据”下，微观与宏观的 JSD 散度丧失了预测力（信息比率 IR 断崖式下跌），则宣布本策略失效。系统绝不能靠“未来函数”盈利。

### 5.2 WFO 滚动样本外测试 (Walk-Forward Optimization)
系统承认并显式定义了超参数空间 $\Theta = \{\alpha_{decay}, span_{base}, \gamma_{brier}\}$。
- **严禁全局最优**: 严禁在全量历史数据上进行网格搜索寻找最优夏普比率。
- **WFO 机制**: 
  1. 使用 $T_{-7}$ 至 $T_0$ 的七年数据进行参数优化（Maximize IR），以确保覆盖完整的宏观扩张与收缩周期（朱格拉/基钦周期），彻底消灭对单一加息/降息周期的过拟合。
  2. 冻结参数 $\Theta_{opt}$，在 $T_0$ 至 $T_{+1}$ 的一年数据上进行**纯样本外 (Out-of-Sample) 前向步进测试**。
  3. 窗口向前滚动 1 年，重复步骤 1 和 2。
- **证伪逻辑**: 如果拼接后的纯样本外收益曲线（OOS Equity Curve）相对于样本内（IS）发生系统性崩溃或长期回撤，即判定模型陷入结构性过拟合，模块退回研发池。

---
© 2026 QQQ Entropy 量化风控与实盘工程组.
