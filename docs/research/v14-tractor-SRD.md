這份 SRD 將徹底剝離你對高維數學的浪漫幻想。它不包含任何關於「狀態機」、「凱利散度」或「熱力學」的修辭。這是一份關於生存、魯棒性（Robustness）與絕對防禦的工程圖紙。
把它寫入你的程式碼庫，命名為 V_Baseline。在你的 V12 能夠在樣本外（Out-of-Sample）顯著擊敗它之前，這個「泥地拖拉機」就是你實盤唯一應該信任的總司令。
SRD (System Requirements Document): V_Baseline (Mud Tractor) 判別式尾部風險過濾器
Document Status: PRODUCTION BASELINE (The Champion) Target Audience: System Architect / Core Quant Engineer / Claude Code Terminal Affected Modules: src/engine/baseline/ (全新獨立目錄，嚴禁依賴任何 V11/V12 的底層推斷組件)
1. 架構哲學與核心定位 (Architecture Philosophy)
拋棄生成，擁抱判別：不再試圖擬合宏觀經濟的資料生成過程 P(X|Regime)，承認在 120 個月頻樣本下這是不可能完成的任務。直接求解 P(Crisis|X)。
拒絕黑盒降維：廢除 PCA 和流形學習。機器的線性代數在小樣本下會失效，但經濟學常識不會。用硬編碼的結構化聚合（Structural Composites）替代數據驅動的特徵提取。
單一目標：它不預測明天是漲是跌，也不預測是否處於「繁榮」。它的唯一目標是：過濾掉那些可能導致系統性毀滅的尾部左偏分佈（Left-tail Drawdowns）。
2. 結構性特徵工程 (Structural Dimensionality Reduction)
嚴格限制輸入維度為 3。嚴禁添加第 4 個特徵，否則在 120 個樣本下將直接引發過擬合。所有底層物理特徵在進入聚合前，均需計算基於歷史滾動視窗的 Z-Score。
2.1 Growth Composite (增長動能軸)
衡量實體經濟的擴張/收縮速率。
輸入：ISM_Manufacturing (PMI 絕對值或 YoY), Corporate_Profit_Margin_YoY (企業利潤率動能)。
聚合邏輯（算術平均）：
2.2 Liquidity Composite (流動性水位軸)
衡量市場資金的寬裕程度與信用擴張意願。
輸入：Real_Money_Supply_YoY (實際貨幣供給增速), Yield_Curve_Slope (10Y-2Y 期限利差)。
聚合邏輯（算術平均）：
2.3 Stress Composite (尾部恐慌軸) - [CRITICAL]
衡量金融系統底層的流動性擠兌與恐慌蔓延。
輸入：Credit_Spread (高收益債信用利差), VIX_36m_Z (VIX中長期偏離度)。
聚合邏輯（極值保留）： 絕對禁止使用平均數。危機的爆發是非線性的，利差和 VIX 只要有一個爆表，就是致命的。
3. 目標定義與模型拓撲 (Target & Model Topology)
3.1 物理目標變數 Y (Target Definition)
拋棄模糊的 BUST 標籤，定義絕對的物理紅線。
目標 Y=1：在未來的 T+1 到 T+20 個交易日內，標普 500 指數出現大於 8% 的最大回撤（Maximum Drawdown），或 VIX 突破 30。
目標 Y=0：未觸發上述極端條件。
3.2 核心推斷引擎 (The Inference Engine)
使用帶有強正則化的邏輯斯迴歸（L2-Regularized Logistic Regression / Ridge Logistic）。
輸入特徵矩陣 X：[C_{growth}, C_{liquidity}, C_{stress}]。
正則化約束：強制開啟 L2 懲罰項（Penalty），懲罰係數 C 需通過交叉驗證設定在較強區間（如 C \le 1.0），死死壓住權重，防止對特定噪音特徵的過度依賴。
輸出：\hat{p} = P(Y=1|X)。即未來一個月內爆發系統性危機的概率。
4. 雙軌制競技場協議 (The Arena Protocol)
這台拖拉機將作為 V12 的「照妖鏡」。
影子運行：V_Baseline 與 V12 在實盤或樣本外回測中同步接收 ALFRED 資料，同步輸出風險概率。
決策熔斷機制：在並行測試期間，若 V_Baseline 輸出的 \hat{p} > 0.75（高度危機預警），而 V12 依然輸出 BOOM 或高 Beta 敞口，強制採信 V_Baseline 的結果，執行風控降倉。
淘汰法則：經過完整的一年樣本外步進測試（Walk-Forward），使用 Brier Score（均方概率誤差）評估兩者的概率校準度。若 V12 的 Brier Score 高於（劣於）V_Baseline，直接將 V12 代碼庫歸檔廢棄。
5. 驗收標準 (Acceptance Criteria - The Falsification Tests)
如果你連這三個最基礎的機器學習常識測試都通不過，就不要再談論任何高級架構。
AC-1 (代碼極簡約束)：src/engine/baseline/ 目錄下的核心特徵構建與推斷代碼，合計不得超過 200 行。嚴禁引入任何複雜的設計模式或抽象類。保持泥地裡的粗糙與直接。
AC-2 (噪音擬合/前向洩露檢驗 - Label Permutation)：
在訓練前，調用 np.random.shuffle(Y) 將目標變數打亂，破壞 X 與 Y 的真實物理聯繫。
重新訓練模型並在測試集上推斷。
通過標準：打亂標籤後的模型，其樣本外 AUC 必須收斂在 0.45 \sim 0.55 之間（純隨機猜測）。若 AUC 顯著偏離 0.5，證明特徵工程中存在嚴重的前向洩露（Look-ahead Bias），必須立即停止開發並清查數據管道。
AC-3 (概率校準度檢驗 - Out-of-Sample Calibration)：
在樣本外測試中，將模型輸出的概率 \hat{p} 劃分為多個區間（如 0-20%, 20-40% ... 80-100%）。
計算每個區間內 Y=1 的實際發生頻率。
通過標準：繪製的校準曲線（Reliability Diagram）必須大致貼合 y=x 的對角線。如果你輸出 80% 的危機概率，歷史上這些點必須真的有大約 80% 發生了暴跌。嚴禁出現概率長期鎖死在 0 或 1 的極端分佈。
執行指令： 這份 SRD 不需要高深的數學推導，它只需要絕對的執行紀律。讓 Claude Code 建立目錄，寫入這三個合成因子和一個邏輯斯迴歸。不要在開發過程中手癢去添加第 4 個因子，不要去平滑 C_{stress}。去把這台拖拉機開進泥地裡。

