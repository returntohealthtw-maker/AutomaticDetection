import requests, urllib3
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=15)
token = r.json().get('token')
s = requests.Session()
s.verify = False
s.headers.update({'Authorization': 'Bearer ' + token})

job_id = 'a99e612b-200d-4cc8-a601-e8565d055a8f'
test_urls = [
    f'{BASE}/api/v1/parent-child/report/{job_id}',
    f'{BASE}/parent-child/report/{job_id}',
    f'{BASE}/api/v1/parent-child/status/{job_id}',
]
for url in test_urls:
    try:
        r2 = s.get(url, timeout=15)
        ct = r2.headers.get('content-type', '')
        sz = len(r2.content)
        print(f'{url}')
        print(f'  -> {r2.status_code} {ct} size={sz}')
        if r2.status_code == 200:
            print('  [OK] accessible')
            if 'json' in ct:
                import json
                print('  data:', json.dumps(r2.json(), ensure_ascii=False)[:200])
        elif r2.status_code == 404:
            print('  [404 NOT FOUND]')
        else:
            print('  text:', r2.text[:200])
    except Exception as e:
        print(f'{url}')
        print(f'  -> EXCEPTION: {e}')
