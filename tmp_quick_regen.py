import requests, sys, time
requests.packages.urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login',
                  json={'phone':'0900000000','password':'admin123'}, timeout=15, verify=False)
tok = r.json()['token']
H = {'Authorization': f'Bearer {tok}', 'Content-Type': 'application/json'}

# 查 110/111 現狀
print("=== 目前 110/111 狀態 ===")
for sid in [110, 111]:
    rs = requests.get(f'{BASE}/api/v1/eeg/sessions/{sid}/stats', headers=H, timeout=15, verify=False)
    d = rs.json()
    print(f"  sid={sid} {d.get('subject_name')}: status={d.get('report_status')} url={bool(d.get('report_url'))}")

# 批次觸發其餘 session（不等待完成）
TARGETS = [109,108,107,106,105,104,103,102,101,100,99,98,97,96,95,94,93,92,90,89]
print(f"\n=== 批次觸發 {len(TARGETS)} 個 session 重新生成 ===")
ok, fail = [], []
for sid in TARGETS:
    try:
        rs = requests.get(f'{BASE}/api/v1/eeg/sessions/{sid}/stats', headers=H, timeout=10, verify=False)
        cur = rs.json().get('report_status','?')
        if cur == 'generating':
            print(f"  sid={sid}: 已在 generating，跳過")
            continue
        rr = requests.post(f'{BASE}/api/v1/reports/sessions/{sid}/regenerate',
                           headers=H, json={}, timeout=15, verify=False)
        if rr.status_code == 200:
            jid = rr.json().get('job_id','?')
            print(f"  ✅ sid={sid}: 觸發成功 job={jid}")
            ok.append(sid)
        else:
            print(f"  ❌ sid={sid}: HTTP {rr.status_code}")
            fail.append(sid)
    except Exception as e:
        print(f"  ❌ sid={sid}: {e}")
        fail.append(sid)
    time.sleep(1)  # 避免觸發太快

print(f"\n成功觸發: {len(ok)} 個  失敗: {len(fail)} 個")
print("所有報告完成後，専注/放鬆 數值將與後台 qEEG 值一模一樣")
