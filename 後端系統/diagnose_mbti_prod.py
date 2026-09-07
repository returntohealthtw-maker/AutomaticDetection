"""
用最新演算法計算生產環境最近 3 位不同受測者的 MBTI。
"""
import sys, io, requests, json, urllib3
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
urllib3.disable_warnings()

BASE  = "https://backend-production-2da61.up.railway.app"
s = requests.Session(); s.verify = False

TOKEN = s.post(f"{BASE}/api/v1/auth/login",
               json={"phone":"0900000000","password":"admin123"}, timeout=10
               ).json().get("token","")
s.headers["Authorization"] = f"Bearer {TOKEN}"
print("登入成功\n")

# ── 取 EEG sessions 列表 ──────────────────────────────────────
r = s.get(f"{BASE}/api/v1/eeg/sessions", timeout=15)
all_sess = r.json().get("sessions", [])
print(f"共 {len(all_sess)} 個 EEG session")

# 取最近 3 個不同 subject_name 的 session
seen = {}
recent = []
for sess in sorted(all_sess, key=lambda x: x.get("created_at",""), reverse=True):
    name = sess.get("subject_name") or "Unknown"
    sid  = sess.get("session_id") or sess.get("id")
    if name not in seen and sid:
        seen[name] = True
        recent.append({"name": name, "sid": sid, "created_at": sess.get("created_at","")})
    if len(recent) >= 3:
        break

print(f"\n最近 3 位不同受測者：")
for x in recent:
    print(f"  [{x['sid']}] {x['name']}  {x['created_at']}")

# ── 查詢 MBTI 診斷 ────────────────────────────────────────────
for item in recent:
    name = item['name']
    sid  = item['sid']
    print(f"\n{'='*65}")
    print(f"  受測者：{name}  │  Session ID: {sid}")
    print('='*65)

    r2 = s.get(f"{BASE}/api/v1/reports/diag/mbti/{sid}", timeout=20)
    if r2.status_code != 200:
        print(f"  ⚠ {r2.status_code}: {r2.text[:200]}")
        continue

    data = r2.json()
    payload = data.get("mbti") or data

    primary     = payload.get("mbti_primary")
    profiles    = payload.get("mbti_profiles") or []
    secondaries = payload.get("mbti_secondaries") or []
    layers      = payload.get("mbti_layers") or {}
    bagua_name  = payload.get("mbti_bagua_name", "")

    print(f"  八卦卦位：{bagua_name}")
    print(f"  ✅ 主性格：{primary}")
    if secondaries:
        for sec in secondaries:
            print(f"     次性格：{sec.get('mbti')}  強度 {sec.get('strength')}%  ({sec.get('reason','')})")
    else:
        print("     (無達門檻次性格，此人性格特質鮮明)")

    if profiles:
        print(f"\n  群組評分完整分布：")
        for p in profiles[:8]:
            pct = int(p.get('pct', 0))
            bar = '█' * (pct // 5) + ('░' if pct % 5 >= 3 else '')
            print(f"    {p.get('type','?'):4s} {pct:3d}%  {bar}")

    if layers:
        print(f"\n  四層別原始結果：")
        for k, v in layers.items():
            if isinstance(v, dict):
                t = v.get('type', '?')
                bg = v.get('bagua_name', '')
                conf = v.get('confidence', 0)
                print(f"    {k:10s}: {t}  卦:{bg}  信心度:{conf}%")
