import sys, requests, urllib3, datetime
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=8)
token = r.json().get('token','')
h = {'Authorization': 'Bearer '+token}

sl = requests.get(BASE+'/eeg/sessions?limit=200', headers=h, verify=False, timeout=15).json()
all_s = sl.get('sessions', sl) if isinstance(sl, dict) else sl

print(f"資料庫共 {len(all_s)} 筆 sessions（最新 10 筆）：")
for s in all_s[:10]:
    ca = s.get('created_at', 0)
    try: dt = datetime.datetime.fromtimestamp(int(str(ca)[:10])).strftime('%m/%d %H:%M:%S')
    except: dt = str(ca)[:16]
    print(f"  #{s.get('session_id'):4d}  {(s.get('subject_name') or '?'):18s}  {dt}  captures={s.get('total_captures','?')}  status={s.get('status','?')}")

print("\n=== 分析：資料庫沒有新 session 的可能原因 ===")
print("1. APP 上傳 HTTP 500 → 資料完全沒到後端")
print("2. APP 還在「採集中」，尚未觸發上傳")
print("3. 去重機制（15分鐘內同名 session 被擋）")

# 檢查是否有最近 90 分鐘的 session（包含被 deduplicated 的）
now = datetime.datetime.now()
cutoff = now.timestamp() - 90*60
recent = [s for s in all_s if int(str(s.get('created_at',0))[:10]) > cutoff]
print(f"\n最近 90 分鐘的 sessions（{len(recent)} 筆）：")
for s in recent:
    ca = s.get('created_at', 0)
    try: dt = datetime.datetime.fromtimestamp(int(str(ca)[:10])).strftime('%H:%M:%S')
    except: dt = str(ca)[:16]
    print(f"  #{s.get('session_id')} {(s.get('subject_name') or '?'):18s} {dt} captures={s.get('total_captures','?')}")
