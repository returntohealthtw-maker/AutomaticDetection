import requests, urllib3
from datetime import datetime, timezone, timedelta
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
now = datetime.now(timezone.utc)
r = requests.post(BASE+'/sessions/upload', json={
    "subject_name":"驗證測試_完整","subject_age":30,"subject_gender":"male",
    "report_type":"adult","consultant_name":"系統管理員",
    "captures":[{"seq_num":i,
                 "captured_at":(now+timedelta(seconds=i)).isoformat(),
                 "delta":200000,"theta":80000,"low_alpha":30000,
                 "high_alpha":20000,"low_beta":15000,"high_beta":12000,
                 "low_gamma":8000,"high_gamma":3000,"good_signal":0,
                 "attention":60,"meditation":55,"is_baseline":0} for i in range(10)]
}, verify=False, timeout=20)
import json
print(r.status_code)
if r.ok:
    d = r.json()
    print(f"session_id={d.get('session_id')} captures_saved={d.get('captures_saved')} firebase_sync_ok={d.get('firebase_sync_ok')}")
else:
    print(r.text[:200])
