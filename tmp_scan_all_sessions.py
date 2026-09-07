"""
掃描所有已完成的 session：比較後台 qEEG 值 vs eSense 值
找出哪些 session 的舊報告與後台不一致
"""
import requests, sys, json
requests.packages.urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login',
                  json={'phone':'0900000000','password':'admin123'}, timeout=15, verify=False)
H = {'Authorization': f'Bearer {r.json()["token"]}'}

# 取所有 session
r2 = requests.get(f'{BASE}/api/v1/eeg/sessions?limit=50', headers=H, timeout=15, verify=False)
sessions_raw = r2.json()
sessions = sessions_raw if isinstance(sessions_raw, list) else sessions_raw.get('sessions', sessions_raw.get('data', []))

print(f"共取得 {len(sessions)} 筆 session")
print()

inconsistent = []
no_qeeg = []

for s in sessions:
    sid = s.get('session_id')
    name = s.get('subject_name', '?')
    status = s.get('report_status', '?')
    has_url = bool(s.get('report_url'))
    
    # 跳過無完成報告的（目前 generating/failed）
    if not (status == 'completed' and has_url):
        print(f"  sid={sid} {name}: status={status} url={has_url} → 跳過")
        continue
    
    # 取詳細 stats
    r3 = requests.get(f'{BASE}/api/v1/eeg/sessions/{sid}/stats', headers=H, timeout=15, verify=False)
    d = r3.json()
    qab = d.get('qeeg_abilities') or {}
    eeg = d.get('eeg_stats') or {}
    q_focus  = qab.get('focus')
    q_relax  = qab.get('relaxation')
    e_attn   = eeg.get('attention_percentage')
    e_medi   = eeg.get('meditation_percentage')
    
    if not q_focus:
        no_qeeg.append({'sid': sid, 'name': name})
        print(f"  sid={sid} {name}: 無 qEEG 資料")
        continue
    
    diff_focus = abs(q_focus - (e_attn or 0))
    diff_relax = abs(q_relax - (e_medi or 0))
    is_inconsistent = diff_focus > 3 or diff_relax > 3
    
    mark = "⚠️ 不一致" if is_inconsistent else "✅ 一致"
    print(f"  sid={sid} {name}: qEEG専注={q_focus} 放鬆={q_relax} | eSense専注={e_attn} 放鬆={e_medi} → {mark}")
    
    if is_inconsistent:
        inconsistent.append({'sid': sid, 'name': name, 
                             'q_focus': q_focus, 'q_relax': q_relax,
                             'e_attn': e_attn, 'e_medi': e_medi})

print()
print("="*60)
print(f"報告已完成且有 qEEG vs eSense 差異的 session（舊報告與後台不一致）：")
for item in inconsistent:
    print(f"  sid={item['sid']} {item['name']}: 舊報告可能顯示eSense({item['e_attn']}/{item['e_medi']}) 後台顯示qEEG({item['q_focus']}/{item['q_relax']})")
print()
print(f"總計: {len(inconsistent)} 個 session 的舊報告需要重新生成")
print(f"無 qEEG 資料: {len(no_qeeg)} 個 session（不需更新）")
