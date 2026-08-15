"""
透過 Railway stats API 驗證 Firebase 資料是否正確儲存
（Railway 後端有 Service Key 可讀 Firebase）
"""
import sys, requests, urllib3, json
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()

BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False)
token = r.json().get('token') or r.json().get('access_token')
h = {'Authorization': 'Bearer '+token}

print("=" * 60)
print("【驗證1】PostgreSQL + Firebase 雙重儲存確認")
print("=" * 60)
for sid in [122, 123]:
    st = requests.get(BASE+f'/eeg/sessions/{sid}/stats', headers=h, verify=False)
    d = st.json()
    fb_sid = d.get('firebase_session_id')
    name   = d.get('subject_name')
    cap    = d.get('total_captures')
    bdna   = d.get('braindna_result') or {}

    print(f"\nsession #{sid} [{name}]")
    print(f"  PostgreSQL captures: {cap}")
    print(f"  firebase_session_id: {fb_sid}")
    print(f"  BrainDNA stress={bdna.get('stress')} balance={bdna.get('balance')} "
          f"energy={bdna.get('energy')} mbti={bdna.get('mbti')}")

    # 透過 Railway 的 Firebase 讀取接口
    fb_r = requests.get(BASE+f'/eeg/firebase/{sid}', headers=h, verify=False)
    if fb_r.ok:
        fd = fb_r.json()
        print(f"  Firebase 直讀: {fd}")
    else:
        print(f"  Firebase 直讀端點: {fb_r.status_code}")

print()
print("=" * 60)
print("【驗證2】查看 EEG captures 的實際值域（確認非 bandTo100）")
print("=" * 60)
cap_r = requests.get(BASE+'/sessions/122/captures?limit=3', headers=h, verify=False)
if cap_r.ok:
    caps = cap_r.json()
    if isinstance(caps, dict):
        caps = caps.get('captures', caps.get('data', []))
    print(f"  共 {len(caps)} 筆（前3筆）：")
    for c in caps[:3]:
        print(f"    seq={c.get('seq_num')} delta={c.get('delta')} theta={c.get('theta')} "
              f"low_alpha={c.get('low_alpha')} good_signal={c.get('good_signal')}")
else:
    print(f"  captures 查詢: {cap_r.status_code} {cap_r.text[:100]}")

print()
print("=" * 60)
print("【驗證3】Firebase 健康端點直接查 captures 總數")
print("=" * 60)
# 用 Railway 的 firebase-check 端點（如有）
fck = requests.get(BASE+'/eeg/firebase-check/d8fd7d9d-bbd0-4edf-bfb3-f76cec77b01c',
                   headers=h, verify=False)
print(f"  firebase-check: {fck.status_code} {fck.text[:200]}")

# 用 all-subjects-overview 找鄭靜怡
ov = requests.get(BASE+'/reports/all-subjects-overview?q=鄭靜怡', headers=h, verify=False)
for s in ov.json().get('subjects', []):
    if '鄭靜怡' in (s.get('name') or ''):
        bw = s.get('latest_brainwave') or {}
        src = bw.get('_source', 'none')
        print(f"\n  Subject #{s.get('subject_id')} {s.get('name')}: "
              f"sessions={s.get('sessions_count')} bw_source={src}")
        if bw and bw.get('bands_avg'):
            print(f"  bands: {bw.get('bands_avg')}")
