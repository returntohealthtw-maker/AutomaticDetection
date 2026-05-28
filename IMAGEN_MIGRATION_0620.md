# 🚨 2026/06/20 執行：Imagen → Gemini Image 遷移

> **背景**：Google 宣布 `imagen-4.0-generate-001`（及所有 Imagen 系列）
> 將於 **2026/06/24～06/30 停止服務**。
> 到期後所有報告圖片會直接失敗（API 回傳 404/410）。

---

## 需要修改的檔案（共 2 個）

### 1. `_reports_review/adult/vite.config.ts`

**找到這行：**
```ts
const IMAGEN_MODEL = readEnvVar('IMAGEN_MODEL') || 'imagen-4.0-generate-001';
```

**改為：**
```ts
const IMAGEN_MODEL = readEnvVar('IMAGEN_MODEL') || 'gemini-2.0-flash-preview-image-generation';
```

---

### 2. `_reports_review/child/vite.config.ts`（如果也有同樣的行）

同上修改。

---

### 3. API 呼叫格式可能需要調整（在 `services/geminiService.ts`）

新版 Gemini Image 模型的呼叫格式與 Imagen 不同：

**舊版 Imagen（`/models/imagen-4.0-generate-001:predict`）：**
```json
{
  "instances": [{ "prompt": "..." }],
  "parameters": { "sampleCount": 1, "aspectRatio": "16:9" }
}
```

**新版 Gemini Image（`/models/gemini-2.0-flash-preview-image-generation:generateContent`）：**
```json
{
  "contents": [{ "role": "user", "parts": [{ "text": "Generate image: ..." }] }],
  "generationConfig": { "responseModalities": ["IMAGE", "TEXT"] }
}
```

回傳格式也不同：
- 舊版：`predictions[0].bytesBase64Encoded`
- 新版：`candidates[0].content.parts[].inlineData.data`（找 mimeType 含 image/ 的 part）

---

## 遷移前要確認的事項

- [ ] 先在 AI Studio 測試新模型品質：https://aistudio.google.com/
- [ ] 確認 `IMAGEN_MODEL` 環境變數（Vercel）沒有硬編碼舊版模型名稱
- [ ] 新模型的速率限制（可能與 Imagen 不同）
- [ ] 遷移後先重新生成一份測試報告確認圖片品質

## 目前可用的候選新模型

| 模型名稱 | 說明 | 備注 |
|---|---|---|
| `gemini-2.0-flash-preview-image-generation` | 目前最穩定的 Gemini 圖像模型 | 推薦 |
| `gemini-2.0-flash-exp` | 實驗版，可能不穩定 | 備用 |

---

## 提醒時間軸

| 日期 | 動作 |
|---|---|
| **2026/06/20**（今天） | 在 AI Studio 測試新模型，確認品質可接受 |
| **2026/06/21** | 修改程式碼、build、deploy |
| **2026/06/22** | 驗證一份完整報告 |
| **2026/06/24** | Imagen 正式停用（已安全遷移） |

---

*此文件由 AI 助手於 2026/05/28 建立，作為遷移提醒用。*
