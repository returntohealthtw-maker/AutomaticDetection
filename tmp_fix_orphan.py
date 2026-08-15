"""
1. 把郭以琳/郭以樂的卡住報告標記為 failed
2. 確認前端後台能看到他們
"""
import sys, requests, urllib3
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'

r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False)
token = r.json().get('token') or r.json().get('access_token')
h = {'Authorization': 'Bearer '+token}

# 清掉卡住的 orphan 報告
for rid in [136, 137, 138]:
    ru = requests.post(BASE+f'/reports/{rid}/update-summary',
                       json={"status": "failed"}, headers=h, verify=False)
    print(f"report #{rid} → failed: {ru.status_code} {ru.text[:100]}")

print()
# 確認前台顯示
for name in ['郭以琳', '郭以樂']:
    ov = requests.get(BASE+f'/reports/all-subjects-overview?q={name}', headers=h, verify=False)
    d = ov.json().get('subjects', [])
    for s in d:
        if name in (s.get('name') or ''):
            print(f"{s.get('name')}: sessions_count={s.get('sessions_count')}, "
                  f"reports={[(r.get('report_id'), r.get('status')) for r in s.get('reports',[])]}")
