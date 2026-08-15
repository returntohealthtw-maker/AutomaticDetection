import requests, json

BASE = "https://backend-production-2da61.up.railway.app/api/v1"
r = requests.post(f"{BASE}/auth/login", json={"phone": "0900000000", "password": "admin123"}, timeout=30)
token = r.json()["token"]
headers = {"Authorization": f"Bearer {token}"}

data = json.load(open('_tmp_child_reports.json', encoding='utf-8'))
for c in data:
    rid = c['report_id']
    sid = c['session_id']
    r = requests.get(f"{BASE}/reports/session/{sid}/signed-url", params={"report_id": rid, "days": 3}, headers=headers, timeout=30)
    print(rid, sid, r.status_code)
    j = r.json()
    url = j.get("signed_url") or j.get("url") or j.get("pdf_url")
    print("  url key found:", list(j.keys()))
    if not url:
        print("  RESP:", json.dumps(j, ensure_ascii=False)[:300])
        continue
    resp = requests.get(url, timeout=60)
    fn = f'_tmp_child_{rid}.pdf'
    with open(fn, 'wb') as f:
        f.write(resp.content)
    print('  saved', fn, len(resp.content), 'bytes')
