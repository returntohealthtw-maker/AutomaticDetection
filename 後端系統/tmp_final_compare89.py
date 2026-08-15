"""
Session 89 楊女毓 — BrainDNA vs qEEG Z-score 最終對比（修正後）
"""
import sys, requests, json, warnings, math
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

BASE = 'https://backend-production-2da61.up.railway.app'
s = requests.Session()
s.verify = False
r = s.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'})
token = r.json().get('access_token','')
s.headers['Authorization'] = f'Bearer {token}'

# 取 session 89 完整資料
r2 = s.get(f'{BASE}/api/v1/sessions/89')
d = r2.json()
qeeg_raw = d.get('qeeg_scores_json','')
qeeg = json.loads(qeeg_raw) if isinstance(qeeg_raw, str) and qeeg_raw else {}

# ── BrainDNA (best 30s window) 結果 ──
# 取 captures 重算
r3 = s.get(f'{BASE}/api/v1/sessions/89/captures', params={'limit': 200})
data = r3.json()
caps = data.get('captures', data if isinstance(data, list) else [])
raw_caps = sorted([c for c in caps if c.get('delta', 0) > 1000],
                  key=lambda c: c.get('seq_num', 0))

BANDS = ['delta','theta','low_alpha','high_alpha','low_beta','high_beta','low_gamma','high_gamma']
CAP = {b: 2_000_000 for b in BANDS}
_PROP_RANGE = {
    'delta': (0.60, 0.80), 'theta': (0.15, 0.30),
    'low_alpha': (0.10, 0.20), 'high_alpha': (0.10, 0.20),
    'low_beta': (0.05, 0.10), 'high_beta': (0.05, 0.10),
    'low_gamma': (0.03, 0.06), 'high_gamma': (0.03, 0.06),
}
def _pr(val, l1, l2):
    if val >= l2: return 1.0
    if val <= l1: return val/l1*0.5
    return (val-l1)/(l2-l1)*0.5+0.5

WINDOW_SIZE = 30
best_score, best_idx = -1, -1
for start in range(0, len(raw_caps), WINDOW_SIZE):
    w = raw_caps[start:start+WINDOW_SIZE]
    if len(w) < WINDOW_SIZE: continue
    lg_prop = 0.0
    for cap in w:
        vals = {b: float(cap.get(b,0) or 0) for b in BANDS}
        tot = sum(vals.values())
        if tot > 0: lg_prop += vals['low_gamma']/tot
    avg = lg_prop / WINDOW_SIZE
    sc = _pr(avg, 0.03, 0.06)
    if sc > best_score: best_score, best_idx = sc, start

bdna = {}
if best_idx >= 0:
    w = raw_caps[best_idx:best_idx+WINDOW_SIZE]
    for band in BANDS:
        ps = 0.0
        for cap in w:
            vals = {b: float(cap.get(b,0) or 0) for b in BANDS}
            tot = sum(vals.values())
            if tot > 0: ps += vals[band]/tot
        avg_p = ps / len(w)
        l1,l2 = _PROP_RANGE[band]
        bdna[band] = {'prop': round(avg_p*100,2), 'score': min(100, round(_pr(avg_p,l1,l2)*100))}

print("=" * 65)
print("  Session 89 楊女毓 — BrainDNA vs qEEG Z-score 對比（修正後）")
print("=" * 65)
print(f"\n【BrainDNA 頻段分數（Best 30s window: 第{best_idx}-{best_idx+WINDOW_SIZE-1}秒）】")
print(f"  {'頻段':<14} {'佔比%':>8}  {'BrainDNA分數':>12}")
print(f"  {'-'*40}")
for b in BANDS:
    info = bdna.get(b, {})
    note = " ← 超過閾值上限 cap 到 100" if info.get('score',0) == 100 else ""
    print(f"  {b:<14} {info.get('prop',0):>7.2f}%  {info.get('score',0):>12}{note}")

print(f"\n【qEEG Z-score 能力分數（已更新：常模校準+訊號品質修正）】")
sq = qeeg.get('signal_quality', {})
print(f"  訊號品質: {sq.get('quality_grade','?')} (可用 epoch: {sq.get('usable_epoch_ratio',0)*100:.1f}%)")
print(f"  {'能力':<14} {'分數':>8}")
print(f"  {'-'*25}")
ability_names_cn = {
    'intuition': '直覺感知',
    'energy': '活力精力',
    'relaxation': '放鬆冥想',
    'focus': '專注力',
    'logic': '邏輯分析',
    'awareness': '整合意識',
    'empathy': '情緒共感',
}
for k, v in qeeg.get('ability_scores', {}).items():
    sc = v.get('score') if isinstance(v, dict) else v
    cn = ability_names_cn.get(k, k)
    print(f"  {cn:<14} {sc:>8.1f}")

print(f"\n【qEEG 複合心理功能指標】")
composite_names_cn = {
    'ccr': '認知負荷彈性',
    'ebi': '能量-平靜平衡',
    'reb': '靜息 Alpha 效能',
    'rrr': '放鬆-甦醒比',
    'sli': '壓力耐受指標',
    'edc': '情緒調節穩定',
    'isi': '整合同理指數',
}
for k, v in qeeg.get('composite_indices', {}).items():
    sc = v.get('score') if isinstance(v, dict) else v
    cn = composite_names_cn.get(k, k)
    print(f"  {cn:<14} {sc:>8.1f}")

print(f"\n【修正前 vs 修正後 qEEG 對比】")
print(f"  {'項目':<20} {'修正前':>10}  {'修正後':>10}")
print(f"  {'-'*45}")
print(f"  {'訊號品質(grade)':<20} {'D (0.0%)':>10}  {sq.get('quality_grade','?') + f' ({sq.get(\"usable_epoch_ratio\",0)*100:.0f}%)':>10}")
print(f"  {'常模版本':<20} {'v1.0(文獻誤用)':>10}  {'v1.1(TG校準)':>10}")
print(f"  {'直覺感知':<20} {'29.7':>10}  {qeeg.get('ability_scores',{}).get('intuition',{}).get('score',0) if isinstance(qeeg.get('ability_scores',{}).get('intuition'),dict) else qeeg.get('ability_scores',{}).get('intuition',0):>10.1f}")
print(f"  {'邏輯分析':<20} {'21.3':>10}  {qeeg.get('ability_scores',{}).get('logic',{}).get('score',0) if isinstance(qeeg.get('ability_scores',{}).get('logic'),dict) else qeeg.get('ability_scores',{}).get('logic',0):>10.1f}")
print(f"  {'專注力':<20} {'42.2':>10}  {qeeg.get('ability_scores',{}).get('focus',{}).get('score',0) if isinstance(qeeg.get('ability_scores',{}).get('focus'),dict) else qeeg.get('ability_scores',{}).get('focus',0):>10.1f}")
