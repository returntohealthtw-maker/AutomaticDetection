import requests, time, sys
requests.packages.urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login',
                  json={'phone':'0900000000','password':'admin123'}, timeout=15, verify=False)
H = {'Authorization': f'Bearer {r.json()["token"]}'}

old_end = 'bed58597660a4aa4183002f57a1945'
print('等待新 PDF 生成...')
for i in range(30):
    time.sleep(5)
    r3 = requests.get(f'{BASE}/api/v1/eeg/sessions/110/stats', headers=H, timeout=15, verify=False)
    d = r3.json()
    url = d.get('report_url') or ''
    st = d.get('report_status') or ''
    url_end = url[-30:] if url else '(empty)'
    print(f'  [{(i+1)*5}s] status={st}  ...{url_end}')
    if st == 'completed' and url and old_end not in url:
        print('  !! 新報告 URL 產生:', url[:100])
        break
    if st == 'completed' and url and i >= 14:
        print('  URL 未改變 (快取或相同 hash)')
        break
