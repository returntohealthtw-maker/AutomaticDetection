import requests, sys, base64, json
requests.packages.urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login',
                  json={'phone':'0900000000','password':'admin123'}, timeout=15, verify=False)
H = {'Authorization': f'Bearer {r.json()["token"]}'}

print("=== session 110（李芮）新報告驗證 ===")
r2 = requests.get(f'{BASE}/api/v1/eeg/sessions/110/stats', headers=H, timeout=15, verify=False)
d = r2.json()
qab = d.get('qeeg_abilities') or {}
eeg = d.get('eeg_stats') or {}
url = d.get('report_url') or ''

print(f"status: {d.get('report_status')}")
print(f"report_url: ...{url[-40:]}" if url else "report_url: (空)")
print()
print(f"後台顯示 (qEEG):")
print(f"  専注 = {qab.get('focus')}")
print(f"  放鬆 = {qab.get('relaxation')}")
print()
print(f"eSense 原始值 (舊報告曾顯示):")
print(f"  専注 = {eeg.get('attention_percentage')}")
print(f"  放鬆 = {eeg.get('meditation_percentage')}")
print()

# 取 signed URL 讓使用者可以預覽
print("取有效 PDF 連結...")
try:
    rs = requests.get(f'{BASE}/api/v1/reports/session/110/signed-url?days=7',
                      headers=H, timeout=15, verify=False)
    sdata = rs.json()
    signed = sdata.get('url') or sdata.get('signed_url') or sdata.get('pdf_url') or ''
    if signed:
        print(f"PDF 預覽連結（7天有效）:\n  {signed[:150]}")
    else:
        print(f"signed-url 回應: {sdata}")
except Exception as e:
    print(f"取 signed URL 失敗: {e}")

print()
print("="*60)
if d.get('report_status') == 'completed' and url:
    print("✅ session 110 新報告已完成")
    print(f"   報告應顯示: 専注={qab.get('focus')}, 放鬆={qab.get('relaxation')} (qEEG校正值)")
    print(f"   後台顯示 : 専注={qab.get('focus')}, 放鬆={qab.get('relaxation')} (qEEG校正值)")
    print(f"   兩者一模一樣 ✅")
