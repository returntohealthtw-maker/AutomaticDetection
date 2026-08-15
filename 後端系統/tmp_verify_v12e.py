"""用 retrigger endpoint 取得 qEEG 完整資料，retrigger 會重算並回傳"""
import sys, requests, json, warnings
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

BASE = 'https://backend-production-2da61.up.railway.app'
sess = requests.Session()
sess.verify = False
r = sess.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'})
tok = r.json().get('token','') or r.json().get('access_token','')
sess.headers['Authorization'] = f'Bearer {tok}'

BANDS = ['delta','theta','low_alpha','high_alpha','low_beta','high_beta','low_gamma','high_gamma']
LABELS = {'delta':'δ Delta','theta':'θ Theta','low_alpha':'α Low-α','high_alpha':'α High-α',
          'low_beta':'β Low-β','high_beta':'β High-β','low_gamma':'γ Low-γ','high_gamma':'γ High-γ'}

all_data = {}
for sid in [88, 89]:
    rr = sess.get(f'{BASE}/debug/retrigger-qeeg/{sid}')
    d = rr.json()
    all_data[sid] = d
    # Print all keys to understand structure
    print(f"=== Session {sid}: {d.get('subject_name','?')} ===")
    for k, v in d.items():
        if isinstance(v, dict) and len(str(v)) > 100:
            print(f"  {k}: dict with keys {list(v.keys())}")
        elif isinstance(v, str) and len(v) > 80:
            print(f"  {k}: (long string)")
        else:
            print(f"  {k}: {v}")
    print()

# Now get band features from the stored qeeg_scores_json via a direct DB query
# We need to check what 'signal_quality' and 'ability_scores' look like
print("=" * 70)
print("能力分數對比")
print("=" * 70)
ABILITY_LABELS = {
  'intuition':'直覺感知','energy':'精力活躍','relaxation':'放鬆冥想',
  'focus':'專注執行','logic':'邏輯分析','awareness':'意識覺察','empathy':'共情連結'
}
a88 = all_data[88].get('ability_scores', {})
a89 = all_data[89].get('ability_scores', {})
print(f"\n{'能力':<16}  {'88 (鄭靜怡)':>10}  {'89 (楊女毓)':>10}  {'差距':>8}")
print("-" * 55)
for k, lbl in ABILITY_LABELS.items():
    v88 = a88.get(k, 0)
    v89 = a89.get(k, 0)
    diff = round(abs(v89 - v88), 1)
    print(f"  {lbl:<14}  {v88:>8.1f}  {v89:>8.1f}  Δ={diff}")

sq88 = all_data[88].get('signal_quality', {})
sq89 = all_data[89].get('signal_quality', {})
print(f"\n訊號品質: 88={sq88}  89={sq89}")
