import sys, requests, urllib3
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=8)
token = r.json().get('token','')
h = {'Authorization': 'Bearer '+token}

# 確認版本
ver = requests.get(BASE+'/app/version', verify=False, timeout=8).json()
print(f"版本：{ver.get('html_version')}")

# Session #129 的 subject_name
st = requests.get(BASE+'/eeg/sessions/129/stats', headers=h, verify=False, timeout=8).json()
print(f"Session #129 subject_name: '{st.get('subject_name')}' (期望：_test_開頭)")

# 查詢鄭靜怡相關 sessions
sl = requests.get(BASE+'/eeg/sessions?limit=200', headers=h, verify=False, timeout=15).json()
all_s = sl.get('sessions', sl) if isinstance(sl, dict) else sl
zheng_sessions = [s for s in all_s if '靜怡' in str(s.get('subject_name',''))]
print(f"\n鄭靜怡相關 sessions ({len(zheng_sessions)} 筆)：")
for s in zheng_sessions:
    print(f"  #{s.get('session_id')} name={s.get('subject_name')} captures={s.get('total_captures','?')}")

# 本地閾值驗證
sys.path.insert(0, 'D:/Write program/AutomaticDetection/後端系統')
from app.services.braindna_algorithms import _PROP_RANGE, _proportion_range
l1, l2 = _PROP_RANGE['r_lalpha']
score = _proportion_range(0.082, l1, l2)
print(f"\n閾值驗證：low_alpha=8.2%, level1={l1*100:.1f}%, level2={l2*100:.1f}%")
print(f"  得分 = {score*100:.0f} (舊 level2=8% 時會得100，現在得 {score*100:.0f})")
print(f"  {'✅ 修正成功，不再得100' if score < 1.0 else '❌ 還是100'}")
