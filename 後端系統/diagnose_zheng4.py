import sys, io, json, requests, urllib3
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
urllib3.disable_warnings()
BASE = "https://backend-production-2da61.up.railway.app"
s = requests.Session(); s.verify = False
TOKEN = s.post(f"{BASE}/api/v1/auth/login", json={"phone":"0900000000","password":"admin123"}, timeout=15).json()["token"]
s.headers["Authorization"] = f"Bearer {TOKEN}"

# Get ALL events - search in raw response text
r = s.get(f"{BASE}/api/v1/reports/events/sessions?limit=500", timeout=30)
text = r.text
print('session 87 in events response:', 'session_id": 87' in text or '"session_id":87' in text)
print('鄭靜怡 in events response:', '鄭靜怡' in text)

# Check recent failed reports
r2 = s.get(f"{BASE}/api/v1/reports/sessions-with-status?page=1&limit=10&only_missing=true", timeout=20)
if r2.ok:
    for x in r2.json().get('sessions', []):
        if x.get('session_id') == 87 or '靜怡' in (x.get('subject_name') or ''):
            print('\n=== missing session ===')
            print(json.dumps(x, ensure_ascii=False, indent=2))

# Count how many failed reports have null error (via list)
r3 = s.get(f"{BASE}/api/v1/reports/list", timeout=30)
failed_no_err = [x for x in r3.json().get('reports',[]) if x.get('status')=='failed' and not x.get('error_message') and not x.get('headless_error')]
print(f'\nFailed reports without error_message: {len(failed_no_err)}')
for x in failed_no_err[:8]:
    print(f"  report_id={x['report_id']} session={x.get('session_id')} name={x.get('subject_name')}")

# App version and when deployed
r4 = s.get(f"{BASE}/api/v1/app/version", timeout=10)
print('\napp version:', r4.json())

# raw_arrays sample count
r5 = s.get(f"{BASE}/api/v1/sessions/87", timeout=15)
if r5.ok:
    raw = r5.json().get('raw_arrays_json','')
    if raw:
        import json as j
        d = j.loads(raw)
        lens = {k: len(v) for k,v in d.items() if isinstance(v,list)}
        print('\nraw_arrays lengths:', lens)
    print('bdna_mode:', r5.json().get('bdna_mode'))
    print('mbti:', r5.json().get('mbti'))
    print('firebase_session_id:', r5.json().get('firebase_session_id'))
