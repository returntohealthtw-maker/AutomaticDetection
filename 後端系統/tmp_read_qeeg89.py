import sys, requests, json, warnings
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

BASE = 'https://backend-production-2da61.up.railway.app'
s = requests.Session()
s.verify = False
r = s.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'})
token = r.json().get('access_token','')
s.headers['Authorization'] = f'Bearer {token}'

r2 = s.get(f'{BASE}/api/v1/sessions/89')
d = r2.json()
qeeg_raw = d.get('qeeg_scores_json','')
qeeg = json.loads(qeeg_raw) if isinstance(qeeg_raw, str) else qeeg_raw

print("=== signal_quality ===")
print(json.dumps(qeeg.get('signal_quality',{}), ensure_ascii=False, indent=2))
print("\n=== ability_scores ===")
for k,v in qeeg.get('ability_scores',{}).items():
    print(f"  {k}: {v.get('score') if isinstance(v,dict) else v}")
print("\n=== composite_indices ===")
for k,v in qeeg.get('composite_indices',{}).items():
    print(f"  {k}: {v.get('score') if isinstance(v,dict) else v}")
print("\n=== report_flags ===")
for f in qeeg.get('report_flags',[]):
    print(f"  {f.get('flag')}: {f.get('severity')}")
