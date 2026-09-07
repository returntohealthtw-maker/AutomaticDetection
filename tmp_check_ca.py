import requests, urllib3, sys
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=8)
h = {'Authorization': 'Bearer '+r.json().get('token','')}
c = requests.get(BASE+'/sessions/124/captures?limit=2', headers=h, verify=False, timeout=10).json()
caps = c if isinstance(c, list) else c.get('captures', c.get('data', []))
for cap in caps[:2]:
    ca = cap.get('captured_at')
    print(f"captured_at={ca} (len={len(str(ca))} digits)")
    print(f"  -> {'毫秒 ms' if ca and ca > 10_000_000_000 else '秒 s'}")
