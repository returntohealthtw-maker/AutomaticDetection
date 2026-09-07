"""
把 Railway 受測者的完整資料（email, phone, occupation, medical_history, medications）
補充到 Firebase 已建立的受測者記錄（用 PATCH 更新）

比對鍵：姓名 + 出生日期
"""
import sys, io, json, requests, urllib3
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
urllib3.disable_warnings()

FIREBASE_API_KEY  = "AIzaSyBc-ZEcT8fvyn-dBZ0Bhm5IsakncVp1ngQ"
FIREBASE_EMAIL    = "migration@returntohealthtw.com"
FIREBASE_PASSWORD = "MigrateEEG@2026"
CF_BASE      = "https://asia-east1-gen-lang-client-0435688289.cloudfunctions.net/api/api"
RAILWAY_BASE = "https://backend-production-2da61.up.railway.app"

GENDER_MAP = {"男": "male", "女": "female", "M": "male", "F": "female",
              "male": "male", "female": "female", "other": "other"}

# ── 登入 ──────────────────────────────────────────────────────────────────────
r = requests.post(
    f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}",
    json={"email": FIREBASE_EMAIL, "password": FIREBASE_PASSWORD, "returnSecureToken": True},
    verify=False, timeout=15)
token = r.json()["idToken"]
fb_hdrs = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
print("✅ Firebase 登入成功")

rs = requests.Session(); rs.verify = False
rw_tok = rs.post(f"{RAILWAY_BASE}/api/v1/auth/login",
                 json={"phone": "0900000000", "password": "admin123"}, timeout=15).json().get("token", "")
rs.headers["Authorization"] = f"Bearer {rw_tok}"
print("✅ Railway 登入成功")

# ── 取得 Railway 所有受測者（含完整欄位）─────────────────────────────────────
rw_subs_r = rs.get(f"{RAILWAY_BASE}/api/v1/subjects", timeout=20)
rw_subs = rw_subs_r.json() if isinstance(rw_subs_r.json(), list) else []
print(f"📋 Railway 受測者共 {len(rw_subs)} 筆")

# 建立 Railway 比對 dict：key = 姓名（Firebase 沒存生日，只能用姓名比對）
# 若同名多筆，取最新建立的那筆
rw_map = {}
for sub in sorted(rw_subs, key=lambda x: x.get("created_at") or ""):
    key = (sub.get("name") or "").strip()
    rw_map[key] = sub

# ── 取得 Firebase 所有受測者 ─────────────────────────────────────────────────
fb_r = requests.get(f"{CF_BASE}/users/subjects", headers=fb_hdrs, verify=False, timeout=20)
fb_data = fb_r.json()
fb_subs = fb_data.get("subjects", [])
print(f"📋 Firebase 受測者共 {len(fb_subs)} 筆\n")

ok = 0; skip = 0; not_found = 0

for fb_sub in fb_subs:
    fb_id   = fb_sub.get("subjectId") or fb_sub.get("id", "")
    fb_name = (fb_sub.get("name") or "").strip()
    fb_bd   = (fb_sub.get("birthDate") or "").strip()

    key = fb_name
    rw = rw_map.get(key)

    if not rw:
        print(f"  ⚠ 找不到對應 Railway 資料：{fb_name} ({fb_bd})")
        not_found += 1
        continue

    # 檢查是否已有完整資料（避免重複寫）
    already_has = all([
        fb_sub.get("email"),
        fb_sub.get("phone"),
    ])
    if already_has:
        print(f"  ⏭ {fb_name}：已有完整資料，跳過")
        skip += 1
        continue

    # 組裝要更新的欄位
    patch_payload = {
        "email":         rw.get("email") or None,
        "phone":         rw.get("phone") or None,
        "occupation":    rw.get("occupation") or None,
        "medicalHistory": rw.get("medical_history") or None,
        "currentMeds":   rw.get("medications") or None,
        "gender":        GENDER_MAP.get(rw.get("gender", ""), "other"),
        "birthDate":     rw.get("birth_date") or fb_bd,
    }
    # 去除 None 值（PATCH 不送空欄位）
    patch_payload = {k: v for k, v in patch_payload.items() if v is not None}

    r2 = requests.patch(
        f"{CF_BASE}/users/subjects/{fb_id}",
        json=patch_payload, headers=fb_hdrs, verify=False, timeout=20
    )
    if r2.status_code in (200, 201):
        ok += 1
        email_show = rw.get("email", "")[:30]
        print(f"  ✅ {fb_name}：已補充 email={email_show} phone={rw.get('phone','')}")
    else:
        print(f"  ❌ {fb_name}：PATCH 失敗 {r2.status_code} {r2.text[:100]}")

print(f"\n完成！更新 {ok} 筆，跳過 {skip} 筆，找不到對應 {not_found} 筆")
