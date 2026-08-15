import sys, requests, urllib3, time, random, json
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'

r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=8)
token = r.json().get('token','')
h = {'Authorization': 'Bearer '+token}

# ── 用毫秒格式（模擬真實 Android）上傳 180 筆 ──
print("=== 步驟1：模擬 Android APP 上傳 180 筆腦波（毫秒格式）===")
now_ms = int(time.time() * 1000)
random.seed(42)
caps = []
for i in range(180):
    caps.append({
        "seq_num": i,
        "captured_at": now_ms + i * 1000,   # 毫秒，每秒 +1000
        "is_baseline": 1 if i < 10 else 0,
        "good_signal": 0,
        "attention":   random.randint(40, 75),
        "meditation":  random.randint(30, 65),
        "delta":       random.randint(150000, 350000),
        "theta":       random.randint(80000, 180000),
        "low_alpha":   random.randint(20000, 60000),
        "high_alpha":  random.randint(15000, 40000),
        "low_beta":    random.randint(10000, 25000),
        "high_beta":   random.randint(8000, 20000),
        "low_gamma":   random.randint(3000, 12000),
        "high_gamma":  random.randint(2000, 8000),
    })

body = {
    "subject_name":    "雙DB驗證",
    "consultant_name": "admin",
    "report_type":     "life_script",
    "subject_age":     35,
    "subject_gender":  "F",
    "session_duration": 180,
    "total_captures":  180,
    "is_success":      True,
    "captures":        caps,
}
resp = requests.post(BASE+'/sessions/upload', json=body, verify=False, timeout=30)
print(f"  HTTP {resp.status_code}")
if resp.status_code != 200:
    print(f"  ❌ 上傳失敗: {resp.text[:300]}")
    sys.exit(1)

rj = resp.json()
pg_sid  = rj.get('session_id')
fb_sid  = rj.get('firebase_session_id')
fb_ok   = rj.get('firebase_sync_ok')
print(f"  ✅ 上傳成功")
print(f"  PostgreSQL session_id = {pg_sid}")
print(f"  Firebase  session_id  = {fb_sid}")
print(f"  Firebase sync ok      = {fb_ok}")

# ── 步驟2：驗證 PostgreSQL ──
print()
print("=== 步驟2：驗證 PostgreSQL 筆數 ===")
cap_r = requests.get(BASE+f'/sessions/{pg_sid}/captures?limit=5', headers=h, verify=False, timeout=10)
if cap_r.ok:
    cr = cap_r.json()
    cl = cr if isinstance(cr, list) else cr.get('captures', cr.get('data', []))
    total = cr.get('total', len(cl)) if isinstance(cr, dict) else len(cl)
    print(f"  PostgreSQL captures 筆數 = {total}")
    if cl:
        c0 = cl[0]
        print(f"  第1筆: delta={c0.get('delta')} good_signal={c0.get('good_signal')} captured_at={c0.get('captured_at')}")
    pg_count = total
else:
    print(f"  ❌ 查詢失敗: {cap_r.status_code}")
    pg_count = 0

# ── 步驟3：驗證 Firebase ──
print()
print("=== 步驟3：驗證 Firebase 筆數 ===")
if fb_sid:
    fb_r = requests.get(BASE+f'/eeg/admin/firebase-session/{fb_sid}', headers=h, verify=False, timeout=20)
    if fb_r.ok:
        fj = fb_r.json()
        fb_count = fj.get('eeg_count', 0)
        print(f"  Firebase eeg_features 筆數 = {fb_count}")
        print(f"  sample_delta = {fj.get('sample_delta')}")
        print(f"  sample_fields = {fj.get('sample_fields')}")
    else:
        print(f"  ❌ Firebase 查詢失敗: {fb_r.status_code} {fb_r.text[:200]}")
        fb_count = 0
else:
    print("  ❌ firebase_session_id 為空，Firebase sync 未成功")
    fb_count = 0

# ── 結論 ──
print()
print("=== 結論 ===")
pg_ok = pg_count >= 150
fb_ok2 = fb_count >= 150
print(f"  PostgreSQL: {'✅' if pg_ok else '❌'} {pg_count} 筆")
print(f"  Firebase:   {'✅' if fb_ok2 else '❌'} {fb_count} 筆")
if pg_ok and fb_ok2:
    print("  🎉 兩個 DB 都有完整腦波資料！")
elif pg_ok and not fb_ok2:
    print("  ⚠️  PostgreSQL 有資料，Firebase 筆數不足（可能還在同步中）")
else:
    print("  ❌ 有問題，需要調查")
