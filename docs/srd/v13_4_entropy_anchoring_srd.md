# SRD-v13.4: QQQ Bayesian Orthogonal Factor Monitor - Entropy Anchoring & Full-Stack Transparency

**Version**: 13.4  
**Status**: Sealed for Implementation  
**Architect**: Gemini CLI / Senior Systems Architect  
**Reviewers**: Tech Leader, Senior Data Scientist, UI/UX Engineer (v2 Audit)  
**Date**: 2026-04-03

---

## 3. 功能性需求 (Functional Requirements)

### 3.1 FR-1: 2018 锚定深度回放 (Sequential Replay)
*   **FR-1.1 状态标记**: 必须在 Metadata 中记录 `hydration_anchor: "2018-01-01"`，该字段需透传至 UI 层。

### 3.4 FR-4: 物理参与度底线 (Beta Floor)
*   **FR-4.2 状态判定**: 系统必须计算 `is_floor_active = (protected_beta > raw_target_beta) && (protected_beta == 0.5)`，并将其作为 UI 告警的触发器。

---

## 4. 技术规范 (Technical Specifications)

### 4.5 用户界面数据契约 (User Interface Data Contract)

#### 4.5.1 Discord Payload 扩展
*   **Title Logic**: 若 `is_floor_active == True`，标题强制前缀 `[BETA FLOOR TRIGGERED]`，颜色设为 `#FFA500`。
*   **Fields**: 
    *   `Target Beta`: 显式展示 `final_target_beta` (0.50x)。
    *   `Raw Beta`: 展示未经底线拦截的原始后验值。
    *   `Hydration Status`: 展示锚定日期与回演总样本数。

#### 4.5.2 Web API (/api/v1/weights)
*   **Response Structure**:
    ```json
    {
      "timestamp": "2026-04-03T00:00:00Z",
      "levels": {
        "level1": {"weight": 2.5, "contribution": 0.45, "factors": ["credit_spread"]},
        "level2": {"weight": 2.0, "contribution": 0.30, "factors": ["liquidity", "yield"]},
        "default_fallback": 1.0
      }
    }
    ```

---

## 5. UI/UX 表现层规范 (UX Requirements)

| 场景 | UI/UX 表现要求 (Requirement) |
| :--- | :--- |
| **深度预热中** | Web 端显示骨架屏，状态文案：`Deep Hydration in progress: Replaying 2018-2026...` |
| **触发底线** | Discord 背景色设为 `#FFA500`；Web 端 Beta 数字变为 `Amber-400` 并显示锁定图标。 |
| **透明度展示** | 列表/雷达图实时展示 Level 1-5 权重。高亮核心因子（Credit Spread）的健康度。 |
| **系统就绪** | 预热完成后，页脚显示 `Prior State: v13.4 Anchored @ 2018-01-01`。 |

---

## 6. 验证协议
*   **AC-13**: 验证 Discord Payload 是否包含 `hydration_anchor`。
*   **AC-14**: 模拟 `raw_beta = 0.1` 场景，验证 Discord 标题是否正确跳变为 `[BETA FLOOR TRIGGERED]`。

---
**核准**: Gemini CLI (Architect)
