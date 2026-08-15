"""Session #63（小孩）深度 debug"""
import sys, math, urllib3, requests, statistics
urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8')

BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=15)
token = r.json().get('token','')
hdrs = {'Authorization': f'Bearer {token}'}

raw = requests.get(f'{BASE}/api/admin/raw-export/63', headers=hdrs, verify=False, timeout=30).json().get('raw_arrays', {})
n = len(raw.get('r_lalpha') or [])
print(f'Session #63  樣本數: {n} 秒')

KEYS = ['r_delta','r_theta','r_lalpha','r_halpha','r_lbeta','r_hbeta','r_lgamma','r_hgamma']
CAP  = dict(r_delta=98000,r_theta=98000,r_lalpha=50000,r_halpha=50000,r_lbeta=50000,r_hbeta=50000,r_lgamma=10000,r_hgamma=10000)
PR   = dict(r_delta=(0.60,0.80),r_theta=(0.15,0.30),r_lalpha=(0.10,0.20),r_halpha=(0.10,0.20),
            r_lbeta=(0.05,0.10),r_hbeta=(0.05,0.10),r_lgamma=(0.03,0.06),r_hgamma=(0.03,0.06))
MDQ  = 30_000
# BrainDNA 族群統計（log10 空間）
POP = dict(r_delta=(5.298,0.542),r_theta=(4.725,0.441),r_lalpha=(4.073,0.424),
           r_halpha=(4.090,0.377),r_lbeta=(4.026,0.404),r_hbeta=(4.089,0.393),
           r_lgamma=(3.757,0.426),r_hgamma=(3.753,0.629))
NAMES = dict(r_delta='delta',r_theta='theta',r_lalpha='low_alpha',r_halpha='high_alpha',
             r_lbeta='low_beta',r_hbeta='high_beta',r_lgamma='low_gamma',r_hgamma='high_gamma')

def pr(v, l1, l2):
    if v <= 0: return 0.0
    if v >= l2: return 1.0
    if v <= l1: return (v/l1)*0.5
    return (v-l1)/(l2-l1)*0.5 + 0.5

def get_row(i):
    return {k: float((raw.get(k) or [0])[i] if i < len(raw.get(k) or []) else 0) for k in KEYS}

# ── 1. 全段原始值統計（對比族群均值）─────────────────────────────────────────
print()
print('[1] 全段原始值 vs BrainDNA 族群均值（成人）')
print(f'{"頻段":<12}  {"族群均值":>10}  {"本次均值":>10}  {"z分數":>8}  {"品質過濾後均值":>14}  CAP')
print('-'*68)
for k in KEYS:
    arr_all = [float(v) for v in (raw.get(k) or []) if v and float(v) > 0]
    # 過濾低品質秒的均值
    delta_arr = [float(v) for v in (raw.get('r_delta') or [])]
    arr_filt = [float((raw.get(k) or [])[i]) for i in range(n)
                if i < len(raw.get(k) or []) and i < len(delta_arr)
                and delta_arr[i] >= MDQ and (raw.get(k) or [])[i] > 0]
    m_pop = 10**POP[k][0]
    m_all = statistics.mean(arr_all) if arr_all else 0
    m_f = statistics.mean(arr_filt) if arr_filt else 0
    z = (math.log10(m_all)-POP[k][0])/POP[k][1] if m_all > 0 else 0
    flag = ' ⚠ 低' if z < -1.5 else (' ⚠ 高' if z > 1.5 else '')
    print(f'{NAMES[k]:<12}  {m_pop:>10,.0f}  {m_all:>10,.0f}  {z:>+8.2f}{flag}  {m_f:>14,.0f}  {CAP[k]:,}')

# ── 2. 訊號品質：delta 分佈 ──────────────────────────────────────────────────
print()
delta_arr = [float((raw.get('r_delta') or [0])[i]) for i in range(n)]
low_quality = sum(1 for d in delta_arr if d < MDQ)
print(f'[2] 訊號品質')
print(f'  delta 全段：最小={min(delta_arr):,.0f}  最大={max(delta_arr):,.0f}  均值={statistics.mean(delta_arr):,.0f}')
print(f'  delta < 30K 的秒數：{low_quality}/{n}  ({low_quality/n*100:.1f}%)')

# ── 3. 找最佳視窗 ────────────────────────────────────────────────────────────
nw = math.ceil(n/30); best_idx=0; best_s=-1
for wi in range(nw):
    s, e = wi*30, min((wi+1)*30, n)
    ps, vs = 0, 0
    for i in range(s, e):
        row = get_row(i)
        tot = sum(row.values())
        if tot<=0: continue
        ps += min(row['r_lgamma'],10000)/tot; vs+=1
    if vs>0:
        score = pr(ps/vs, 0.03, 0.06)
        if score > best_s: best_s=score; best_idx=wi
bw_s = best_idx*30; bw_e = min((best_idx+1)*30, n)

print()
print(f'[3] 最佳視窗：第{best_idx}視窗（秒 {bw_s}~{bw_e-1}）')
ps_sum = {k:0.0 for k in KEYS}; valid=0; filt=0; totals=[]
for i in range(bw_s, bw_e):
    row = get_row(i)
    tot = sum(row.values())
    if tot<=0: continue
    if row['r_delta'] < MDQ: filt+=1; continue
    for k in KEYS: ps_sum[k] += min(row[k], CAP[k]) / tot
    totals.append(tot); valid+=1

avg_total = statistics.mean(totals) if totals else 0
print(f'  過濾 delta<30K：{filt}秒  有效秒：{valid}秒  每秒平均分母：{avg_total:,.0f}')
print()

# 對比各成人 session 的分母
print(f'[4] 分母大小對比（同為最佳視窗有效秒均值）')
for ref_sid, label in [(57,'成人#57 正常'),(60,'成人#60 偏低'),(62,'成人#62 放鬆')]:
    raw_r = requests.get(f'{BASE}/api/admin/raw-export/{ref_sid}', headers=hdrs, verify=False, timeout=30).json().get('raw_arrays', {})
    nr = len(raw_r.get('r_lalpha') or [])
    nw_r = math.ceil(nr/30); bi=0; bs=-1
    for wi in range(nw_r):
        s,e = wi*30,min((wi+1)*30,nr)
        _ps,_vs=0,0
        for ii in range(s,e):
            _r={k:float((raw_r.get(k) or [0])[ii] if ii<len(raw_r.get(k) or []) else 0) for k in KEYS}
            _t=sum(_r.values())
            if _t<=0: continue
            _ps+=min(_r['r_lgamma'],10000)/_t; _vs+=1
        if _vs>0:
            _sc=pr(_ps/_vs,0.03,0.06)
            if _sc>bs: bs=_sc; bi=wi
    _s,_e=bi*30,min((bi+1)*30,nr)
    _tots=[]
    for ii in range(_s,_e):
        _r={k:float((raw_r.get(k) or [0])[ii] if ii<len(raw_r.get(k) or []) else 0) for k in KEYS}
        _t=sum(_r.values())
        if _t<=0: continue
        if _r['r_delta']<MDQ: continue
        _tots.append(_t)
    _avg=statistics.mean(_tots) if _tots else 0
    print(f'  {label}：{_avg:>12,.0f}')
print(f'  小孩 #63  ：{avg_total:>12,.0f}')

print()
print('[5] 最終計算結果')
print(f'{"頻段":<12}  {"原始佔比%":>10}  {"最終值":>8}  {"後台顯示"}')
DISPLAY = dict(r_delta=19,r_theta=34,r_lalpha=12,r_halpha=11,r_lbeta=17,r_hbeta=53,r_lgamma=35,r_hgamma=23)
for k in KEYS:
    pp = ps_sum[k]/valid*100 if valid else 0
    l1,l2 = PR[k]
    fv = round(pr(ps_sum[k]/valid if valid else 0, l1, l2)*100)
    match = '✓' if fv == DISPLAY.get(k,0) else f'← 後台={DISPLAY.get(k,0)}'
    print(f'{NAMES[k]:<12}  {pp:>10.3f}  {fv:>8}  {match}')
