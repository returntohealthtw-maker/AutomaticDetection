import requests, sys, time
requests.packages.urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login',
                  json={'phone':'0900000000','password':'admin123'}, timeout=15, verify=False)
H = {'Authorization': f'Bearer {r.json()["token"]}'}

print("輪詢 session 110/111 狀態（5 分鐘，每 30 秒一次）...")
for i in range(10):
    time.sleep(30)
    for sid in [110, 111]:
        r3 = requests.get(f'{BASE}/api/v1/eeg/sessions/{sid}/stats', headers=H, timeout=15, verify=False)
        d = r3.json()
        st  = d.get('report_status', '?')
        url = d.get('report_url') or ''
        qab = d.get('qeeg_abilities') or {}
        print(f"  [{(i+1)*30}s] sid={sid} {d.get('subject_name','?')} status={st}  url={'✅' if url else '(空)'}  qEEG専注={qab.get('focus')} 放鬆={qab.get('relaxation')}")
        if st == 'completed' and url:
            print(f"    !! 完成！PDF: {url[:80]}")
    print()
