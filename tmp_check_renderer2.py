import requests, sys, time
requests.packages.urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login',
                  json={'phone':'0900000000','password':'admin123'}, timeout=15, verify=False)
H = {'Authorization': f'Bearer {r.json()["token"]}', 'Content-Type': 'application/json'}

# 查近期 sessions，找有 qeeg 且報告已完成的
print("查近期 sessions...")
r2 = requests.get(f'{BASE}/api/v1/eeg/sessions?limit=20', headers=H, timeout=15, verify=False)
sessions = r2.json() if isinstance(r2.json(), list) else r2.json().get('sessions', r2.json().get('data', []))
print(f"共取得 {len(sessions)} 筆")

# 列出最近 10 筆
for s in sessions[:10]:
    sid = s.get('session_id')
    name = s.get('subject_name','?')
    status = s.get('report_status','?')
    has_url = bool(s.get('report_url'))
    print(f"  sid={sid} {name} status={status} has_url={has_url}")

# 找最新一個已完成且有 URL 的
target = None
for s in sessions[:15]:
    if s.get('report_status') == 'completed' and s.get('report_url') and s.get('session_id') != 110:
        target = s
        break

if target:
    tsid = target['session_id']
    print(f"\n用 session {tsid}（{target.get('subject_name')}）做驗證重生成")
    
    # 讀 qeeg
    r3 = requests.get(f'{BASE}/api/v1/eeg/sessions/{tsid}/stats', headers=H, timeout=15, verify=False)
    d3 = r3.json()
    qab = d3.get('qeeg_abilities') or {}
    print(f"  qeeg_abilities: 専注={qab.get('focus')}, 放鬆={qab.get('relaxation')}")
    print(f"  eSense: 専注={d3.get('eeg_stats',{}).get('attention_percentage')}, 放鬆={d3.get('eeg_stats',{}).get('meditation_percentage')}")
    old_url = d3.get('report_url','')
    
    # 觸發重生成
    print(f"  觸發重生成...")
    rr = requests.post(f'{BASE}/api/v1/reports/sessions/{tsid}/regenerate',
                       headers=H, json={}, timeout=20, verify=False)
    print(f"  HTTP {rr.status_code}: {rr.text[:200]}")
    
    print(f"\n等待報告完成（最多 3 分鐘）...")
    for i in range(36):
        time.sleep(5)
        r4 = requests.get(f'{BASE}/api/v1/eeg/sessions/{tsid}/stats', headers=H, timeout=15, verify=False)
        d4 = r4.json()
        st = d4.get('report_status','')
        url = d4.get('report_url','') or ''
        print(f"  [{(i+1)*5}s] {st}  {'...' + url[-25:] if url else '(空)'}")
        if st == 'completed' and url:
            print(f"\n  ✅ 完成！qeeg_abilities={d4.get('qeeg_abilities')}")
            if url != old_url:
                print(f"  新 PDF URL（前 80 字）: {url[:80]}")
            else:
                print(f"  URL 未變（快取）")
            break
else:
    print("\n找不到可用的目標 session")
