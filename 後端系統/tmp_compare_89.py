import sys, json, warnings, os
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')
sys.path.insert(0, 'D:/Write program/AutomaticDetection/後端系統')
os.chdir('D:/Write program/AutomaticDetection/後端系統')

import requests
BASE = 'https://backend-production-2da61.up.railway.app'
s = requests.Session()
s.verify = False
r = s.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'})
token = r.json().get('access_token', '')
s.headers['Authorization'] = f'Bearer {token}'

r2 = s.get(f'{BASE}/api/v1/sessions/89/captures')
caps = r2.json().get('captures', [])
caps_sorted = [c for c in caps if c['seq_num'] > 0]
print(f"楊女毓 Session 89 - 有效樣本數: {len(caps_sorted)}")

raw_arrays = {
    'r_delta':  [c['delta']      for c in caps_sorted],
    'r_theta':  [c['theta']      for c in caps_sorted],
    'r_lalpha': [c['low_alpha']  for c in caps_sorted],
    'r_halpha': [c['high_alpha'] for c in caps_sorted],
    'r_lbeta':  [c['low_beta']   for c in caps_sorted],
    'r_hbeta':  [c['high_beta']  for c in caps_sorted],
    'r_lgamma': [c['low_gamma']  for c in caps_sorted],
    'r_hgamma': [c['high_gamma'] for c in caps_sorted],
    'r_attn':   [c['attention']  for c in caps_sorted],
    'r_medi':   [c['meditation'] for c in caps_sorted],
}

# 顯示原始平均值
print("\n--- 原始頻段平均值（bandTo100，0-100）---")
for k in ['r_delta','r_theta','r_lalpha','r_halpha','r_lbeta','r_hbeta','r_lgamma','r_hgamma']:
    arr = raw_arrays[k]
    avg = sum(arr)/len(arr) if arr else 0
    print(f"  {k:10s}: {avg:.1f}")

# === BrainDNA ===
print("\n" + "="*55)
print("A. BrainDNA 佔比演算法（proportionRange 0-100）")
print("="*55)
from app.services.braindna_algorithms import compute_all as bdna_compute
bdna = bdna_compute(raw_arrays, is_child=False)
print(f"  valid        : {bdna.get('valid')}")
print(f"  input_scale  : {bdna.get('input_scale')}")
print(f"  overall_score: {bdna.get('overall_score')}")
print(f"  stress       : {bdna.get('stress')}")
print(f"  balance      : {bdna.get('balance')}")
print(f"  energy       : {bdna.get('energy')}")
print(f"  color        : {bdna.get('color')}")
print(f"  mbti         : {bdna.get('mbti')}")
b = bdna.get('bands', {})
if b:
    print("\n  頻段 proportionRange 分數（0-100）：")
    labels = {
        'delta':'Delta','theta':'Theta',
        'low_alpha':'Low Alpha','high_alpha':'High Alpha',
        'low_beta':'Low Beta','high_beta':'High Beta',
        'low_gamma':'Low Gamma','high_gamma':'High Gamma'
    }
    for k in ['delta','theta','low_alpha','high_alpha','low_beta','high_beta','low_gamma','high_gamma']:
        print(f"    {labels.get(k,k):12s}: {b.get(k, 'N/A')}")

# === qEEG Z-score ===
print("\n" + "="*55)
print("B. qEEG Z-score + sigmoid 演算法（0-100，50=常模平均）")
print("="*55)
from app.services.qeeg_pipeline import run_qeeg_pipeline
qeeg = run_qeeg_pipeline(
    raw_arrays=raw_arrays,
    captures=None,
    subject_info={'name':'楊女毓','age':None,'sex':'','test_condition':'eyes_closed'}
)
if qeeg:
    sq = qeeg.get('signal_quality', {})
    print(f"  訊號品質: {sq.get('quality_grade')}  (可用={sq.get('usable_epoch_ratio')})")
    bf = qeeg.get('band_features', {}).get('Fp1', {})
    print("\n  頻段 log Z-score 分數（0-100，50=常模平均）：")
    labels2 = {
        'delta':'Delta','theta':'Theta',
        'low_alpha':'Low Alpha','high_alpha':'High Alpha',
        'low_beta':'Low Beta','high_beta':'High Beta',
        'low_gamma':'Low Gamma','high_gamma':'High Gamma'
    }
    for k in ['delta','theta','low_alpha','high_alpha','low_beta','high_beta','low_gamma','high_gamma']:
        info = bf.get(k, {})
        print(f"    {labels2.get(k,k):12s}: {info.get('score_0_100','N/A'):5}  (z={info.get('z_score','?'):+.2f}, rel={info.get('relative_power',0):.3f})")

    print("\n  七大能力分數（0-100，50=常模平均）：")
    names = {'intuition':'直覺洞察','energy':'能量續航','relaxation':'內在安定',
             'focus':'高度專注','logic':'邏輯分析','awareness':'外界覺察','empathy':'共情柔軟'}
    for k,v in qeeg.get('ability_scores',{}).items():
        print(f"    {names.get(k,k):8s}: {v['score']:5.1f}  ({v['status']})")

    print("\n  複合心理功能指標（0-100）：")
    cnames = {'ccr':'認知控制','ebi':'能量平衡','reb':'理性情緒平衡',
              'rrr':'放鬆恢復','sli':'壓力負荷','edc':'情緒延遲','isi':'人際同步'}
    for k,v in qeeg.get('composite_indices',{}).items():
        print(f"    {cnames.get(k,k):8s}: {v['score']:5.1f}  ({v['status']})")

    flags = qeeg.get('report_flags', [])
    print(f"\n  Report Flags（{len(flags)} 個）：")
    for f in flags:
        print(f"    [{f['priority'].upper():6s}] {f['flag']}")
        print(f"           → {f['interpretation'][:70]}")
else:
    print("  qEEG 計算失敗")

print("\n" + "="*55)
print("對照說明：")
print("  BrainDNA: proportionRange → 0代表完全不存在，100代表最高活躍")
print("  qEEG:     Z-score sigmoid  → 50代表常模平均，>70高於常模，<30低於常模")
print("="*55)
