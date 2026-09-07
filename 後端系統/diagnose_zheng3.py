"""查 session 87 完整診斷"""
import sys, io, json, requests, urllib3
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
urllib3.disable_warnings()

BASE = "https://backend-production-2da61.up.railway.app"
SID = 87

s = requests.Session(); s.verify = False
TOKEN = s.post(f"{BASE}/api/v1/auth/login",
               json={"phone":"0900000000","password":"admin123"}, timeout=15).json()["token"]
s.headers["Authorization"] = f"Bearer {TOKEN}"
INGEST = requests.get(f"{BASE}/api/v1/app/version", verify=False, timeout=10).json()
print("html_version:", INGEST.get("html_version"))

# headless brainwave endpoint
r = s.get(f"{BASE}/api/v1/reports/headless/brainwave/{SID}", timeout=20)
print("\n=== headless/brainwave/87 ===")
print(f"status={r.status_code}")
if r.ok:
    d = r.json()
    print(json.dumps(d, ensure_ascii=False, indent=2)[:3000])

# session detail via sessions endpoint
r2 = s.get(f"{BASE}/api/v1/sessions/{SID}", timeout=15)
print("\n=== sessions/87 ===")
print(f"status={r2.status_code}")
if r2.ok:
    print(json.dumps(r2.json(), ensure_ascii=False, indent=2)[:2000])

# captures
r3 = s.get(f"{BASE}/api/v1/sessions/{SID}/captures", timeout=15)
print("\n=== captures/87 ===")
if r3.ok:
    d3 = r3.json()
    caps = d3.get("captures", d3) if isinstance(d3, dict) else d3
    print(f"total={d3.get('total', len(caps) if isinstance(caps, list) else '?')}")
    if isinstance(caps, list) and caps:
        c0 = caps[0]
        print(f"first seq={c0.get('seq_num')} delta={c0.get('delta')} theta={c0.get('theta')}")
        print(f"keys: {list(c0.keys())[:15]}")

# stats full
r4 = s.get(f"{BASE}/api/v1/eeg/sessions/{SID}/stats", timeout=15)
print("\n=== eeg/stats/87 ===")
if r4.ok:
    d4 = r4.json()
    es = d4.get("eeg_stats", {})
    print(f"sample_count={es.get('sample_count')} bdna_mode={d4.get('bdna_mode')}")
    print(f"has raw_arrays: {bool(d4.get('raw_arrays_json') or es.get('raw_arrays_json'))}")
    print(f"firebase_session_id={d4.get('firebase_session_id')}")
    ba = es.get("bands_avg", {})
    print(f"bands_avg: {ba}")
    b7 = es.get("bands_7") or es.get("bands7")
    if b7: print(f"bands_7: {b7}")

# Check if we can see report created_at via admin diag
r5 = s.get(f"{BASE}/api/v1/reports/diag", timeout=15)
print("\n=== reports/diag ===")
print(f"status={r5.status_code}")
if r5.ok:
    print(json.dumps(r5.json(), ensure_ascii=False, indent=2)[:1500])

# Try report-gen validation - simulate start without actually starting
# Check firebase sync queue for session 87
for path in [
    "/api/v1/admin/firebase-sync/status",
    "/api/v1/admin/firebase-sync/pending",
]:
    r6 = s.get(f"{BASE}{path}", timeout=15)
    print(f"\n=== {path} === status={r6.status_code}")
    if r6.ok and isinstance(r6.json(), dict):
        j = r6.json()
        # search for session 87
        txt = json.dumps(j, ensure_ascii=False)
        if str(SID) in txt:
            print(txt[:2000])
        else:
            print(f"keys={list(j.keys())} (no mention of session {SID})")
