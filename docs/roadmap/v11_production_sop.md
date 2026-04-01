# V11.5 生产运行 SOP (Standard Operating Procedure)

> **版本:** 2026-03-31 (Convergence Release)  
> **适用入口:** `python -m src.main`  
> **核心基线:** `docs/v11_production_checklist.md`

---

## 1. 运行频率与时点

1. **执行时点**：每个美股交易日收盘并结算完毕后。
2. **推荐窗口**：`18:30-19:00 ET` (北京时间次日凌晨)。此时期权与 FRED 数据已完成清算同步。

## 2. 生产命令

```bash
# 标准生产运行 (含云端同步与 Discord 通知)
python -m src.main

# 调试模式 (输出 JSON 且不保存状态)
python -m src.main --json --no-save
```

## 3. GitHub Actions 自动化架构

1. **`ci.yml`**: 逻辑验证。负责代码审计 (Lint)、V11 原生测试及全样本性能回测。
2. **`deploy-web.yml`**: 生产分发。每日收盘后生成 `status.json` 并推送到 Vercel Blob 的 `prod/` 命名空间。
3. **`discord-signal.yml`**: 生产通知。盘中双时区触发决策提醒。

**约束**：所有工作流必须共享 `runtime.yml` 这一核心底座，确保环境一致性。

## 4. 每日运行流水线 (Lifecycle)

### Step 1: 运行时记忆复活
系统启动后自动调用 `CloudPersistenceBridge` 从 Vercel Storage 的 `prod/` 命名空间拉取：
*   `data/signals.db` (历史轨迹)
*   `data/macro_historical_dump.csv` (DNA 库)
*   `data/v11_prior_state.json` (贝叶斯先验)

若云端缺失，则只能回退到仓库中的 canonical DNA；
若 canonical DNA 也缺失，生产任务必须失败并报警，不允许 synthetic baseline 混入主路径。
若 Blob 列表、鉴权、网络或已存在对象下载失败，则任务也必须立即失败，禁止带着 stale runtime state 继续推断并回写。

### Step 2: 模型 JIT 训练
系统读取 DNA 库，在内存中即时训练 **高斯朴素贝叶斯分类器**。该过程确保模型参数永远捕捉最新的宏观波动模式。

### Step 3: 递归贝叶斯推断
使用前一日的后验概率作为今日先验，结合当日特征向量执行推断。
*   **不确定性定价**：`EntropyController` 计算分布熵，对目标 Beta 执行 Haircut。

### Step 4: 行为守卫与执行
*   **结算锁**：每当发生资产桶切换（如 CASH -> QQQ），强制锁定 1 个交易日。
*   **复苏锁**：危机后恢复期强制锁定，防止频繁进出损耗 Alpha。

### Step 5: 分发与同步
1. 生成 `status.json` 供 Web 端消费。
2. 写入数据库记录。
3. 将最新状态推回云端（覆盖旧有状态，实现进化）。

---

## 5. 故障处置 (Disaster Recovery)

| 场景 | 处置逻辑 |
| :--- | :--- |
| **API 采集失败** | 自动降级。非核心指标注入中性值，记录 Warning。 |
| **Vercel 存储为空** | **冷启动自愈**。系统从仓库内 canonical DNA Bootstrap prior 记忆；若 canonical DNA 缺失则任务失败。 |
| **DB 模式冲突** | **破坏性对齐**。`init_db` 会自动检测并重置不兼容的旧 Schema。 |
| **网络同步中断** | 自动重试。`CloudPersistenceBridge` 执行 3 次指数退避重试。 |

---

## 6. 核心质量准则 (AC)

*   **AC-1 因果隔离**：严禁引入未来函数。
*   **AC-2 数值对齐**：Macro 数据必须采用小数标准（ERP 0.05）。
*   **AC-3 比特级一致**：连续三次运行的结果必须完全一致。

---
**“逻辑决定生存，纪律守护繁荣。”**  
© 2026 QQQ Entropy 决策系统开发组.
