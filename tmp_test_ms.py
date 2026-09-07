import requests, urllib3, sys, time
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'

# Android 使用 System.currentTimeMillis() = 毫秒
now_ms = int(time.time() * 1000)  # 毫秒，13位數，e.g. 1785408000000
now_s  = int(time.time())         # 秒，10位數，e.g. 1785408000

print(f"毫秒格式: {now_ms} ({len(str(now_ms))} 位)")
print(f"秒格式:   {now_s} ({len(str(now_s))} 位)")

caps_ms = [{"seq_num":i,"captured_at": now_ms + i*1000,  # 毫秒，每秒 +1000
            "is_baseline":0,"good_signal":0,"attention":55,"meditation":45,
            "delta":250000,"theta":120000,"low_alpha":30000,"high_alpha":20000,
            "low_beta":15000,"high_beta":12000,"low_gamma":8000,"high_gamma":3000}
           for i in range(5)]
body = {"subject_name":"ms_format_test","consultant_name":"admin","report_type":"life_script",
        "subject_age":40,"subject_gender":"F","session_duration":5,"total_captures":5,
        "captures":caps_ms}

print("\n=== 測試毫秒格式 captured_at ===")
resp = requests.post(BASE+'/sessions/upload', json=body, verify=False, timeout=15)
print(f"HTTP {resp.status_code}")
try:
    j = resp.json()
    if resp.status_code == 200:
        print(f"✅ 成功: session_id={j.get('session_id')}")
        # 查這個 session 存進去的 captured_at 值
        import requests as rq
        r = rq.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=8)
        h = {'Authorization': 'Bearer '+r.json().get('token','')}
        sid = j.get('session_id')
        caps_r = rq.get(BASE+f'/sessions/{sid}/captures?limit=1', headers=h, verify=False, timeout=10).json()
        cl = caps_r if isinstance(caps_r, list) else caps_r.get('captures', [])
        if cl:
            stored_ca = cl[0].get('captured_at')
            print(f"  stored captured_at={stored_ca} ({len(str(stored_ca))} 位)")
            print(f"  -> {'毫秒 ms' if stored_ca and stored_ca > 10_000_000_000 else '秒 s'}")
    else:
        print(f"❌ 失敗: {j}")
except Exception as e:
    print(f"Exception: {e}")
    print(resp.text[:300])
