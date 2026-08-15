"""
模擬 APP 採集完成後的 API 呼叫流程，找 500 的來源
"""
import sys, requests, urllib3, json
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'

# 模擬顧問帳號登入（郭馨雯）
# 先用管理員確認顧問帳號
r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False)
token = r.json().get('token') or r.json().get('access_token')
h_admin = {'Authorization': 'Bearer '+token}

# 取顧問帳號清單
cons_r = requests.get(BASE+'/consultants', headers=h_admin, verify=False)
print("=== 顧問帳號清單 ===")
if cons_r.ok:
    cons_list = cons_r.json()
    if isinstance(cons_list, dict):
        cons_list = cons_list.get('consultants', cons_list.get('data', []))
    for c in cons_list[:10]:
        print(f"  id={c.get('consultant_id')} name={c.get('name')} phone={c.get('phone')} role={c.get('role')}")
else:
    print(f"  {cons_r.status_code}: {cons_r.text[:200]}")

print()
print("=== 模擬管理員查 session #114 的 stats（採集完成後打的端點）===")
sr = requests.get(BASE+'/eeg/sessions/114/stats', headers=h_admin, verify=False)
print(f"  stats: {sr.status_code}")
if sr.ok:
    d = sr.json()
    print(f"  bdna: {d.get('braindna_result')}")
    print(f"  bands_avg keys: {list((d.get('eeg_stats') or d.get('bands_avg') or {}).keys())[:5]}")
else:
    print(f"  ERROR: {sr.text[:200]}")

print()
print("=== 測試 POST /eeg/save-stats（WebApp 路徑是否還在被呼叫）===")
# 模擬一個 save-stats 請求
test_payload = {
    "session_id": "test_verify_only",
    "subject_name": "測試",
    "consultant_name": "admin",
    "duration_seconds": 180,
    "sample_count": 180,
    "bands_avg": {"delta": 100, "theta": 50, "alpha": 30, "beta": 20, "gamma": 10},
}
ss_r = requests.post(BASE+'/eeg/save-stats', json=test_payload, headers=h_admin, verify=False)
print(f"  save-stats: {ss_r.status_code} {ss_r.text[:150]}")

print()
print("=== 測試 /sessions/upload（POST 一個假的 upload 看回應格式）===")
# 只是測試端點是否存在，不真的上傳
fake_upload = {"subject_name": "", "consultant_name": "", "captures": []}
up_r = requests.post(BASE+'/sessions/upload', json=fake_upload, headers=h_admin, verify=False)
print(f"  upload (empty): {up_r.status_code} {up_r.text[:150]}")

print()
print("=== 後台「查看細節」按鈕：/reports/all-subjects-overview?q=李悅瑄 ===")
ov = requests.get(BASE+'/reports/all-subjects-overview?q=李悅瑄', headers=h_admin, verify=False)
print(f"  {ov.status_code}")
if ov.ok:
    d = ov.json().get('subjects', [])
    for s in d[:2]:
        print(f"  name={s.get('name')} sessions_count={s.get('sessions_count')} "
              f"latest_session_id={s.get('latest_session_id')} "
              f"reports={len(s.get('reports',[]))}")
        print(f"  reports: {[(r.get('report_id'), r.get('status'), r.get('report_kind')) for r in s.get('reports',[])]}")
