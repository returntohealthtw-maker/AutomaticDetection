"""
等 Railway 部署，然後呼叫 admin/firebase-session/{fb_sid} 確認 Firebase EEG 筆數
"""
import sys, time, requests, urllib3
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()

BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False)
token = r.json().get('token') or r.json().get('access_token')
h = {'Authorization': 'Bearer '+token}

# 等待部署
print("等待 Railway 部署...（最多 120 秒）")
target_ver = "2026.07.30.02"
for i in range(24):
    time.sleep(5)
    vr = requests.get(BASE+'/app/version', headers=h, verify=False, timeout=5)
    if vr.ok:
        cur = vr.json().get('html_version', '')
        print(f"  [{i*5+5}s] current={cur}")
        if cur >= target_ver:
            print(f"  ✅ 部署完成！版本={cur}")
            break
    else:
        print(f"  [{i*5+5}s] status={vr.status_code}")
else:
    print("  ⚠️ 超時，繼續執行驗證...")

print()
print("=" * 60)
print("Firebase EEG 資料驗證")
print("=" * 60)

test_sessions = [
    (122, "d8fd7d9d-bbd0-4edf-bfb3-f76cec77b01c", "鄭靜怡_retest"),
    (123, "942cb4a8-411e-40ea-bb17-272f7abcd5d2", "鄭靜怡"),
]

for pg_sid, fb_sid, name in test_sessions:
    print(f"\nsession #{pg_sid} [{name}]")
    print(f"  Firebase sid={fb_sid}")
    
    fb_r = requests.get(BASE+f'/eeg/admin/firebase-session/{fb_sid}',
                        headers=h, verify=False, timeout=30)
    if fb_r.ok:
        fd = fb_r.json()
        ok = fd.get('ok')
        count = fd.get('eeg_count', 0)
        fields = fd.get('sample_fields', [])
        delta = fd.get('sample_delta')
        gs = fd.get('sample_good_signal')
        
        if ok and count > 0:
            print(f"  ✅ Firebase EEG 筆數={count}")
            print(f"     第1筆欄位: {fields}")
            print(f"     delta={delta} good_signal={gs}")
        else:
            print(f"  ❌ Firebase 無資料: {fd}")
    else:
        print(f"  端點回傳 {fb_r.status_code}: {fb_r.text[:100]}")

print()
print("=== 驗證完成 ===")
