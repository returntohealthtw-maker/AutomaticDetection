import sys, requests, urllib3, json, time
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
MARITAL = 'https://web-production-2c7d43.up.railway.app'

r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False)
token = r.json().get('token') or r.json().get('access_token')
h = {'Authorization': 'Bearer '+token}

# ── Step 1: debug the 500 error ──
regen_r = requests.post(BASE+'/reports/sessions/112/regenerate', json={'report_id': 130}, headers=h, verify=False)
print('Regen HTTP:', regen_r.status_code)
print('Regen headers:', dict(regen_r.headers))
print('Regen body:', regen_r.text[:500])
