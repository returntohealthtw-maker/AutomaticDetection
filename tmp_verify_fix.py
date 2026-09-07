import sys, requests, urllib3
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=8)
token = r.json().get('token','')
h = {'Authorization': 'Bearer '+token}

# 1. 確認版本
ver = requests.get(BASE+'/app/version', verify=False, timeout=8).json()
print(f"版本：{ver.get('html_version')} (期望 2026.07.30.09)")

# 2. 確認 session #129 的 subject_name 已改
st = requests.get(BASE+'/eeg/sessions/129/stats', headers=h, verify=False, timeout=8).json()
print(f"\nSession #129 subject_name: {st.get('subject_name')}")
print(f"  (期望包含 '_test_' 或類似前綴)")

# 3. 從 all-subjects-overview 確認鄭靜怡的最新 session 已回到 #124
ao = requests.get(BASE+'/reports/all-subjects-overview', headers=h, verify=False, timeout=20).json()
zheng = [s for s in ao if '鄭靜怡' in (s.get('name','') or '')]
for z in zheng:
    print(f"\n鄭靜怡: latest_session={z.get('latest_session_id')} (期望 124)")
    bw = z.get('latest_brainwave', {})
    bands_7 = bw.get('bands_7', {})
    print(f"  bands_7 low_alpha={bands_7.get('alpha_low')} (期望非100)")
    print(f"  bands_7 theta={bands_7.get('theta')}")
    print(f"  _source={bw.get('_source','?')}")

# 4. 手動計算 session #124 的新 low_alpha 得分驗證
import sys
sys.path.insert(0, 'D:/Write program/AutomaticDetection/後端系統')
try:
    from app.services.braindna_algorithms import _PROP_RANGE, _proportion_range
    l1, l2 = _PROP_RANGE['r_lalpha']
    score = _proportion_range(0.082, l1, l2)
    print(f"\n本地計算驗證（低Alpha 8.2% → level2={l2*100:.0f}%）：得分 = {score*100:.0f}")
except Exception as e:
    print(f"本地驗證失敗：{e}")
