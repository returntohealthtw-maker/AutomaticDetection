"""深查 session 110：找出後台與報告 専注/放鬆 不一致的真正原因"""
import requests, sys, json
requests.packages.urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login',
                  json={'phone':'0900000000','password':'admin123'}, timeout=15, verify=False)
token = r.json().get('token','')
H = {'Authorization': f'Bearer {token}'}

print("=== session 110 完整 stats ===")
r2 = requests.get(f'{BASE}/api/v1/eeg/sessions/110/stats', headers=H, timeout=20, verify=False)
d = r2.json()
print(f"subject_name: {d.get('subject_name')}")
print(f"created_at: {d.get('created_at')}")
print(f"eeg_stats.attention_percentage: {d.get('eeg_stats',{}).get('attention_percentage')}")
print(f"eeg_stats.meditation_percentage: {d.get('eeg_stats',{}).get('meditation_percentage')}")
print(f"qeeg_abilities: {json.dumps(d.get('qeeg_abilities'), ensure_ascii=False)}")
print(f"report_status: {d.get('report_status')}")
print(f"report_url: {d.get('report_url','')[:80]}...")

# 取 180 筆 captures 確認 eSense 原始平均
print("\n=== session 110 captures eSense 原始值 ===")
r3 = requests.get(f'{BASE}/api/v1/sessions/110/captures', headers=H, timeout=20, verify=False)
caps_raw = r3.json()
caps = caps_raw if isinstance(caps_raw, list) else caps_raw.get('captures', caps_raw.get('data', []))
if caps:
    atts = [c.get('attention', 0) or 0 for c in caps]
    meds = [c.get('meditation', 0) or 0 for c in caps]
    print(f"captures 共 {len(caps)} 筆")
    print(f"attention 平均: {sum(atts)/len(atts):.1f}  (四捨五入={round(sum(atts)/len(atts))})")
    print(f"meditation 平均: {sum(meds)/len(meds):.1f}  (四捨五入={round(sum(meds)/len(meds))})")
else:
    print(f"回應結構: {type(caps_raw)} keys={list(caps_raw.keys()) if isinstance(caps_raw, dict) else 'list'}")

# 查 sessions.py upload 的執行順序：qEEG 是否在報告生成前完成
print("\n=== 查 sessions.py 的 qEEG 執行順序 ===")
with open(r"D:\Write program\AutomaticDetection\後端系統\app\routers\sessions.py", encoding='utf-8') as f:
    sess_src = f.read()

# 找 qeeg 和 trigger_external_report 的先後順序
qeeg_pos = sess_src.find('_qeeg_result')
report_pos = sess_src.find('trigger_external_report')
print(f"qeeg 計算位置: 行 ~{sess_src[:qeeg_pos].count(chr(10))+1}")
print(f"trigger_external_report 位置: 行 ~{sess_src[:report_pos].count(chr(10))+1}")
print(f"qEEG 先於 報告生成？: {qeeg_pos < report_pos}")

# 確認 qeeg_scores_json 是在 trigger_external_report 之前還是之後寫入
qjson_pos = sess_src.find('qeeg_scores_json')
print(f"qeeg_scores_json 寫入位置: 行 ~{sess_src[:qjson_pos].count(chr(10))+1}")
print(f"qeeg_scores_json 先於 報告生成？: {qjson_pos < report_pos}")

# 印出相關程式碼
print("\n=== sessions.py 關鍵執行順序（含行號）===")
lines = sess_src.split('\n')
for i, line in enumerate(lines, 1):
    if any(kw in line for kw in ['qeeg', 'trigger_external_report', 'db.commit', 'qeeg_scores_json', 'firebase_sync']):
        if any(c.strip() for c in [line]):
            print(f"  L{i:4d}: {line.rstrip()}")
