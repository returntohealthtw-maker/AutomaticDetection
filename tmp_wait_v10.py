import requests, urllib3, time, sys
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
for i in range(40):
    try:
        hv = requests.get(BASE+'/app/version', verify=False, timeout=8).json().get('html_version')
        print(f'[{i}] {hv}', flush=True)
        if hv == '2026.07.30.10':
            print('DEPLOYED OK')
            sys.exit(0)
    except Exception as e:
        print(f'[{i}] err {e}', flush=True)
    time.sleep(8)
print('NOT YET')
sys.exit(1)
