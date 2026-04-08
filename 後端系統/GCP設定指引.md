# GCP 後端部署指引

## 階段一：建立 GCP 帳號與專案

1. 前往 https://cloud.google.com 申請帳號（新帳號有 $300 美金免費額度）
2. 建立新專案，專案名稱例如：`eeg-report-system`
3. 記下你的 **Project ID**（之後會用到）

---

## 階段二：建立 Cloud SQL（MySQL）

### 步驟 1：開啟 Cloud SQL
- GCP 控制台 → 搜尋「Cloud SQL」→ 點「建立執行個體」

### 步驟 2：選擇資料庫
- 選 **MySQL**
- 版本：MySQL 8.0

### 步驟 3：設定規格（100 人同時檢測建議）
| 項目 | 建議設定 |
|------|---------|
| 執行個體 ID | `eeg-db` |
| 密碼 | 設定強密碼，記下來 |
| 地區 | `asia-east1`（台灣最近） |
| 機器類型 | `db-n1-standard-2`（2 vCPU, 7.5GB RAM）|
| 儲存空間 | 50 GB SSD，開啟自動增加 |

### 步驟 4：網路設定
- 連線 → 「新增網路」→ 輸入 `0.0.0.0/0`（先開放所有 IP，之後再限縮）
- 或使用 Cloud SQL Auth Proxy（更安全，推薦正式環境）

### 步驟 5：建立資料庫與使用者
連上 Cloud SQL 後執行：
```sql
CREATE DATABASE eeg_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'eeg_user'@'%' IDENTIFIED BY 'your_strong_password';
GRANT ALL PRIVILEGES ON eeg_system.* TO 'eeg_user'@'%';
FLUSH PRIVILEGES;
```

---

## 階段三：建立 Cloud Storage（PDF 儲存）

1. GCP 控制台 → 搜尋「Cloud Storage」→「建立值區（Bucket）」
2. 名稱：`eeg-reports-{你的專案ID}`（名稱全球唯一）
3. 地區：`asia-east1`
4. 存取控制：「細部存取控制」
5. 建立後，設定公開讀取：
   ```
   Bucket → 權限 → 新增主體 → allUsers → Cloud Storage 物件檢視者
   ```

---

## 階段四：部署到 Cloud Run

### 步驟 1：安裝 Google Cloud SDK
前往 https://cloud.google.com/sdk/docs/install 下載並安裝

### 步驟 2：登入並設定專案
```powershell
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### 步驟 3：建立 Dockerfile
（已在後端系統資料夾中提供）

### 步驟 4：部署
```powershell
cd "d:\Write program\AutomaticDetection\後端系統"
gcloud run deploy eeg-api `
  --source . `
  --region asia-east1 `
  --allow-unauthenticated `
  --set-env-vars "DB_HOST=YOUR_CLOUD_SQL_IP,DB_NAME=eeg_system,DB_USER=eeg_user,DB_PASSWORD=YOUR_PASSWORD,GCS_BUCKET_NAME=YOUR_BUCKET"
```

---

## 階段五：更新 Android App 的 API 網址

部署完成後，Cloud Run 會給你一個網址，例如：
```
https://eeg-api-xxxxxxxxxx-de.a.run.app
```

在 Android App 的 `CLS_DB.java` 或網路設定中，將 API 基底網址改為此網址。

---

## 費用估算（100 人/天）

| 服務 | 月費估算 |
|------|---------|
| Cloud SQL db-n1-standard-2 | ~USD $70/月 |
| Cloud Run（按使用量）| ~USD $5-15/月 |
| Cloud Storage（PDF）| ~USD $1-5/月 |
| **合計** | **~USD $76-90/月**（約 NTD 2,400-2,800） |

> 💡 初期測試可用較小機型 `db-f1-micro`，費用約 $10/月

---

## 本地測試（目前狀態）

系統目前已可在本機完整運行：
- API：http://localhost:8000
- 互動式文件：http://localhost:8000/docs
- 資料庫：SQLite（`eeg_dev.db`）
- PDF：`reports/` 資料夾

切換到 GCP MySQL 只需修改 `.env` 中的設定即可，程式碼不用改。
