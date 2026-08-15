import sys, requests, urllib3
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=8)
token = r.json().get('token','')
h = {'Authorization': 'Bearer '+token}

# 查所有 sessions 中名字含「郭以」的
print("=== 查所有 sessions 含「郭以琳」或「郭以樂」===")
sl = requests.get(BASE+'/eeg/sessions', headers=h, verify=False, timeout=10)
all_sessions = sl.json().get('sessions', [])
print(f"  總共 {len(all_sessions)} 筆 sessions")

guo_sessions = [s for s in all_sessions if '郭以' in (s.get('subject_name') or '')]
print(f"  含「郭以」的 sessions：{len(guo_sessions)} 筆")
for s in guo_sessions:
    sid = s.get('session_id')
    print(f"\n  #{sid} {s.get('subject_name')} type={s.get('report_type')} status_code={s.get('status')}")
    # 查這個 session 的 captures
    cap_r = requests.get(BASE+f'/sessions/{sid}/captures?limit=3', headers=h, verify=False, timeout=10)
    if cap_r.ok:
        caps = cap_r.json()
        if isinstance(caps, dict):
            caps_list = caps.get('captures', caps.get('data', []))
            total = caps.get('total', len(caps_list))
        else:
            caps_list = caps
            total = len(caps)
        print(f"    captures總筆數: {total}")
        if caps_list:
            c = caps_list[0]
            print(f"    第1筆: delta={c.get('delta')} good_signal={c.get('good_signal')}")
    else:
        print(f"    captures查詢失敗: {cap_r.status_code}")

if not guo_sessions:
    print("  ❌ 資料庫中完全找不到郭以琳/郭以樂的真實腦波 session")
    print("  → 他們的 APP 檢測因 500 錯誤，資料完全沒有存入後台")
    print("  → 需要重新檢測")
