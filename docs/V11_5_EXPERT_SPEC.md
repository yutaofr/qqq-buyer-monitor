# 基于递归贝叶斯推断与信息熵定价的宏观制度引擎技术白皮书 (v11.5)

## 1. 证据空间：非参数化自适应分位数变换 (Adaptive Quantile Mapping)
系统拒绝直接处理具有异方差性和厚尾分布的原始宏观指标。
*   **数学算子**：对原始特征序列 $x_t$，执行自适应 EWMA 分位数转换：
    $$F(x_t; \lambda) = \frac{\sum_{i=0}^t e^{-(t-i)\lambda} \cdot \mathbb{I}(x_i \le x_t)}{\sum_{i=0}^t e^{-(t-i)\lambda}}$$
*   **时域特征衍生**：
    - **位置能级 (Position)**：$F(x_t)$，表征特征在历史长河中的相对分位。
    - **动能矢量 (Momentum)**：$\Delta F(x_t) = F(x_t) - \text{SMA}(F(x), n)$，表征宏观环境变迁的加速度。
*   **解决方案意义**：该映射将 $\mathbb{R}^n$ 空间强制收缩至 $U(0,1)^n$ 超立方体，消除了量纲差异，使得信贷利差（BPS）与 ERP（百分比）在似然估计中具备等权的几何意义。

## 2. 推断核心：递归贝叶斯算子与 JIT 似然标定
*   **JIT 似然估计**：系统不存储静态参数，而是每次运行通过 DNA 库（`macro_historical_dump.csv`）进行实时核密度估计（KDE）或高斯参数拟合。
*   **递归推断公式**：
    $$P(R_{k,t} | \mathbf{e}_t) = \eta \cdot P(\mathbf{e}_t | R_{k,t}) \cdot [ \sum_j P(R_{k,t} | R_{j,t-1}) \cdot P(R_{j,t-1} | \mathbf{e}_{t-1}) ]$$
    其中，$\eta$ 为归一化常数，$P(R_{k,t} | R_{j,t-1})$ 为制度转移矩阵 $T$。
*   **折衷选择（Why GNB over HMM?）**：
    - **可选方案**：隐马尔可夫模型 (HMM)。
    - **折衷点**：HMM 在宏观小样本下极易陷入局部最优且对初始值敏感。我们选择 **GaussianNB + 显式转移矩阵修正**。
    - **理由**：GNB 提供了更强的正则化，且通过递归先验引入了时域连续性，兼具了 HMM 的平滑特征与朴素贝叶斯的泛化定力。

## 3. 风险定价：Shannon 熵 Haircut 算子
*   **不确定性量化**：$H(P) = -\sum_{k \in \mathcal{R}} p_k \log_2 p_k$。
*   **Beta 推出逻辑**：
    $$\beta_{final} = \beta_{base}(R_{max}) \cdot (1 - \text{Clip}(\frac{H(P) - H_{min}}{H_{max} - H_{min}}, 0, 1))^\alpha$$
*   **数学目标**：当后验分布高度极化（确信度高）时，Beta 趋向基准值；当分布趋于均匀（模型犹豫）时，系统自动执行**不确定性减仓**。

## 4. 增量因子进场节奏 (Deployment Pacing)
*   **逻辑方案**：不同于存量仓位的 Beta 管理，增量资金采用 **Kelly-derived Pacing**。
*   **数学解**：基于 Class B 战术特征（如价格回撤深度、短期 VIX 偏离）计算“进场就绪度”。
*   **状态机执行**：`FAST` (2.0x) -> `BASE` (1.0x) -> `SLOW` (0.5x) -> `PAUSE` (0.0x)。
*   **优劣分析**：该方案避免了在主跌浪中过早耗尽现金，确保了“子弹”在 `CAPITULATION`（投降）制度下概率最高时爆发。
