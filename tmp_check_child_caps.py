"""深入查看兒童 sessions 的 captures 格式"""
import requests, json, urllib3
urllib3.disable_warnings()

base = 'https://backend-production-2da61.up.railway.app/api/v1'
token = requests.post(f'{base}/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False).json()['token']
h = {'Authorization': f'Bearer {token}'}

child_sids = [113, 65, 63, 5]

for sid in child_sids:
    rc = requests.get(f'{base}/sessions/{sid}/captures', headers=h, verify=False)
    caps = rc.json().get('captures', [])
    
    rs = requests.get(f'{base}/eeg/sessions/{sid}/stats', headers=h, verify=False)
    stats = rs.json()
    
    print(f"\n{'='*60}")
    print(f"Session {sid} - {stats.get('subject_name')} ({stats.get('report_type')})")
    print(f"Total captures: {len(caps)}")
    
    # 顯示前 3 筆 captures
    bands = ['delta','theta','low_alpha','high_alpha','low_beta','high_beta','low_gamma','high_gamma']
    for i, c in enumerate(caps[:3]):
        print(f"\n  Capture {i} (seq={c.get('seq_num')}): attn={c.get('attention')} medi={c.get('meditation')}")
        for b in bands:
            print(f"    {b}: {c.get(b)}")
    
    # 判斷格式
    deltas = [c.get('delta', 0) for c in caps]
    delta_max = max(deltas) if deltas else 0
    
    if delta_max > 10000:
        fmt = "RAW（原始值，正常）"
    elif delta_max < 200:
        fmt = "⚠️ bandTo100 或數值極小（可能有問題）"
    else:
        fmt = f"不明 delta_max={delta_max}"
    
    print(f"\n  delta_max={delta_max} → {fmt}")
    
    # eeg_stats 的 bands_avg
    ba = stats.get('eeg_stats', {}).get('bands_avg', {})
    print(f"  eeg_stats.bands_avg.delta={ba.get('delta')} theta={ba.get('theta')}")
