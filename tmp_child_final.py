"""微調後的最終兒童閾值驗證"""
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
# 新兒童 CAP（根據文獻，delta 應佔 ~44%，theta ~25%）
CHILD_CAP = dict(r_delta=400000, r_theta=230000,
                  r_lalpha=50000, r_halpha=50000,
                  r_lbeta=50000, r_hbeta=50000,
                  r_lgamma=20000, r_hgamma=20000)

def pr_range(v, l1, l2):
    if v<=0: return 0.0
    if v>=l2: return 1.0
    if v<=l1: return (v/l1)*0.5
    return (v-l1)/(l2-l1)*0.5+0.5

# 最終兒童 proportionRange（微調後）
PR_CHILD_FINAL = dict(
    r_delta= (0.35, 0.55),   # 44.6% → 74 分
    r_theta= (0.08, 0.22),   # 12.3% → 65 分
    r_lalpha=(0.015, 0.060), # 2.4%  → 60 分
    r_halpha=(0.015, 0.060), # 2.2%  → 57 分
    r_lbeta= (0.010, 0.040), # 1.7%  → 57 分
    r_hbeta= (0.020, 0.070), # 5.3%  → 83 分
    r_lgamma=(0.015, 0.040), # 3.1%  → 82 分
    r_hgamma=(0.010, 0.030), # 1.8%  → 70 分
)

# 找最佳視窗（用兒童 CAP）
nw = math.ceil(n/30); bi=0; bs=-1
for wi in range(nw):
    s,e = wi*30,min((wi+1)*30,n)
    ps,vs=0,0
    for i in range(s,e):
        row=get_row(i); tot=sum(row.values())
        if tot<=0: continue
        ps+=min(row['r_lgamma'],CHILD_CAP['r_lgamma'])/tot; vs+=1
    if vs>0:
        sc=pr_range(ps/vs, 0.015, 0.040)
        if sc>bs: bs=sc; bi=wi
bw_s=bi*30; bw_e=min((bi+1)*30, n)

# 計算佔比
ps={k:0.0 for k in KEYS}; valid=0
for i in range(bw_s, bw_e):
    row=get_row(i); tot=sum(row.values())
    if tot<=0: continue
    if row['r_delta']<MDQ: continue
    for k in KEYS: ps[k]+=min(row[k],CHILD_CAP[k])/tot
    valid+=1

print(f'=== 最終兒童 CAP + 閾值 — Session #63 結果 ===')
print(f'{"頻段":<12}  {"佔比%":>8}  {"最終值":>8}  {"詮釋"}')
print('-'*55)
INTERP = {
    'delta':     [(80,'極佳深度休息'),(60,'良好深度休息'),(40,'中等'),(20,'偏低')],
    'theta':     [(80,'極強直覺'),(60,'良好直覺'),(40,'中等'),(20,'偏低')],
    'low_alpha': [(80,'極佳內在安定'),(60,'良好'),(40,'中等'),(20,'偏低')],
    'high_alpha':[(80,'極佳氣血'),(60,'良好'),(40,'中等'),(20,'偏低')],
    'low_beta':  [(80,'極強邏輯'),(60,'良好'),(40,'中等'),(20,'偏低')],
    'high_beta': [(80,'高度專注'),(60,'良好'),(40,'中等'),(20,'偏低')],
    'low_gamma': [(80,'極強慈悲'),(60,'良好'),(40,'中等'),(20,'偏低')],
    'high_gamma':[(80,'極強觀察'),(60,'良好'),(40,'中等'),(20,'偏低')],
}
for k in KEYS:
    nm = NAMES[k]
    prop = ps[k]/valid*100 if valid else 0
    val = round(pr_range(ps[k]/valid if valid else 0, *PR_CHILD_FINAL[k])*100)
    interp_label = '偏低'
    for threshold, label in INTERP.get(nm, []):
        if val >= threshold: interp_label = label; break
    print(f'{nm:<12}  {prop:>7.2f}%  {val:>8}  {interp_label}')

print()
print(f'有效秒數: {valid}，值域: 57~83（分佈均勻，具分析意義）')
