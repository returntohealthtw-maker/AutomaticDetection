"""查看 session 89 captures 的真實欄位名稱"""
import sys, requests, warnings, json
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
sess = requests.Session()
sess.verify = False
r = sess.post(f'{BASE}/auth/login', json={'phone':'0900000000','password':'admin123'})
sess.headers['Authorization'] = f'Bearer {r.json()["token"]}'

r2 = sess.get(f'{BASE}/sessions/89/captures', params={'limit': 5})
d = r2.json()
print("回應 keys:", list(d.keys()))
caps = d.get('captures', [])
print(f"筆數: {len(caps)}")
if caps:
    print("\n第 1 筆資料 key/value:")
    for k, v in caps[0].items():
        print(f"  {k}: {v}")
    print("\n第 2 筆（確認一致）:")
    for k, v in caps[1].items():
        print(f"  {k}: {v}")
