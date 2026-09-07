import sys, requests, urllib3, json, time
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False)
token = r.json().get('token') or r.json().get('access_token')
h = {'Authorization': 'Bearer '+token}

# 先 reset report #130 back to pending
reset_r = requests.post(BASE+'/report-gen/reset-stuck', json={'report_id': 130}, headers=h, verify=False)
print("Reset #130:", reset_r.status_code, reset_r.text[:200])

time.sleep(2)

# 查 session 112 的 subject_id
sr = requests.get(BASE+'/eeg/sessions/112/stats', headers=h, verify=False)
d = sr.json()
subject_id = d.get('subject_id')
print("subject_id:", subject_id)

# Trigger marital report regeneration
payload = {
    "session_id": 112,
    "report_type": "marital",
    "partner_session_id": 49,
    "name": "洪任佑",
    "partner_name": "王筱琪"
}
tr = requests.post(BASE+'/report-gen/trigger', json=payload, headers=h, verify=False)
print("Trigger marital regen:", tr.status_code, tr.text[:300])
