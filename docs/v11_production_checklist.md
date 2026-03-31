# V11.5 发布前终极 Checklist (架构收敛与生产基线)

## 1. 物理层审计 (The Great Purge Audit)
- [ ] **零挂载依赖**：确认 `src/engine/` 下除 `v11/` 外无任何 Python 文件残留。
- [ ] **导入闭环**：通过 `ruff check .` 确认所有模块不再引用已删除的 `Tier0/1/2` 或旧模型。
- [ ] **测试覆盖**：执行 `pytest tests -q`，确认 66+ 项 V11 原生测试 100% 通过。

## 2. 数值一致性铁律 (Numerical Integrity)
- [ ] **ERP/收益率单位**：`macro_historical_dump.csv` 中的 `erp_pct` 和 `real_yield_10y_pct` 必须为 **小数格式**（例：5% 记为 `0.05`）。
- [ ] **量纲统一**：确认 `ProbabilitySeeder` 接收到的特征向量没有单位冲突（信用利差维持 BPS 整数，估值维持小数）。
- [ ] **无固定阈值**：确认风险定价不依赖固定 entropy cutoff；高熵只能连续减仓，不能把防御 beta 拉回更高风险。
- [ ] **反馈闭环**：`_upsert_v11_macro_feedback` 必须强制写入 `ISO-Date` 字符串，严禁带入 `00:00:00` 时间戳污染。

## 3. 云端持久化审计 (Stateless Persistence)
- [ ] **命名空间隔离**：确认 `CloudPersistenceBridge` 在 `main` 分支运行时指向 `prod/`，开发分支指向 `staging/`。
- [ ] **同步完整性**：同步清单必须涵盖 `signals.db` (轨迹), `macro_historical_dump.csv` (DNA), `v11_prior_state.json` (记忆), `status.json` (分发)。
- [ ] **自愈验证**：若 `v11_prior_state.json` 缺失，引擎必须能通过 canonical DNA 库自动完成 prior Bootstrap；若 canonical DNA 缺失，系统必须 fail closed。

## 4. 数据库模式一致性 (Schema Parity)
- [ ] **破坏性同步**：确认 `src/store/db.py` 中的 `init_db` 包含对旧 Schema 的检测逻辑（若缺失 `target_beta` 列则强制 DROP 并重建）。
- [ ] **GHA 兼容性**：确保在无状态的 GitHub Actions 容器中，数据库初始化不会报 `OperationalError`。

## 5. 推理逻辑与风险定价 (Inference Logic)
- [ ] **制度定力**：理解 V11 的“迟到”特质。Regime Stabilizer 会过滤政治嘴炮（如关税噪音），切换制度需要宏观特征的结构性位移。
- [ ] **熵值 Haircut**：确认在 `MID_CYCLE` 状态下，若熵值（Entropy）抬升，系统是否正确执行了 Beta 削减（如从 1.0x 降至 0.8x）。
- [ ] **BUST 执行**：确认在 `BUST` 概率主导时，存量仓位执行去杠杆，增量资金执行 `DEPLOY_PAUSE`。

## 6. Web 分发对齐 (Frontend Distribution)
- [ ] **URL 绝对对齐**：`index.html` 中的 `PROD_BLOB_URL` 必须包含 `/prod/` 路径前缀。
- [ ] **契约同步**：前端 JS 消费的 key（如 `data.signal.entropy`）必须与 `web_exporter.py` 输出的 JSON 结构比特级匹配。
- [ ] **语义解耦**：`raw_regime / stable_regime / deployment_state / execution_bucket` 必须分别导出并按真实语义消费。
- [ ] **数据源状态**：验证在云端同步成功后，仪表盘显示为 `CLOUD_SYNCED` 而非 `LOCAL_FALLBACK`。

## 7. 终极实证 (Triple-Run Validation)
- [ ] **三轮幂等性**：本地生产流水线连续运行三次，输出结果（Regime, Beta, Posterior）必须完全一致。
- [ ] **回测审计**：全样本 `backtest` 必须是 walk-forward causal audit，当前基线约为 `Accuracy 98.71% / Brier 0.0225 / Entropy 0.046 / Lock 0.4%`。

---
**架构师评审签字：** `Gemini-CLI-Architect-V11.5`
**发布日期：** 2026-03-31
