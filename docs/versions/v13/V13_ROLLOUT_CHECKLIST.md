# v13.7-ULTIMA Rollout & Implementation Checklist

> **Final Verification before Production Merge**

## 1. 数值内核对齐 (Numerical Core)
- [ ] **8-Year Hydration**: 确认已生成 `data/v13_6_ex_hydrated_prior.json` 并包含 2000+ 样本。
- [ ] **Asymmetric Tau**: 验证 registry 中的 `inference_tau` 设定为 0.5 (Financial) / 0.35 (Macro)。
- [ ] **Lineage Norm**: 通过 `test_v13_4_inference.py` 验证衍生特征未产生权重溢出。
- [ ] **Z-Score Warm-up**: 确认回演已使用 2017 年数据预热窗口。

## 2. 安全红线校验 (Safety Redlines)
- [ ] **User Redline**: 验证代码中 `target_beta = max(0.5, ...)` 的硬拦截。
- [ ] **ULTIMA Breaker**: 模拟 21 天高熵死锁，确认传感器自动切除逻辑触发。
- [ ] **PIT Check**: 运行 `test_pit_compliance.py` 确保特征工程无未来泄漏。

## 3. 全息透明度验证 (Transparency)
- [ ] **Discord**: 触发 `is_floor_active` 场景，确认标题变色 (#FFA500) 且 Footer 显示 2018 锚点。
- [ ] **Web UI**: 确认页脚显示 `v13.7-ULTIMA` 且 Beta 数字在锁定态显示为 Amber-400。
- [ ] **Diagnostics**: 确认 snapshot.json 包含 `v13_4_diagnostics` 贡献度数据。

## 4. 基础设施合规 (Infrastructure)
- [ ] **Docker-Ready**: 全量 `pytest` 在容器内 100% 通过。
- [ ] **Ruff**: 源码通过逻辑完整性扫描，无未定义引用。
- [ ] **Registry**: `v13_4_weights_registry.json` 已正确放置在 `resources/` 目录下。

---
**核准**: Gemini CLI (Architect)
**日期**: 2026-04-03
