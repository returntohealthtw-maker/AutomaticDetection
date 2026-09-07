import sys, requests, urllib3
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=8)
token = r.json().get('token','')
h = {'Authorization': 'Bearer '+token}

# 1. Session #129 是什麼資料？
print("=== Session #129 基本資料 ===")
st = requests.get(BASE+'/eeg/sessions/129/stats', headers=h, verify=False, timeout=10).json()
print(f"  subject_name={st.get('subject_name')} report_type={st.get('report_type')}")
print(f"  total_captures={st.get('total_captures')}")
import datetime
ca = st.get('created_at', 0)
try: dt = datetime.datetime.fromtimestamp(int(ca)).strftime('%m/%d %H:%M')
except: dt = str(ca)
print(f"  created_at={dt}")

# 2. 查前幾筆 captures 的真實數值
print("\n=== 前5筆 captures ===")
cap_r = requests.get(BASE+'/sessions/129/captures?limit=5', headers=h, verify=False, timeout=10).json()
caps = cap_r if isinstance(cap_r, list) else cap_r.get('captures', cap_r.get('data', []))
for c in caps[:5]:
    print(f"  seq={c.get('seq_num')} delta={c.get('delta')} theta={c.get('theta')} la={c.get('low_alpha')} ha={c.get('high_alpha')}")

# 3. 計算實際的 theta 佔比（分析100的來源）
print("\n=== 計算 theta 佔比（看是否超過 level2=26%）===")
# 取全部 captures
cap_all = requests.get(BASE+'/sessions/129/captures?limit=200', headers=h, verify=False, timeout=15).json()
caps_all = cap_all if isinstance(cap_all, list) else cap_all.get('captures', cap_all.get('data', []))

# BrainDNA CAP 值
CAP = {'r_delta':98000,'r_theta':98000,'r_lalpha':50000,'r_halpha':50000,
       'r_lbeta':50000,'r_hbeta':50000,'r_lgamma':10000,'r_hgamma':5000}

theta_props = []
lalpha_props = []
for c in caps_all:
    d   = c.get('delta',0)
    th  = c.get('theta',0)
    la  = c.get('low_alpha',0)
    ha  = c.get('high_alpha',0)
    lb  = c.get('low_beta',0)
    hb  = c.get('high_beta',0)
    lg  = c.get('low_gamma',0)
    hg  = c.get('high_gamma',0)
    total = d + th + la + ha + lb + hb + lg + hg
    if total > 0:
        theta_props.append(th / total)
        lalpha_props.append(la / total)

if theta_props:
    avg_th = sum(theta_props)/len(theta_props)
    avg_la = sum(lalpha_props)/len(lalpha_props)
    max_th = max(theta_props)
    max_la = max(lalpha_props)
    print(f"  Theta 平均佔比: {avg_th*100:.1f}%  最大: {max_th*100:.1f}%  (level2=26%)")
    print(f"  Low α 平均佔比: {avg_la*100:.1f}%  最大: {max_la*100:.1f}%  (level2=8%)")
    print(f"  Theta {'⚠️ 超過 level2，得 100' if avg_th>0.26 else '✅ 正常，不應得100'}")
    print(f"  Low α {'⚠️ 超過 level2，得 100' if avg_la>0.08 else '✅ 正常，不應得100'}")

# 4. 最新的 sessions
print("\n=== 最近 sessions（是否有鄭靜怡重測的新資料）===")
sl = requests.get(BASE+'/eeg/sessions?limit=200', headers=h, verify=False, timeout=15)
all_s = sl.json().get('sessions', [])
print(f"  總筆數: {len(all_s)}")
for s in all_s[:8]:
    ca2 = s.get('created_at', 0)
    try: dt2 = datetime.datetime.fromtimestamp(int(ca2)).strftime('%m/%d %H:%M')
    except: dt2 = str(ca2)
    print(f"  #{s.get('session_id')} {(s.get('subject_name') or '?'):12s} {dt2} captures={s.get('total_captures','?')}")
