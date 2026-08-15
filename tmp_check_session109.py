import requests, sys, json
requests.packages.urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login',
                  json={'phone':'0900000000','password':'admin123'},
                  timeout=15, verify=False)
token = r.json().get('token','')
H = {'Authorization': f'Bearer {token}'}

print("=== session 109 完整 stats ===")
r2 = requests.get(f'{BASE}/api/v1/eeg/sessions/109/stats', headers=H, timeout=15, verify=False)
data = r2.json()
print(json.dumps(data, ensure_ascii=False, indent=2))

print("\n=== session 109 前 5 筆 captures（看 attention/meditation 原始值）===")
r3 = requests.get(f'{BASE}/api/v1/sessions/109/captures', headers=H, timeout=15, verify=False)
caps = r3.json()
if isinstance(caps, list):
    for c in caps[:5]:
        print(f"  seq={c.get('seq_num',c.get('sequence_num','?'))} attention={c.get('attention')} meditation={c.get('meditation')}")
    # 計算平均
    atts = [c.get('attention',0) for c in caps if c.get('attention') is not None]
    meds = [c.get('meditation',0) for c in caps if c.get('meditation') is not None]
    print(f"\n  全 {len(atts)} 筆平均: attention={sum(atts)/len(atts):.1f}, meditation={sum(meds)/len(meds):.1f}")
elif isinstance(caps, dict):
    inner = caps.get('captures', caps.get('data', []))
    for c in inner[:5]:
        print(f"  seq={c.get('seq_num','?')} attention={c.get('attention')} meditation={c.get('meditation')}")
    atts = [c.get('attention',0) for c in inner if c.get('attention') is not None]
    meds = [c.get('meditation',0) for c in inner if c.get('meditation') is not None]
    if atts:
        print(f"\n  全 {len(atts)} 筆平均: attention={sum(atts)/len(atts):.1f}, meditation={sum(meds)/len(meds):.1f}")
