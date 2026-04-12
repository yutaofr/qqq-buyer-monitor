# Architecture: V15 Backtest Parity Verification
> 支撑文档: `V15_BACKTEST_PARITY_SRD.md` | 关联 PRD: `PRD.md`

---

## 1. 模块划分与新增实体

```
scripts/
└── [NEW] kelly_parity_backtest.py     # 🔓 [Script] 发起带有严控变量参数的回测调用与记录收集

docker-compose.yml 
└── [APPEND] kelly-parity service      # ✅ 提供一键自动化启动指令
```

---

## 2. 接口契约（API Contracts）

### 2.1 `scripts/kelly_parity_backtest.py` 内部调用协定
由于禁止修改现有的 `src.backtest.run_v12_audit`，必须以最高遵循形式通过如下结构发起实参传递：

**直接调用**:
```python
summary_b = run_v12_audit(
    artifact_dir=str(output_dir / "treatment_kelly"),
    use_canonical_pipeline=True,
    # Evaluation Start 等条件应直接由现阶段环境默认获取 (2018-01-01)
)
```

**指标过滤与萃取**: 过滤出的记录将不包含底层所有复杂噪音，只对架构评审组交付以下硬核推断指标：
- `top1_accuracy`
- `mean_brier`
- `mean_entropy`
- `lock_incidence`
- `compared_points`
- `posterior_mode` (透传自 summary_b 控制状态)
- `var_smoothing` (透传自 summary_b 控制状态)

### 2.2 `docker-compose.yml` 追加服务
接口名称为 `kelly-parity`，容器命令应当锁定为运行刚建立好的测试流。环境变量需与其他模块并齐以免丢失 db 环境。

---

## 3. 并行调用拓扑图

```
                [CLI User/CI]
                      │
        docker-compose run kelly-parity
                      │
                      ▼
         [ kelly_parity_backtest.py ]
                      │
           (完全黑盒依赖·不得插手)
                      │
      ┌───────────────┴───────────────┐
      │   src.backtest:run_v12_audit  │
      └───────────────┬───────────────┘
                      │
          Summary Dict 返回推断结果
                      │
                      ▼
    [萃取 Top-1, Brier 并渲染 Markdown/JSON]
                      │
                      ▼
            artifacts/kelly_parity/
         ( parity_report.md + _summary.json )
```

---

© 2026 QQQ Entropy AI Governance — V15 Parity Diagnostics Architecture
