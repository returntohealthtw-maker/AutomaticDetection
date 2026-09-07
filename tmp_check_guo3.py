import sys, requests, urllib3
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=8)
token = r.json().get('token','')
h = {'Authorization': 'Bearer '+token}

# session #116 郭以琳_test 的 captures 抽樣（看是否是真實腦波）
print("=== session #116 郭以琳_test 詳細 ===")
st = requests.get(BASE+'/eeg/sessions/116/stats', headers=h, verify=False, timeout=10).json()
print(f"  subject_name={st.get('subject_name')} report_type={st.get('report_type')}")
print(f"  total_captures={st.get('total_captures')}")
# 抽取前 5 筆看真實性
cap_r = requests.get(BASE+'/sessions/116/captures?limit=5', headers=h, verify=False, timeout=10)
if cap_r.ok:
    caps = cap_r.json()
    cl = caps if isinstance(caps, list) else caps.get('captures', caps.get('data', []))
    print(f"  前5筆 delta 值: {[c.get('delta') for c in cl[:5]]}")
    print(f"  前5筆 theta 值: {[c.get('theta') for c in cl[:5]]}")
    print(f"  （若每筆都一樣 = 模擬測試資料；各不相同 = 真實腦波）")

print()
print("=== 資料庫 sessions 總數查詢 ===")
# 用較大 limit 查全部
sl2 = requests.get(BASE+'/eeg/sessions?limit=200', headers=h, verify=False, timeout=15)
all_s = sl2.json().get('sessions', [])
print(f"  sessions 總筆數: {len(all_s)}")
guo_real = [s for s in all_s if ('郭以琳' == s.get('subject_name') or '郭以樂' == s.get('subject_name'))]
print(f"  名字完全符合「郭以琳」或「郭以樂」（非測試）: {len(guo_real)} 筆")
for s in guo_real:
    print(f"    #{s.get('session_id')} {s.get('subject_name')} type={s.get('report_type')}")

print()
if len(guo_real) == 0:
    print("結論：郭以琳、郭以樂的 APP 真實腦波資料「完全未存入後台」")
    print("      當時 VARCHAR(10) bug 導致 500，資料沒有儲存")
    print("      ➜ 需要重新檢測")
else:
    print("結論：找到真實腦波資料，可能不需要重新檢測")
