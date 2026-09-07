import requests, sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = "https://backend-production-2da61.up.railway.app"
r = requests.post(f"{BASE}/api/v1/auth/login", json={"phone":"0900000000","password":"admin123"}, timeout=15)
token = r.json().get("token","")
H = {"Authorization": f"Bearer {token}"}

# 取 sessions 清單，找出正確的 session ID 欄位名稱
r2 = requests.get(f"{BASE}/api/v1/eeg/sessions?limit=300", headers=H, timeout=20)
sessions = r2.json().get("sessions", [])

# 找許家三人
found = [s for s in sessions if any(n in (s.get("subject_name","") or "") 
         for n in ["許恩蕊","許睿恩","許允約"])]

print(f"找到 {len(found)} 筆\n")
for s in found:
    # 印出所有 key 確認正確欄位名
    print(f"【{s.get('subject_name')}】 所有欄位：")
    for k, v in s.items():
        if v is not None and v != "" and v != 0:
            print(f"  {k}: {v}")
    print()

# 逐一查 captures
print("="*50)
print("查各人的 captures 數量：\n")

# 先找到 session ID 的正確欄位
for s in found:
    name = s.get("subject_name","?")
    # 猜測可能的 session_id 欄位
    sid = None
    for key in ["session_id","id","railway_session_id","sessionId"]:
        if s.get(key) and isinstance(s.get(key), (int, str)):
            sid = s.get(key)
            break
    
    fb_id = s.get("firebase_session_id")
    created = s.get("created_at","?")
    
    print(f"{name} | session_id={sid} | firebase_id={fb_id or '無'} | created={created}")
    
    if sid:
        # 查 captures
        r3 = requests.get(f"{BASE}/api/v1/sessions/{sid}/captures", headers=H, timeout=15)
        print(f"  /sessions/{sid}/captures: HTTP {r3.status_code}")
        if r3.status_code == 200:
            caps = r3.json()
            count = len(caps) if isinstance(caps, list) else caps.get("count","?")
            print(f"  → Railway DB 中有 {count} 筆 captures")
        else:
            print(f"  → {r3.text[:100]}")
        
        # 查 session stats
        r4 = requests.get(f"{BASE}/api/v1/eeg/sessions/{sid}/stats", headers=H, timeout=15)
        if r4.status_code == 200:
            stats = r4.json()
            print(f"  stats: bands_avg={bool(stats.get('bands_avg'))}, firebase_session_id={stats.get('firebase_session_id')}")
    print()
