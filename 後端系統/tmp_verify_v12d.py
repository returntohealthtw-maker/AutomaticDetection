"""用 retrigger endpoint 取得最新 qEEG 結果（retrigger 會即時計算並回傳）"""
import sys, requests, json, warnings
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

BASE = 'https://backend-production-2da61.up.railway.app'
sess = requests.Session()
sess.verify = False
r = sess.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'})
sess.headers['Authorization'] = f'Bearer {r.json()["token"]}'

BANDS = ['delta','theta','low_alpha','high_alpha','low_beta','high_beta','low_gamma','high_gamma']
LABELS = {'delta':'δ Delta','theta':'θ Theta','low_alpha':'α Low-α','high_alpha':'α High-α',
          'low_beta':'β Low-β','high_beta':'β High-β','low_gamma':'γ Low-γ','high_gamma':'γ High-γ'}

rows = {}
for sid in [88, 89]:
    rr = sess.get(f'{BASE}/debug/retrigger-qeeg/{sid}')
    print(f"retrigger {sid}: {rr.status_code}")
    d = rr.json()
    rows[sid] = d

print()

# retrigger 回傳結構中有 ability_scores + signal_quality
# 還要取 band_features，需要讀 postgres stored qeeg
# 嘗試取 full qeeg from stats endpoint with different format
for sid in [88, 89]:
    rr2 = sess.get(f'{BASE}/api/v1/eeg/sessions/{sid}/stats')
    d2 = rr2.json()
    keys = list(d2.keys())
    print(f"Session {sid} stats keys: {keys}")
    # 嘗試找 qeeg
    for k in keys:
        if 'qeeg' in str(k).lower():
            val = d2[k]
            print(f"  {k}: {str(val)[:200]}")
    print()
