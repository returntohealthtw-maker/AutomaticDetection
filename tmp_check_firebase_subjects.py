import requests, sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

API_KEY = "AIzaSyBc-ZEcT8fvyn-dBZ0Bhm5IsakncVp1ngQ"
auth_r = requests.post(
    f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}",
    json={"email":"migration@returntohealthtw.com","password":"MigrateEEG@2026","returnSecureToken":True},
    timeout=15
)
id_token = auth_r.json().get("idToken","")
print("Firebase auth OK")

FB_BASE = "https://asia-east1-gen-lang-client-0435688289.cloudfunctions.net/api/api"
FH = {"Authorization": f"Bearer {id_token}"}

# 查 subjects 清單（用 migration 帳號創建的）
print("\n=== migration 帳號下的 subjects 清單 ===")
r = requests.get(f"{FB_BASE}/users/subjects", headers=FH, timeout=10)
print(f"HTTP {r.status_code}")
if r.status_code == 200:
    data = r.json()
    subjects = data.get("subjects", data if isinstance(data, list) else [])
    print(f"共 {len(subjects)} 個受測者：")
    for s in subjects:
        print(f"  [{s.get('subjectId',s.get('id','?'))}] 姓名={s.get('name','?')} 年齡={s.get('age','?')}")
else:
    print(r.text[:300])

# 直接查 session 內容看 metadata
print("\n=== 三人的 Firebase session 中 subjectId 欄位 ===")
# 用 Firestore REST API 查 sessions collection
PROJECT_ID = "gen-lang-client-0435688289"
FS_BASE = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"
FS_H = {"Authorization": f"Bearer {id_token}"}

fb_ids = {
    "許恩蕊": "f919a5ce-0e4f-46b1-bc6c-e7d905191baa",
    "許睿恩": "61b82071-1d82-4d35-8291-2259e18e78c3",
    "許允約":  "fc850d83-9ab5-4558-b4cb-04345ae03cb5",
}

for name, fb_id in fb_ids.items():
    r2 = requests.get(f"{FS_BASE}/sessions/{fb_id}", headers=FS_H, timeout=10)
    if r2.status_code == 200:
        doc = r2.json()
        fields = doc.get("fields", {})
        subject_id = fields.get("subjectId",{}).get("stringValue","❌ 無 subjectId")
        meta = fields.get("metadata",{})
        print(f"  {name}: subjectId={subject_id}")
        # 嘗試顯示 metadata
        if "mapValue" in meta:
            meta_fields = meta["mapValue"].get("fields",{})
            sn = meta_fields.get("subject_name",{}).get("stringValue","")
            print(f"          metadata.subject_name={sn}")
    elif r2.status_code == 403:
        print(f"  {name}: 403 PERMISSION_DENIED（session 非 migration 帳號建立，無法讀取）")
    else:
        print(f"  {name}: HTTP {r2.status_code}")
