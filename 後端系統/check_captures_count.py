import sys, io, requests, urllib3
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
urllib3.disable_warnings()

BASE  = "https://backend-production-2da61.up.railway.app"
s = requests.Session(); s.verify = False
TOKEN = s.post(f"{BASE}/api/v1/auth/login",
               json={"phone":"0900000000","password":"admin123"}, timeout=10
               ).json().get("token","")
s.headers["Authorization"] = f"Bearer {TOKEN}"

# 取最近 3 位不同受測者的 sessions
all_sess = s.get(f"{BASE}/api/v1/eeg/sessions", timeout=15).json().get("sessions", [])
seen = {}; recent = []
for sess in sorted(all_sess, key=lambda x: x.get("created_at",""), reverse=True):
    name = sess.get("subject_name") or "Unknown"
    sid  = sess.get("session_id") or sess.get("id")
    if name not in seen and sid:
        seen[name] = True
        recent.append({"name": name, "sid": sid})
    if len(recent) >= 3:
        break

for item in recent:
    sid  = item["sid"]
    name = item["name"]
    # 用 diag/mbti 端點取得 captures 數量（端點內部有查 eeg_captures）
    rd = s.get(f"{BASE}/api/v1/reports/diag/mbti/{sid}", timeout=20).json()
    
    # 從 stats 取 total_captures
    rs = s.get(f"{BASE}/api/v1/eeg/sessions/{sid}/stats", timeout=15).json()
    eeg = rs.get("eeg_stats") or {}
    sample_count = eeg.get("sample_count", "?")
    
    # diag 回傳的 mbti payload 裡有 captures 數
    mbti_p = rd.get("mbti") or {}
    layers = rd.get("mbti_layers") or {}
    profiles = rd.get("mbti_profiles") or []
    primary = mbti_p.get("mbti_primary") or rd.get("mbti_result", {}).get("mbti_type", "?")
    
    print(f"\n  [{sid}] {name}")
    print(f"    eeg_stats.sample_count = {sample_count}")
    print(f"    diag 端點 lo_alpha_avg = {rd.get('db_values', {}).get('lo_alpha_avg_from_db', '?')}")
    print(f"    MBTI 主型 = {primary}")
    if profiles:
        print(f"    profiles: {[(p['type'], p['pct']) for p in profiles[:4]]}")
