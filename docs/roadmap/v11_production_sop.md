# v11 生产环境每日运行标准操作程序 (Standard Operating Procedure)

## 1. 运行节拍 (Timing)
*   **执行频率**: 每个交易日一次。
*   **执行时间**: 16:30 - 17:00 ET (美股收盘后，数据源初步稳定)。
*   **紧急触发**: 若发生全市场熔断 (Circuit Breaker)，手动触发一次以确认是否进入 BLACKOUT。

## 2. 数据采集口径 (Data Ingestion)

| 变量 | 数据源 | T+N 延迟 | 影子代理 (Shadow Proxy) |
| :--- | :--- | :--- | :--- |
| **Credit Spread** | FRED (BAMLH0A0HYM2) | T+1 | 上日收盘 +5bps (保守假设) |
| **VIX / VIX3M** | YFinance (^VIX, ^VIX3M) | T+0 | 实现波动率 (Realized Vol) |
| **QQQ Price** | YFinance (QQQ) | T+0 | 停止运行 |
| **Liquidity** | Fed H.4.1 (WALCL) | T+7 | 线性插值 |

---

## 3. 核心流水线步骤 (The Pipeline)

### STEP 1: 数据清洗与降级审计 (`DataDegradationPipeline`)
*   **动作**: 运行物理常识校验（VIX < 9 判定为脏数据）。
*   **产出**: `cleaned_df` 和 `Quality_Score`。
*   **红线**: 若 `Quality_Score < 0.5`，流水线**立即中断**，信号强制切回 `CASH`。

### STEP 2: 外生记忆更新 (`ExogenousMemoryOperator`)
*   **动作**: 根据当日信贷利差恶化率，计算今日记忆半衰期 $\lambda$。
*   **产出**: `dynamic_lambda_t`。

### STEP 3: 概率推断 (Bayesian Engine)
*   **动作**: 将 `dynamic_lambda` 注入 EWMA 分位数计算，运行 PCA-KDE 模型。
*   **产出**: 后验概率向量 $P(Regime)$。

### STEP 4: 逆转与解冻判定 (`DualAnchorKillSwitch`)
*   **动作**: 检查 VIX 期限结构 Z-Score 是否满足 $Z_{slow} > 3.0$。
*   **产出**: `is_kill_switch_active` (最高优先级)。

### STEP 5: 独裁信号映射与覆盖 (`HysteresisMapper` + `Overrider`)
*   **动作 5.1**: `Mapper` 根据迟滞死区输出建议仓位。
*   **动作 5.2**: `Overrider` 根据 STEP 1 的质量分对建议进行降级（例如 0.7 分则禁止 QLD）。
*   **产出**: **Final_Signal** (QLD, QQQ, 或 CASH)。

---

## 4. 故障处理预案 (Failsafe Actions)

### 场景 A：YFinance API 宕机
*   **现象**: QQQ/VIX 读数为 `NaN`。
*   **对策**: `DataDegradationPipeline` 自动启用 1 日前向填充。Quality Score 降至 0.7。
*   **结果**: 系统仍可运行，但 `Overrider` 自动屏蔽 QLD，仅允许输出 QQQ 或 CASH 指令。

### 场景 B：信用利差数据断流 (FRED 延迟)
*   **现象**: 超过 2 个交易日无更新。
*   **对策**: `AdaptiveMemoryEngine` 锁定在 0.5 年半衰期（极端保守），强制提升 $P(BUST)$ 的先验。
*   **结果**: 系统发出黄色 `SHIELD DEPLOYED` 警告，降级至 QQQ。

### 场景 C：结算锁期冲突
*   **现象**: 用户试图在 T+1 冷却期内二次调仓。
*   **对策**: Dashboard 显示 `LOCKED` 状态，不显示任何新信号。

---

## 5. 每日检查清单 (Daily Checklist)
1.  [ ] 检查 `v11_quality_score` 是否等于 1.0。
2.  [ ] 确认 `kill_switch` 状态是否与 `VIX3M-VIX` 趋势背离。
3.  [ ] 验证 `target_exposure` 是否符合迟滞死区逻辑。
4.  [ ] 存档当日 $P(BUST)$ 的贝叶斯分布截图。

---
*Last Updated: March 2026*
*Architect's Note: Operation over Optimization. Survival over Alpha.*
