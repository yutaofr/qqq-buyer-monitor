# v11 Runtime Storage Contract

> 日期: 2026-03-30
> 适用入口: `python -m src.main --engine v11`
> 相关代码: `src/main.py`, `src/store/cloud_manager.py`, `src/engine/v11/conductor.py`

## 1. 直接结论

### Q1. 为什么今天会显示 `MID_CYCLE 100%`，是不是先验库坏了？

不是先验库单独把系统“拉歪”了。

2026-03-30 的一次真实运行检查结果是：

- `runtime_priors`
  - `MID_CYCLE`: `57.64%`
  - `LATE_CYCLE`: `16.35%`
  - `BUST`: `13.69%`
  - `RECOVERY`: `12.31%`
  - `CAPITULATION`: `0.02%`
- `posterior`
  - `MID_CYCLE`: `100.0%`
  - `LATE_CYCLE`: `~0`
  - `BUST`: `~0`
  - `RECOVERY`: `~0`

这说明当前输出的主因不是 prior 本身，而是 classifier likelihood 在今天的 6 因子向量上直接塌缩到了 `MID_CYCLE`，然后再经过 runtime prior 重加权，结果仍然保持 `MID_CYCLE=1.0`。

也就是说：

1. 先验确实偏向 `MID_CYCLE`，但只是温和偏置，不足以单独把结果推到 `100%`。
2. 真正决定这次显示的是当日观测向量和当前标签体系/训练语料之间的匹配关系。
3. 如果人的宏观判断认为“更像末期或下行期”，优先该审的是：
   - regime 标签体系
   - 6 因子的判别力与缩放
   - 训练样本的近端代表性
   - `GaussianNB` 的类条件分布假设
   - `GaussianNB` 的 `theta_ / var_ / class_prior_` 是否通过了当前的模型完整性校验

不是先把锅甩给 `v11_prior_state.json`。

### Q2. GitHub Actions 里会不会按设计读 Vercel Storage，再写回更新后的 prior？

会，但只针对“运行时可变状态”。

执行顺序在 `src/main.py` 中是：

1. 启动时 `cloud.pull_state(...)`
2. 拉取运行时状态文件到本地工作目录
3. 运行 collectors 和 `V11Conductor.daily_run(...)`
4. 回写 `data/v11_prior_state.json`
5. 追加 `data/macro_historical_dump.csv`
6. 保存 `data/signals.db`
7. 如果不是 `--no-save`，并且在 CI 中，再执行 `cloud.push_state(...)`

当前正式 cloud round-trip 的 runtime 文件只有：

- `data/signals.db`
- `data/macro_historical_dump.csv`
- `data/v11_prior_state.json`

### Q3. 还有什么 runtime 文件需要同步到 Vercel Storage 读取？

当前 active inference path 不需要更多文件。

边界要区分清楚：

- 必须 round-trip 的 mutable runtime state
  - `data/v11_prior_state.json`
  - `data/macro_historical_dump.csv`
  - `data/signals.db`
- 本地 checked-in bootstrap seed，不属于 cloud runtime state
  - `data/v11_poc_phase1_results.csv`
- 已经不在 active runtime path 的旧件，不应继续冒充 runtime state
  - `data/v11_full_evidence_history.csv`
- 单独上传的展示/审计工件，不参与本次推断读链路
  - `status.json`
  - `v11_feature_library.csv`

其中：

- `status.json` 是 dashboard/前端消费工件
- `v11_feature_library.csv` 当前只是单独上传的辅助工件，不是 `v11` 当日推断的必需输入
- 实时单日输入行现在可以携带轻量 provenance 字段，例如 `source_credit_spread`
  - 这些字段不属于 cloud runtime round-trip 清单
  - 它们只用于当日推断中的 data quality penalty，不会替代 canonical DNA

### Q4. 如果 Vercel Storage 为空，或者第一次运行怎么办？

初始化顺序是确定性的，不会因为 blob 为空就随机起步。

顺序如下：

1. `CloudPersistenceBridge.pull_state(...)` 先尝试从 blob 拉取
2. 如果单个 blob 缺失 (`404` / pathname miss)，则退回本地仓库内已有 seed/runtime 文件
3. 如果 `data/v11_prior_state.json` 本地也不存在：
   - `PriorKnowledgeBase` 用 `data/v11_poc_phase1_results.csv` 的历史 regime 标签做 deterministic bootstrap
4. 如果连 `data/macro_historical_dump.csv` / `data/v11_poc_phase1_results.csv` 都缺失或损坏：
   - 生产与审计主路径现在直接 fail closed
   - synthetic bootstrap 仅允许在测试或显式灾备工具中使用
5. 如果 blob 列表、鉴权、网络或已存在对象的下载发生非 `404` 异常：
   - `pull_state(...)` 直接返回 fatal
   - `src.main` 必须中止运行，禁止用潜在 stale state 继续推断并回写

注意：

- synthetic bootstrap 不再是生产初始化方案
- 生产首跑应该优先依赖 checked-in canonical seed，再把第一天生成的 runtime state 推回 blob

## 2. Runtime Storage 边界

### 2.1 Namespace 规则

`CloudPersistenceBridge` 的 namespace 规则是：

- `main` 分支: `prod/...`
- 非 `main` 分支: `staging/<branch>...`

例如本地冒烟时设置：

```bash
GITHUB_ACTIONS=true
GITHUB_REF_NAME=local-env-smoke
```

对应 namespace 就是：

```text
staging/local-env-smoke
```

### 2.2 当前 cloud round-trip 清单

这是 `src/main.py` 中正式保留的最小 runtime 同步清单：

```text
data/signals.db
data/macro_historical_dump.csv
data/v11_prior_state.json
```

云端枚举采用分页 cursor 拉取；对象数量增长后，仍必须完整覆盖当前 namespace 的 blob 视图。

这三项分别承担：

- `signals.db`: 历史信号与运行输入审计
- `macro_historical_dump.csv`: v11 因子上下文与次日 seeder 基线
- `v11_prior_state.json`: 贝叶斯先验/转移记忆/执行态记忆

### 2.3 不再视为 runtime cloud state 的文件

以下文件不再属于 cloud runtime round-trip：

- `data/v11_poc_phase1_results.csv`
  - 角色: checked-in regime seed
  - 性质: bootstrap corpus，不是日更 runtime state
- `data/v11_full_evidence_history.csv`
  - 角色: 历史遗留
  - 性质: 当前 active v11 主路径未消费，也未在每日运行中更新

## 3. 首跑初始化契约

### 3.1 推荐的生产首跑

生产首跑推荐顺序：

1. 仓库内保留 canonical `data/macro_historical_dump.csv`
2. 仓库内保留 canonical `data/v11_poc_phase1_results.csv`
3. 允许 `data/v11_prior_state.json` 缺失
4. 首次 GitHub Actions 运行后自动生成并 push `data/v11_prior_state.json`

### 3.2 不推荐但仍可自愈的场景

如果 canonical baseline 缺失，当前规则是不允许生产/审计继续运行。

因此生产要求是：

1. canonical macro/regime seed 才是唯一允许的初始态
2. synthetic bootstrap 只作为测试或离线灾备工具
3. 首跑后立即把 runtime state 固化到 blob，避免每天重新从初始态起步

## 4. `MID_CYCLE 100%` 的解释口径

当前对外解释必须统一为：

1. `100%` 指的是当天 posterior 分布塌缩，不是 prior 本身等于 `100%`
2. prior 当前只是“偏 mid-cycle”，不是“锁死 mid-cycle”
3. 如果要纠偏，优先重审因子、标签和训练分布
4. 不要把“用户主观宏观判断”和“系统 posterior”混成一个字段

## 5. 显示层口径

v11 Discord 摘要现在应使用：

- `stable_regime` 作为 `Bayesian Regime`
- `raw_regime` 作为明细中的 `Raw Posterior Top-1`
- `Posterior Distribution` 单独展示完整分布

这样可以避免把“稳定状态机输出”和“当天 top-1 后验”混在一起。

## 6. 运维规则

### 6.1 `--no-save`

`--no-save` 是只读烟测：

- 会 pull cloud state
- 会跑完整推断
- 不会回写 `signals.db`
- 不会回写 `macro_historical_dump.csv`
- 不会 push 更新后的 runtime state

### 6.2 生产运行

标准生产运行：

```bash
python -m src.main --engine v11 --export-web
python -m src.main --engine v11 --notify-discord --export-web
```

这两条路径在 CI 中都会：

1. 先 pull runtime state
2. 完成推断
3. 回写 runtime state
4. 单独上传 `status.json`

其中第 1 步的规则是：

- 单个对象缺失 (`404`) 允许冷启动回退
- 非 `404` 的 blob list / auth / network / download 异常必须 fail closed

## 7. 需要持续关注的风险

1. `MID_CYCLE 100%` 这类单点塌缩说明当前 classifier 对近端样本的区分过于自信。
2. `CAPITULATION` 当前几乎没有有效先验质量，仍然是稀疏状态。
3. 任何 synthetic baseline 都不得进入生产或审计主路径。
