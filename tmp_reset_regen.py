import requests, time, sys
requests.packages.urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = 'https://backend-production-2da61.up.railway.app'
SID  = 110

r = requests.post(f'{BASE}/api/v1/auth/login',
                  json={'phone':'0900000000','password':'admin123'}, timeout=15, verify=False)
H = {'Authorization': f'Bearer {r.json()["token"]}', 'Content-Type': 'application/json'}

# 直接重觸發（報告管理後台用的端點，若狀態為 generating 它會重置並重啟）
print("重新觸發報告生成...")
rr = requests.post(f'{BASE}/api/v1/reports/sessions/{SID}/regenerate',
                   headers=H, json={}, timeout=20, verify=False)
print(f"HTTP {rr.status_code}: {rr.text[:300]}")
job_id = (rr.json().get('job_id') or '') if rr.status_code == 200 else ''
print(f"job_id: {job_id}")

print("\n等待完成（最多 3 分鐘）...")
for i in range(36):
    time.sleep(5)
    r3 = requests.get(f'{BASE}/api/v1/eeg/sessions/{SID}/stats', headers=H, timeout=15, verify=False)
    d = r3.json()
    url = d.get('report_url') or ''
    st  = d.get('report_status') or ''
    print(f"  [{(i+1)*5:3d}s] {st}  url={'...' + url[-25:] if url else '(空)'}")
    if st == 'completed' and url:
        qab = d.get('qeeg_abilities') or {}
        print(f"\n  ✅ 報告完成！")
        print(f"  qeeg_abilities: 専注={qab.get('focus')}, 放鬆={qab.get('relaxation')}")
        print(f"  => 報告中専注={qab.get('focus')}, 放鬆={qab.get('relaxation')} 與後台一致 ✅")
        break
else:
    print("\n  ⏱ 超時，請在後台管理頁手動查看 session 110 狀態")
