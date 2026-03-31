# 无状态云原生决策中枢：V11.5 架构设计与状态治理手册

## 1. 物理架构：JIT 模型溯源与数据闭环
V11.5 核心遵循 **"Logic follows Data"** 准则。
*   **JIT 训练架构**：生产容器不依赖任何预训练权重。
    - **Bootstrap**：启动时从 Vercel Storage 同步 `macro_historical_dump.csv`。
    - **Fitting**：在内存中实时拟合 GaussianNB。
    - **Inference**：执行当日推断。
    - **Feedback**：推断结果实时回填至 CSV，实现“在线进化”。
*   **理由**：在分布式无状态环境中，JIT 彻底消除了模型版本与数据版本不匹配的隐患。

## 2. 状态机治理：解决“频繁波动”与“冷启动滞后”的工程方案
为了避免在概率临界区出现频繁换仓（Signal Churn），架构设计了四重过滤与对齐：
1.  **Regime Stabilizer (施密特触发器)**：新制度的后验概率必须连续 $N$ 天超过当前制度，且概率差值大于 $\delta$ 阈值。
2.  **Inertial Beta Mapper (信息熵惯性)**：采用基于 Shannon 熵的 Odds-Ratio 动态屏障。只有累积证据（Evidence）超过当前不确定性阈值时才允许 Beta 切换。
3.  **Smart Priming (冷启动智能对齐)**：检测到 `execution_state` 缺失（T0 运行）时，系统自动跳过惯性屏障，直接将 `raw_beta` 锚定为起始 `current_beta`。这消除了新环境部署首日的默认值滞后。
4.  **Settlement Lock (物理结算锁)**：调仓动作后，系统状态机强制进入 `remaining_cooldown=1` 的死区。

## 3. 持久化层：破坏性 Schema 与审计透明度
*   **审计透明度 (AC-4)**：所有导出至 `status.json` 的信号必须强制解耦 **Intent (意志)** 与 **Action (行动)**。
    - **Raw Target Beta**：贝叶斯核的原始科学推断结果。
    - **Target Beta**：经过惯性映射与行为守卫后的实际执行目标。
    - **目的**：防止审计者将“惯性观察期”误判为“引擎不响应”。

## 4. 系统的优缺点分析 (Trade-offs)
*   **优点**：
    - **确定性**：连续运行三次，结果比特级一致。
    - **自愈性**：核心记忆（Prior JSON）丢失后，可依赖 DNA CSV 自动重建并通由 Smart Priming 立即恢复最优 Beta。
    - **透明度**：意志与行动的分离让量化黑盒变得可解释、可审计。
*   **缺点**：
    - **惯性延迟**：非冷启动状态下，制度切换会比价格拐点延迟 1-2 天。这是为了换取系统在宏观噪声干扰下的**绝对定力**。
