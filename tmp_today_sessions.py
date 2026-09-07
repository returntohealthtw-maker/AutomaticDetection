import requests, urllib3, datetime, sys
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=8)
token = r.json().get('token','')
h = {'Authorization': 'Bearer '+token}

# 目前後端健康
health = requests.get(BASE.replace('/api/v1','') + '/health', verify=False, timeout=5)
print(f"後端狀態: {health.status_code} {'OK' if health.status_code==200 else 'ERROR'}")

# 取全部 session 含失敗的
sl = requests.get(BASE+'/eeg/sessions?limit=200', headers=h, verify=False, timeout=15).json()
all_s = sl.get('sessions', sl) if isinstance(sl, dict) else sl

# 分析今天的所有 sessions
today = datetime.date.today()
today_s = [s for s in all_s if int(str(s.get('created_at',0))[:10]) > datetime.datetime(today.year, today.month, today.day).timestamp()]

print(f"\n今天 ({today}) 共 {len(today_s)} 筆 sessions:")
for s in today_s:
    ca = s.get('created_at', 0)
    try: dt = datetime.datetime.fromtimestamp(int(str(ca)[:10])).strftime('%H:%M')
    except: dt = '?'
    name = (s.get('subject_name') or '?')
    status = {1:'成功',2:'失敗','1':'成功','2':'失敗'}.get(str(s.get('status','')), f"status={s.get('status','?')}")
    cap = s.get('total_captures', '?')
    prefix = '⚠️ TEST' if name.startswith('_test_') or name in ('A驗證','B驗證','_verify_upload_test','migration_test') else '✅'
    print(f"  {prefix} #{s.get('session_id'):4d} {name:18s} {dt} captures={cap} [{status}]")

# 找22:00-23:00之間的 sessions
print("\n22:00-現在的 sessions:")
cutoff = datetime.datetime(2026, 7, 30, 22, 0, 0).timestamp()
late = [s for s in today_s if int(str(s.get('created_at',0))[:10]) >= cutoff]
if late:
    for s in late:
        ca = s.get('created_at', 0)
        try: dt = datetime.datetime.fromtimestamp(int(str(ca)[:10])).strftime('%H:%M:%S')
        except: dt = '?'
        print(f"  #{s.get('session_id')} {(s.get('subject_name') or '?')} {dt} captures={s.get('total_captures','?')}")
else:
    print("  ⛔ 完全沒有 → 上傳請求根本沒到後端")
