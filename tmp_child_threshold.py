"""分析 Session #63 的實際比例，推導兒童適用閾值"""
import sys, math, urllib3, requests, statistics
urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8')

BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=15)
token = r.json().get('token','')
hdrs = {'Authorization': f'Bearer {token}'}

raw = requests.get(f'{BASE}/api/admin/raw-export/63', headers=hdrs, verify=False, timeout=30).json().get('raw_arrays', {})
n = len(raw.get('r_lalpha') or [])

KEYS = ['r_delta','r_theta','r_lalpha','r_halpha','r_lbeta','r_hbeta','r_lgamma','r_hgamma']
CAP  = dict(r_delta=98000,r_theta=98000,r_lalpha=50000,r_halpha=50000,r_lbeta=50000,r_hbeta=50000,r_lgamma=10000,r_hgamma=10000)
MDQ  = 30_000

NAMES = dict(r_delta='delta',r_theta='theta',r_lalpha='low_alpha',r_halpha='high_alpha',
             r_lbeta='low_beta',r_hbeta='high_beta',r_lgamma='low_gamma',r_hgamma='high_gamma')

def get_row(i):
    return {k: float((raw.get(k) or [0])[i] if i < len(raw.get(k) or []) else 0) for k in KEYS}

def pr(v, l1, l2):
    if v <= 0: return 0.0
    if v >= l2: return 1.0
    if v <= l1: return (v/l1)*0.5
    return (v-l1)/(l2-l1)*0.5 + 0.5

# 找最佳視窗
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

# 收集每秒比例（過濾低品質秒）
per_sec_props = {k: [] for k in KEYS}
for i in range(bw_s, bw_e):
    row = get_row(i)
    tot = sum(row.values())
    if tot <= 0: continue
    if row['r_delta'] < MDQ: continue
    for k in KEYS:
        per_sec_props[k].append(min(row[k], CAP[k]) / tot)

# 現有成人閾值
PR_ADULT = dict(r_delta=(0.60,0.80),r_theta=(0.15,0.30),r_lalpha=(0.10,0.20),r_halpha=(0.10,0.20),
                r_lbeta=(0.05,0.10),r_hbeta=(0.05,0.10),r_lgamma=(0.03,0.06),r_hgamma=(0.03,0.06))

# 建議兒童閾值（根據兒童腦波文獻與 Session #63 觀測值）
# 兒童特徵：theta 主導（非 delta），高頻 gamma 佔比更低
PR_CHILD = dict(
    r_delta=(0.10, 0.20),   # 成人: 60~80%  → 兒童: 10~20%（全頻段均高，delta cap 後佔比低）
    r_theta=(0.08, 0.16),   # 成人: 15~30%  → 兒童:  8~16%（theta雖高但分母也大）
    r_lalpha=(0.02, 0.05),  # 成人: 10~20%  → 兒童:  2~ 5%
    r_halpha=(0.02, 0.05),  # 成人: 10~20%  → 兒童:  2~ 5%
    r_lbeta=(0.01, 0.03),   # 成人:  5~10%  → 兒童:  1~ 3%
    r_hbeta=(0.03, 0.07),   # 成人:  5~10%  → 兒童:  3~ 7%（兒童 hbeta 絕對值高）
    r_lgamma=(0.01, 0.025), # 成人:  3~ 6%  → 兒童:  1~2.5%
    r_hgamma=(0.01, 0.02),  # 成人:  3~ 6%  → 兒童:  1~ 2%
)

print('[Session #63 兒童：成人閾值 vs 建議兒童閾值 對比]')
print(f'{"頻段":<12}  {"實際佔比%":>10}  {"成人閾值":>14}  {"成人最終值":>10}  {"兒童閾值":>14}  {"兒童最終值":>10}')
print('-'*80)

for k in KEYS:
    props = per_sec_props[k]
    avg_p = statistics.mean(props) if props else 0
    l1a, l2a = PR_ADULT[k]
    l1c, l2c = PR_CHILD[k]
    v_adult = round(pr(avg_p, l1a, l2a) * 100)
    v_child = round(pr(avg_p, l1c, l2c) * 100)
    th_a = f'{l1a*100:.0f}%~{l2a*100:.0f}%'
    th_c = f'{l1c*100:.0f}%~{l2c*100:.0f}%'
    print(f'{NAMES[k]:<12}  {avg_p*100:>10.3f}  {th_a:>14}  {v_adult:>10}  {th_c:>14}  {v_child:>10}')

print()
print('[CAP 問題分析]')
print('成人 CAP: delta=98K, theta=98K, lgamma=10K')
print('兒童均值: delta=826K, theta=167K → 兩個都遠超 CAP')
for k in KEYS:
    arr_all = [float((raw.get(k) or [0])[i]) for i in range(n) if i < len(raw.get(k) or [])]
    arr_pos = [v for v in arr_all if v > 0]
    pct_at_cap = sum(1 for v in arr_pos if v >= CAP[k]) / len(arr_pos) * 100 if arr_pos else 0
    flag = ' ← 長期超 CAP，cap 設計不適合兒童' if pct_at_cap > 50 else ''
    print(f'  {NAMES[k]:<12}: {pct_at_cap:.0f}% 的秒數超過 CAP {CAP[k]:,}{flag}')
