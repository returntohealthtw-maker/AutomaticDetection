import sys, requests, json, warnings
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

BASE = 'https://backend-production-2da61.up.railway.app'
s = requests.Session()
s.verify = False
r = s.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'})
token = r.json().get('access_token','')
s.headers['Authorization'] = f'Bearer {token}'

# 查所有 sessions，找到 session 89
r2 = s.get(f'{BASE}/api/v1/eeg/sessions')
data = r2.json()
sessions = data if isinstance(data, list) else data.get('sessions', [])
for sess in sessions:
    sid = sess.get('session_id') or sess.get('id')
    if str(sid) == '89':
        print("=== session 89 ===")
        print(json.dumps(sess, ensure_ascii=False, indent=2))
        break
else:
    print("未找到 session 89，列出可用欄位：")
    if sessions:
        print(json.dumps(sessions[0], ensure_ascii=False, indent=2))

# 查 session 89 stats
r3 = s.get(f'{BASE}/api/v1/sessions/89/stats')
print(f"\n=== /sessions/89/stats → {r3.status_code} ===")
if r3.ok:
    d = r3.json()
    qeeg = d.get('qeeg_scores_json')
    if qeeg:
        print("qeeg_scores_json 存在！")
    else:
        print("qeeg_scores_json 不存在。可用欄位：", list(d.keys())[:15])
