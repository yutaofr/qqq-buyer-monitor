# V14.5 QLD 三線共振雷達引擎 (Resonance Detector Engine) 系統規格書

## 1. 核心設計理念 (Core Philosophy)

本模組被定義為 V11 導體管線 (V11Conductor) 中的**高階戰術信號層**。其設計遵循 QQQ 治理守則，嚴格執行「內生共振 (Endogenous Resonance)」，訊號完全提取自 V11 隱馬可夫模型與貝葉斯推斷引擎的動態輸出，不依賴任何外部滯後指標（如 VIX 系數）。

## 2. 三線共振演算法 (The Triple-Resonance Algorithm)

共振引擎由以下三條物理邏輯鏈匯聚而成：

### A. 風險淨化線 (Risk Clearance)
- **物理指標**：Mud Tractor 概率 ($P_{tractor}$) + QQQ Sidecar 概率 ($P_{sidecar}$)
- **判定門檻**：$P_{tractor} + P_{sidecar} < 0.05$
- **含義**：左尾風險（崩盤風險）與短週期尾部風險同時消失，市場進入「物理安全區」。

### B. 訊息精確線 (Entropy Collapse)
- **物理指標**：正規化資訊熵 (Normalized Entropy, $H_{norm}$) 與高熵連續天數 (Streak)
- **判定門檻**：$H_{norm} < 0.65$ 且 $Streak = 0$
- **含義**：市場資訊流從混沌轉向有序，系統對當前週期的信心度極高。

### C. 中週期主導線 (Mid-Cycle Dominance)
- **物理指標**：Mid-Cycle 後驗機率 ($P_{mid}$)、一階變化率 ($\Delta P_{mid}$) 與二階加速度 ($Acc_{mid}$)
- **判定門檻**：$P_{mid} > 0.40$ 且 $P_{mid} > P_{late}$ 且 ($\Delta P_{mid} > 0$ 或 $Acc_{mid} > 0$)
- **含義**：中週期復甦力量完全壓制末升段衰退力量，且動能具備正向加速度。

## 3. 輸出信號矩陣 (Signal Matrix)

| 動作 (Action) | 物理觸發條件 | 信心度計算 (Confidence) |
| :--- | :--- | :--- |
| **BUY_QLD** | 三線（A, B, C）同時達成共振 | $0.7 + (P_{mid} - 0.4) + (0.65 - H_{norm})$ [Max: 1.0] |
| **SELL_QLD** | A 觸發風險峰值 (T>0.15 或 S>0.10) 或 B 觸發高熵不穩定 (H>0.75) 或 C 出現末升段過度擴張 | $Max(P_{tractor}, P_{sidecar}, P_{late})$ |
| **HOLD** | 未達成買/賣共振閾值 | 0.0 (中性觀望) |

## 4. 工程實施規範 (Engineering Standards)

- **無未來函數**：所有 $\Delta$ 與 $Acc$ 計算僅提取截止至 $t_0$ 的歷史向量。
- **隔離副作用**：共振結果僅作為字典字段注入 `conductor` 輸出，不直接干預 `BehavioralGuard` 的桶位分配，保持物理層的原子性。
- **100% 覆蓋**：所有門檻變更必須通過 `tests/unit/test_resonance_detector.py` 的回歸測試。

---
© 2026 QQQ Entropy AI Governance. V14.5 Revision.
