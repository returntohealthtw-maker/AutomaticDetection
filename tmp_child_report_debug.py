import sys, urllib3, requests, json
urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8')
BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=15)
token = r.json().get('token','')
hdrs = {'Authorization': f'Bearer {token}'}

# 查 Session 63 狀態
s63 = requests.get(f'{BASE}/api/v1/eeg/sessions/63/stats', headers=hdrs, verify=False, timeout=15).json()
print('Session 63:')
print(f'  report_status: {s63.get("report_status")}')
print(f'  report_type:   {s63.get("report_type")}')
print(f'  subject_age:   {s63.get("subject_age")}')
print(f'  report_url:    {s63.get("report_url")}')
print()

# 嘗試觸發重新生成，看錯誤訊息
resp = requests.post(f'{BASE}/api/v1/reports/sessions/63/regenerate', headers=hdrs, verify=False, timeout=60)
print(f'Generate status code: {resp.status_code}')
try:
    print(f'Response: {json.dumps(resp.json(), ensure_ascii=False, indent=2)}')
except:
    print(f'Response text: {resp.text[:2000]}')
