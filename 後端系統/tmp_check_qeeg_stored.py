import sys, requests, json, warnings
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

BASE = 'https://backend-production-2da61.up.railway.app'
s = requests.Session()
s.verify = False
r = s.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'})
token = r.json().get('access_token','')
s.headers['Authorization'] = f'Bearer {token}'

# 查 session 89 的 qeeg_scores_json via stats endpoint
r2 = s.get(f'{BASE}/api/v1/eeg/sessions/89/stats')
stats = r2.json()
print("=== session 89 stats ===")
# Check if qeeg_scores_json exists in stats
qeeg_json = stats.get('qeeg_scores_json')
if qeeg_json:
    if isinstance(qeeg_json, str):
        qeeg = json.loads(qeeg_json)
    else:
        qeeg = qeeg_json
    print(f"qEEG signal_quality: {qeeg.get('signal_quality', {}).get('quality_grade')}")
    print(f"qEEG abilities: {list(qeeg.get('ability_scores', {}).keys())}")
else:
    print("qeeg_scores_json 不存在於 stats 回應中")
    print("可用欄位：", list(stats.keys()))

# 直接 debug endpoint 取得原始 qeeg
r3 = s.get(f'{BASE}/debug/qeeg/89')
if r3.status_code == 200:
    print("\n=== debug/qeeg/89 ===")
    print(json.dumps(r3.json(), ensure_ascii=False, indent=2)[:2000])
else:
    print(f"\ndebug/qeeg/89 → {r3.status_code}: {r3.text[:200]}")
