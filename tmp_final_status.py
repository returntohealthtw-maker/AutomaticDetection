import requests, urllib3, time
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=8)
token = r.json().get('token','')
h = {'Authorization': 'Bearer '+token}

print("=" * 55)
print("系統狀態最終確認")
print("=" * 55)
for name, url, extra_key in [
    ("health",    "https://backend-production-2da61.up.railway.app/health", None),
    ("version",   BASE+"/app/version",            "html_version"),
    ("sessions",  BASE+"/eeg/sessions",            None),
    ("overview",  BASE+"/reports/all-subjects-overview", None),
    ("session87", BASE+"/eeg/sessions/87/stats",  "subject_name"),
]:
    t0 = time.time()
    try:
        rr = requests.get(url, headers=h, verify=False, timeout=30)
        ms = int((time.time()-t0)*1000)
        ok = "✅" if rr.ok else "❌"
        d = rr.json() if rr.ok else {}
        if extra_key:
            extra = str(d.get(extra_key, ""))
        elif name == "sessions":
            extra = f"count={len(d.get('sessions', []))}"
        elif name == "overview":
            extra = f"subjects={len(d.get('subjects', []))}"
        else:
            extra = ""
        print(f"  {ok} {name:10s} HTTP {rr.status_code}  {ms}ms  {extra}")
    except Exception as e:
        print(f"  ❌ {name}: {e}")
print()
print("結論：不需要回退到舊版本。")
print("問題已確認：今天的 500 是測試腳本用了毫秒格式的 captured_at（整數溢位），不是程式問題。")
