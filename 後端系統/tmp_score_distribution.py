"""查看所有 session 的 BrainDNA highBeta + lowGamma 分數分佈"""
import sys, requests, warnings, json, math
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
sess = requests.Session()
sess.verify = False
r = sess.post(f'{BASE}/auth/login', json={'phone':'0900000000','password':'admin123'})
sess.headers['Authorization'] = f'Bearer {r.json()["token"]}'

# 取所有 sessions
r2 = sess.get(f'{BASE}/eeg/sessions', params={'limit': 200})
sessions = r2.json().get('sessions', [])
print(f"共 {len(sessions)} 個 session")

CAP = {'delta':98000,'theta':98000,'low_alpha':50000,'high_alpha':50000,
       'low_beta':50000,'high_beta':50000,'low_gamma':10000,'high_gamma':10000}
PROP_RANGE_HB = (0.05, 0.10)
PROP_RANGE_LG = (0.03, 0.06)
BANDS_API = ['delta','theta','low_alpha','high_alpha','low_beta','high_beta','low_gamma','high_gamma']

def clamp(v, cap): return min(float(v or 0), float(cap))
def prop_range(val, l1, l2):
    if val <= 0: return 0.0
    if val >= l2: return 1.0
    if val <= l1: return (val/l1)*0.5
    return (val-l1)/(l2-l1)*0.5+0.5
def calc_score(prop, l1, l2): return round(prop_range(prop, l1, l2)*100)

results = []
for s in sessions:
    sid = s['session_id']
    r3 = sess.get(f'{BASE}/sessions/{sid}/captures', params={'limit': 200})
    raw_caps = [c for c in r3.json().get('captures', []) if (c.get('delta') or 0) > 1000]
    if len(raw_caps) < 30:
        continue

    # 建 30 秒視窗，找最佳
    windows = []
    tmp = []
    for c in raw_caps:
        row = {b: float(c.get(b) or 0) for b in BANDS_API}
        tmp.append(row)
        if len(tmp) >= 30:
            windows.append(tmp); tmp = []
    if tmp: windows.append(tmp)

    best_win = None
    best_lg_score = -1
    for w in windows:
        col_sums = [sum(r[b] for b in BANDS_API) for r in w]
        lg_capped = [clamp(r['low_gamma'], 10000) for r in w]
        props = [cv/cs for cv, cs in zip(lg_capped, col_sums) if cs > 0]
        prop_avg = sum(props)/len(props) if props else 0
        sc = prop_range(prop_avg, 0.03, 0.06)
        if sc > best_lg_score:
            best_lg_score = sc
            best_win = w

    if not best_win: continue
    col_sums = [sum(r[b] for b in BANDS_API) for r in best_win]

    def band_score(band, l1, l2):
        cap = CAP[band]
        cap_v = [clamp(r[band], cap) for r in best_win]
        props = [cv/cs for cv, cs in zip(cap_v, col_sums) if cs > 0]
        return round(prop_range(sum(props)/len(props) if props else 0, l1, l2)*100)

    hb = band_score('high_beta', 0.05, 0.10)
    lg = band_score('low_gamma', 0.03, 0.06)
    results.append({'sid': sid, 'name': s.get('subject_name','?'), 'hb': hb, 'lg': lg, 'n': len(raw_caps)})

print(f"\n{'sid':>4}  {'姓名':<12}  {'high_beta':>9}  {'low_gamma':>10}  {'筆數':>6}")
print("-"*55)
for r in sorted(results, key=lambda x: x['sid']):
    hb_flag = ' ⚠100' if r['hb'] == 100 else ''
    lg_flag = ' ⚠100' if r['lg'] == 100 else ''
    print(f"  {r['sid']:>3}  {r['name']:<12}  {r['hb']:>7}{hb_flag}  {r['lg']:>8}{lg_flag}  {r['n']:>6}")

hb_100 = sum(1 for r in results if r['hb'] == 100)
lg_100 = sum(1 for r in results if r['lg'] == 100)
hb_avg = sum(r['hb'] for r in results)/len(results) if results else 0
lg_avg = sum(r['lg'] for r in results)/len(results) if results else 0
print(f"\nhigh_beta: 平均={hb_avg:.0f}，達100的={hb_100}/{len(results)} ({100*hb_100/len(results):.0f}%)")
print(f"low_gamma: 平均={lg_avg:.0f}，達100的={lg_100}/{len(results)} ({100*lg_100/len(results):.0f}%)")
