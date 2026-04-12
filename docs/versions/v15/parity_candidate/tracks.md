# tracks.md — V15 Backtest Parity 验证实施轨道
> 全局实施计划 | 架构: architecture.md | SRD: V15_BACKTEST_PARITY_SRD.md

所有节点必须满足：单向依存、不打圈、不出错。必须 100% 只触及允许触碰的修改边缘。

---

## 节点执行规范

### P-01 — 构筑证明组件 `kelly_parity_backtest.py`
- **状态**: `[DONE]`
- **锁定文件**: `scripts/kelly_parity_backtest.py` [NEW]
- **操作原则**:
  - 创建新文件并建立 argparse 入门。
  - 直接调用 `src.backtest.run_v12_audit` (携带 `use_canonical_pipeline=True`)。
  - 承接字典提取推论指标，排版写入规定的 markdown report 及 summary.json。

---

### P-02 — 挂载 Docker 操作台 (CI 扩展)
- **状态**: `[DONE]`
- **锁定文件**: `docker-compose.yml`
- **依赖前置**: P-01
- **操作原则**:
  - 寻至末尾。
  - 追加包含 `image`, `build`, `volumes`, `env_file`, 及 `command` (指向新挂载的 script) 的完整服务设定。

---

### P-03 — 跨域实证运行 (AC-P1 & AC-P2 验收)
- **状态**: `[DONE]`
- **依赖前置**: P-02
- **操作指令**: 
  ```bash
  docker-compose run kelly-parity
  ```
- **验收**:
  1. 命令正常结束，没有发生任何 StackTrace。
  2. 生成报告位于指定文件夹 `artifacts/kelly_parity/`。
  3. 人工核查生成的 `parity_summary.json`，确保记录的 `top1_accuracy` 确落在规定可控的 [0.50, 0.60] 水位区间内。报告 Brier 等指标亦属一致。

---

### P-04 — 基本功能免疫回溯验证 (AC-P3)
- **状态**: `[TODO]`
- **依赖前置**: P-03
- **操作指令**:
  ```bash
  docker-compose run test
  ```
- **验收**: 测试防线未受损，全部历史约束指标为 0 failures。

---

### P-05 — 证据归档提交
- **状态**: `[DONE]`
- **目标**: 将此次清白验真工件推至远程分支，等待 A/B 环境对比组得出数据一锤定音。
- **执行命令**:
  ```bash
  git add scripts/kelly_parity_backtest.py docker-compose.yml
  git commit -m "feat(kelly): establish backtest parity diagnostic tools"
  git push
  ```

---
© 2026 QQQ Entropy AI Governance — V15 Parity Check Tracks
