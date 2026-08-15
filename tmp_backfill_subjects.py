"""
補建 Firebase subjects 記錄腳本
- 從 Railway DB 取出所有有 firebase_session_id 的 sessions
- 比對 Firebase subjects 清單，找出缺少的人
- 呼叫 POST /users/subjects 補建
- 呼叫 PATCH /sessions/{firebase_session_id} 補上 subjectId
"""
import requests, sys, json, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ── Railway 登入 ────────────────────────────────────────────────
RAILWAY_BASE = "https://backend-production-2da61.up.railway.app"
r = requests.post(f"{RAILWAY_BASE}/api/v1/auth/login",
                  json={"phone":"0900000000","password":"admin123"}, timeout=15)
RH = {"Authorization": f"Bearer {r.json().get('token','')}"}

# 取所有 sessions（有 firebase_session_id 的）
r2 = requests.get(f"{RAILWAY_BASE}/api/v1/eeg/sessions?limit=300", headers=RH, timeout=20)
all_sessions = r2.json().get("sessions", [])
firebase_sessions = [s for s in all_sessions if s.get("firebase_session_id")]
print(f"Railway 中有 firebase_session_id 的 sessions: {len(firebase_sessions)} 筆")

# ── Firebase 登入 ───────────────────────────────────────────────
API_KEY = "AIzaSyBc-ZEcT8fvyn-dBZ0Bhm5IsakncVp1ngQ"
auth_r = requests.post(
    f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}",
    json={"email":"migration@returntohealthtw.com","password":"MigrateEEG@2026","returnSecureToken":True},
    timeout=15
)
id_token = auth_r.json().get("idToken","")
FB_BASE = "https://asia-east1-gen-lang-client-0435688289.cloudfunctions.net/api/api"
FH = {"Authorization": f"Bearer {id_token}"}

# 取 Firebase 現有 subjects（migration 帳號下的）
r3 = requests.get(f"{FB_BASE}/users/subjects", headers=FH, timeout=15)
fb_subjects = r3.json().get("subjects", []) if r3.status_code == 200 else []
# 建立 name → subjectId 的對照表
name_to_fb_subject_id = {s.get("name",""): s.get("subjectId") or s.get("id") for s in fb_subjects}
print(f"Firebase 現有 subjects: {len(fb_subjects)} 筆")
print(f"名單: {list(name_to_fb_subject_id.keys())[:20]}...\n")

# ── 找出需要補建的受測者 ────────────────────────────────────────
need_create = []
already_have = []

# 用 name+age 去重（同名同年齡的不重複建立）
seen_keys = set()
for s in firebase_sessions:
    name = s.get("subject_name","")
    age  = s.get("subject_age") or 0
    gender = s.get("subject_gender") or "unknown"
    fb_id = s.get("firebase_session_id","")
    session_id = s.get("session_id")
    
    if not name:
        continue
    
    key = f"{name}_{age}"
    if key in seen_keys:
        continue
    seen_keys.add(key)
    
    if name in name_to_fb_subject_id:
        already_have.append({"name": name, "fb_subject_id": name_to_fb_subject_id[name]})
    else:
        need_create.append({
            "name": name, "age": age, "gender": gender,
            "fb_session_id": fb_id, "railway_session_id": session_id
        })

print(f"已有 Firebase subjects 記錄: {len(already_have)} 人")
for x in already_have:
    print(f"  ✅ {x['name']} → {x['fb_subject_id']}")

print(f"\n需要補建: {len(need_create)} 人")
for x in need_create:
    print(f"  ❌ {x['name']} (age={x['age']}, gender={x['gender']}, railway_sid={x['railway_session_id']})")

print("\n" + "="*60)
print("開始補建...")
created = []
failed = []

for x in need_create:
    payload = {
        "name": x["name"],
        "relationship": "個案",
    }
    # 用年齡推算出生年份（用今年 2026 - age，月日設 01-01）
    if x["age"] and int(x["age"]) > 0:
        birth_year = 2026 - int(x["age"])
        payload["birthDate"] = f"{birth_year}-01-01"
    if x["gender"] in ("男","M","male"):
        payload["gender"] = "male"
    elif x["gender"] in ("女","F","female"):
        payload["gender"] = "female"
    
    r4 = requests.post(f"{FB_BASE}/users/subjects", headers=FH, json=payload, timeout=10)
    if r4.status_code in (200, 201):
        new_subject_id = r4.json().get("subjectId") or r4.json().get("id","")
        print(f"  ✅ 建立 {x['name']} → subjectId={new_subject_id}")
        created.append({**x, "new_subject_id": new_subject_id})
        name_to_fb_subject_id[x["name"]] = new_subject_id
        time.sleep(0.3)
    else:
        print(f"  ❌ 建立 {x['name']} 失敗: HTTP {r4.status_code} {r4.text[:100]}")
        failed.append(x)

print(f"\n✅ 成功補建: {len(created)} 人")
print(f"❌ 失敗: {len(failed)} 人")

# 儲存結果供後續 PATCH session 用
with open("tmp_subjects_created.json", "w", encoding="utf-8") as f:
    json.dump({
        "created": created,
        "name_to_fb_subject_id": name_to_fb_subject_id,
        "firebase_sessions": [{
            "name": s.get("subject_name"),
            "railway_session_id": s.get("session_id"),
            "firebase_session_id": s.get("firebase_session_id"),
            "age": s.get("subject_age"),
            "gender": s.get("subject_gender"),
        } for s in firebase_sessions]
    }, f, ensure_ascii=False, indent=2)
print("\n結果已儲存到 tmp_subjects_created.json")
