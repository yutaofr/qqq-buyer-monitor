# QQQ Bayesian Orthogonal Factor Monitor: 系統技術百科 (WIKI_TC)

本百科提供 QQQ 監測系統的建模邏輯、執行機制與技術規格說明，數據與公式均與 v14.0 核心代碼庫嚴格對齊。

---

### 一、 建模邏輯：物理維度與特徵工程

系統將市場動能拆解為多個互為正交的物理維度。每個物理指標派生為 `_pct`（分位數排名）與 `_momentum`（動能）特徵，構成 14 維高維向量輸入。

#### 1. 核心特徵權重矩陣 (Feature Weights)
系統根據物理重要性對似然函數進行加權處理：

| 物理維度 | 代表指標 | 權重 | 技術作用 |
| :--- | :--- | :--- | :--- |
| **信用 (Credit)** | Spread | 2.5x | 提取純粹違約風險脈衝。 |
| **估值 (Valuation)** | ERP | 2.5x | 評估風險溢酬的絕對物理高度。 |
| **流動性 (Liquidity)** | Net Liquidity | 2.0x | 追蹤全球貨幣供應總量約束。 |
| **利率 (Rate)** | Real Yield | 2.0x | 評估折現率重力。 |
| **實體 (Micro)** | PMI, Labor | 1.5x | 偵測企業端與勞動力市場的冷熱。 |
| **系統壓力 (Stress)** | MOVE / Vol | 1.5x | 捕捉固收與波動率市場的斷裂。 |

#### 2. Gram-Schmidt 正交化公式
為了消除因子間的共線性，對 `move` 等因子執行殘差化處理：
$$ x_{i}^{orth} = x_{i} - \frac{\text{Cov}(x_i, x_{ref})}{\text{Var}(x_{ref})} \cdot x_{ref} $$

---

### 二、 貝氏推論引擎 (Bayesian Engine)

系統採用遞迴貝氏框架進行制度估計，並通過以下「硬化參數」鎖定邏輯邊界：

1.  **貝氏乘法原則**: 嚴禁線性加權混合，確保信心累積效應：
    $$ P(R|e) \propto Prior \times Likelihood $$
2.  **標度溫度 (Tau Lock)**:
    - **Base Tau**: 3.0 (用於校準過度自信)。
    - **Acute Tau**: 2.1 (自動應用於 PMI、勞動力等急性動能因子)。
3.  **先驗合成比例 (Prior Blending)**:
    當樣本數 > 100 時，系統強制執行以下比例：
    - **5%** 靜態歷史引力 (Historical Baseline)
    - **65%** 最近記憶 (Recent Posterior)
    - **30%** 制度預測轉移 (Predicted Shift)

---

### 三、 執行機制與防禦層級

1.  **資訊熵懲罰 (Entropy Haircut)**:
    當後驗機率分布混亂（熵高）時，系統自動下修風險暴露。
    $$ \beta_{protected} = \beta_{raw} \cdot e^{-H(P)}, \quad H(P) = -\sum p_i \log_2 p_i $$
2.  **執行紅線 (Execution Redlines)**:
    - **Beta Floor**: 0.5 (物理底線)。
    - **Beta Ceiling**: 1.2 (最高槓桿約束)。
3.  **部署節奏 (Deployment State)**:
    由制度態直接映射：`RECOVERY -> FAST`, `MID -> BASE`, `LATE -> SLOW`, `BUST -> PAUSE`。

---

### 四、 全景稽核數據 (v14.7 Audit Report)

系統在 PIT-Safe OOS 環境下的表現（樣本數：2809）：

| 稽核指標 | Tractor (SPY) | Sidecar (QQQ) |
| :--- | :--- | :--- |
| **OOS AUC Score** | **0.6018** | **0.5782** |
| **OOS Brier Score** | **0.1478** | **0.1564** |
| **AC-2 驗證** | **PASS (0.49)** | **PASS (0.50)** |

---

### 五、 結語

本監測終端不提供任何收益承諾，僅作為基於物理週期與貝氏數學的邏輯外骨骼。

**「數據誠實，邏輯自洽。」**

---
© 2026 QQQ Entropy AI Governance.
*In Math We Trust, In Bayesian We Infer, In Orthogonality We Stand.*
