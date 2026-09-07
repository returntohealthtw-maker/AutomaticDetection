import sys, requests, urllib3
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=8)
token = r.json().get('token','')
h = {'Authorization': 'Bearer '+token}

def analyze_session(sid, label):
    print(f"\n=== {label} (Session #{sid}) ===")
    cap_all = requests.get(BASE+f'/sessions/{sid}/captures?limit=200', headers=h, verify=False, timeout=15).json()
    caps = cap_all if isinstance(cap_all, list) else cap_all.get('captures', cap_all.get('data', []))
    print(f"  筆數: {len(caps)}")
    
    KEYS = ['delta','theta','low_alpha','high_alpha','low_beta','high_beta','low_gamma','high_gamma']
    
    props = {k: [] for k in KEYS}
    for c in caps:
        total = sum(c.get(k, 0) for k in KEYS)
        if total > 0:
            for k in KEYS:
                props[k].append(c.get(k, 0) / total)
    
    print(f"  {'頻段':8s}  {'平均佔比':10s}  {'最大佔比':10s}  level2    是否可能100")
    thresholds = {
        'delta': 0.60, 'theta': 0.26, 'low_alpha': 0.08, 'high_alpha': 0.08,
        'low_beta': 0.06, 'high_beta': 0.10, 'low_gamma': 0.07, 'high_gamma': 0.06
    }
    for k in KEYS:
        if props[k]:
            avg = sum(props[k])/len(props[k])
            mx  = max(props[k])
            lv2 = thresholds.get(k, 0.1)
            flag = '⚠️ 超過→100' if avg > lv2 else ('接近' if avg > lv2*0.85 else '✅ 正常')
            print(f"  {k:12s}  {avg*100:6.1f}%     {mx*100:6.1f}%     {lv2*100:.0f}%     {flag}")

# 真實鄭靜怡資料
analyze_session(124, "真實鄭靜怡 (07/30 17:47)")

# 我的測試資料（被標為鄭靜怡）
print("\n--- 對比：session #129 是我的測試資料（隨機生成，非真實腦波）---")
analyze_session(129, "我的測試資料 (random.seed(42))")
