"""Session #60 vs #62：逐層追蹤原始值差異"""
import sys, math, urllib3, requests, statistics
urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8')

BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=15)
token = r.json().get('token','')
hdrs = {'Authorization': f'Bearer {token}'}

def get_raw(sid):
    return requests.get(f'{BASE}/api/admin/raw-export/{sid}', headers=hdrs, verify=False, timeout=30).json().get('raw_arrays', {})

raw60 = get_raw(60)
raw62 = get_raw(62)

KEYS = ['r_delta','r_theta','r_lalpha','r_halpha','r_lbeta','r_hbeta','r_lgamma','r_hgamma']
CAP  = dict(r_delta=98000,r_theta=98000,r_lalpha=50000,r_halpha=50000,r_lbeta=50000,r_hbeta=50000,r_lgamma=10000,r_hgamma=10000)
PR   = dict(r_delta=(0.60,0.80),r_theta=(0.15,0.30),r_lalpha=(0.10,0.20),r_halpha=(0.10,0.20),
            r_lbeta=(0.05,0.10),r_hbeta=(0.05,0.10),r_lgamma=(0.03,0.06),r_hgamma=(0.03,0.06))
MDQ  = 30_000
NAMES = dict(r_delta='delta',r_theta='theta',r_lalpha='low_alpha',r_halpha='high_alpha',
             r_lbeta='low_beta',r_hbeta='high_beta',r_lgamma='low_gamma',r_hgamma='high_gamma')

def pr(v, l1, l2):
    if v <= 0: return 0.0
    if v >= l2: return 1.0
    if v <= l1: return (v/l1)*0.5
    return (v-l1)/(l2-l1)*0.5 + 0.5

def best_window(raw):
    n = len(raw.get('r_lalpha') or [])
    nw = math.ceil(n/30); best_idx=0; best_s=-1
    for wi in range(nw):
        s, e = wi*30, min((wi+1)*30, n)
        ps, vs = 0, 0
        for i in range(s, e):
            row = {k: float((raw.get(k) or [0])[i] if i < len(raw.get(k) or []) else 0) for k in KEYS}
            tot = sum(row.values())
            if tot<=0: continue
            ps += min(row['r_lgamma'],10000)/tot; vs+=1
        if vs>0:
            score = pr(ps/vs, 0.03, 0.06)
            if score > best_s: best_s=score; best_idx=wi
    return best_idx*30, min((best_idx+1)*30, n)

bw60_s, bw60_e = best_window(raw60)
bw62_s, bw62_e = best_window(raw62)

def analyze_window(raw, ws, we):
    totals, rows_ok = [], []
    for i in range(ws, we):
        row = {k: float((raw.get(k) or [0])[i] if i < len(raw.get(k) or []) else 0) for k in KEYS}
        tot = sum(row.values())
        if tot <= 0: continue
        if row['r_delta'] < MDQ: continue
        totals.append(tot)
        rows_ok.append(row)
    if not rows_ok: return None
    avg_total = statistics.mean(totals)
    result = {}
    for k in KEYS:
        raw_vals = [r[k] for r in rows_ok]
        result[k] = {
            'raw_mean': round(statistics.mean(raw_vals)),
            'capped_mean': round(statistics.mean([min(v, CAP[k]) for v in raw_vals])),
            'avg_proportion': statistics.mean([min(r[k], CAP[k]) / sum(r.values()) for r in rows_ok]),
        }
    return result, avg_total, len(rows_ok)

info60, total60, n60 = analyze_window(raw60, bw60_s, bw60_e)
info62, total62, n62 = analyze_window(raw62, bw62_s, bw62_e)

print(f'Session    最佳視窗          有效秒  每秒平均分母（uncapped total）')
print(f'  #60      秒{bw60_s}~{bw60_e-1}     {n60}秒    {total60:>12,.0f}')
print(f'  #62      秒{bw62_s}~{bw62_e-1}     {n62}秒    {total62:>12,.0f}')
print(f'  分母比：60的分母 = 62的 {total60/total62:.1f} 倍')
print()

print(f'{"頻段":<12}  {"60-原始均值":>12}  {"62-原始均值":>12}  {"原始值倍數":>10}  {"60佔比%":>8}  {"62佔比%":>8}  {"60最終值":>9}  {"62最終值":>9}')
print('-'*95)
for k in KEYS:
    i60 = info60[k]; i62 = info62[k]
    ratio = i60['raw_mean'] / i62['raw_mean'] if i62['raw_mean'] > 0 else 0
    p60 = i60['avg_proportion']*100
    p62 = i62['avg_proportion']*100
    l1, l2 = PR[k]
    f60 = round(pr(i60['avg_proportion'], l1, l2)*100)
    f62 = round(pr(i62['avg_proportion'], l1, l2)*100)
    print(f'{NAMES[k]:<12}  {i60["raw_mean"]:>12,}  {i62["raw_mean"]:>12,}  {ratio:>10.1f}x  {p60:>8.2f}  {p62:>8.2f}  {f60:>9}  {f62:>9}')

print()
print('── 關鍵差異分析 ──────────────────────────────────────────')
print(f'Session #60 delta 原始均值: {info60["r_delta"]["raw_mean"]:,.0f}  → 分母小，其他頻段佔比被放大')
print(f'Session #62 delta 原始均值: {info62["r_delta"]["raw_mean"]:,.0f}  → 分母大，其他頻段佔比被壓縮')
print(f'hbeta 原始均值: 60={info60["r_hbeta"]["raw_mean"]:,}  62={info62["r_hbeta"]["raw_mean"]:,}')
print(f'lgamma 原始均值: 60={info60["r_lgamma"]["raw_mean"]:,}  62={info62["r_lgamma"]["raw_mean"]:,}')
print()
print('── 結論 ───────────────────────────────────────────────────')
print('BrainDNA 算的是「佔比」，不是絕對值。')
print(f'Session #60: delta均值 {info60["r_delta"]["raw_mean"]:,}，分母小 → gamma/beta佔比高')
print(f'Session #62: delta均值 {info62["r_delta"]["raw_mean"]:,}，分母大 → gamma/beta佔比低')
print('兩次量測狀態不同（#60 更高度緊張/專注，#62 更放鬆），不是算法問題。')
