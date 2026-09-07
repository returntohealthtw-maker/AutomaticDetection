"""確認版本已部署，並用 retrigger 取得最新 qEEG 分數"""
import sys, requests, json, warnings
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
s = requests.Session()
s.verify = False
r = s.post(f'{BASE}/auth/login', json={'phone':'0900000000','password':'admin123'})
token = r.json().get('access_token','')
s.headers['Authorization'] = f'Bearer {token}'

# 1. 確認版本
rv = requests.get('https://backend-production-2da61.up.railway.app/api/v1/app/version', verify=False)
v = rv.json()
print(f"html_version: {v.get('html_version','?')}")
print(f"(期望: 2026.06.29.07)")
print()

# 2. retrigger session 88 + 89
for sid in [88, 89]:
    rr = s.get(f'https://backend-production-2da61.up.railway.app/debug/retrigger-qeeg/{sid}')
    if rr.status_code == 200:
        data = rr.json()
        q = data.get('qeeg_result', {})
        bf = q.get('band_features', {}).get('Fp1', {})
        sq = q.get('signal_quality', {})
        abls = q.get('ability_scores', {})
        print(f"=== Session {sid} ===")
        print(f"  訊號品質: {sq.get('quality_grade','?')} (可用: {sq.get('usable_epochs','?')}/{sq.get('total_epochs','?')})")
        print(f"  頻段 qEEG Z-score (0-100):")
        for band, info in sorted(bf.items()):
            if isinstance(info, dict):
                sc = round(info.get('score_0_100', 0), 1)
                z  = round(info.get('z_score', 0), 3)
                print(f"    {band:<14} z={z:+.3f}  score={sc}")
        print(f"  能力分數:")
        for k, v2 in sorted(abls.items()):
            print(f"    {k:<18} {round(v2,1)}")
        print()
    else:
        print(f"Session {sid}: retrigger failed {rr.status_code}")
