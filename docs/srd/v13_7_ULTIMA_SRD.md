# SRD-v13.7-ULTIMA: QQQ Bayesian Orthogonal Factor Monitor

**Version**: 13.7-ULTIMA (GOLD-FINAL)  
**Status**: ARCHITECTURE SEALED  
**Architect**: Gemini CLI / Senior Systems Architect  
**Sealed By**: Tech Leader, ML Tuning Expert, UI/UX Engineer, Final User  
**Date**: 2026-04-03

---

## 1. 架构目标 (Objective)
彻底解决冷启动高熵混沌，引入“实体经济重力”感知，实现基于 8 年历史马尔可夫记忆的理性防御。通过多层审计，达成统计严谨性与实战生存哲学的终极平衡。

---

## 2. 核心数值内核 (Numerical Core)

### 2.1 深度锚定预热 (Deep Hydration - FR-1)
*   **基准**: 强制执行从 **2018-01-01** 至今的全量历史序列回放（2154 样本）。
*   **目标**: 构建具有长期自洽性的先验分布（Counts）与转移矩阵。
*   **PIT 严谨性**: 预热过程严格模拟 T+0 决策，严禁使用日后修正数据（Revised Data）。

### 2.2 似然度锐化与非对称 Tau (Asymmetric Sharpening)
*   **算法**: 针对不同因子类别应用差异化平滑参数。
*   **金融核心 (Level 1-2)**: $\tau=0.5$ (保持稳健惯性)。
*   **宏观/动量 (Level 3-4)**: $\tau=0.35$ (提升边际恶化的穿透力)。
*   **解耦**: 所有参数由 `v13_4_weights_registry.json` 统一驱动。

### 2.3 特征血统归一化 (Lineage Normalization)
*   **逻辑**: 对同一原始因子衍生的特征（如动量、加速度）执行权重平摊。
*   **目的**: 防止因特征冗余导致的似然度过载与后验概率过度偏移。

---

## 3. 实体信号注入 (Real-Economy Gravity)

### 3.1 12 因子特征空间 (FR-7)
*   **PMI 动量 (pmi_momentum)**: 21d EWMA 平滑 + 3个月窗口加速度。
*   **劳动力松弛 (labor_slack)**: 21d EWMA 平滑 + 职位空缺/失业率 Z-Score。
*   **平滑逻辑**: 强制使用 21 日 EWMA 消除月度数据的阶梯跳变（Aliasing Defense）。

### 3.2 传导路径权重 (Weight Matrix)
*   Level 1 (2.5x): `credit_spread_bps`, `erp_ttm_pct` (定海神针)。
*   Level 2 (2.0x): `net_liquidity`, `real_yield` (定价引力)。
*   Level 3 (1.5x): `pmi_momentum`, `labor_slack` (实体预警)。

---

## 4. 防御与熔断协议 (Defense Layers)

### 4.1 ULTIMA 熔断机制 (FR-13)
*   **触发**: 高熵持续天数 > 21d。
*   **动作**: 强制切除所有非核心感官（Level 2-5 权重归零），回归信贷基本盘。

### 4.2 二阶动力学阻尼 (FR-12)
*   **置信度映射**: $Confidence = \exp(-0.6 \cdot H^2)$。
*   **物理意义**: 在高熵冲突区加速脱离风险，但通过阻尼 $k=0.6$ 防止自杀式减仓。

### 4.3 用户红线 (User Redline - FR-4)
*   **底线锁定**: 推荐仓位 `target_beta` **永久锁定不低于 0.5**。
*   **优先级**: 业务红线高于一切统计防御逻辑。

---

## 5. 全息监控规范 (Visibility)

### 5.1 Discord & Web 对齐 (UX-01)
*   **变色逻辑**: 触发 0.5 底线拦截时，标题变橙 (`#FFA500`)，Web 数值变黄 (`amber-400`)。
*   **透明元数据**: 透传 `hydration_anchor`, `raw_target_beta`, `q_core_val`。

---

## 6. 验证协议
*   **单元测试**: 100% 通过（含对齐后的质量评分断言）。
*   **Hash Check**: 锁定 `sha256:bab03...` 契约。

---
**核准状态**: FINAL SEALED (v13.7-ULTIMA)
