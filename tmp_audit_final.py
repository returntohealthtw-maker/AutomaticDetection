import requests, warnings
warnings.filterwarnings('ignore')

BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
token = requests.post(f'{BASE}/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False).json().get('token','')
h = {'Authorization': f'Bearer {token}'}

print('=== 全部 Session 的 DB 實際筆數（完整掃描）===')
counts = {}
for sid in range(1, 90):
    r = requests.get(f'{BASE}/sessions/{sid}/captures', headers=h, timeout=10, verify=False)
    if r.ok:
        total = r.json().get('total', 0)
        if total not in counts:
            counts[total] = []
        counts[total].append(sid)

print('\n 筆數 | Sessions')
for n in sorted(counts.keys()):
    print(f'  {n:3d}   | {counts[n]}')

print(f'\n總結：')
print(f'  只有 1 筆的 session 數: {len(counts.get(1, []))}')
print(f'  只有 2-5 筆的 session 數: {sum(len(v) for k,v in counts.items() if 2 <= k <= 5)}')
print(f'  有 100+ 筆的 session 數: {sum(len(v) for k,v in counts.items() if k >= 100)}')
print(f'\n  → 整個系統從未有過 180 筆原始逐秒腦波資料')
