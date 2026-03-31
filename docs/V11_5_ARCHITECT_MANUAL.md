# 无状态云原生决策中枢：V11.5 架构设计与状态治理手册

## 1. 物理架构：JIT 模型溯源与数据闭环
V11.5 核心遵循 **"Logic follows Data"** 准则。
*   **JIT 训练架构**：生产容器不依赖任何预训练权重。
    - **Bootstrap**：启动时从 Vercel Storage 同步 `macro_historical_dump.csv`。
    - **Fitting**：在内存中实时拟合 GaussianNB。
    - **Inference**：执行当日推断。
    - **Feedback**：推断结果实时回填至 CSV，实现“在线进化”。
*   **理由**：在分布式无状态环境中，JIT 彻底消除了模型版本与数据版本不匹配的隐患。

## 2. 状态机治理：解决“频繁波动”的工程方案
为了避免在概率临界区出现频繁换仓（Signal Churn），架构设计了三重过滤：
1.  **Regime Stabilizer (施密特触发器)**：新制度的后验概率必须连续 $N$ 天超过当前制度，且概率差值大于 $\delta$ 阈值。
2.  **Inertial Beta Mapper (惯性平滑)**：计算目标 Beta 的指数平滑路径 $\text{Target}_t = \alpha \cdot \text{Raw}_t + (1-\alpha) \cdot \text{Target}_{t-1}$。
3.  **Settlement Lock (物理结算锁)**：调仓动作后，系统状态机强制进入 `remaining_cooldown=1` 的死区，物理阻断磁盘写与 IO 变更。

## 3. 持久化层：破坏性 Schema 同步策略
*   **问题**：旧版本数据库与 V11.5 的数值标准（Decimal Normalize）存在冲突。
*   **方案**：`init_db` 执行破坏性同步。若检测到列定义不符，立即 `DROP TABLE`。
*   **折衷**：牺牲了旧数据的连续性，换取了全链路数值的一致性。在量化决策中，错误的数据解读（如将 0.05 读作 5.0）比数据丢失更具毁灭性。

## 4. 系统的优缺点分析 (Trade-offs)
*   **优点**：
    - **确定性**：连续运行三次，结果比特级一致。
    - **自愈性**：核心记忆（Prior JSON）丢失后，可依赖 DNA CSV 自动重建。
*   **缺点**：
    - **延迟性**：由于稳定器存在，制度切换会比价格拐点延迟 1-2 天。这是为了换取系统在关税战、政治嘴炮干扰下的**绝对定力**。
