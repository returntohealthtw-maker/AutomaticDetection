import json, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('/tmp/raw_arrays.json') as f:
    raw = json.load(f)

KEYS = ['r_delta','r_theta','r_lalpha','r_halpha','r_lbeta','r_hbeta','r_lgamma','r_hgamma']
CAP  = dict(r_delta=98000, r_theta=98000, r_lalpha=50000, r_halpha=50000,
            r_lbeta=50000, r_hbeta=50000, r_lgamma=10000, r_hgamma=10000)
PROP_RANGE = dict(r_delta=(0.60,0.80), r_theta=(0.15,0.30),
                  r_lalpha=(0.10,0.20), r_halpha=(0.10,0.20),
                  r_lbeta=(0.05,0.10),  r_hbeta=(0.05,0.10),
                  r_lgamma=(0.03,0.06), r_hgamma=(0.03,0.06))
MIN_DELTA = 30000

def bdna_pr(v, l1, l2):
    if v <= 0: return 0
    if v >= l2: return 1.0
    if v <= l1: return v/l1*0.5
    return (v-l1)/(l2-l1)*0.5+0.5

n = len(raw['r_lalpha'])
ps_capped = {k:0.0 for k in KEYS}
ps_true   = {k:0.0 for k in KEYS}
vs = 0
for i in range(n):
    row = {k: float(raw[k][i]) for k in KEYS}
    tot_uncapped = sum(row.values())
    if tot_uncapped <= 0: continue
    if row['r_delta'] < MIN_DELTA: continue
    for k in KEYS:
        ps_capped[k] += min(row[k], CAP[k]) / tot_uncapped
        ps_true[k]   += row[k] / tot_uncapped
    vs += 1

print(f"受測者: wayne pan  有效秒數: {vs}/{n}")
print()

labels = {'r_delta':'Delta','r_theta':'Theta','r_lalpha':'Low Alpha','r_halpha':'High Alpha',
          'r_lbeta':'Low Beta','r_hbeta':'High Beta','r_lgamma':'Low Gamma','r_hgamma':'High Gamma'}

header = f"{'頻段':<12} {'真實原始佔比':>10} {'BrainDNA截斷佔比':>14} {'proportionRange':>15}"
print(header)
print('-'*56)

for k in KEYS:
    true_pct   = ps_true[k]/vs*100
    capped_pct = ps_capped[k]/vs*100
    score = round(bdna_pr(ps_capped[k]/vs, *PROP_RANGE[k]) * 100)
    row = f"{labels[k]:<12} {true_pct:>9.1f}%  {capped_pct:>11.1f}%  {score:>12}分"
    print(row)

total_true = sum(ps_true[k]/vs*100 for k in KEYS)
total_cap  = sum(ps_capped[k]/vs*100 for k in KEYS)
print('-'*56)
print(f"{'總和':<12} {total_true:>9.1f}%  {total_cap:>11.1f}%")

print()
print('='*56)
print('5頻段合計對比（報告帶入的是 proportionRange 分數）:')
print(f"{'頻段':<8} {'真實原始佔比':>10} {'proportionRange':>13}  差距")
five = [
    ('Delta',  ['r_delta']),
    ('Theta',  ['r_theta']),
    ('Alpha',  ['r_lalpha','r_halpha']),
    ('Beta',   ['r_lbeta','r_hbeta']),
    ('Gamma',  ['r_lgamma','r_hgamma']),
]
for name, ks in five:
    true = sum(ps_true[k]/vs*100 for k in ks)
    scores = [round(bdna_pr(ps_capped[k]/vs, *PROP_RANGE[k])*100) for k in ks]
    score_avg = round(sum(scores)/len(scores))
    diff = score_avg - true
    print(f"{name:<8} {true:>9.1f}%  {score_avg:>9}分  {diff:+.1f}")

print()
print('說明：')
print('  真實原始佔比 = 每頻段/八頻段總和 × 100  (論文使用)')
print('  BrainDNA截斷佔比 = 截斷後/原始總和 × 100  (中間步驟)')
print('  proportionRange = 對照族群正常區間的正規化分數  (目前報告帶入)')
