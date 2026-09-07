import sys, requests, json, warnings
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

BASE = 'https://backend-production-2da61.up.railway.app'
s = requests.Session()
s.verify = False
r = s.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'})
token = r.json().get('access_token','')
s.headers['Authorization'] = f'Bearer {token}'

# 查 session 89 完整 debug 資料
r2 = s.get(f'{BASE}/debug/resync-raw-session/89')
print("=== debug endpoint ===")
print(json.dumps(r2.json(), ensure_ascii=False, indent=2))

# 查看 logs 是否有 qEEG 相關記錄
r3 = s.get(f'{BASE}/api/v1/sessions/89/captures', params={'limit': 5})
caps = r3.json().get('captures', [])
print(f"\n=== captures 數量: {len(caps)} ===")
if caps:
    print("good_signal 值（前5筆）:", [c.get('good_signal') for c in caps[:5]])
    print("seq_num 範圍:", caps[0].get('seq_num'), "~", caps[-1].get('seq_num') if len(caps)>1 else '?')
