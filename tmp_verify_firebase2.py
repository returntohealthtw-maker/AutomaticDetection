"""
用正確的 Firebase API 端點和格式驗證 session #122/#123 的資料
"""
import sys, requests, urllib3, json
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()

FB_BASE = "https://asia-east1-gen-lang-client-0435688289.cloudfunctions.net/api/api"
FB_WEB_API_KEY = "AIzaSyBc-ZEcT8fvyn-dBZ0Bhm5IsakncVp1ngQ"
FB_EMAIL = "migration@returntohealthtw.com"
FB_PASS  = "MigrateEEG@2026"

# Firebase 登入
auth_r = requests.post(
    f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FB_WEB_API_KEY}",
    json={"email": FB_EMAIL, "password": FB_PASS, "returnSecureToken": True},
    verify=False, timeout=15
)
fb_token = auth_r.json()['idToken']
fh = {'Authorization': f'Bearer {fb_token}', 'Content-Type': 'application/json'}
print("Firebase 登入成功")

# 測試 session IDs
test_sessions = [
    ("d8fd7d9d-bbd0-4edf-bfb3-f76cec77b01c", "session #122 鄭靜怡_retest"),
    ("942cb4a8-411e-40ea-bb17-272f7abcd5d2", "session #123 鄭靜怡"),
]

for fb_sid, label in test_sessions:
    print(f"\n{'='*60}")
    print(f"=== {label} | Firebase sid={fb_sid[:16]}... ===")
    
    # 1. GET /eeg/{sessionId}?limit=200  (正確端點)
    eeg_r = requests.get(
        f"{FB_BASE}/eeg/{fb_sid}?limit=5",
        headers=fh, verify=False, timeout=15
    )
    if eeg_r.ok:
        data = eeg_r.json()
        features = data.get('features') or data.get('data') or []
        print(f"  1. GET /eeg/{{}}: status={eeg_r.status_code} count={len(features)}")
        if features:
            first = features[0]
            print(f"     欄位: {list(first.keys())[:12]}")
            for k in ['delta','theta','low_alpha','high_alpha','low_beta','high_beta','low_gamma','high_gamma','good_signal']:
                if k in first:
                    print(f"     {k}: {first[k]}")
    else:
        print(f"  1. GET /eeg/{{}}: {eeg_r.status_code} {eeg_r.text[:150]}")
    
    # 2. GET /sessions/{sessionId}
    sess_r = requests.get(
        f"{FB_BASE}/sessions/{fb_sid}",
        headers=fh, verify=False, timeout=15
    )
    if sess_r.ok:
        ss = sess_r.json()
        print(f"  2. session: subjectName={ss.get('subjectName')} samplingRate={ss.get('samplingRate')}")
        print(f"     status={ss.get('status')} braindna_stress={ss.get('braindna_stress')}")
        # 顯示所有頂層欄位
        print(f"     所有欄位: {list(ss.keys())[:15]}")
    else:
        print(f"  2. GET /sessions/{{}}: {sess_r.status_code} {sess_r.text[:150]}")
    
    # 3. 嘗試 Firestore REST API 直接查
    # sessions collection
    FS_BASE = f"https://firestore.googleapis.com/v1/projects/gen-lang-client-0435688289/databases/(default)/documents"
    fs_r = requests.get(
        f"{FS_BASE}/sessions/{fb_sid}",
        headers={'Authorization': f'Bearer {fb_token}'}, verify=False, timeout=15
    )
    if fs_r.ok:
        fsdata = fs_r.json()
        fields = fsdata.get('fields', {})
        print(f"  3. Firestore sessions/{fb_sid[:16]}... → 欄位數={len(fields)}")
        for k in list(fields.keys())[:5]:
            val_type = list(fields[k].keys())[0] if fields[k] else '?'
            val = list(fields[k].values())[0] if fields[k] else '?'
            print(f"     {k}: {str(val)[:40]}")
    else:
        print(f"  3. Firestore直查: {fs_r.status_code} {fs_r.text[:100]}")

print("\n=== 驗證完成 ===")
