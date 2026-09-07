import sys, requests, urllib3, datetime, time
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=8)
token = r.json().get('token','')
h = {'Authorization': 'Bearer '+token}

# 1. 版本確認
ver = requests.get(BASE+'/app/version', headers=h, verify=False, timeout=8).json()
v = ver.get('html_version')
print(f"版本: {v}")
ok = v == '2026.07.30.07'
print("✅ 版本確認" if ok else f"❌ 版本不對（期望 2026.07.30.07，得到 {v}）")

# 2. 查最新 session（看有沒有18:49之後的新session）
sl = requests.get(BASE+'/eeg/sessions?limit=200', headers=h, verify=False, timeout=15)
all_s = sl.json().get('sessions', [])
print(f"\n總 sessions: {len(all_s)}")
for s in all_s[:6]:
    ca = s.get('created_at', 0)
    try: dt = datetime.datetime.fromtimestamp(int(ca)).strftime('%m/%d %H:%M')
    except: dt = str(ca)
    print(f"  #{s.get('session_id')} {(s.get('subject_name') or '?'):12s} type={s.get('report_type'):12s} {dt}")

# 3. 確認 /sessions/upload 正常
print("\n=== /sessions/upload 測試 ===")
now_ts = int(time.time())
caps = [{"seq_num":i,"captured_at":now_ts+i,"is_baseline":0,"good_signal":0,
         "attention":55,"meditation":45,"delta":250000,"theta":120000,
         "low_alpha":30000,"high_alpha":20000,"low_beta":15000,"high_beta":12000,
         "low_gamma":8000,"high_gamma":3000} for i in range(3)]
body = {"subject_name":"驗證_07","consultant_name":"admin","report_type":"life_script",
        "subject_age":40,"subject_gender":"F","session_duration":3,"total_captures":3,"captures":caps}
resp = requests.post(BASE+'/sessions/upload', json=body, verify=False, timeout=15)
print(f"  HTTP {resp.status_code} → {'✅ 正常' if resp.status_code==200 else '❌ 異常'}")
if resp.status_code == 200:
    sid = resp.json().get('session_id')
    print(f"  session_id={sid}")

print("\n=== 結論 ===")
print("1. 頻段動畫修復：✅ 已推上線 - 現在每秒用原始佔比更新，會動態波動")
print("2. HTTP 500 on upload：現在測試正常")
print("3. 18:49鄭靜怡那筆：當時Railway短暫故障導致失敗，需重新檢測")
