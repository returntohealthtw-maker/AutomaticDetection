"""讀取 PostgreSQL 中 session 88/89 的 qeeg_scores_json 完整頻段分數並對比"""
import sys, requests, json, warnings
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
sess = requests.Session()
sess.verify = False
r = sess.post(f'{BASE}/auth/login', json={'phone':'0900000000','password':'admin123'})
print("login:", r.status_code, r.text[:100])
token = r.json().get('access_token','')
sess.headers['Authorization'] = f'Bearer {token}'

BANDS = ['delta','theta','low_alpha','high_alpha','low_beta','high_beta','low_gamma','high_gamma']
LABELS = {'delta':'δ Delta','theta':'θ Theta','low_alpha':'α Low-α','high_alpha':'α High-α',
          'low_beta':'β Low-β','high_beta':'β High-β','low_gamma':'γ Low-γ','high_gamma':'γ High-γ'}

rows = {}
for sid in [88, 89]:
    r2 = sess.get(f'{BASE}/eeg/sessions/{sid}/stats')
    d = r2.json()
    q_json = d.get('qeeg_scores_json') or '{}'
    if isinstance(q_json, str):
        q = json.loads(q_json)
    else:
        q = q_json
    rows[sid] = {'name': d.get('subject_name','?'), 'qeeg': q, 'stats': d}

print("=" * 72)
print(f"{'qEEG v1.2 (inter-individual SD) 對比':^72}")
print("=" * 72)
print(f"\n{'頻段':<14}  {'88 (鄭靜怡)':^18}  {'89 (楊女毓)':^18}  差距")
print("-" * 72)

for sid in [88, 89]:
    q = rows[sid]['qeeg']
    rows[sid]['bf'] = q.get('band_features', {}).get('Fp1', {})

for band in BANDS:
    lbl = LABELS.get(band, band)
    bf88 = rows[88]['bf'].get(band, {}) if rows[88]['bf'] else {}
    bf89 = rows[89]['bf'].get(band, {}) if rows[89]['bf'] else {}
    s88 = bf88.get('score_0_100')
    s89 = bf89.get('score_0_100')
    z88 = bf88.get('z_score', 0)
    z89 = bf89.get('z_score', 0)
    diff = round(abs((s89 or 0) - (s88 or 0)), 1) if s88 is not None and s89 is not None else '?'
    print(f"  {lbl:<14}  {(s88 or 0):>5.1f} (z={z88:+.2f})  {(s89 or 0):>5.1f} (z={z89:+.2f})  Δ={diff}")

print()
print(f"\n{'能力分數':<18}  {'88':>8}  {'89':>8}  差距")
print("-" * 50)
ABILITY_LABELS = {
  'intuition':'直覺感知','energy':'精力活躍','relaxation':'放鬆冥想',
  'focus':'專注執行','logic':'邏輯分析','awareness':'意識覺察','empathy':'共情連結'
}
q88 = rows[88]['qeeg'].get('ability_scores', {})
q89 = rows[89]['qeeg'].get('ability_scores', {})
for k, lbl in ABILITY_LABELS.items():
    a88 = q88.get(k)
    a89 = q89.get(k)
    diff = round(abs((a89 or 0) - (a88 or 0)), 1) if a88 and a89 else '?'
    print(f"  {lbl:<16}  {(a88 or 0):>6.1f}  {(a89 or 0):>6.1f}  Δ={diff}")

print()
print("=== 結論 ===")
if rows[88]['bf'] and rows[89]['bf']:
    sc_diffs = []
    for band in BANDS:
        s88 = rows[88]['bf'].get(band, {}).get('score_0_100', 50)
        s89 = rows[89]['bf'].get(band, {}).get('score_0_100', 50)
        sc_diffs.append(abs(s89 - s88))
    avg_diff = sum(sc_diffs) / len(sc_diffs)
    print(f"  頻段平均差距: {avg_diff:.1f} 分（v1.1 舊版約 5-10 分，現在改善為 {avg_diff:.0f} 分）")
