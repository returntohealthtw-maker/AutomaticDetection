# SDK 資料需求 與 後端演算法規格
> 解答：SDK只給原始腦波數據，後端自行運算所有報告數值（含MBTI多性格交互）

---

## 一、結論先說

✅ **完全可行。** 只要 SDK 每秒提供以下 11 個原始數值，我們後端就能運算報告中的全部數值，包括 MBTI 強弱比例與多性格交互。

---

## 二、需要 SDK 廠商提供的最小數據集

### 每秒回呼一次（必要，共 11 個欄位）

```
SDK Callback：onEEGData(data)

必要欄位（11個）：
─────────────────────────────────────────────────────
欄位名稱          型別     說明
─────────────────────────────────────────────────────
theta             Float    θ波原始功率（4–8 Hz）
alpha_high        Float    α↑高子頻帶功率（10–13 Hz）
alpha_low         Float    α↓低子頻帶功率（8–10 Hz）
beta_low          Float    β↓低子頻帶功率（13–20 Hz）
beta_high         Float    β↑高子頻帶功率（20–30 Hz）
gamma_low         Float    γ↓低子頻帶功率（30–35 Hz）
gamma_high        Float    γ↑高子頻帶功率（35–100 Hz）
smr               Float    SMR功率（12–15 Hz）【可選，若裝置能提供】
attention         Int      專注力分數（0–100，eSense演算法）
relaxation        Int      放鬆度分數（0–100，冥想演算法）
signal_quality    Int      訊號品質（0=良好 1=微弱 2=噪音）
─────────────────────────────────────────────────────

注意：
• 功率值建議使用「相對功率（0–1的浮點數）」或「μV²」，單位需固定一致
• 「每秒一次」指的是「每秒輸出一個平均值」（設備可能內部以 512Hz 採樣，
  但對外回呼時輸出1秒的均值即可）
• signal_quality = 2（噪音）的筆數不計入有效採集，不影響報告品質
```

> ⚠️ **關於 Fp2：** 您已確認裝置只有 Fp1，**無法計算 FAA（前額葉 Alpha 不對稱性）**。
> 本文件第五節說明替代方案。

---

## 三、我們後端自行計算的全部數值

> SDK 只需給以上 11 個原始值，以下所有數值**全由後端運算**，無需 SDK 提供。

### 3-A 後端即時計算（每秒）

```
每秒收到 11 個原始值後，後端立即計算：

1. 各頻帶正規化分數（0–100%）
   → 用前30秒靜息基線正規化（見第四節）

2. FAA 替代指標（E/I 單通道法）
   → single_channel_EI = (beta_high - alpha_avg) / (beta_high + alpha_avg)
   → alpha_avg = (alpha_high + alpha_low) / 2

3. 即時狀態標籤（App畫面顯示用）
   → 主導頻帶 = max(theta, alpha_high, alpha_low, beta_low, beta_high, gamma_low, gamma_high)
   → 壓力水平 = PLI = (beta_high + theta) / (alpha_low + smr)
   → 專注狀態 = CCR = beta_high / theta
```

### 3-B 後端場次結束後計算（3分鐘完成後）

以下為所有報告內容所需計算的全部數值：

```
【輸入】：180秒 × 11個原始值 = 1980 個浮點數

【後端計算輸出】：

一、基礎統計（每個頻帶計算）
  avg_theta, avg_alpha_high, avg_alpha_low,
  avg_beta_low, avg_beta_high, avg_gamma_low, avg_gamma_high
  avg_attention, avg_relaxation
  → 各頻帶的 180秒均值

  peak_theta, peak_alpha_high, ...   → 各頻帶的最高值（波峰）
  trough_theta, trough_alpha_high,...→ 各頻帶的最低值（波谷）
  std_theta, std_alpha_high, ...     → 各頻帶標準差（穩定性）

二、9大指標正規化（0–100%）
  score_theta       = 正規化(avg_theta)        → θ直覺 %
  score_alpha_high  = 正規化(avg_alpha_high)   → α↑氣血 %
  score_alpha_low   = 正規化(avg_alpha_low)    → α↓安定 %
  score_beta_low    = 正規化(avg_beta_low)     → β↓邏輯 %
  score_beta_high   = 正規化(avg_beta_high)    → β↑執行 %
  score_gamma_low   = 正規化(avg_gamma_low)    → γ↓慈悲 %
  score_gamma_high  = 正規化(avg_gamma_high)   → γ↑觀察 %
  score_attention   = avg_attention            → 專注力 %（已是0-100不需轉換）
  score_relaxation  = avg_relaxation           → 放鬆度 %

三、大腦運作模式（報告第1-2章）
  理性思維群 = (score_beta_high + score_beta_low) / 2
  直覺感知群 = (score_theta + score_alpha_low) / 2
  環境意識群 = (score_gamma_high + score_gamma_low) / 2
  主導模式   = max(理性, 直覺, 環境) 對應的名稱

四、峰谷分析（報告第1-3章）
  全局最高波 = max(9個score中最大值)  → 最高腦波名稱+數值
  全局最低波 = min(9個score中最小值)  → 最低腦波名稱+數值
  兩極落差   = 全局最高 − 全局最低
  主導波強度 = (全局最高 / 平均值) × 50  → 百分比

五、全腦平衡指標（報告第1-4章）
  滋養指數   = (score_theta + score_alpha_low + score_gamma_low) / 3
  張力指數   = (score_beta_high + score_gamma_high) / 2
  滋養壓力比 = 滋養 / (滋養 + 張力) × 100
  腦均程度   = 100 − (9個score的標準差 / 9個score的均值 × 100)

六、MBTI（報告第2章）→ 詳見第五節

七、家庭影響（報告第3章）
  父性影響力   = (score_beta_low + score_beta_high) / 2
  母性影響力   = (score_theta + score_alpha_low + score_gamma_low) / 3
  情感安全感   = score_alpha_low
  家族壓力傳承 = (score_theta × 0.6 + score_gamma_low × 0.4)
  情感壓抑指數 = 100 − (score_gamma_low × 0.76)
  依附創傷指數 = max(0, (45 − score_alpha_low) × 0.8)
  過度警覺指數 = score_beta_high
  深層情緒積累 = score_theta

八、性格成熟與壓力（報告第2-4章）
  穩定指數   = score_alpha_low
  壓力敏感度 = score_beta_high
  成熟模式比 = 穩定 / (穩定 + 壓力敏感度) × 100
```

---

## 四、正規化方法（原始值 → 百分比）

```
步驟一：採集前30秒靜息基線
  baseline[band] = 第1–30秒 的 avg(raw[band])

步驟二：計算相對比率
  ratio[band] = raw_avg[band] / baseline[band]

步驟三：映射到 0–100%
  score = clamp(ratio × 50, 0, 100)
         = clamp((raw_avg / baseline) × 50, 0, 100)

  說明：
  ratio = 0.0 → score = 0%   （完全沒有此波）
  ratio = 1.0 → score = 50%  （與基線相同，中等）
  ratio = 2.0 → score = 100% （是基線的2倍，極高）

特殊處理：
  attention 和 relaxation 已是 0–100 整數，直接使用，不需正規化
  若靜息期 < 10秒（裝置連線慢），改用族群常模作為 baseline
```

---

## 五、MBTI 演算法（Fp1 單通道版）

### 5-A FAA 替代方案（只有 Fp1 的情況）

```
由於只有 Fp1（左前額葉），無法計算 FAA（左右不對稱）
改用「Beta-Alpha 相對強度法」判斷 E/I：

原始 FAA 法（需要 Fp1 + Fp2）：
  FAA = ln(Fp2_alpha) − ln(Fp1_alpha)   ← 無法使用

替代法（僅需 Fp1）：
  E/I_raw = (beta_high − alpha_avg) / (beta_high + alpha_avg)
  alpha_avg = (alpha_high + alpha_low) / 2

  E/I_raw > +0.10 → 外向(E)傾向
  E/I_raw < −0.10 → 內向(I)傾向
  −0.10 ~ +0.10  → 中間型(mx)

  E_score(%) = clamp((E/I_raw + 1) / 2 × 100, 0, 100)
               → 50% = 中間，> 50% = E，< 50% = I
```

### 5-B 四維度 MBTI 計算公式

```
E/I 外向-內向（使用替代法）：
  E_raw = (score_beta_high × 0.5 + score_gamma_high × 0.3 + score_attention × 0.2)
  I_raw = (score_alpha_low × 0.5 + score_relaxation × 0.3 + score_theta × 0.2)
  E% = E_raw / (E_raw + I_raw) × 100

N/S 直覺-感知：
  N_raw = (score_theta × 0.5 + score_gamma_low × 0.3 + score_alpha_low × 0.2)
  S_raw = (score_beta_low × 0.5 + score_beta_high × 0.3 + score_alpha_high × 0.2)
  N% = N_raw / (N_raw + S_raw) × 100

T/F 思考-情感：
  T_raw = (score_beta_low × 0.5 + score_beta_high × 0.3 + score_alpha_high × 0.2)
  F_raw = (score_gamma_low × 0.4 + score_theta × 0.3 + score_alpha_low × 0.3)
  F% = F_raw / (T_raw + F_raw) × 100   ← 注意：報告顯示 F%（情感%）

J/P 判斷-認知：
  J_raw = (score_beta_high × 0.5 + score_beta_low × 0.3 + score_alpha_high × 0.2)
  P_raw = (score_alpha_low × 0.4 + score_theta × 0.4 + score_gamma_low × 0.2)
  J% = J_raw / (J_raw + P_raw) × 100

→ 主類型 = 組合(E或I, N或S, T或F, J或P)，各維度取 50% 為分界線
```

### 5-C 多重 MBTI 性格出現與交互作用 ✨

這是最關鍵的功能。180秒的腦波資料可以顯示**哪些性格在不同時段交替出現**。

#### 方法：6段時間窗口分析

```
將 180 秒分為 6 個窗口，每窗口 30 秒：
  段1:  第  1 – 30 秒
  段2:  第 31 – 60 秒
  段3:  第 61 – 90 秒
  段4:  第 91 – 120 秒
  段5:  第 121 – 150 秒
  段6:  第 151 – 180 秒

對每個窗口分別計算 MBTI 類型：
  → 每段得出 E/I%, N/S%, T/F%, J/P% 和對應的 MBTI 代號

結果示例：
  段1: ENFJ（E=58, N=62, F=54, J=57）
  段2: ENFJ（E=55, N=65, F=51, J=52）
  段3: ENTP（E=52, N=60, F=48, J=44）← T/F 和 J/P 翻轉
  段4: ENFJ（E=57, N=59, F=53, J=55）
  段5: INFJ（E=46, N=64, F=56, J=58）← E/I 翻轉（疲勞）
  段6: ENFJ（E=54, N=62, F=52, J=56）
```

#### 多性格統計輸出

```
主性格（出現最多次）：ENFJ（出現 4/6 段 = 67%）
次要性格（第二多）：  ENTP（出現 1/6 段 = 17%）
壓力性格：           INFJ（出現 1/6 段 = 17%）

性格穩定度：
  EI_穩定度 = 1 − (EI_各段標準差 / 50)  → 越高=越穩定
  NS_穩定度 = ...
  TF_穩定度 = ...
  JP_穩定度 = ...
  整體穩定度 = 四維度穩定度均值

各維度平均分數（加權，中後段權重較高）：
  E_avg = 段1×0.10 + 段2×0.15 + 段3×0.20 + 段4×0.20 + 段5×0.20 + 段6×0.15
  同理計算 N%, F%, J%
```

#### 性格交互作用矩陣

```
計算每相鄰兩段之間的「性格切換距離」：

MBTI類型距離 = 各維度差異加總
  E(58)→E(52)：差 6  （無翻轉）
  N(62)→N(60)：差 2
  F(54)→T(48)：差 6  + 翻轉懲罰 +20
  J(57)→P(44)：差13  + 翻轉懲罰 +20
  → 段2→段3 的切換距離 = 6+2+26+33 = 67（較大，有性格切換）

輸出指標：
  多性格係數   = 出現不同MBTI類型的段數 / 總段數
                 → 0.33 = 6段中2段不同，代表「中度多性格」

  出現的性格列表：[ENFJ(主), ENTP(次), INFJ(壓力下)]

  性格切換觸發條件（報告說明用）：
    ENTP 出現在 61-90 秒 → 推測：該時段受外部刺激/挑戰
    INFJ 出現在 121-150 秒 → 推測：疲勞/內省狀態
```

---

## 六、需要告知 SDK 廠商的完整規格

以下為可直接傳給對方的技術文件：

```
=====================================
腦波 SDK 輸出需求規格 v1.1
（我方後端自行演算，SDK 只需提供原始數據）
=====================================

回呼頻率：每秒一次（1 Hz）
回呼方法：onEEGData(data: EEGData)

EEGData 必要欄位（11個）：
┌──────────────┬────────┬─────────────────────────────────────┐
│ 欄位         │ 型別   │ 說明                                │
├──────────────┼────────┼─────────────────────────────────────┤
│ theta        │ Float  │ θ波（4–8 Hz）1秒平均功率            │
│ alpha_high   │ Float  │ α↑（10–13 Hz）1秒平均功率           │
│ alpha_low    │ Float  │ α↓（8–10 Hz）1秒平均功率            │
│ beta_low     │ Float  │ β↓（13–20 Hz）1秒平均功率           │
│ beta_high    │ Float  │ β↑（20–30 Hz）1秒平均功率           │
│ gamma_low    │ Float  │ γ↓（30–35 Hz）1秒平均功率           │
│ gamma_high   │ Float  │ γ↑（35–100 Hz）1秒平均功率          │
│ smr          │ Float  │ SMR（12–15 Hz）1秒平均功率【可選】  │
│ attention    │ Int    │ 專注力 0–100（eSense 演算法輸出）   │
│ relaxation   │ Int    │ 放鬆度 0–100（冥想演算法輸出）      │
│ signal_quality│ Int   │ 0=良好 1=微弱 2=噪音               │
└──────────────┴────────┴─────────────────────────────────────┘

功率值規格：
  • 單位：相對功率（0.0–1.0 的浮點數）或 μV²，兩者擇一但需固定
  • 內容：設備內部高頻採樣後，輸出每1秒的「平均值」
  • 非必要提供：每秒的 min/max/std — 我方後端自行計算

電極說明：
  • 僅 Fp1（左前額葉）— 已確認無 Fp2
  • alpha_high / alpha_low 的 Fp1 通道數值無需額外回呼（包含在整體頻帶中即可）

不需要提供：
  • 每秒的最大值、最小值、標準差（後端自行計算）
  • delta 波（δ，0.5–4 Hz）— 報告未使用
  • FAA 計算值 — 因無 Fp2，後端改用替代演算法
  • 任何 MBTI 計算 — 後端自行演算
  • 正規化後的百分比 — 後端自行計算
=====================================
```

---

## 七、後端資料庫欄位更新（eeg_raw_captures）

依照以上規格，更新 `eeg_raw_captures` 資料表：

```sql
CREATE TABLE eeg_raw_captures (
  capture_id      BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  session_id      BIGINT UNSIGNED NOT NULL,
  second_index    SMALLINT NOT NULL,          -- 第幾秒（1–180）
  captured_at     TIMESTAMP(3) NOT NULL,      -- 毫秒精度

  -- 7個子頻帶原始功率（SDK提供）
  theta           FLOAT NOT NULL,             -- θ直覺
  alpha_high      FLOAT NOT NULL,             -- α↑氣血
  alpha_low       FLOAT NOT NULL,             -- α↓安定
  beta_low        FLOAT NOT NULL,             -- β↓邏輯
  beta_high       FLOAT NOT NULL,             -- β↑執行
  gamma_low       FLOAT NOT NULL,             -- γ↓慈悲
  gamma_high      FLOAT NOT NULL,             -- γ↑觀察
  smr             FLOAT NULL,                 -- SMR（可選）

  -- 2個複合分數（SDK提供）
  attention       TINYINT UNSIGNED NOT NULL,  -- 專注力 0–100
  relaxation      TINYINT UNSIGNED NOT NULL,  -- 放鬆度 0–100

  -- 訊號狀態（SDK提供）
  signal_quality  TINYINT UNSIGNED DEFAULT 0, -- 0=良好 1=微弱 2=噪音
  is_baseline     TINYINT(1) DEFAULT 0,       -- 是否為基線期（前30秒）

  INDEX idx_session_second (session_id, second_index)
);
```

---

## 八、多重 MBTI 完整輸出範例

```json
{
  "mbti_primary": "ENFJ",
  "mbti_primary_rate": 67,
  "mbti_appearances": [
    { "type": "ENFJ", "count": 4, "segments": [1,2,4,6], "rate": 67 },
    { "type": "ENTP", "count": 1, "segments": [3],       "rate": 17 },
    { "type": "INFJ", "count": 1, "segments": [5],       "rate": 17 }
  ],
  "dimension_scores": {
    "E": 54, "I": 46,
    "N": 62, "S": 38,
    "F": 52, "T": 48,
    "J": 55, "P": 45
  },
  "dimension_stability": {
    "EI": 0.88,
    "NS": 0.92,
    "TF": 0.71,
    "JP": 0.85,
    "overall": 0.84
  },
  "multi_personality_index": 0.33,
  "segment_results": [
    { "seg": 1, "seconds": "1–30",   "type": "ENFJ", "E":58,"N":62,"F":54,"J":57 },
    { "seg": 2, "seconds": "31–60",  "type": "ENFJ", "E":55,"N":65,"F":51,"J":52 },
    { "seg": 3, "seconds": "61–90",  "type": "ENTP", "E":52,"N":60,"F":48,"J":44 },
    { "seg": 4, "seconds": "91–120", "type": "ENFJ", "E":57,"N":59,"F":53,"J":55 },
    { "seg": 5, "seconds": "121–150","type": "INFJ", "E":46,"N":64,"F":56,"J":58 },
    { "seg": 6, "seconds": "151–180","type": "ENFJ", "E":54,"N":62,"F":52,"J":56 }
  ],
  "personality_switch_pattern": "ENFJ主導，在壓力時偶現ENTP（邏輯驅動），疲勞時偶現INFJ（內省模式）"
}
```
