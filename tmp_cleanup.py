"""
1. 刪除測試建立的假 session #115 和 report #139
2. 確認報告 #132（李悅瑄）的狀態
"""
import sys, requests, urllib3, json
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'

r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False)
token = r.json().get('token') or r.json().get('access_token')
h = {'Authorization': 'Bearer '+token}

print("=== report #139 狀態 ===")
rr = requests.get(BASE+'/reports/diag/report/139', headers=h, verify=False)
print(f"  {rr.json()}")

print()
print("=== report #132（李悅瑄）狀態 ===")
rr2 = requests.get(BASE+'/reports/diag/report/132', headers=h, verify=False)
print(f"  {rr2.json()}")

print()
print("=== 用 update-summary 取消 report #139 ===")
ru = requests.post(BASE+'/reports/139/update-summary', json={"status": "failed"}, headers=h, verify=False)
print(f"  {ru.status_code} {ru.text[:150]}")

print()
print("=== reset-stuck session #115 report ===")
rs = requests.post(BASE+'/reports/sessions/115/reset-stuck', headers=h, verify=False)
print(f"  {rs.status_code} {rs.text[:150]}")

print()
print("=== 確認 session #114 的詳細 stats（BrainDNA 指標）===")
sr = requests.get(BASE+'/eeg/sessions/114/stats', headers=h, verify=False)
d = sr.json()
print(f"  subject_name: {d.get('subject_name')}")
bd = d.get('braindna_result') or {}
print(f"  mbti={bd.get('mbti')} stress={bd.get('stress')} balance={bd.get('balance')} energy={bd.get('energy')}")
# 找 500 的線索：是否有例外字段
print(f"  全部 keys: {list(d.keys())}")
