"""Session #62：最佳30秒視窗 vs 全部180秒（兩者都套用 delta<30K 過濾）"""
import sys, math, urllib3, requests, statistics
urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8')

BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=15)
token = r.json().get('token','')
hdrs = {'Authorization': f'Bearer {token}'}

raw = requests.get(f'{BASE}/api/admin/raw-export/62', headers=hdrs, verify=False, timeout=30).json().get('raw_arrays', {})
n = len(raw.get('r_lalpha') or [])
print(f'Session #62  樣本數: {n} 秒')

KEYS = ['r_delta','r_theta','r_lalpha','r_halpha','r_lbeta','r_hbeta','r_lgamma','r_hgamma']
CAP  = dict(r_delta=98000,r_theta=98000,r_lalpha=50000,r_halpha=50000,r_lbeta=50000,r_hbeta=50000,r_lgamma=10000,r_hgamma=10000)
PR   = dict(r_delta=(0.60,0.80),r_theta=(0.15,0.30),r_lalpha=(0.10,0.20),r_halpha=(0.10,0.20),
            r_lbeta=(0.05,0.10),r_hbeta=(0.05,0.10),r_lgamma=(0.03,0.06),r_hgamma=(0.03,0.06))
MDQ  = 30_000  # MIN_DELTA_QUALITY

def pr(v, l1, l2):
    if v <= 0: return 0.0
    if v >= l2: return 1.0
    if v <= l1: return (v/l1)*0.5
    return (v-l1)/(l2-l1)*0.5 + 0.5

def get_row(i):
    return {k: float((raw.get(k) or [0])[i] if i < len(raw.get(k) or []) else 0) for k in KEYS}

def calc(start, end, apply_filter=True):
    ps = {k:0.0 for k in KEYS}; valid=0; filtered=0
    for i in range(start, end):
        row = get_row(i)
        tot = sum(row.values())
        if tot <= 0: continue
        if apply_filter and row['r_delta'] < MDQ:
            filtered += 1; continue
        for k in KEYS: ps[k] += min(row[k], CAP[k]) / tot
        valid += 1
    if valid == 0: return None, 0, 0
    res = {k: round(pr(ps[k]/valid, *PR[k])*100) for k in KEYS}
    return res, valid, filtered

# ── 找最佳視窗 ──────────────────────────────────────────────────────────────
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
print(f'最佳視窗: 第{best_idx}視窗（秒 {bw_s}~{bw_e-1}）\n')

# ── 計算三組結果 ────────────────────────────────────────────────────────────
res_30s, v30, f30 = calc(bw_s, bw_e, apply_filter=True)
res_all, vall, fall = calc(0, n, apply_filter=True)
res_all_nf, vall_nf, _ = calc(0, n, apply_filter=False)

NAMES = dict(r_delta='Delta 深度休息',r_theta='Theta 直覺能力',
             r_lalpha='Low α 內在安定',r_halpha='High α 氣血飽滿',
             r_lbeta='Low β 邏輯分析',r_hbeta='High β 高度專注',
             r_lgamma='Low γ 慈悲柔軟',r_hgamma='High γ 觀察環境')

# 差異分析
print(f'{"頻段":<18}  {"目前(30s)":>10}  {"全180s(過濾)":>14}  {"差異":>6}  {"全180s(不過濾)":>16}')
print('-'*72)
for k in KEYS:
    v1 = res_30s.get(k,0) if res_30s else 0
    v2 = res_all.get(k,0) if res_all else 0
    v3 = res_all_nf.get(k,0) if res_all_nf else 0
    diff = v2 - v1
    flag = ' ←' if abs(diff) >= 10 else ''
    print(f'{NAMES[k]:<18}  {v1:>10}  {v2:>14}  {diff:>+6}{flag}  {v3:>16}')

print()
# 過濾統計
delta_arr = [get_row(i)['r_delta'] for i in range(n)]
filtered_cnt = sum(1 for d in delta_arr if d < MDQ)
print(f'180秒中 delta<30K 的秒數: {filtered_cnt}/{n}  ({filtered_cnt/n*100:.1f}%)')
print(f'最佳30秒視窗過濾掉: {f30}/30 秒  有效計算: {v30} 秒')
print(f'全180秒過濾後有效: {vall}/{n} 秒')
print()
print(f'[後台目前顯示值（參考）]')
print('  delta=13  theta=32  high_alpha=10  low_alpha=15  high_beta=33  low_beta=18  high_gamma=20  low_gamma=26')
