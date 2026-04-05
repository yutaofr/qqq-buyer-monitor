# QQQ 決策系統 v14 技術指南 (v14.0-PANORAMA)

## 核心設計目標：數據完整性與全景校準

v14 的核心任務是解決回測中的數據洩漏（Data Leakage）問題，並通過多維度參數掃描（Panorama Matrix）來驗證信號的穩定性。系統不再追求單一回測路徑的最優化，而是追求在不同參數擾動下的表現一致性。

---

## 1. 決策輸出定義

系統將決策流程拆解為四個可審計的輸出量：

1.  **Raw Target Beta**: 貝氏推論引擎輸出的後驗期望值。反映模型在理想正交輸入下的原始判斷。
2.  **Target Beta**: 最終執行水位。在 Raw Beta 基礎上疊加了資訊熵懲罰與換檔慣性邏輯，用於平滑信號。限制區間為 `[0.5, 1.2]`。
3.  **Sidecar State (^VXN Vitals)**: 專屬波動率數據鏈路狀態。分為 `FULL`（數據完整）與 `DEGRADED`（數據延遲或缺失）。
4.  **Deployment Pacing**: 針對增量資金的投入節奏（FAST, BASE, SLOW, PAUSE）。

---

## 2. 狀態估計與制度定義 (Regime Estimation)

系統根據 14 個正交特徵（7 個物理指標的 Pct 與 Momentum 對）對當前市場環境進行分類：

| 制度標籤 | 技術含義 | 部署節奏 |
| :--- | :--- | :--- |
| **RECOVERY** | 低波動率修復態 | DEPLOY_FAST |
| **MID_CYCLE** | 低熵擴張態 | DEPLOY_BASE |
| **LATE_CYCLE** | 高熵壓力態 | DEPLOY_SLOW |
| **BUST** | 系統性衰退態 | DEPLOY_PAUSE |

---

## 3. 系統硬化與 PIT 安全性 (Data Integrity)

v14 實施了嚴格的因果硬化措施：

1.  **因果標準化 (Causal Normalization)**: 嚴禁使用全局均值。所有分位數排名（Weighted Rank）基於 25 年歷史回放的 EWMA 邏輯。
2.  **Sidecar PIT Validation**: 修正了 ^VXN 數據的同步邏輯。如果在模擬 T 日決策時該數據尚未發布，系統會強制進入 `DEGRADED` 模式。
3.  **數值對齊**: 確保回測稽核與生產環境在相同輸入下誤差為 0。

---

## 4. 貝氏推論約束 (The Trinity Locks)

為了保證模型長期穩定，代碼中鎖定了以下核心參數：

- **計算模式**: 後驗機率僅通過貝氏乘法計算 ($Posterior \propto Prior \times Likelihood$)。
- **溫度標度 (Tau Lock)**: `inference_tau` 鎖定為 **3.0**。其中急性因子（如 PMI、勞動力動能）自動使用尖銳化標度（2.1）。
- **先驗引力 (Prior Gravity Lock)**：成熟期系統強制維持 **5%** 的靜態先驗權重，其餘 95% 分配給最近記憶 (65%) 與制度轉移 (30%)。

---

## 5. 特徵權重矩陣 (Feature Weights)

系統不對所有因子一視同仁，而是根據物理重要性分配固定權重：

- **2.5x (核心軸心)**: 信用利差 (Spread)、股權風險溢酬 (ERP)。
- **2.0x (估值重力)**: 淨流動性 (Net Liquidity)、真實收益率 (Real Yield)。
- **1.5x (實體與壓力)**: 製造業 PMI、勞動力市場 (Labor Slack)、國債波動率 (MOVE)。
- **0.5x - 1.0x (輔助指標)**: 盈虧平衡通膨、銅金比、日圓套息動量。

---

## 6. 全景稽核數據 (v14.7 Audit Results)

### 6.1 核心稽核指標 (2015-01-01 至今)

| 稽核指標 | Tractor (SPY) | Sidecar (QQQ) |
| :--- | :--- | :--- |
| **OOS AUC Score** | **0.6018** | **0.5782** |
| **OOS Brier Score** | **0.1478** | **0.1564** |
| **AC-2 (Shuffled AUC)** | PASS (0.4931) | PASS (0.4961) |

---

## 7. 決策終端元素解讀 (Interface Guide)

### 7.1 指標與儀表
- **Current / Stable Regime**: 系統對當前週期的狀態估計。Stable 版本要求證據持續累積以減少無效交易。
- **Shannon Entropy (資訊熵)**: 衡量後驗分布的混亂度。**物理含義**: 當熵值升高時，系統因數據衝突自動收縮 Beta。
- **Calibration Status**: 傳感器與數據鏈路的健康檢查。

### 7.2 執行疊加 (Armor & Sidecar)
- **Breadth Penalty**: 市場廣度懲罰。當上漲過度集中於少數個股時觸發。
- **Sidecar Prob**: 針對 Nasdaq 100 波動率特性的獨立壓力評估。

---

## 8. 產物索引 (Audit Index)

### 8.1 v14 基石與邊車校準圖
![v14 基石校準](../research/v14_baseline_calibration.png)
![v14 邊車校準](../research/v14_sidecar_calibration.png)

---
© 2026 QQQ Entropy 決策系統開發組
*Grounding in Code, Driven by Physics.*
