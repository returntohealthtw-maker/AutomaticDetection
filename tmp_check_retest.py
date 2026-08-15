import sys, requests, urllib3, datetime
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=8)
token = r.json().get('token','')
h = {'Authorization': 'Bearer '+token}

sl = requests.get(BASE+'/eeg/sessions?limit=200', headers=h, verify=False, timeout=15)
all_s = sl.json().get('sessions', [])

# 篩選今天 18:49 (UTC+8 = 10:49 UTC) 以後的 session
# 18:49 UTC+8 = 18:49 - 8 = 10:49 UTC
# 2026/07/30 18:49 UTC+8 的 Unix timestamp
import datetime as dt
cutoff = int(dt.datetime(2026, 7, 30, 18, 48).timestamp())  # 18:48 UTC+8

print(f"查找 18:48 以後的所有 session (cutoff={cutoff}):")
found = []
for s in all_s:
    ca = s.get('created_at', 0)
    try:
        ts = int(ca)
        if ts > cutoff:
            found.append(s)
    except:
        pass

if not found:
    print("❌ 18:48 以後完全沒有任何 session 進入後台！")
    print("   代表 APP 重測時，upload 請求根本沒有到達後台")
    print()
    print("   可能原因：")
    print("   1. 手機網路問題（WiFi/4G 連不上 Railway）")
    print("   2. APP 顯示的錯誤是 upload 失敗（可以看APP顯示的錯誤訊息嗎？）")
    print("   3. APP 還在舊版本，upload URL 指向舊地址")
else:
    print(f"找到 {len(found)} 筆：")
    for s in found:
        ca = s.get('created_at', 0)
        try: d = datetime.datetime.fromtimestamp(int(ca)).strftime('%H:%M')
        except: d = str(ca)
        print(f"  #{s.get('session_id')} {(s.get('subject_name') or '?'):12s} {d} captures={s.get('total_captures','?')}")

# 另外確認目前 upload 端點正常
print()
print("=== 後台 upload 端點目前狀態 ===")
import time
now_ts = int(time.time())
caps = [{"seq_num":i,"captured_at":now_ts+i,"is_baseline":0,"good_signal":0,
         "attention":55,"meditation":45,"delta":250000,"theta":120000,
         "low_alpha":30000,"high_alpha":20000,"low_beta":15000,"high_beta":12000,
         "low_gamma":8000,"high_gamma":3000} for i in range(5)]
body = {"subject_name":"ping_test","consultant_name":"admin","report_type":"life_script",
        "subject_age":30,"subject_gender":"F","session_duration":5,"total_captures":5,"captures":caps}
resp = requests.post(BASE+'/sessions/upload', json=body, verify=False, timeout=15)
print(f"  HTTP {resp.status_code} → {'✅ 正常' if resp.status_code==200 else '❌ 異常'}")
if resp.status_code != 200:
    print(f"  ERROR: {resp.text[:300]}")
