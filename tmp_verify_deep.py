"""
深入驗證：
1. 夫妻報告 PDF 能開啟 + 確認洪任佑/王筱琪數值
2. 個人報告 #135 為何是 failed + 找原始 GCS 檔案
3. regenerate 500 根本原因
"""
import sys, requests, urllib3, json
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'

r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False)
token = r.json().get('token') or r.json().get('access_token')
h = {'Authorization': 'Bearer '+token}

print("=" * 60)
print("A. 取夫妻報告 #130 的 signed URL 並確認 PDF 可下載")
print("=" * 60)
sr = requests.get(BASE+'/reports/session/112/signed-url?report_id=130', headers=h, verify=False)
url_130 = ''
if sr.ok:
    j = sr.json()
    url_130 = j.get('signed_url') or j.get('url') or j.get('pdf_url') or ''
    print(f"  GCS path: {j.get('gcs_path')}")
    print(f"  Signed URL (first 100): {url_130[:100]}")
    if url_130:
        rp = requests.get(url_130, verify=False, timeout=15)
        print(f"  GET PDF: {rp.status_code}, size={len(rp.content)}, is_pdf={rp.content[:4]==b'%PDF'}")
else:
    print(f"  Error: {sr.status_code} {sr.text[:100]}")

print()
print("=" * 60)
print("B. 個人報告 #135 的完整歷史與 client_summary")
print("=" * 60)
# 取 client_summary 完整內容
import requests as req_lib
raw_cs = req_lib.get(BASE+'/reports/session/112/signed-url?report_id=135', headers=h, verify=False)
print(f"  signed-url for #135: {raw_cs.status_code} {raw_cs.text[:200]}")

# 查 #135 的 client_summary
cs_q = requests.get(BASE+f'/reports/diag/report/135', headers=h, verify=False)
d135 = cs_q.json()
print(f"  #135 diag: {d135}")

print()
print("=" * 60)
print("C. GCS 中有哪些洪任佑的 PDF（找原始個人報告）")
print("=" * 60)
# Try to find old personal report via import-from-gcs diagnostic
try:
    gcs_list = requests.get(BASE+'/reports/import-from-gcs?prefix=reports/general/&list_only=true', headers=h, verify=False, timeout=15)
    if gcs_list.ok:
        files = gcs_list.json().get('files') or []
        hong_files = [f for f in files if '洪' in str(f)]
        print(f"  Total files in GCS: {len(files)}")
        print(f"  洪任佑相關: {len(hong_files)}")
        for f in hong_files[:5]:
            print(f"    {f}")
    else:
        print(f"  GCS list error: {gcs_list.status_code} {gcs_list.text[:100]}")
except Exception as e:
    print(f"  Exception: {e}")

print()
print("=" * 60)
print("D. regenerate 端點 500 錯誤詳情")
print("=" * 60)
# Try regenerate with verbose error catching
regen_r = requests.post(BASE+'/reports/sessions/112/regenerate', json={'report_id': 130}, headers=h, verify=False)
print(f"  Status: {regen_r.status_code}")
print(f"  Body: {regen_r.text[:300]}")
# Also try without report_id
regen_r2 = requests.post(BASE+'/reports/sessions/112/regenerate', headers=h, verify=False)
print(f"  Without report_id: {regen_r2.status_code} {regen_r2.text[:200]}")
