"""
完整驗證 session #122/#123 在 Firebase 的儲存狀況：
1. eeg_features 筆數
2. 各欄位是否正確（raw bands、qeeg、braindna）
3. sessions collection 是否存在
"""
import sys, requests, urllib3, json, os
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()

BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False)
token = r.json().get('token') or r.json().get('access_token')
h = {'Authorization': 'Bearer '+token}

# 先取 session #122 和 #123 的 firebase_session_id
print("=== 取 Firebase session ID ===")
for sid in [122, 123]:
    sr = requests.get(BASE+f'/eeg/sessions/{sid}/stats', headers=h, verify=False)
    d = sr.json()
    fsid = d.get('firebase_session_id') or d.get('firebase_sync_ok')
    print(f"  session #{sid}: subject={d.get('subject_name')} firebase_session_id={fsid}")

# 改直接呼叫 Firebase REST API 驗證
FIREBASE_PROJECT = "gen-lang-client-0435688289"
FB_WEB_API_KEY = "AIzaSyBc-ZEcT8fvyn-dBZ0Bhm5IsakncVp1ngQ"
FB_EMAIL = "migration@returntohealthtw.com"
FB_PASS  = "MigrateEEG@2026"

print()
print("=== 登入 Firebase ===")
auth_r = requests.post(
    f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FB_WEB_API_KEY}",
    json={"email": FB_EMAIL, "password": FB_PASS, "returnSecureToken": True},
    timeout=15, verify=False
)
if auth_r.status_code != 200:
    print(f"  Firebase 登入失敗: {auth_r.text[:100]}")
    sys.exit(1)
fb_token = auth_r.json()['idToken']
print(f"  Firebase 登入成功")

FB_API = f"https://asia-east1-{FIREBASE_PROJECT}.cloudfunctions.net/api/api"
fb_h = {'Authorization': f'Bearer {fb_token}', 'Content-Type': 'application/json'}

# 查 firebase_session_id  d8fd7d9d-bbd0-4edf-bfb3-f76cec77b01c（session #122）
test_fb_sids = ["d8fd7d9d-bbd0-4edf-bfb3-f76cec77b01c"]

# 先拿 #123 的 firebase_session_id
sr123 = requests.get(BASE+'/eeg/sessions/123/stats', headers=h, verify=False).json()
fs123 = sr123.get('firebase_session_id')
if fs123:
    test_fb_sids.append(fs123)

print()
for fb_sid in test_fb_sids:
    print(f"=== 驗證 Firebase session_id={fb_sid} ===")
    
    # 1. 查 eeg_features 筆數
    feat_r = requests.get(
        FB_API + f"/eeg/features?session_id={fb_sid}&limit=5",
        headers=fb_h, timeout=15, verify=False
    )
    if feat_r.ok:
        feat_d = feat_r.json()
        count = feat_d.get('total') or len(feat_d.get('features', []))
        sample = feat_d.get('features', [{}])[0] if feat_d.get('features') else {}
        print(f"  eeg_features 總筆數: {count}")
        if sample:
            keys = list(sample.keys())
            print(f"  第一筆欄位: {keys[:10]}...")
            # 檢查關鍵欄位
            for k in ['delta', 'theta', 'low_alpha', 'high_alpha', 'good_signal', 'seq_num']:
                print(f"    {k}: {sample.get(k)}")
    else:
        print(f"  eeg_features 查詢失敗: {feat_r.status_code} {feat_r.text[:100]}")
    
    # 2. 查 sessions collection
    sess_r = requests.get(
        FB_API + f"/sessions/{fb_sid}",
        headers=fb_h, timeout=15, verify=False
    )
    if sess_r.ok:
        ss = sess_r.json()
        print(f"  session: subjectName={ss.get('subjectName')} braindna_stress={ss.get('braindna_stress')} qeeg={list((ss.get('qeeg_scores') or {}).keys())[:3] if ss.get('qeeg_scores') else 'none'}")
    else:
        print(f"  session 查詢: {sess_r.status_code} {sess_r.text[:100]}")

print()
print("=== 完成 ===")
