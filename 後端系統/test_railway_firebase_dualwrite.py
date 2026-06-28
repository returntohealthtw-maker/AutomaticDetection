#!/usr/bin/env python3
"""
測試 Railway 後端雙寫功能：PostgreSQL + Firebase
執行: python test_railway_firebase_dualwrite.py
"""
import sys, urllib3, requests, json, time
urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8')

RAILWAY_BASE     = 'https://backend-production-2da61.up.railway.app'
FIREBASE_API_BASE= 'https://asia-east1-gen-lang-client-0435688289.cloudfunctions.net/api/api'
FIREBASE_API_KEY = 'AIzaSyBc-ZEcT8fvyn-dBZ0Bhm5IsakncVp1ngQ'
RAILWAY_PHONE    = '0900000000'
RAILWAY_PASSWORD = 'admin123'
FIREBASE_EMAIL   = 'migration@returntohealthtw.com'
FIREBASE_PASSWORD= 'MigrateEEG@2026'

print("=" * 80)
print("Railway → Firebase 雙寫測試")
print("=" * 80)

# Step 1: Login to Railway
print("\n【步驟 1】登入 Railway 後端...")
try:
    r = requests.post(
        f'{RAILWAY_BASE}/api/v1/auth/login',
        json={'phone': RAILWAY_PHONE, 'password': RAILWAY_PASSWORD},
        verify=False, timeout=15
    )
    if r.status_code == 200:
        railway_token = r.json().get('token', '')
        print(f"✅ 登入成功，取得 token: {railway_token[:20]}...")
    else:
        print(f"❌ 登入失敗: {r.status_code} {r.text}")
        sys.exit(1)
except Exception as e:
    print(f"❌ 登入例外: {e}")
    sys.exit(1)

railway_headers = {'Authorization': f'Bearer {railway_token}'}

# Step 2: Upload test EEG session
print("\n【步驟 2】上傳測試 EEG session...")
now_ms = int(time.time() * 1000)
test_session_payload = {
    "consultant_name": "系統管理員",
    "subject_name":    "Firebase雙寫測試",
    "subject_birthday":"1990-01-01",
    "subject_gender":  "M",
    "subject_age":     35,
    "report_type":     "adult",
    "start_time":      now_ms - 180_000,
    "end_time":        now_ms,
    "is_success":      True,
    "captures": [
        {"seq_num": i, "is_baseline": 0,
         "captured_at": now_ms // 1000 - 180 + i,
         "good_signal": 0,
         "attention": 68 + i, "meditation": 55 + i,
         "delta": 35, "theta": 62,
         "low_alpha": 45, "high_alpha": 38,
         "low_beta": 52, "high_beta": 48,
         "low_gamma": 25, "high_gamma": 20, "feedback": 0}
        for i in range(3)
    ]
}

try:
    r = requests.post(
        f'{RAILWAY_BASE}/api/v1/sessions/upload',
        headers=railway_headers,
        json=test_session_payload,
        verify=False, timeout=30
    )
    if r.status_code in (200, 201):
        upload_result = r.json()
        railway_session_id = upload_result.get('session_id')
        print(f"✅ 上傳成功！Railway session_id: {railway_session_id}")
        print(f"   回傳: {json.dumps(upload_result, ensure_ascii=False)[:200]}")
    else:
        print(f"❌ 上傳失敗: {r.status_code} {r.text[:500]}")
        sys.exit(1)
except Exception as e:
    print(f"❌ 上傳例外: {e}")
    sys.exit(1)

# Step 3: Wait for Firebase sync
print("\n【步驟 3】等待 10 秒讓 Firebase 背景同步...")
time.sleep(10)
print("✅ 等待完成")

# Step 4: Verify PostgreSQL
print("\n【步驟 4】驗證 PostgreSQL 儲存...")
total_captures = 0
try:
    r = requests.get(
        f'{RAILWAY_BASE}/api/v1/sessions/{railway_session_id}/captures',
        headers=railway_headers, verify=False, timeout=15
    )
    if r.status_code == 200:
        data = r.json()
        captures_list = data.get('captures', data) if isinstance(data, dict) else data
        total_captures = data.get('total', len(captures_list)) if isinstance(data, dict) else len(data)
        print(f"✅ PostgreSQL 儲存成功！共 {total_captures} 筆 captures")
        if captures_list:
            c = captures_list[0]
            print(f"   第一筆: seq_num={c.get('seq_num')}, attention={c.get('attention')}")
    else:
        print(f"❌ 查詢失敗: {r.status_code} {r.text[:300]}")
except Exception as e:
    print(f"❌ 查詢例外: {e}")

# Step 5: Login to Firebase and verify
print("\n【步驟 5】登入 Firebase 並驗證同步...")
firebase_token = None
found = False
try:
    r = requests.post(
        f'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}',
        json={'email': FIREBASE_EMAIL, 'password': FIREBASE_PASSWORD, 'returnSecureToken': True},
        timeout=15
    )
    if r.status_code == 200:
        firebase_token = r.json().get('idToken', '')
        print(f"✅ Firebase 登入成功，token: {firebase_token[:20]}...")
    else:
        print(f"❌ Firebase 登入失敗: {r.status_code} {r.text}")
except Exception as e:
    print(f"❌ Firebase 登入例外: {e}")

if firebase_token:
    try:
        r = requests.get(
            f'{FIREBASE_API_BASE}/sessions?limit=10',
            headers={'Authorization': f'Bearer {firebase_token}'}, timeout=15
        )
        if r.status_code == 200:
            sessions = r.json()
            print(f"✅ 查詢到 {len(sessions)} 個 Firebase sessions")
            for sess in sessions:
                meta = sess.get('metadata', {})
                if str(meta.get('railway_session_id')) == str(railway_session_id):
                    found = True
                    print(f"\n🎯 找到對應的 Firebase session！")
                    print(f"   Firebase session_id: {sess.get('id')}")
                    print(f"   status:              {sess.get('status')}")
                    print(f"   durationSec:         {sess.get('durationSec')}")
                    print(f"   railway_session_id:  {meta.get('railway_session_id')}")
                    print(f"   subject_name:        {meta.get('subject_name')}")
                    break
            if not found:
                print(f"\n⚠️  未找到對應的 Firebase session (railway_session_id={railway_session_id})")
                for sess in sessions[:3]:
                    m = sess.get('metadata', {})
                    print(f"   - Firebase: {sess.get('id')}, Railway: {m.get('railway_session_id')}, 受測者: {m.get('subject_name')}")
        else:
            print(f"❌ 查詢 Firebase sessions 失敗: {r.status_code} {r.text[:300]}")
    except Exception as e:
        print(f"❌ 查詢 Firebase 例外: {e}")

# Summary
print("\n" + "=" * 80)
print("測試總結")
print("=" * 80)
print(f"Railway session_id : {railway_session_id}")
print(f"PostgreSQL 儲存    : {'✅ 成功' if total_captures > 0 else '❌ 失敗'} ({total_captures} 筆)")
print(f"Firebase 同步      : {'✅ 成功' if found else '⚠️  未找到或尚未完成'}")
print("=" * 80)
