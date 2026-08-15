import requests, sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = "https://backend-production-2da61.up.railway.app"

r = requests.post(f"{BASE}/api/v1/auth/login", json={"phone":"0900000000","password":"admin123"}, timeout=15)
data = r.json()
token = data.get("token","")
H = {"Authorization": f"Bearer {token}"}

r2 = requests.get(f"{BASE}/api/v1/eeg/sessions?limit=300", headers=H, timeout=20)
sessions = r2.json().get("sessions", [])
print(f"Total sessions: {len(sessions)}")

found = [s for s in sessions if any(n in (s.get("subject_name","") or "") for n in ["許恩蕊","許睿恩","許允約"])]
print(f"許家三人共 {len(found)} 筆：\n")

for s in found:
    sid = s.get("id")
    fb_id = s.get("firebase_session_id")
    name = s.get("subject_name","?")
    created = str(s.get("created_at","?"))[:19]
    captures = s.get("capture_count","?")
    print(f"  session_id={sid}  姓名={name}")
    print(f"    created_at={created}")
    print(f"    capture_count={captures}")
    print(f"    firebase_session_id={fb_id or '❌ 無（未同步到Firebase）'}")
    print(f"    raw_arrays_json={'有' if s.get('raw_arrays_json') else '無'}")
    print(f"    qeeg_scores_json={'有' if s.get('qeeg_scores_json') else '無'}")
    print()

# 也確認 Firebase
print("="*50)
print("確認 Firebase 是否有這三人：")
FB_BASE = "https://asia-east1-gen-lang-client-0435688289.cloudfunctions.net/api/api"
FB_HEADERS = {"Content-Type": "application/json"}

# 嘗試搜尋 subjects
names_to_check = ["許恩蕊","許睿恩","許允約"]
for name in names_to_check:
    try:
        # 從 Railway sessions 找對應的 firebase_session_id
        s_matches = [s for s in found if s.get("subject_name") == name]
        if s_matches:
            fb_id = s_matches[0].get("firebase_session_id")
            if fb_id:
                r3 = requests.get(f"{FB_BASE}/sessions/{fb_id}", headers=FB_HEADERS, timeout=10)
                print(f"  {name}: Firebase session {fb_id} → HTTP {r3.status_code}")
            else:
                print(f"  {name}: Railway DB 無 firebase_session_id → ❌ 未同步")
        else:
            print(f"  {name}: Railway DB 找不到此人")
    except Exception as e:
        print(f"  {name}: 查詢失敗 {e}")
