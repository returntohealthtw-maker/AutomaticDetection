"""
1. 恢復 report #130 到 completed 狀態，使用已知的 GCS URL
2. 驗證 report #135 是否完整
"""
import sys, requests, urllib3, json
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'

r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False)
token = r.json().get('token') or r.json().get('access_token')
h = {'Authorization': 'Bearer '+token}

# 1. 驗證夫妻報告 GCS 檔案還在
gcs_url = 'https://storage.googleapis.com/brainwave-child-reports/reports/manual/130_20260729100013_%E6%B4%AA%E4%BB%BB%E4%BD%91_%E7%8E%8B%E7%AD%B1%E7%90%AA_%E5%A4%AB%E5%A6%BB%E9%9B%99%E8%85%A6%E6%B3%A2%E5%85%B1%E6%8C%AF%E5%A0%B1%E5%91%8A.pdf'
# Also try the non-encoded version
gcs_url_plain = 'https://storage.googleapis.com/brainwave-child-reports/reports/manual/130_20260729100013_洪任佑_王筱琪_夫妻雙腦波共振報告.pdf'

print("=" * 60)
print("1. 驗證 GCS 檔案可存取")
print("=" * 60)
hr = requests.head(gcs_url, verify=False, timeout=10, allow_redirects=True)
print(f"  URL encoded: {hr.status_code}, size={hr.headers.get('content-length')}")
hr2 = requests.head(gcs_url_plain, verify=False, timeout=10, allow_redirects=True)
print(f"  URL plain: {hr2.status_code}, size={hr2.headers.get('content-length')}")

# 使用哪個 URL
use_url = gcs_url if hr.ok else (gcs_url_plain if hr2.ok else None)
print(f"  使用 URL: {use_url[:80] if use_url else 'NONE'}")

print()
print("=" * 60)
print("2. 恢復 report #130 到 completed 狀態")
print("=" * 60)
# 用 update-summary 端點，更新 status 和 pdf_url
payload_restore = {
    "status": "completed",
    "pdf_url": gcs_url_plain,  # 使用原始 GCS 永久 URL（非 signed）
}
ru = requests.post(BASE+'/reports/130/update-summary', json=payload_restore, headers=h, verify=False)
print(f"  update-summary: {ru.status_code} {ru.text[:200]}")

print()
print("=" * 60)
print("3. 驗證 #130 更新後的狀態")
print("=" * 60)
rr = requests.get(BASE+'/reports/diag/report/130', headers=h, verify=False)
print(f"  {rr.json()}")

print()
print("=" * 60)
print("4. 驗證 #135 個人報告完整")
print("=" * 60)
rr2 = requests.get(BASE+'/reports/diag/report/135', headers=h, verify=False)
d135 = rr2.json()
print(f"  {d135}")
if d135.get('pdf_url_prefix'):
    # 測試 signed URL
    sr135 = requests.get(BASE+'/reports/session/112/signed-url?report_id=135', headers=h, verify=False)
    if sr135.ok:
        url_135 = sr135.json().get('signed_url') or ''
        if url_135:
            hr135 = requests.head(url_135, verify=False, timeout=10)
            print(f"  PDF accessible: {hr135.status_code}, size={hr135.headers.get('content-length')}")
        print(f"  Signed URL: {sr135.json().get('gcs_path')}")
    else:
        print(f"  signed-url error: {sr135.status_code} {sr135.text[:100]}")
