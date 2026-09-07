import sys, requests, json, warnings
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
s = requests.Session()
s.verify = False

r = s.get(f'{BASE}/app/version')
v = r.json()
print(f"版本: html_version={v.get('html_version')} (期望: 2026.06.29.06)")
assert v.get('html_version') == '2026.06.29.06', "版本未更新！"
print("✅ 版本確認")

r2 = s.post(f'{BASE}/auth/login', json={'phone':'0900000000','password':'admin123'})
token = r2.json().get('access_token','')
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

# 取 session 89 captures
r3 = s.get(f'{BASE}/sessions/89/captures', params={'limit': 200}, headers=headers)
caps = r3.json().get('captures', [])
raw_caps = [c for c in caps if c.get('delta',0) > 1000]
print(f"raw_caps: {len(raw_caps)}")

BANDS = ['delta','theta','low_alpha','high_alpha','low_beta','high_beta','low_gamma','high_gamma']
raw_arrays = {f'r_{b}': [c.get(b, 0) for c in raw_caps] for b in BANDS}

payload = {
    "subject_name":  "qEEG頻段測試",
    "subject_age":   35,
    "subject_gender": "F",
    "report_type":   "adult",
    "sample_count":  len(raw_caps),
    "attention_percentage": 50,
    "meditation_percentage": 50,
    "bands_avg": {"delta": 31, "theta": 53, "low_alpha": 26, "high_alpha": 31,
                  "low_beta": 60, "high_beta": 100, "low_gamma": 100, "high_gamma": 81},
    "raw_arrays": raw_arrays,
}
r4 = s.post(f'{BASE}/eeg/save-stats', json=payload, headers=headers)
print(f"\n/eeg/save-stats → {r4.status_code}")
d = r4.json()

print(f"session_id:        {d.get('session_id')}")
print(f"qeeg_signal_grade: {d.get('qeeg_signal_grade')}")
qb = d.get('qeeg_band_scores')
if qb:
    print("\n✅ qEEG 頻段分數（0-100）:")
    for band, score in sorted(qb.items()):
        bar = '█' * int(score // 5)
        print(f"  {band:<14} {score:>6.1f}  {bar}")
else:
    print(f"❌ qeeg_band_scores 不存在！d={json.dumps(d, ensure_ascii=False)[:300]}")
