import json, math, urllib3, requests, statistics, sys
urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8')

BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login',
                  json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=15)
token = r.json().get('token','')
hdrs = {'Authorization': f'Bearer {token}'}

def get_raw(sid):
    return requests.get(f'{BASE}/api/admin/raw-export/{sid}',
                        headers=hdrs, verify=False, timeout=30).json().get('raw_arrays', {})

raw60 = get_raw(60)
raw57 = get_raw(57)
KEYS = ['r_delta','r_theta','r_lalpha','r_halpha','r_lbeta','r_hbeta','r_lgamma','r_hgamma']
CAP  = dict(r_delta=98000,r_theta=98000,r_lalpha=50000,r_halpha=50000,
            r_lbeta=50000,r_hbeta=50000,r_lgamma=10000,r_hgamma=10000)

def get_row(raw, i):
    return {k: float((raw.get(k) or [0])[i] if i < len(raw.get(k) or []) else 0) for k in KEYS}

# ── 最佳視窗逐秒 ─────────────────────────────────────────────────────────────
print('[Session #60 最佳視窗 (秒30~59) 逐秒詳細分析]')
print(f'{"秒":>4}  {"delta":>10}  {"hbeta":>10}  {"lgamma":>10}  {"uncap總":>12}  {"hb%":>7}  {"lg%":>7}  標記')
print('-'*85)

hb_props, lg_props, deltas = [], [], []
suspicious = []
for i in range(30, 60):
    row = get_row(raw60, i)
    total = sum(row.values())
    hb_cap = min(row['r_hbeta'], 50000)
    lg_cap = min(row['r_lgamma'], 10000)
    hb_p = hb_cap / total * 100 if total else 0
    lg_p = lg_cap / total * 100 if total else 0
    hb_props.append(hb_p)
    lg_props.append(lg_p)
    deltas.append(row['r_delta'])

    flags = []
    if row['r_delta'] < 20000:        flags.append('DELTA極低!')
    elif row['r_delta'] < 50000:      flags.append('delta偏低')
    if row['r_theta'] > 90000:        flags.append('theta高')
    ab = row['r_lalpha']+row['r_halpha']+row['r_lbeta']+row['r_hbeta']
    if ab > 120000:                   flags.append('EMG?')
    if lg_p > 6.0:                    flags.append(f'lg超閾値')
    if hb_p > 10.0:                   flags.append(f'hb超閾值')
    if flags:
        suspicious.append(i)
    f = '  '.join(flags)
    delta_v = row['r_delta']
    hbeta_v = row['r_hbeta']
    lgamma_v = row['r_lgamma']
    print(f'{i:4d}  {delta_v:>10,.0f}  {hbeta_v:>10,.0f}  {lgamma_v:>10,.0f}  {total:>12,.0f}  {hb_p:7.2f}  {lg_p:7.2f}  {f}')

print()
print(f'hbeta  每秒佔比: 最小={min(hb_props):.2f}%  最大={max(hb_props):.2f}%  '
      f'平均={statistics.mean(hb_props):.3f}%  [BrainDNA閾值 5%~10%]')
print(f'lgamma 每秒佔比: 最小={min(lg_props):.2f}%  最大={max(lg_props):.2f}%  '
      f'平均={statistics.mean(lg_props):.3f}%  [BrainDNA閾值 3%~6%]')
print(f'超過上限閾值:  hbeta>10%: {sum(1 for p in hb_props if p>10)}/30秒  '
      f'lgamma>6%: {sum(1 for p in lg_props if p>6)}/30秒')
print()
print(f'Delta 逐秒範圍: 最小={min(deltas):,.0f}  最大={max(deltas):,.0f}  '
      f'變化倍數={max(deltas)/max(min(deltas),1):.0f}x')
print(f'族群平均 delta: 198,609  (Session60 均值: {statistics.mean(deltas):,.0f})')
print()
print(f'可疑秒數 (delta極低/EMG/超閾值): {suspicious}')

# ── 找出根本原因：delta 與 gamma 相關性 ─────────────────────────────────────
print()
print('[delta值 vs lgamma佔比 相關分析]')
pairs = []
for i in range(30, 60):
    row = get_row(raw60, i)
    total = sum(row.values())
    lg_p = min(row['r_lgamma'], 10000) / total * 100 if total else 0
    pairs.append((row['r_delta'], lg_p))
# 低delta(<50K) vs 高delta(>100K)
low_d = [p for d,p in pairs if d < 50000]
high_d = [p for d,p in pairs if d > 100000]
print(f'  delta < 50K  的秒數: {len(low_d)}秒  lgamma佔比均值 = {statistics.mean(low_d):.2f}%')
print(f'  delta > 100K 的秒數: {len(high_d)}秒  lgamma佔比均值 = {statistics.mean(high_d) if high_d else 0:.2f}%')
print()

# ── 對照 Session 57 同一範圍 ─────────────────────────────────────────────────
print('[Session #57 最佳視窗 (秒30~59) delta分佈對比]')
deltas57 = [get_row(raw57, i)['r_delta'] for i in range(30, 60)]
low57 = sum(1 for d in deltas57 if d < 50000)
high57 = sum(1 for d in deltas57 if d > 100000)
print(f'  Session 57: delta最小={min(deltas57):,.0f}  最大={max(deltas57):,.0f}  '
      f'均值={statistics.mean(deltas57):,.0f}')
print(f'  Session 57: delta<50K的秒數={low57}/30  delta>100K的秒數={high57}/30')
print()

# ── 假如過濾掉 delta 極低的秒數，結果會怎樣 ─────────────────────────────────
print('[若過濾 delta<10000 的秒數 → 結果變化]')
def calc_final(raw, start, end, min_delta=0):
    prop_sums = {k: 0.0 for k in KEYS}
    valid = 0
    for i in range(start, end):
        row = get_row(raw, i)
        if row['r_delta'] < min_delta:
            continue
        total = sum(row.values())
        if total <= 0: continue
        for k in KEYS:
            prop_sums[k] += min(row[k], CAP[k]) / total
        valid += 1
    if valid == 0:
        return {}, 0

    def pr(v, l1, l2):
        if v <= 0: return 0.0
        if v >= l2: return 1.0
        if v <= l1: return (v/l1)*0.5
        return (v-l1)/(l2-l1)*0.5 + 0.5

    PROP_R = dict(r_delta=(0.60,0.80),r_theta=(0.15,0.30),r_lalpha=(0.10,0.20),
                  r_halpha=(0.10,0.20),r_lbeta=(0.05,0.10),r_hbeta=(0.05,0.10),
                  r_lgamma=(0.03,0.06),r_hgamma=(0.03,0.06))
    result = {}
    for k in KEYS:
        avg_prop = prop_sums[k] / valid
        result[k] = round(pr(avg_prop, *PROP_R[k]) * 100)
    return result, valid

NAMES = dict(r_delta='delta',r_theta='theta',r_lalpha='low_alpha',r_halpha='high_alpha',
             r_lbeta='low_beta',r_hbeta='high_beta',r_lgamma='low_gamma',r_hgamma='high_gamma')

orig, v0 = calc_final(raw60, 30, 60, min_delta=0)
filt1, v1 = calc_final(raw60, 30, 60, min_delta=5000)
filt2, v2 = calc_final(raw60, 30, 60, min_delta=10000)

print(f'  {"頻段":<12}  {"原始(30秒)":>12}  {"過濾delta<5K({v1}秒)":>18}  {"過濾delta<10K({v2}秒)":>18}')
print(f'  {"":<12}  {"(未過濾)":>12}  {"有效秒={v1}":>18}  {"有效秒={v2}":>18}')
print('  ' + '-'*65)
for k in KEYS:
    n = NAMES[k]
    print(f'  {n:<12}  {orig.get(k,0):>12}  {filt1.get(k,0):>18}  {filt2.get(k,0):>18}')
