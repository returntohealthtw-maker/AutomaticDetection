# -*- coding: utf-8 -*-
"""
後端 API 全功能自我檢測腳本
測試新資料庫位置下所有主要功能是否正常
"""
import sys, time, os
sys.path.insert(0, ".")
import requests

BASE  = os.environ.get("BASE", "http://localhost:8002")
PASS  = []
FAIL  = []

def check(name, ok, detail=""):
    if ok:
        PASS.append(name)
        print(f"  PASS  {name}")
    else:
        FAIL.append(name)
        print(f"  FAIL  {name}  {detail}")

def get(path, **kw):
    try:
        return requests.get(BASE + path, timeout=10, **kw)
    except Exception as e:
        return None

def post(path, **kw):
    try:
        return requests.post(BASE + path, timeout=10, **kw)
    except Exception as e:
        return None

print("=" * 60)
print("backend API self-test")
print(f"target: {BASE}")
print(f"DB: D:/Write program/Database/ToOtherProject/eeg_dev.db")
print("=" * 60)

# ── 1. DB Row Count ─────────────────────────────────────────────
print("\n[1] DB row count verification")
import sqlite3
conn = sqlite3.connect("D:/Write program/Database/ToOtherProject/eeg_dev.db")
sessions_count  = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
captures_count  = conn.execute("SELECT COUNT(*) FROM eeg_captures").fetchone()[0]
reports_count   = conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
conn.close()
check(f"sessions table: {sessions_count} rows (>=7)",  sessions_count >= 7,  f"got {sessions_count}")
check(f"eeg_captures table: {captures_count} rows (>=422)", captures_count >= 422, f"got {captures_count}")
check(f"reports table: {reports_count} rows (>=7)",    reports_count >= 7,   f"got {reports_count}")

# ── 2. Health Check ──────────────────────────────────────────────
print("\n[2] Health check")
r = get("/health")
check("GET /health 200", r and r.status_code == 200, r.text[:80] if r else "no response")
if r and r.status_code == 200:
    d = r.json()
    check("health.api = ok",      d.get("api")      == "ok", str(d))
    check("health.database = ok", d.get("database") == "ok", str(d))

r2 = get("/healthz")
check("GET /healthz 200", r2 and r2.status_code == 200, r2.text[:60] if r2 else "no response")

# ── 3. Static Assets ─────────────────────────────────────────────
print("\n[3] Static assets")
r = get("/static-app/app_prototype.html")
check("GET app_prototype.html", r and r.status_code == 200, r.status_code if r else "err")

r = get("/dashboard")
check("GET /dashboard (admin)", r and r.status_code in [200, 302, 307], r.status_code if r else "err")

# ── 4. Bootstrap + Auth ──────────────────────────────────────────
print("\n[4] Auth API")
r = post("/api/v1/auth/bootstrap", json={})
bootstrap_ok = (r is not None) and (r.status_code in [200, 201, 409])
check("POST /api/v1/auth/bootstrap (create or already-initialized)",
      bootstrap_ok,
      f"status={r.status_code if r else 'err'} {r.text[:80] if r else ''}")

# admin fixed credentials: 0900000000 / admin123
r = post("/api/v1/auth/login", json={"phone": "0900000000", "password": "admin123"})
check("POST /api/v1/auth/login", r and r.status_code == 200,
      f"status={r.status_code if r else 'err'}")
TOKEN = None
if r and r.status_code == 200:
    TOKEN = r.json().get("token") or r.json().get("access_token")
    check("login returned token", bool(TOKEN))

AUTH = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}

if TOKEN:
    r = get("/api/v1/auth/me", headers=AUTH)
    check("GET /api/v1/auth/me", r and r.status_code == 200,
          f"status={r.status_code if r else 'err'}")

# ── 5. Subjects API ──────────────────────────────────────────────
print("\n[5] Subjects API")
r = get("/api/v1/subjects", headers=AUTH)
check("GET /api/v1/subjects (with token)", r and r.status_code == 200,
      f"status={r.status_code if r else 'err'}")
if r and r.status_code == 200:
    items = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
    check("subjects response is list", isinstance(items, list), type(items).__name__)

# ── 6. Sessions Upload ───────────────────────────────────────────
print("\n[6] Session upload")
session_payload = {
    "subject_name": "autotest-subject",
    "subject_birthday": "1990-01-01",
    "subject_gender": "M",
    "subject_age": 35,
    "report_type": "adult",
    "report_audience": "student",
    "start_time": int(time.time() * 1000) - 60000,
    "end_time":   int(time.time() * 1000),
    "total_captures": 3,
    "is_success": True,
    "captures": [
        {
            "seq_num": i, "is_baseline": 0,
            "captured_at": int(time.time()*1000) + i*1000,
            "good_signal": 0, "attention": 60+i, "meditation": 50+i,
            "delta": 75, "theta": 65,
            "low_alpha": 68, "high_alpha": 70,
            "low_beta": 62, "high_beta": 64,
            "low_gamma": 55, "high_gamma": 57
        }
        for i in range(3)
    ]
}
r = post("/api/v1/sessions/upload", json=session_payload, headers=AUTH)
check("POST /api/v1/sessions/upload", r and r.status_code in [200, 201],
      f"status={r.status_code if r else 'err'} {r.text[:120] if r else ''}")
SESSION_ID = None
if r and r.status_code in [200, 201]:
    d = r.json()
    SESSION_ID = d.get("session_id")
    check("upload returned session_id", bool(SESSION_ID))

# ── 7. EEG stats API ────────────────────────────────────────────
print("\n[7] EEG stats")
eeg_payload = {
    "session_id":   SESSION_ID or 1,
    "subject_name": "autotest-subject",
    "attention": 65, "meditation": 55,
    "delta": 75, "theta": 65,
    "low_alpha": 68, "high_alpha": 70,
    "low_beta": 62, "high_beta": 64,
    "low_gamma": 55, "high_gamma": 57
}
r = post("/api/v1/eeg/save-stats", json=eeg_payload, headers=AUTH)
check("POST /api/v1/eeg/save-stats", r and r.status_code in [200, 201, 404],
      f"status={r.status_code if r else 'err'}")

# ── 8. Reports API ──────────────────────────────────────────────
print("\n[8] Reports API")
r = get("/api/v1/reports/list", headers=AUTH)
check("GET /api/v1/reports/list", r and r.status_code == 200,
      f"status={r.status_code if r else 'err'}")
if r and r.status_code == 200:
    items = r.json() if isinstance(r.json(), list) else r.json().get("reports", r.json().get("items", []))
    check("reports list is list", isinstance(items, list), type(items).__name__)
    check(f"reports list has {len(items)} entries (>=7)", len(items) >= 7, len(items))

# ── 9. Report Gen Health ────────────────────────────────────────
print("\n[9] Report generation")
r = get("/api/v1/report-gen/health", headers=AUTH)
check("GET /api/v1/report-gen/health", r and r.status_code == 200,
      f"status={r.status_code if r else 'err'}")

# ── 10. Analysis / MBTI (HTTP API) ──────────────────────────────
print("\n[10] MBTI analysis API")
mbti_payload = {
    "delta": 75, "theta": 65,
    "low_alpha": 68, "high_alpha": 70,
    "low_beta": 62, "high_beta": 64,
    "low_gamma": 55, "high_gamma": 57,
    "attention": 65, "meditation": 55
}
r = post("/api/v1/analysis/mbti", json=mbti_payload, headers=AUTH)
check("POST /api/v1/analysis/mbti", r and r.status_code == 200,
      f"status={r.status_code if r else 'err'}")
if r and r.status_code == 200:
    d = r.json()
    # API returns "mbti" key
    mt = d.get("mbti") or d.get("mbti_type","")
    check("mbti field in response", bool(mt), str(d)[:100])
    check("mbti is 4 letters", len(str(mt)) == 4, mt)

# ── 11. MBTI Algorithm local ────────────────────────────────────
print("\n[11] MBTI algorithm (local)")
from app.services.algorithms import compute_mbti, BandAverages
p1 = BandAverages(75,65,68,68,62,62,55,55,70,55,60)
p2 = BandAverages(75,72,62,62,62,62,55,55,45,65,60)
p3 = BandAverages(75,60,75,75,62,62,55,55,55,70,60)
r1, r2, r3 = compute_mbti(p1), compute_mbti(p2), compute_mbti(p3)
check("MBTI 3 people are different",
      len({r1["mbti_type"], r2["mbti_type"], r3["mbti_type"]}) > 1,
      f"{r1['mbti_type']} {r2['mbti_type']} {r3['mbti_type']}")
all16 = set()
for la in range(30, 90, 3):
    for th in range(30, 90, 3):
        avg = BandAverages(75,th,la,la,62,62,55,55,60,50,60)
        all16.add(compute_mbti(avg)["mbti_type"])
check(f"MBTI covers >= 10 types (got {len(all16)})", len(all16) >= 10, sorted(all16))

# ── 12. App Version ─────────────────────────────────────────────
print("\n[12] App version")
r = get("/api/v1/app/version")
check("GET /api/v1/app/version", r and r.status_code == 200,
      f"status={r.status_code if r else 'err'}")
if r and r.status_code == 200:
    ver = r.json().get("html_version","") or r.json().get("version","")
    check(f"version field present ({ver})", bool(ver))

# ── Summary ─────────────────────────────────────────────────────
print("\n" + "=" * 60)
total = len(PASS) + len(FAIL)
print(f"Result: {len(PASS)}/{total} passed")
if FAIL:
    print("FAILED:")
    for f in FAIL:
        print(f"  - {f}")
else:
    print("All tests passed!")
print("=" * 60)
sys.exit(0 if not FAIL else 1)
