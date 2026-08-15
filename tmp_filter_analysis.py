"""分析不同過濾閾值對結果的影響"""
import sys, math, urllib3, requests, statistics
urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8')

BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=15)
token = r.json().get('token','')
hdrs = {'Authorization': f'Bearer {token}'}
raw60 = requests.get(f'{BASE}/api/admin/raw-export/60', headers=hdrs, verify=False, timeout=30).json().get('raw_arrays', {})

KEYS = ['r_delta','r_theta','r_lalpha','r_halpha','r_lbeta','r_hbeta','r_lgamma','r_hgamma']
CAP  = dict(r_delta=98000,r_theta=98000,r_lalpha=50000,r_halpha=50000,r_lbeta=50000,r_hbeta=50000,r_lgamma=10000,r_hgamma=10000)
PR   = dict(r_delta=(0.60,0.80),r_theta=(0.15,0.30),r_lalpha=(0.10,0.20),r_halpha=(0.10,0.20),
            r_lbeta=(0.05,0.10),r_hbeta=(0.05,0.10),r_lgamma=(0.03,0.06),r_hgamma=(0.03,0.06))

def pr(v, l1, l2):
    if v <= 0: return 0.0
    if v >= l2: return 1.0
    if v <= l1: return (v/l1)*0.5
    return (v-l1)/(l2-l1)*0.5 + 0.5

def calc(raw, start, end, min_delta=0):
    ps = {k:0.0 for k in KEYS}; valid=0
    filtered = []
    for i in range(start, end):
        row = {k: float((raw.get(k) or [0])[i] if i < len(raw.get(k) or []) else 0) for k in KEYS}
        tot = sum(row.values())
        if tot <= 0: continue
        if row['r_delta'] < min_delta:
            filtered.append(i); continue
        for k in KEYS: ps[k] += min(row[k], CAP[k]) / tot
        valid += 1
    if valid == 0: return None, []
    res = {k: round(pr(ps[k]/valid, *PR[k])*100) for k in KEYS}
    return res, filtered

# 找最佳視窗
def best_window(raw):
    n = len(raw.get('r_lalpha') or [])
    nw = math.ceil(n/30); best_idx=0; best_s=-1
    for wi in range(nw):
        s, e = wi*30, min((wi+1)*30, n)
        ps, vs = 0, 0
        for i in range(s, e):
            row = {k: float((raw.get(k) or [0])[i] if i<len(raw.get(k) or []) else 0) for k in KEYS}
            tot = sum(row.values())
            if tot<=0: continue
            ps += min(row['r_lgamma'],10000)/tot; vs+=1
        if vs>0:
            score = pr(ps/vs, 0.03, 0.06)
            if score > best_s: best_s=score; best_idx=wi
    return best_idx*30, min((best_idx+1)*30, n)

bw_s, bw_e = best_window(raw60)
print(f'最佳視窗: 秒 {bw_s}~{bw_e-1}')
print()

# 統計各 delta 範圍的秒數
deltas = [float((raw60.get('r_delta') or [0])[i] if i<len(raw60.get('r_delta') or []) else 0) for i in range(bw_s, bw_e)]
print('[delta值分佈統計]')
thresholds = [5000, 10000, 20000, 30000, 50000]
for t in thresholds:
    cnt = sum(1 for d in deltas if d < t)
    secs = [bw_s+i for i, d in enumerate(deltas) if d < t]
    print(f'  delta < {t:>6,}: {cnt:2d}/30秒  {secs}')

print()
print('[不同過濾閾值對結果的影響]')
NAMES = dict(r_delta='delta',r_theta='theta',r_lalpha='loA',r_halpha='hiA',
             r_lbeta='loB',r_hbeta='hiB',r_lgamma='loG',r_hgamma='hiG')
print(f'{"閾值":>10}  {"有效秒":>6}  delta  theta   loA   hiA   loB   hiB   loG   hiG')
print('-'*75)

for threshold in [0, 5000, 10000, 20000, 30000, 50000]:
    res, filtered = calc(raw60, bw_s, bw_e, threshold)
    valid = 30 - len(filtered)
    if res:
        vals = [res[k] for k in KEYS]
        print(f'{threshold:>10,}  {valid:>6}  {" ".join(f"{v:>5}" for v in vals)}')

print()
# 找出到底哪些秒數是高 gamma/beta 的元兇
print('[超過閾值的秒詳細]')
print(f'{"秒":>4}  {"delta":>10}  {"hbeta":>10}  {"lgamma":>10}  {"hb佔比%":>9}  {"lg佔比%":>9}  {"貢獻說明"}')
print('-'*75)
for i in range(bw_s, bw_e):
    row = {k: float((raw60.get(k) or [0])[i] if i<len(raw60.get(k) or []) else 0) for k in KEYS}
    tot = sum(row.values())
    if tot <= 0: continue
    hb_p = min(row['r_hbeta'],50000)/tot*100
    lg_p = min(row['r_lgamma'],10000)/tot*100
    if hb_p > 10 or lg_p > 6:
        contrib = []
        if hb_p > 10: contrib.append(f'hb={hb_p:.0f}%>10%')
        if lg_p > 6:  contrib.append(f'lg={lg_p:.0f}%>6%')
        print(f'{i:4d}  {row["r_delta"]:>10,.0f}  {row["r_hbeta"]:>10,.0f}  {row["r_lgamma"]:>10,.0f}  {hb_p:>9.1f}  {lg_p:>9.1f}  {", ".join(contrib)}')
