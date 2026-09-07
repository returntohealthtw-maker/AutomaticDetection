"""
根據學術文獻設計兒童專用 CAP 值，並驗證 Session #63 的結果

學術文獻基準（2025 Springer, 3歲清醒兒童）：
  delta:  39~49% 相對功率
  theta:  ~25%
  alpha:  ~15%（low+high 各一半）
  beta:   ~8%（low+high 各一半）
  gamma:  ~2~4%
"""
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
NAMES = dict(r_delta='delta',r_theta='theta',r_lalpha='low_alpha',r_halpha='high_alpha',
             r_lbeta='low_beta',r_hbeta='high_beta',r_lgamma='low_gamma',r_hgamma='high_gamma')

def get_row(i):
    return {k: float((raw.get(k) or [0])[i] if i < len(raw.get(k) or []) else 0) for k in KEYS}

MDQ = 30_000
CAP_ADULT  = dict(r_delta=98000,r_theta=98000,r_lalpha=50000,r_halpha=50000,
                   r_lbeta=50000,r_hbeta=50000,r_lgamma=10000,r_hgamma=10000)

# ────────────────────────────────────────────────────────
# 兒童 CAP：根據文獻「應佔比 × 平均未截斷總和」反推
#   avg_uncapped_total（Session #63 最佳視窗）≈ 929K
#   delta 應佔 44% → cap = 0.44 × 929K = 409K → 取 400K
#   theta 應佔 25% → cap = 0.25 × 929K = 232K → 取 230K
#   alpha 各 7.5% → cap = 0.075 × 929K = 70K → 維持 50K（略保守）
#   beta  各  4%  → cap = 0.04 × 929K = 37K → 維持 50K
#   gamma 各  2%  → cap = 0.02 × 929K = 19K → 取 20K（原 10K）
# ────────────────────────────────────────────────────────
CAP_CHILD  = dict(r_delta=400000, r_theta=230000,
                   r_lalpha=50000,  r_halpha=50000,
                   r_lbeta=50000,   r_hbeta=50000,
                   r_lgamma=20000,  r_hgamma=20000)

def pr_range(v, l1, l2):
    if v<=0: return 0.0
    if v>=l2: return 1.0
    if v<=l1: return (v/l1)*0.5
    return (v-l1)/(l2-l1)*0.5+0.5

# BrainDNA 成人閾值（原始）
PR_ADULT = dict(r_delta=(0.60,0.80),r_theta=(0.15,0.30),r_lalpha=(0.10,0.20),r_halpha=(0.10,0.20),
                r_lbeta=(0.05,0.10),r_hbeta=(0.05,0.10),r_lgamma=(0.03,0.06),r_hgamma=(0.03,0.06))

# 兒童閾值（根據文獻目標佔比設計）
# level1 ≈ 文獻 25th 百分位，level2 ≈ 文獻 75th 百分位
PR_CHILD_NEW = dict(
    r_delta=(0.35, 0.55),   # 文獻: 39~49% → 正常區間設在 35~55%
    r_theta=(0.18, 0.32),   # 文獻: ~25%  → 正常區間 18~32%
    r_lalpha=(0.04, 0.09),  # 文獻: ~7.5% → 正常區間 4~9%
    r_halpha=(0.04, 0.09),
    r_lbeta=(0.02, 0.05),   # 文獻: ~4%  → 正常區間 2~5%
    r_hbeta=(0.02, 0.05),
    r_lgamma=(0.01, 0.025), # 文獻: ~2%  → 正常區間 1~2.5%
    r_hgamma=(0.01, 0.020),
)

# 找最佳視窗（用新 CAP）
def find_best_window(cap):
    nw = math.ceil(n/30); bi=0; bs=-1
    for wi in range(nw):
        s,e = wi*30,min((wi+1)*30,n)
        ps,vs=0,0
        for i in range(s,e):
            row=get_row(i); tot=sum(row.values())
            if tot<=0: continue
            ps+=min(row['r_lgamma'],cap['r_lgamma'])/tot; vs+=1
        if vs>0:
            sc=pr_range(ps/vs, 0.01, 0.025)
            if sc>bs: bs=sc; bi=wi
    return bi*30, min((bi+1)*30, n)

def calc_props(bw_s, bw_e, cap):
    ps={k:0.0 for k in KEYS}; valid=0
    for i in range(bw_s, bw_e):
        row=get_row(i); tot=sum(row.values())
        if tot<=0: continue
        if row['r_delta']<MDQ: continue
        for k in KEYS: ps[k]+=min(row[k],cap[k])/tot
        valid+=1
    return ps, valid

bw_s_a, bw_e_a = find_best_window(CAP_ADULT)
bw_s_c, bw_e_c = find_best_window(CAP_CHILD)

ps_a, va = calc_props(bw_s_a, bw_e_a, CAP_ADULT)
ps_c, vc = calc_props(bw_s_c, bw_e_c, CAP_CHILD)

print('Session #63（3歲兒童）— 三種方案對比')
print(f'{"頻段":<12}  {"文獻目標%":>10}  {"現行值(舊CAP+兒閾)":>18}  {"新方案(新CAP+兒閾)":>18}')
print('-'*65)
LIT_TARGET = dict(r_delta='39~49%',r_theta='~25%',r_lalpha='~7.5%',r_halpha='~7.5%',
                  r_lbeta='~4%',r_hbeta='~4%',r_lgamma='~2%',r_hgamma='~2%')

PR_CHILD_OLD = dict(r_delta=(0.10,0.30),r_theta=(0.06,0.15),r_lalpha=(0.01,0.04),r_halpha=(0.01,0.04),
                    r_lbeta=(0.010,0.025),r_hbeta=(0.025,0.070),r_lgamma=(0.010,0.030),r_hgamma=(0.005,0.018))

for k in KEYS:
    p_a = ps_a[k]/va*100 if va else 0
    p_c = ps_c[k]/vc*100 if vc else 0
    v_old = round(pr_range(ps_a[k]/va if va else 0, *PR_CHILD_OLD[k])*100)
    v_new = round(pr_range(ps_c[k]/vc if vc else 0, *PR_CHILD_NEW[k])*100)
    print(f'{NAMES[k]:<12}  {LIT_TARGET[k]:>10}  {p_a:>6.1f}% → {v_old:>3}分   {p_c:>6.1f}% → {v_new:>3}分')

print()
print('成人 Session #62（放鬆成人）— 確認成人值不受影響')
raw62 = requests.get(f'{BASE}/api/admin/raw-export/62', headers=hdrs, verify=False, timeout=30).json().get('raw_arrays', {})
n62 = len(raw62.get('r_lalpha') or [])
def get_row62(i): return {k: float((raw62.get(k) or [0])[i] if i < len(raw62.get(k) or []) else 0) for k in KEYS}
nw62=math.ceil(n62/30); bi62=0; bs62=-1
for wi in range(nw62):
    s,e=wi*30,min((wi+1)*30,n62)
    ps62,vs62=0,0
    for i in range(s,e):
        row=get_row62(i); tot=sum(row.values())
        if tot<=0: continue
        ps62+=min(row['r_lgamma'],CAP_ADULT['r_lgamma'])/tot; vs62+=1
    if vs62>0:
        sc62=pr_range(ps62/vs62,0.03,0.06)
        if sc62>bs62: bs62=sc62; bi62=wi
bw62s,bw62e=bi62*30,min((bi62+1)*30,n62)
ps62f={k:0.0 for k in KEYS}; v62=0
for i in range(bw62s,bw62e):
    row=get_row62(i); tot=sum(row.values())
    if tot<=0: continue
    if row['r_delta']<MDQ: continue
    for k in KEYS: ps62f[k]+=min(row[k],CAP_ADULT[k])/tot
    v62+=1
for k in KEYS:
    v62val = round(pr_range(ps62f[k]/v62 if v62 else 0, *PR_ADULT[k])*100)
    print(f'  {NAMES[k]}: {v62val}', end='  ')
print()
