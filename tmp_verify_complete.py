"""
用 Railway 後端的 firebase-diag 端點 + 新增的 session 讀取功能來驗證
"""
import sys, requests, urllib3, json, asyncio
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()

BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False)
token = r.json().get('token') or r.json().get('access_token')
h = {'Authorization': 'Bearer '+token}

print("=" * 60)
print("【驗證1】Firebase Service Key 設定與連線")
print("=" * 60)
d1 = requests.get(BASE+'/eeg/admin/firebase-diag', headers=h, verify=False).json()
print(f"  Service Key 已設定: {d1.get('firebase_key_set')}")
print(f"  Service Key 前綴: {d1.get('firebase_key_prefix')}")
print(f"  Firebase API 可連線: {d1.get('firebase_api_reachable')}")
print(f"  Firebase API 狀態: {d1.get('firebase_api_status')}")
if d1.get('firebase_api_error'):
    print(f"  錯誤: {d1.get('firebase_api_error')}")

print()
print("=" * 60)
print("【驗證2】PostgreSQL captures 已儲存（原始值域確認）")
print("=" * 60)
for sid in [122, 123]:
    cap_r = requests.get(BASE+f'/sessions/{sid}/captures?limit=5', headers=h, verify=False)
    if cap_r.ok:
        caps_data = cap_r.json()
        caps = caps_data if isinstance(caps_data, list) else caps_data.get('captures', caps_data.get('data', []))
        total = cap_r.json().get('total', len(caps)) if isinstance(cap_r.json(), dict) else len(caps)
        print(f"  session #{sid}: PostgreSQL 筆數={total}")
        if caps:
            c = caps[0]
            print(f"    第1筆 delta={c.get('delta')} theta={c.get('theta')} "
                  f"good_signal={c.get('good_signal')} (raw值確認 delta>1000)")
    else:
        print(f"  session #{sid}: {cap_r.status_code}")

print()
print("=" * 60)
print("【驗證3】BrainDNA 演算結果確認（存入 sessions table）")
print("=" * 60)
for sid in [122, 123]:
    st = requests.get(BASE+f'/eeg/sessions/{sid}/stats', headers=h, verify=False).json()
    bdna = st.get('braindna_result') or {}
    print(f"  session #{sid} [{st.get('subject_name')}]:")
    print(f"    stress={bdna.get('stress')} balance={bdna.get('balance')} "
          f"energy={bdna.get('energy')} mind_color={bdna.get('mind_color')}")
    print(f"    mbti={bdna.get('mbti')} overall_score={bdna.get('overall_score')}")
    print(f"    firebase_session_id: {st.get('firebase_session_id')}")
    print(f"    firebase_sync_ok: {st.get('firebase_sync_ok')}")

print()
print("=" * 60)
print("【驗證4】用 Railway 後端 fetch_eeg_features 讀回 Firebase 筆數")
print("=" * 60)
# 透過 Railway 的 firebase_sync.fetch_eeg_features 功能（需要內部端點）
# 呼叫 /eeg/admin/firebase-session-check 端點（若存在）
for sid in [122, 123]:
    st = requests.get(BASE+f'/eeg/sessions/{sid}/stats', headers=h, verify=False).json()
    fb_sid = st.get('firebase_session_id')
    if not fb_sid:
        print(f"  session #{sid}: 無 firebase_session_id")
        continue
    
    # 嘗試透過 Railway admin 端點讀取 Firebase
    fb_check = requests.get(BASE+f'/eeg/admin/firebase-session/{fb_sid}',
                            headers=h, verify=False, timeout=20)
    if fb_check.status_code == 404:
        print(f"  session #{sid} (fb={fb_sid[:12]}...): 端點不存在，需要後端直接查")
    elif fb_check.ok:
        fd = fb_check.json()
        print(f"  session #{sid}: Firebase eeg_features={fd.get('eeg_count')} {fd}")
    else:
        print(f"  session #{sid}: {fb_check.status_code} {fb_check.text[:100]}")

print()
print("=== 結論 ===")
print("如果 Service Key 已設定且 API 可連線，則 firebase_sync_ok=True 代表儲存成功")
print("可在 Firebase Console 直接確認：")
print("  https://console.firebase.google.com/project/gen-lang-client-0435688289/firestore")
