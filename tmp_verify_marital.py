"""
全面驗證夫妻報告 #130 及相關問題
"""
import sys, requests, urllib3, json
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'

r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False)
token = r.json().get('token') or r.json().get('access_token')
h = {'Authorization': 'Bearer '+token}

print("=" * 60)
print("1. Report #130 DB 狀態 (raw SQL diag)")
print("=" * 60)
rr = requests.get(BASE+'/reports/diag/report/130', headers=h, verify=False)
d130 = rr.json()
for k, v in d130.items():
    print(f"  {k}: {v}")

print()
print("=" * 60)
print("2. Report #135 DB 狀態 (個人報告)")
print("=" * 60)
rr2 = requests.get(BASE+'/reports/diag/report/135', headers=h, verify=False)
d135 = rr2.json()
for k, v in d135.items():
    print(f"  {k}: {v}")

print()
print("=" * 60)
print("3. 前台 signed-url 端點：取 #130 的 signed URL")
print("=" * 60)
# 測試不帶 report_id（舊方式，應回傳哪份？）
sr_old = requests.get(BASE+'/reports/session/112/signed-url', headers=h, verify=False)
print(f"  不帶 report_id: {sr_old.status_code} -> {sr_old.text[:120]}")

# 測試帶 report_id=130（夫妻報告）
sr_130 = requests.get(BASE+'/reports/session/112/signed-url?report_id=130', headers=h, verify=False)
print(f"  帶 report_id=130: {sr_130.status_code} -> {sr_130.text[:120]}")

# 測試帶 report_id=135（個人報告）
sr_135 = requests.get(BASE+'/reports/session/112/signed-url?report_id=135', headers=h, verify=False)
print(f"  帶 report_id=135: {sr_135.status_code} -> {sr_135.text[:120]}")

print()
print("=" * 60)
print("4. 測試 signed URL 是否可存取 PDF")
print("=" * 60)
if sr_130.ok:
    try:
        url_130 = sr_130.json().get('url') or sr_130.json().get('signed_url') or sr_130.json().get('pdf_url') or ''
        print(f"  URL for #130: {url_130[:80]}...")
        if url_130:
            head_r = requests.head(url_130, verify=False, timeout=10, allow_redirects=True)
            print(f"  HEAD request: {head_r.status_code}, content-type: {head_r.headers.get('content-type')}, size: {head_r.headers.get('content-length')}")
    except Exception as e:
        print(f"  ERROR: {e}")

print()
print("=" * 60)
print("5. 後台 session #112 顯示的所有報告")
print("=" * 60)
# 查 all-subjects-overview 中的 session 112 reports
ov = requests.get(BASE+'/reports/all-subjects-overview?limit=200', headers=h, verify=False)
subjects = ov.json()
if isinstance(subjects, dict):
    subjects = subjects.get('subjects') or []
for s in subjects:
    if '洪任佑' in (s.get('name') or s.get('subject_name') or ''):
        print(f"  Subject: {s.get('name')}")
        for rep in (s.get('reports') or []):
            print(f"    Report #{rep.get('report_id')}: kind={rep.get('talent_report_kind')} status={rep.get('status')} pdf={'有' if rep.get('pdf_url') else '無'}")

print()
print("=" * 60)
print("6. 洪任佑 & 王筱琪 後台腦波數值（90s window）")
print("=" * 60)
for s in subjects:
    name = s.get('name') or s.get('subject_name', '')
    if '洪任佑' in name or '王筱琪' in name:
        bw = s.get('latest_brainwave') or {}
        ba = bw.get('bands_avg') or {}
        print(f"  {name} (source={bw.get('_source')}):")
        print(f"    Delta={ba.get('delta')} Theta={ba.get('theta')} High_a={ba.get('high_alpha')} Low_a={ba.get('low_alpha')}")
        print(f"    High_b={ba.get('high_beta')} Low_b={ba.get('low_beta')} High_g={ba.get('high_gamma')} Low_g={ba.get('low_gamma')}")
