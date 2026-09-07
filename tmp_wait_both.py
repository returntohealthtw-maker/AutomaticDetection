import requests, sys, time
requests.packages.urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login',
                  json={'phone':'0900000000','password':'admin123'}, timeout=15, verify=False)
H = {'Authorization': f'Bearer {r.json()["token"]}'}

print("持續輪詢 session 110/111（每 20 秒，最多 10 分鐘）...")
done = {110: False, 111: False}
for i in range(30):
    time.sleep(20)
    all_done = True
    for sid in [110, 111]:
        if done[sid]:
            continue
        r3 = requests.get(f'{BASE}/api/v1/eeg/sessions/{sid}/stats', headers=H, timeout=15, verify=False)
        d = r3.json()
        st  = d.get('report_status', '?')
        url = d.get('report_url') or ''
        qab = d.get('qeeg_abilities') or {}
        name = d.get('subject_name', '?')
        print(f"  [{(i+1)*20}s] sid={sid} {name}: status={st} url={'✅' if url else '(空)'}")
        if st == 'completed' and url:
            print(f"    ✅ 完成！報告専注={qab.get('focus')} 放鬆={qab.get('relaxation')} (qEEG校正，與後台一致)")
            done[sid] = True
        elif st == 'failed':
            print(f"    ❌ 生成失敗，需重新觸發")
            done[sid] = True
        else:
            all_done = False
    if all_done:
        break
    print()
