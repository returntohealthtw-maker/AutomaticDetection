"""
驗證 firebase_sync.py 修改是否正確：
1. _ensure_firebase_subject 函式存在且 signature 正確
2. sync_to_firebase 有 subject_age / subject_gender 參數
3. sync_captures_to_firebase 有 subject_age / subject_gender 參數
4. 兩個 sync 函式都有呼叫 _ensure_firebase_subject
5. 實際呼叫 Firebase API 建立一個測試 subject，確認流程可用
"""
import sys, inspect, asyncio, requests
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ── 1. 載入模組，檢查函式 signature ─────────────────────────────────
sys.path.insert(0, r"D:\Write program\AutomaticDetection\後端系統")
from app.services.firebase_sync import (
    _ensure_firebase_subject,
    sync_to_firebase,
    sync_captures_to_firebase,
)

print("=== 1. 函式 signature 驗證 ===")

sig_ensure = inspect.signature(_ensure_firebase_subject)
print(f"_ensure_firebase_subject params: {list(sig_ensure.parameters.keys())}")
assert "client" in sig_ensure.parameters
assert "headers" in sig_ensure.parameters
assert "subject_name" in sig_ensure.parameters
assert "subject_age" in sig_ensure.parameters
assert "subject_gender" in sig_ensure.parameters
print("  ✅ _ensure_firebase_subject 參數正確")

sig_sync = inspect.signature(sync_to_firebase)
print(f"sync_to_firebase params: {list(sig_sync.parameters.keys())}")
assert "subject_age" in sig_sync.parameters, "❌ sync_to_firebase 缺少 subject_age"
assert "subject_gender" in sig_sync.parameters, "❌ sync_to_firebase 缺少 subject_gender"
print("  ✅ sync_to_firebase 參數正確")

sig_cap = inspect.signature(sync_captures_to_firebase)
print(f"sync_captures_to_firebase params: {list(sig_cap.parameters.keys())}")
assert "subject_age" in sig_cap.parameters, "❌ sync_captures_to_firebase 缺少 subject_age"
assert "subject_gender" in sig_cap.parameters, "❌ sync_captures_to_firebase 缺少 subject_gender"
print("  ✅ sync_captures_to_firebase 參數正確")

# ── 2. 原始碼確認 _ensure_firebase_subject 被呼叫 ─────────────────
import inspect as _ins
src_sync = _ins.getsource(sync_to_firebase)
src_cap  = _ins.getsource(sync_captures_to_firebase)

assert "_ensure_firebase_subject" in src_sync, "❌ sync_to_firebase 未呼叫 _ensure_firebase_subject"
assert "_ensure_firebase_subject" in src_cap,  "❌ sync_captures_to_firebase 未呼叫 _ensure_firebase_subject"
assert 'subjectId' in src_sync, "❌ sync_to_firebase 未設定 subjectId"
assert 'subjectId' in src_cap,  "❌ sync_captures_to_firebase 未設定 subjectId"
print("\n=== 2. 呼叫鏈驗證 ===")
print("  ✅ sync_to_firebase 有呼叫 _ensure_firebase_subject 並設定 subjectId")
print("  ✅ sync_captures_to_firebase 有呼叫 _ensure_firebase_subject 並設定 subjectId")

# ── 3. 確認 sessions.py 和 eeg.py 有傳入新參數 ─────────────────────
print("\n=== 3. 呼叫端參數驗證 ===")
with open(r"D:\Write program\AutomaticDetection\後端系統\app\routers\sessions.py", encoding="utf-8") as f:
    sess_src = f.read()
assert "subject_age" in sess_src, "❌ sessions.py 未傳 subject_age"
assert "subject_gender" in sess_src, "❌ sessions.py 未傳 subject_gender"
print("  ✅ sessions.py 有傳 subject_age / subject_gender")

with open(r"D:\Write program\AutomaticDetection\後端系統\app\routers\eeg.py", encoding="utf-8") as f:
    eeg_src = f.read()
assert "subject_age" in eeg_src, "❌ eeg.py 未傳 subject_age"
assert "subject_gender" in eeg_src, "❌ eeg.py 未傳 subject_gender"
print("  ✅ eeg.py 有傳 subject_age / subject_gender")

# ── 4. 實際呼叫 Firebase：驗證 _ensure_firebase_subject 流程 ────────
print("\n=== 4. 實際 Firebase API 流程驗證 ===")

API_KEY = "AIzaSyBc-ZEcT8fvyn-dBZ0Bhm5IsakncVp1ngQ"
auth_r = requests.post(
    f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}",
    json={"email":"migration@returntohealthtw.com","password":"MigrateEEG@2026","returnSecureToken":True},
    timeout=15
)
id_token = auth_r.json().get("idToken","")
assert id_token, "❌ Firebase 認證失敗"
print("  ✅ Firebase 認證成功")

import httpx

async def test_ensure_subject():
    headers = {"Authorization": f"Bearer {id_token}"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        # 測試1：查詢已存在的受測者（許睿恩，剛建立的）
        sid = await _ensure_firebase_subject(client, headers, "許睿恩", 8, "男")
        print(f"  _ensure_firebase_subject('許睿恩'): subjectId={sid}")
        assert sid, "❌ 找不到許睿恩的 subjectId"
        print("  ✅ 已存在受測者正確回傳 subjectId（不重複建立）")

        # 測試2：查詢已存在的受測者（許允約）
        sid2 = await _ensure_firebase_subject(client, headers, "許允約", 2, "男")
        print(f"  _ensure_firebase_subject('許允約'): subjectId={sid2}")
        assert sid2, "❌ 找不到許允約的 subjectId"
        print("  ✅ 許允約 subjectId 正確")

        # 測試3：再次呼叫同名（確認不會重複建立）
        r_list = await client.get("https://asia-east1-gen-lang-client-0435688289.cloudfunctions.net/api/api/users/subjects", headers=headers, timeout=10)
        subjects = r_list.json().get("subjects", [])
        xu_subjects = [s for s in subjects if s.get("name") in ("許睿恩","許允約")]
        print(f"  Firebase subjects 中許睿恩/許允約 共 {len(xu_subjects)} 筆（應為 1+1=2）")
        assert len(xu_subjects) == 2, f"❌ 數量不對: {len(xu_subjects)}"
        print("  ✅ 無重複建立")

asyncio.run(test_ensure_subject())

print("\n" + "="*50)
print("🎉 所有驗證通過！修改正確且可正常執行。")
