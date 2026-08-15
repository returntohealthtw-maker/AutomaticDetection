"""
確認親子報告 result_url 是否可用 + session 112/111 的 bands 問題
"""
import requests, urllib3, json
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=15)
token = r.json().get('token')
s = requests.Session()
s.verify = False
s.headers.update({'Authorization': 'Bearer ' + token})

job_id = 'a99e612b-200d-4cc8-a601-e8565d055a8f'

print('=== 1. 親子報告狀態 ===')
# 透過正確的公開路由測試
status_url = f'{BASE}/parent-child/status/{job_id}'
r_status = s.get(status_url, timeout=15)
print(f'  /parent-child/status/{job_id}: {r_status.status_code}')
if r_status.status_code == 200:
    print(f'  status data: {r_status.text[:300]}')

report_url = f'{BASE}/parent-child/report/{job_id}'
r_rep = s.get(report_url, timeout=30)
ct = r_rep.headers.get('content-type','')
print(f'  /parent-child/report/{job_id}: {r_rep.status_code} ({ct}) size={len(r_rep.content)}')
if r_rep.status_code == 200:
    print('  [OK] 親子報告頁面可存取')
    # Check if it's actual HTML content
    if 'html' in ct.lower():
        print(f'  HTML preview: {r_rep.text[:200]}')
elif r_rep.status_code == 404:
    print('  [404] 報告不存在或仍在生成中')

print()
print('=== 2. 分析 result_url 問題 ===')
# 親子報告 result_url 是 localhost 格式，確認它是否可從外部公開 URL 存取
# 公開 URL 格式應是：https://backend-production-2da61.up.railway.app/parent-child/report/{job_id}
local_url = f'http://127.0.0.1:8080/parent-child/report/{job_id}'
public_url = f'{BASE}/parent-child/report/{job_id}'
print(f'  Original (localhost) result_url: {local_url}')
print(f'  Expected public result_url:      {public_url}')
print(f'  Public URL accessible: {r_rep.status_code == 200}')

print()
print('=== 3. Session 112/111 bands 診斷 ===')
for sid in [112, 111]:
    # 透過 captures API 確認有多少筆資料
    r_caps = s.get(f'{BASE}/api/v1/sessions/{sid}/captures', timeout=15)
    print(f'Session #{sid} captures: {r_caps.status_code}')
    if r_caps.status_code == 200:
        data = r_caps.json()
        if isinstance(data, list):
            caps = data
        else:
            caps = data.get('captures', [])
        print(f'  Capture count: {len(caps)}')
        if caps:
            c0 = caps[0]
            print(f'  First capture keys: {list(c0.keys())[:10]}')
            print(f'  delta={c0.get("delta")}, theta={c0.get("theta")}')
    else:
        print(f'  Error: {r_caps.text[:200]}')
    
    # 確認 eeg stats
    r_stats = s.get(f'{BASE}/api/v1/eeg/sessions/{sid}/stats', timeout=15)
    if r_stats.status_code == 200:
        stats = r_stats.json()
        print(f'  Stats: sample_count={stats.get("sample_count")}, '
              f'bands_avg={bool(stats.get("bands_avg"))}, '
              f'qeeg={bool(stats.get("qeeg_abilities"))}')
        if stats.get('bands_avg'):
            ba = stats.get('bands_avg')
            print(f'  bands: theta={ba.get("theta")}, low_alpha={ba.get("low_alpha")}, high_alpha={ba.get("high_alpha")}')

print()
print('完成')
