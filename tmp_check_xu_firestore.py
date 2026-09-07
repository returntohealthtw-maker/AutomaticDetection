import requests, sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Firebase 認證（用 migration 帳號）
API_KEY = "AIzaSyBc-ZEcT8fvyn-dBZ0Bhm5IsakncVp1ngQ"
auth_r = requests.post(
    f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}",
    json={"email":"migration@returntohealthtw.com","password":"MigrateEEG@2026","returnSecureToken":True},
    timeout=15
)
id_token = auth_r.json().get("idToken","")
print(f"Firebase auth OK")

PROJECT_ID = "gen-lang-client-0435688289"
FS_BASE = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"
FS_H = {"Authorization": f"Bearer {id_token}"}

# 檢查三個 session 文件是否存在於 Firestore sessions collection
fb_ids = {
    "許恩蕊": "f919a5ce-0e4f-46b1-bc6c-e7d905191baa",
    "許睿恩": "61b82071-1d82-4d35-8291-2259e18e78c3",
    "許允約":  "fc850d83-9ab5-4558-b4cb-04345ae03cb5",
}

print("\n=== Firestore sessions collection ===")
for name, fb_id in fb_ids.items():
    r = requests.get(f"{FS_BASE}/sessions/{fb_id}", headers=FS_H, timeout=10)
    print(f"\n{name} ({fb_id}): HTTP {r.status_code}")
    if r.status_code == 200:
        doc = r.json()
        fields = doc.get("fields", {})
        # 顯示重要欄位
        for k in ["subjectName", "subject_name", "name", "createdAt", "created_at"]:
            if k in fields:
                v = fields[k]
                val = v.get("stringValue") or v.get("integerValue") or v.get("timestampValue") or str(v)
                print(f"  {k}: {val}")
        print(f"  全部欄位: {list(fields.keys())}")
    else:
        print(f"  error: {r.text[:150]}")

    # 查 eeg_features subcollection
    r2 = requests.get(f"{FS_BASE}/sessions/{fb_id}/eeg_features", headers=FS_H, timeout=10)
    print(f"  eeg_features: HTTP {r2.status_code} → ", end="")
    if r2.status_code == 200:
        docs = r2.json().get("documents", [])
        print(f"{len(docs)} records")
    else:
        print(f"{r2.text[:100]}")

# 也查 eeg_features collection 頂層
print("\n=== Checking eeg_features top-level collection ===")
for name, fb_id in fb_ids.items():
    r = requests.get(f"{FS_BASE}/eeg_features", headers=FS_H, 
                     params={"pageSize": 1}, timeout=10)
    print(f"Top-level eeg_features: HTTP {r.status_code}")
    if r.status_code == 200:
        print(f"  Sample: {str(r.json())[:200]}")
    break  # 只查一次
