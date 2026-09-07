import sys, urllib3, requests
urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8')
BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=15)
token = r.json().get('token','')
hdrs = {'Authorization': f'Bearer {token}'}
resp = requests.post(f'{BASE}/api/admin/recompute-braindna?force=true', headers=hdrs, verify=False, timeout=120)
data = resp.json()
print('[所有 Session 重算結果 (使用新的 delta<30K 過濾)]')
print(f'{"Session":>10}  {"delta":>6}  {"theta":>6}  {"loAlpha":>8}  {"loB":>6}  {"hiB":>6}  {"loG":>6}  {"hiG":>6}')
print('-'*65)
for d in data.get('details', []):
    sid = d.get('session_id')
    b = d.get('bands', {})
    delta = b.get('delta','?')
    theta = b.get('theta','?')
    loa   = b.get('low_alpha','?')
    lob   = b.get('low_beta','?')
    hib   = b.get('high_beta','?')
    log   = b.get('low_gamma','?')
    hig   = b.get('high_gamma','?')
    print(f'{sid:>10}  {delta:>6}  {theta:>6}  {loa:>8}  {lob:>6}  {hib:>6}  {log:>6}  {hig:>6}')
