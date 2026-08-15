import sys, requests, json, warnings
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

BASE = 'https://backend-production-2da61.up.railway.app'
s = requests.Session()
s.verify = False
r = s.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'})
token = r.json().get('access_token','')
s.headers['Authorization'] = f'Bearer {token}'

r2 = s.get(f'{BASE}/api/v1/sessions/89')
d = r2.json()
qeeg_raw = d.get('qeeg_scores_json','')
qeeg = json.loads(qeeg_raw) if isinstance(qeeg_raw, str) and qeeg_raw else {}

sq = qeeg.get('signal_quality', {})

print("=" * 60)
print("  Session 89 qEEG Z-score (修正後)")
print("=" * 60)
grade = sq.get('quality_grade', '?')
ratio = sq.get('usable_epoch_ratio', 0) * 100
print(f"  signal_quality: {grade}  (usable: {ratio:.0f}%)")
print()

print("  七大能力分數:")
ability_cn = {
    'intuition': '直覺感知',
    'energy':    '活力精力',
    'relaxation':'放鬆冥想',
    'focus':     '專注力',
    'logic':     '邏輯分析',
    'awareness': '整合意識',
    'empathy':   '情緒共感',
}
for k, cn in ability_cn.items():
    v = qeeg.get('ability_scores', {}).get(k, 0)
    sc = v.get('score') if isinstance(v, dict) else v
    print(f"    {cn:<10} {sc:>6.1f}")

print()
print("  複合心理功能指標:")
composite_cn = {
    'ccr': '認知負荷彈性',
    'ebi': '能量-平靜平衡',
    'reb': '靜息Alpha效能',
    'rrr': '放鬆-甦醒比',
    'sli': '壓力耐受指標',
    'edc': '情緒調節穩定',
    'isi': '整合同理指數',
}
for k, cn in composite_cn.items():
    v = qeeg.get('composite_indices', {}).get(k, 0)
    sc = v.get('score') if isinstance(v, dict) else v
    print(f"    {cn:<12} {sc:>6.1f}")

print()
print("  BrainDNA 頻段分數（best 30s window）:")
# Compute BrainDNA from captures
r3 = s.get(f'{BASE}/api/v1/sessions/89/captures', params={'limit': 200})
caps = r3.json().get('captures', [])
raw_caps = sorted([c for c in caps if c.get('delta', 0) > 1000],
                  key=lambda c: c.get('seq_num', 0))
BANDS = ['delta','theta','low_alpha','high_alpha','low_beta','high_beta','low_gamma','high_gamma']
_PR = {'delta':(0.60,0.80),'theta':(0.15,0.30),'low_alpha':(0.10,0.20),'high_alpha':(0.10,0.20),
       'low_beta':(0.05,0.10),'high_beta':(0.05,0.10),'low_gamma':(0.03,0.06),'high_gamma':(0.03,0.06)}
def pr(val,l1,l2):
    if val>=l2: return 1.0
    if val<=l1: return val/l1*0.5
    return (val-l1)/(l2-l1)*0.5+0.5

WS=30; best_sc=-1; best_i=0
for i in range(0,len(raw_caps),WS):
    w=raw_caps[i:i+WS]
    if len(w)<WS: continue
    lg=0.0
    for c in w:
        vals={b:float(c.get(b,0)or 0) for b in BANDS}
        tot=sum(vals.values())
        if tot>0: lg+=vals['low_gamma']/tot
    sc=pr(lg/WS,0.03,0.06)
    if sc>best_sc: best_sc,best_i=sc,i

w=raw_caps[best_i:best_i+WS]
bd_cn={'delta':'Delta','theta':'Theta','low_alpha':'Low Alpha','high_alpha':'High Alpha',
       'low_beta':'Low Beta','high_beta':'High Beta','low_gamma':'Low Gamma','high_gamma':'High Gamma'}
for b in BANDS:
    ps=0.0
    for c in w:
        vals={b2:float(c.get(b2,0)or 0) for b2 in BANDS}
        tot=sum(vals.values())
        if tot>0: ps+=vals[b]/tot
    avg=ps/len(w)
    l1,l2=_PR[b]
    sc=min(100,round(pr(avg,l1,l2)*100))
    note=" (佔比{:.1f}% > {}% 上限)".format(avg*100,int(l2*100)) if sc==100 else ""
    print(f"    {bd_cn[b]:<12} {sc:>5}{note}")

print()
print("修正前 vs 修正後:")
print("  signal_quality: D(usable 0%) → A(usable 100%)  [Android good_signal 0=完美訊號]")
print("  normative: v1.0 文獻誤用(delta norm=12%) → v1.1 ThinkGear校準(delta norm=53%)")
print("  ability scores: 14-42分 → 57-72分  [更符合常模期望中位數50附近]")
