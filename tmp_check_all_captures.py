"""檢查所有 sessions 的 captures 是否有 bandTo100 (=100) 的問題"""
import requests, json, urllib3
urllib3.disable_warnings()

base = 'https://backend-production-2da61.up.railway.app/api/v1'
token = requests.post(f'{base}/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False).json()['token']
h = {'Authorization': f'Bearer {token}'}

# 取最近 20 個 sessions
r = requests.get(f'{base}/eeg/sessions?limit=200', headers=h, verify=False)
sessions = r.json().get('sessions', [])
print(f"總 sessions: {len(sessions)}")

raw_ok = []       # 正常 raw 值
bandto100 = []    # 全部=100（問題格式）
mixed = []        # 有混合（部分=100）
child_sessions = []

for s in sessions:
    sid = s.get('session_id')
    rtype = s.get('report_type', '')
    name = s.get('subject_name', '')
    
    # 只查有 captures 的
    rc = requests.get(f'{base}/sessions/{sid}/captures', headers=h, verify=False)
    if rc.status_code != 200:
        continue
    caps = rc.json().get('captures', [])
    if not caps:
        continue
    
    # 分析前 5 筆 captures 的 delta 值
    deltas = [c.get('delta', 0) for c in caps[:10]]
    delta_max = max(deltas) if deltas else 0
    
    # 看有幾筆是 bandTo100（theta=100, alpha=100...）
    all100_count = sum(1 for c in caps[:10] 
                       if c.get('theta') == 100 and c.get('low_alpha') == 100 
                       and c.get('high_alpha') == 100)
    
    category = 'raw_ok' if delta_max > 10000 and all100_count == 0 else \
               'bandto100' if all100_count >= 8 else \
               'mixed' if all100_count > 0 else 'raw_ok'
    
    info = {'session_id': sid, 'name': name, 'report_type': rtype, 
            'delta_max': delta_max, 'all100_count': all100_count,
            'total_caps': len(caps)}
    
    if category == 'raw_ok':
        raw_ok.append(info)
    elif category == 'bandto100':
        bandto100.append(info)
    else:
        mixed.append(info)
    
    if 'child' in rtype.lower():
        child_sessions.append({**info, 'category': category})

print(f"\n== 分類結果（前10筆抽樣） ==")
print(f"Raw OK（正常）: {len(raw_ok)} 筆")
print(f"BandTo100（問題）: {len(bandto100)} 筆")
print(f"Mixed（混合）: {len(mixed)} 筆")

print(f"\n== 兒童檢測 ({len(child_sessions)} 筆) ==")
for s in child_sessions:
    print(f"  session_id={s['session_id']} {s['name']} → {s['category']} (delta_max={s['delta_max']}, all100={s['all100_count']}/10)")

if bandto100:
    print(f"\n== BandTo100 問題 sessions ==")
    for s in bandto100:
        print(f"  session_id={s['session_id']} {s['name']} type={s['report_type']} total_caps={s['total_caps']}")

if mixed:
    print(f"\n== Mixed 混合 sessions ==")
    for s in mixed:
        print(f"  session_id={s['session_id']} {s['name']} type={s['report_type']} all100={s['all100_count']}/10")
