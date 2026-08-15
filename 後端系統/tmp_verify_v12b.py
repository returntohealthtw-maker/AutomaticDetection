import sys, requests, json, warnings, math
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

BASE = 'https://backend-production-2da61.up.railway.app'
s = requests.Session()
s.verify = False
r = s.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'})
token = r.json().get('access_token','')
s.headers['Authorization'] = f'Bearer {token}'

for sid in [88, 89]:
    rr = s.get(f'{BASE}/debug/retrigger-qeeg/{sid}')
    print(f"Session {sid} status: {rr.status_code}")
    try:
        data = rr.json()
        keys = list(data.keys())
        print(f"  top keys: {keys}")
        # 找 qeeg 相關
        for k in keys:
            if 'qeeg' in k.lower() or 'band' in k.lower() or 'ability' in k.lower():
                v = data[k]
                if isinstance(v, dict):
                    print(f"  {k}: {json.dumps(v, ensure_ascii=False)[:400]}")
    except:
        print(f"  {rr.text[:200]}")
    print()
