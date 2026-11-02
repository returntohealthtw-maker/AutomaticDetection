# AutomaticDetection 回報（MBTI、同步完整性、BLE 問題）— 2026-10-14

本文件只含「讀程式碼得到的事實」與「待決策項目」，**尚未修改任何演算法或程式**。

限制：
- Database 端 Node 版原始碼不在本 workspace，Node 欄位只引用對方描述與 `HANDOFF_TO_FIREBASE_DB_2026-08.md`。
- 14 個 session ID 與 `age-lookup-diagnose-report.json` 未提供，對照表尚未產出。
- `test_mbti_layers.py` 的結果為手動推演，未實際執行。

---

## 1. MBTI 主/副性格

### 1.1 使用者實際看到的畫面來源

| 畫面 | 產生函式 | 主/副/四層怎麼來 | 會不會重複 |
|---|---|---|---|
| 成人 PDF 報告（React `report-app`） | `report_generator.py:253` → `build_mbti_payload`（`algorithms.py:1165`）→ `compute_mbti_v6` | 主性格為 v6 四軸競爭結果；副性格為邊界最近 1～2 軸的字母翻轉（`algorithms.py:511-532`）；`mbti_layers` 固定 `None`（`:1198`）；前端 `wu()` 讀 `mbti_primary`/`mbti_secondaries`（`_patch_report_js.py:12-20`） | 副性格是翻轉一個字母，**不可能等於主性格**。此路徑沒有四層 |
| 兒童報告 App | 同一份 payload（bundle 內有 `mbti_primary`、`secondaries` 引用） | 同上 | 同上 |
| App 內 `screen-results` 多性格畫面 | `app_prototype.html:8023` `_renderR2MbtiAnalysis` → `_etComputeMBTILayers`（`:7742`） | 前端 JS 自算四層（八卦＋30 秒視窗）；`distinctCount === 1` 時顯示「性格高度一致」（`:8062`） | **會重複** |
| 後端 `compute_mbti_layers_from_captures`（`algorithms.py:1052`） | 僅診斷端點 `reports.py:1892`（`/diag/mbti/{id}`）與測試腳本使用 | 報告流程已不呼叫 | 會重複，但不影響使用者畫面 |

### 1.2 `test_mbti_layers.py` 四層全是 INTP 的原因（依程式碼推演）

1. 只有 4 筆 capture，視窗數 `len(captures)//30 = 0`（`algorithms.py:1090-1102`），`window_mbtis` 為空，`layers = {}`，`_layer()` 全部退回 `archetype`（`:1109-1112`）。
2. 值在 30～60（0-100 尺度）卻被當 raw 使用；`LA_MEAN` 為 log10 約 4.07（`app/algorithms/data_stats.py:15`），`log10(45)≈1.65` 的 z≈-5.7，百分位≈0 → 乾卦、theta 不高 → INTP。

其他使「層與層差異」不可靠的地方：
- 視窗數：Python `n//30`（`:948`）、JS `Math.ceil(n/30)`（`app_prototype.html:7696`）。
- 腦色演算法：Python `_calc_mind_color`（`:655`，距離各色中心）與 JS `_etColorForMeans`（`:7633`，f1/f2 範圍＋優先序）不同。
- 原型用 `MAP`（theta 高低分兩型），視窗用 `_calc_personality_from_bagua_color`（腦色分兩型），矛盾距離含人為成分。
- `th_pct` 使用 `DATA_STATS["lowAlpha"]` 的 mean/std（`:390-391`、`:741`、`:812`、`:819`），`DATA_STATS["theta"]` 未被使用。是否沿用 BrainDNA 原版待確認。

### 1.3 「副性格 ≠ 主性格、各層不重複」修法方向（未實作）

| 路徑 | 建議 |
|---|---|
| PDF（v6） | 已滿足，可加斷言保險 |
| App 內四層（JS）＋診斷端點＋後端 `assign_personality_layers` | 分配 peer/social/family 時排除已使用型別；視窗型別全同則用次軸翻轉替補；仍不足就如實顯示「只有 N 層有差異」。前後端須同步改 |

### 1.4 `compute_mbti_v6`（AD）與 Node 版差異

| 項目 | AD Python | Database Node（依對方描述） |
|---|---|---|
| 輸入尺度 | `_raw_band_to_norm100`：`log10(v+1)/6*100`，上限 100（`algorithms.py:427-441`）；**輸入 ≤100 原樣回傳**，raw 剛好 ≤100 會被誤判為已正規化 | 相對功率 % |
| 頻段與 eSense 混用 | `focus`/`relaxation`（0-100 eSense）與頻段值同一加權式（`:477-491`） | 未知 |
| 軸分數 | `50 + diff*0.6`，夾 5～99（`:508-511`） | z-score，`AXIS_SD`（35 筆 session 校準） |
| 判定閾值 | E/I、T/F、J/P 以 diff>0；N/S 為 `nsDiff > 8`（`:496-499`） | 未知 |
| 副性格 | 最多 2 個，`strength = 78 - |diff|*1.8`，夾 10～78，<20 捨棄（`:520-531`） | `mbtiSecondary`/`mbtiTertiary` |
| 各軸 SD 校正 | 無 | 有 |

`statistical-parameter-validation` 提醒：AD 的 v6 係數為設計值，無個體差異 SD；`DATA_STATS` std 為 log10 尺度、來源 BrainDNA 原版，不確定是否為 between-person SD。

**待決策**：以 Node（`AXIS_SD` z-score）或 AD v6 為準；App 內四層畫面保留去重，或改讀統一引擎。

---

## 2. 同步到 Database 的資料完整性

### 2.1 14 個無 subjectId 的 session 對照表

尚未產出（缺 ID）。資料結構：`sessions.subject_id` 為 nullable 外鍵（`models.py:27`），另有 `subject_name`/`subject_age` 快照；`subjects.birth_date` 為 `NOT NULL`（`models.py:250`）。

唯讀查詢：

```sql
SELECT s.session_id, s.subject_id, s.subject_name, s.subject_age,
       s.consultant_name, s.created_at, s.firebase_session_id,
       sub.name AS subj_name, sub.birth_date, sub.firebase_subject_id
FROM sessions s
LEFT JOIN subjects sub ON sub.subject_id = s.subject_id
WHERE s.session_id IN (...14 個 ID...);
```

`subject_id` 為 NULL 者以 `subject_name`＋`subject_age`＋顧問推斷；同名多筆時列出候選，不硬選。

### 2.2 `firebase_sync.py` 現況缺口

| 缺口 | 位置 | 說明 |
|---|---|---|
| 無 `subjectId` 仍建立 session | `:497-503`、`:745-751` | `_ensure_firebase_subject` 回 `None`（`ambiguous`/查不到/例外）時仍送出 session |
| `birthDate` 僅在新建受測者時送 | `:401-407` | matched 時直接回 id，不更新生日 |
| 生日回退 | `:403-407` | 優先 Postgres 生日，否則 `年-01-01` 近似 |
| 殘留標記 | `:735` | metadata 含 `"data_format": "bandTo100"` |

建議（未實作）：
1. `fb_subject_id` 為空時不建立 session，記錄失敗或標記待補。
2. 找到既有受測者時，若 Firebase 缺 `birthDate` 則補送；僅知年份一律補 `YYYY-01-01`。
3. 移除 `data_format: bandTo100`。

---

## 3. 只回答、不改 Android

### 3.1 BLE 封包第 2 位元組為 0x02 的格式、樣本數、字節序、取樣率

**目前程式碼未解析，無法回答。** `CLS_BLE.java:322-324` 對 0x02 只有註解 `//iRawCnt++;`。

可確認的事實：
- 第 0 位元組固定 170（0xAA），否則丟棄。
- 第 1 位元組為封包類型：0x01 頻段/eSense、0x02 raw 類（未解析）、0x03 按鍵。
- 已解析的封包中，第 3 位元組等於後面資料長度（`0x0F`=15、`0x0C`=12、`0x01`=1；`CLS_BLE.java:297-311,328`）。
- 頻段功率為大端序 24 位元（`b[7]*65536+b[8]*256+b[9]`），僅適用 0x01，**不可推論 0x02**。

查證方式（不改 Android）：用 nRF Connect 訂閱
- Service `039AFFF0-2C94-11E3-9E06-0002A5D5C51B`
- Characteristic `039AFFF4-2C94-11E3-9E06-0002A5D5C51B`（`CLS_BLE.java:348-349`）

錄下 0x02 封包，由長度與每秒封包數推算。

### 3.2 廠商通訊協定文件

repo 內未找到。僅有 AD 自己的 `設計文件/07_SDK資料需求與後端演算法.md`；`Android source code/app/libs/` 無 SDK 檔；`TgStreamReader`（`CLS_BT.java`）為外部函式庫，內部實作不可見。需向廠商索取。

### 3.3 經典藍牙 `CODE_RAW` 是否 512 Hz

**無法確認。** `CLS_BT.java:161-162` 為 `case MindDataType.CODE_RAW: break;`，AD 未計數也未設定取樣率。唯一提及 512 Hz 的是 `設計文件/07` 第 38 行「設備可能內部以 512Hz 採樣」，為推測語氣。驗證需在測試版計算每秒 `CODE_RAW` 回呼次數（需改 Android，本次不做）。

---

## 待決策

1. 使用者看到 MBTI 重複的是哪個畫面（截圖或 session ID）。
2. 以 Node 或 AD v6 為準。
3. App 內四層畫面：去重或改讀統一引擎。
4. 提供 14 個 session ID。
5. 2.2 的三項同步缺口是否修正。

## 本次未完成

- [ ] 14 個 session 對照表：缺 ID
- [ ] Node 版與 v6 逐項數值比對：缺 Node 原始碼
- [ ] BLE 0x02 封包格式與取樣率：需抓封包或廠商文件
- [ ] 任何程式修改：等待決策
