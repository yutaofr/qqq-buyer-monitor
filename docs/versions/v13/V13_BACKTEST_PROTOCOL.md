# v13 Backtest Protocol

**Status**: LOCKED  
**Version**: v13.4 / 2026-04-06 governance refresh  
**Parent Spec**: `V13_EXECUTION_OVERLAY_SRD.md`

## 1. Purpose

本协议定义唯一合法的 v13/v11 主链路回测方式。

回测的目标不是“复刻一个看起来差不多的研究版引擎”，而是：

- 用冻结历史输入重放生产 `V11Conductor`
- 验证执行层与物理约束是否改善了真实危机场景
- 拒绝任何通过回测侧偷偷换模型、换先验、换特征来“修漂亮成绩”的做法

## 2. Black-Box Rule

所有回测链路必须把生产链路视为黑盒。

允许：

- 回测构造 frozen `t0` 历史输入
- 回测逐日实例化 `V11Conductor`
- 回测读取生产链路输出的 posterior / beta / deployment / diagnostics / snapshot

禁止：

- 在回测模块里重写 `GaussianNB` 训练与推断主流程
- 在回测模块里单独实现另一套 runtime prior、entropy、beta inertia、behavioral guard
- 在回测侧用隐藏参数改写生产特征契约、似然温度、posterior mode、transition 权重

如果回测需要复用生产中的某个环节，必须先把该环节重构进生产模块，再由回测调用生产函数。

## 3. Frozen Inputs

每次认证回放必须冻结以下输入：

- pinned code revision
- pinned `regime_audit.json`
- pinned `v13_4_weights_registry.json`
- pinned `macro_historical_dump.csv`
- pinned `v11_poc_phase1_results.csv`
- pinned `qqq_history_cache.csv`
- pinned evaluation start / end window

任何缺失都必须 fail closed。

## 4. Data Source Rules

回测不允许 mock FRED 或任何正式数据源。

允许：

- 使用已归档、已 PIT 校验的历史数据文件
- 将云存储替换为本地 artifact 路径

禁止：

- CI / 回测运行时临时下载新市场数据
- moving end date
- synthetic backfill 掩盖缺失源
- mock FRED / mock release timeline / mock publication lag

如果确需刷新价格缓存，必须显式提供 pinned `end_date`，不能使用动态 `today`。

## 5. Config Parity Rule

回测只接受生产链路控制参数：

- `overlay_mode`
- `price_cache_path`
- `price_end_date`
- `allow_price_download` 仅限显式、带 `end_date` 的缓存刷新
- `save_plots`

回测禁止接受以下“研究捷径”参数：

- `var_smoothing`
- `posterior_mode`
- `probability_seeder`
- `audit_overrides`

这些配置如果要变，必须先修改生产配置文件，再回测新的生产配置。

## 6. Forensics Requirement

生产主链路必须为每个回放日保存法医快照。

最小法医工件：

- runtime priors
- prior details / stress score
- feature vector
- quality audit
- posterior penalties
- price topology state
- final execution payload

回测工件必须反向引用这些快照，而不是只输出 top-1 regime。

## 7. Validation Discipline

必须使用时间阻塞的 walk-forward。

要求：

1. 每日训练视角只能看到 `t-20BDay` 之前的信息。
2. 回测窗口中的每一天都必须重新实例化生产 conductor。
3. 最终报告必须区分 validation 与 OOS。
4. 结论优先看中位稳定性与危机覆盖，而不是单一窗口收益最大化。

## 8. Overfitting Rejection

以下任何一项成立则候选方案拒绝：

- 只能修好单一危机窗口
- 通过 lowering tau / changing feature subset / hidden override 才能工作
- 价格侧灰犀牛只能靠“看清黑天鹅”式过拟合似然来触发
- 不能从 frozen artifacts 重放出同样结论

2018Q4 的治理优先级应放在执行层物理约束、价格拓扑耦合、法医诊断可解释性，而不是继续对贝叶斯核做 event-picked tuning。

## 9. Acceptance Outputs

认证回测至少输出：

- `summary.json`
- `probability_audit.csv`
- `execution_trace.csv`
- `full_audit.csv`
- `forensic_trace.jsonl`
- fidelity / audit figures

## 10. Acceptance Gate

只有满足以下条件才可视为通过：

- 回测完全走生产 `V11Conductor`
- 无 live-download 漂移
- 无 hidden model override
- 生产法医快照完整可追溯
- 危机窗口的 `MID_CYCLE` 塌缩显著缓解
- `BUST` / `RECOVERY` 切换可通过 posterior、beta、forensics 三条证据链同时解释
