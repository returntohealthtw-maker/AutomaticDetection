"""
追蹤 session 109 中「放鬆」值在三個地方為何不同
"""
import requests, sys, json, statistics
requests.packages.urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login',
                  json={'phone':'0900000000','password':'admin123'},
                  timeout=15, verify=False)
token = r.json().get('token','')
H = {'Authorization': f'Bearer {token}'}

# 取 180 筆原始 captures
r3 = requests.get(f'{BASE}/api/v1/sessions/109/captures', headers=H, timeout=20, verify=False)
caps_raw = r3.json()
caps = caps_raw if isinstance(caps_raw, list) else caps_raw.get('captures', caps_raw.get('data',[]))
print(f"captures 共 {len(caps)} 筆")

atts = [c.get('attention',0) for c in caps]
meds = [c.get('meditation',0) for c in caps]

print(f"\n【地方1 腦波比對 / 報告管理】 全 session 平均：")
print(f"  attention (專注) 平均 = {statistics.mean(atts):.1f}  (四捨五入={round(statistics.mean(atts))})")
print(f"  meditation (放鬆) 平均 = {statistics.mean(meds):.1f}  (四捨五入={round(statistics.mean(meds))})")

# ── BrainDNA best-30s window 計算 ──────────────────────────────────────
# 從 bandTo100 欄位取資料（ThinkGear 正規化值）
print("\n【地方3 生成報告】BrainDNA best 30s window 計算：")

# 取 bands 欄位
band_keys = ['delta','theta','lowAlpha','highAlpha','lowBeta','highBeta','lowGamma','highGamma']
samples = []
for c in caps:
    row = {}
    for k in band_keys + ['attention','meditation']:
        row[k] = c.get(k, 0) or 0
    samples.append(row)

# 計算 lowGamma proportionRange（best window 選取依據）
def prop_range(val, level1, level2):
    if val <= level1:
        return val / level1 * 0.5
    elif val < level2:
        return (val - level1) / (level2 - level1) * 0.5 + 0.5
    return 1.0

WINDOW = 30
best_score = -1
best_start = 0

for i in range(len(samples) - WINDOW + 1):
    window = samples[i:i+WINDOW]
    # 計算該視窗的 lowGamma 比例
    total_sums = {k: sum(row[k] for row in window) for k in band_keys}
    uncapped_total = sum(total_sums[k] for k in band_keys)
    if uncapped_total == 0:
        continue
    lg_prop_sum = 0
    for row in window:
        uncapped_row = sum(row[k] for k in band_keys)
        if uncapped_row > 0:
            lg_prop_sum += row['lowGamma'] / uncapped_row
    lg_prop = lg_prop_sum / WINDOW
    score = prop_range(lg_prop, 0.03, 0.06)
    if score > best_score:
        best_score = score
        best_start = i

best_window = samples[best_start:best_start+WINDOW]
print(f"  最佳視窗: 第 {best_start}~{best_start+WINDOW-1} 秒")

# 計算最佳視窗的平均 attention / meditation
bw_att = statistics.mean([r['attention'] for r in best_window])
bw_med = statistics.mean([r['meditation'] for r in best_window])
print(f"  best window 平均 attention (專注) = {bw_att:.1f} → 四捨五入 {round(bw_att)}")
print(f"  best window 平均 meditation (放鬆) = {bw_med:.1f} → 四捨五入 {round(bw_med)}")

# 顯示 meditation 的分佈
print(f"\n  meditation 全部值分佈：")
print(f"  min={min(meds)}, max={max(meds)}, median={statistics.median(meds):.1f}")
print(f"  各段計數：")
for rng in [(0,20),(21,40),(41,60),(61,80),(81,100)]:
    cnt = sum(1 for m in meds if rng[0] <= m <= rng[1])
    print(f"    {rng[0]}-{rng[1]}: {cnt} 筆")

# 最佳視窗的 meditation 詳情
bw_meds = [r['meditation'] for r in best_window]
print(f"\n  best window meditation 值：{bw_meds}")
print(f"  best window meditation min={min(bw_meds)}, max={max(bw_meds)}")

# ── 查 Firebase EEG 資料 ────────────────────────────────────────────
print("\n\n【Firebase 端資料】")
API_KEY = "AIzaSyBc-ZEcT8fvyn-dBZ0Bhm5IsakncVp1ngQ"
auth_r = requests.post(
    f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}",
    json={"email":"migration@returntohealthtw.com","password":"MigrateEEG@2026","returnSecureToken":True},
    timeout=15, verify=False
)
id_token = auth_r.json().get("idToken","")
FB_BASE = "https://asia-east1-gen-lang-client-0435688289.cloudfunctions.net/api/api"
FH = {"Authorization": f"Bearer {id_token}"}

fb_id = "d83e7370-bd92-4eb9-a9a0-9c8d36a4df62"
r_eeg = requests.get(f"{FB_BASE}/eeg/{fb_id}", headers=FH, timeout=15, verify=False)
print(f"GET /eeg/{fb_id}: HTTP {r_eeg.status_code}")
if r_eeg.status_code == 200:
    features = r_eeg.json()
    count = len(features) if isinstance(features, list) else "?"
    print(f"  Firebase EEG records: {count} 筆")
    if isinstance(features, list) and features:
        # 看前幾筆的 focus/relaxation 欄位
        print("  前3筆 focus/relaxation:")
        for f in features[:3]:
            print(f"    focus={f.get('focus')}, relaxation={f.get('relaxation')}")
        # 平均
        focuses = [f.get('focus',0) or 0 for f in features]
        relaxes = [f.get('relaxation',0) or 0 for f in features]
        if any(focuses):
            print(f"  Firebase EEG 平均 focus={sum(focuses)/len(focuses):.1f}, relaxation={sum(relaxes)/len(relaxes):.1f}")
else:
    print(f"  response: {r_eeg.text[:150]}")
