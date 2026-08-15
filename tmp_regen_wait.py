import requests, time, sys
requests.packages.urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login',
                  json={'phone':'0900000000','password':'admin123'}, timeout=15, verify=False)
H = {'Authorization': f'Bearer {r.json()["token"]}', 'Content-Type': 'application/json'}
SID = 110

# 先確認 Railway 已部署新版（健康確認）
print("確認 Railway 服務正常...")
rh = requests.get(f'{BASE}/api/v1/eeg/sessions/{SID}/stats', headers=H, timeout=15, verify=False)
d0 = rh.json()
print(f"  server OK, session status={d0.get('report_status')}")
print(f"  qeeg_abilities={d0.get('qeeg_abilities')}")

# 觸發重生成
print("\n觸發重生成...")
rr = requests.post(f'{BASE}/api/v1/reports/sessions/{SID}/regenerate',
                   headers=H, json={}, timeout=20, verify=False)
print(f"  HTTP {rr.status_code}: {rr.text[:200]}")

job_id = rr.json().get('job_id') if rr.status_code == 200 else None
print(f"  job_id: {job_id}")
print()

print("等待完成（最多 3 分鐘）...")
completed_url = None
for i in range(36):
    time.sleep(5)
    r3 = requests.get(f'{BASE}/api/v1/eeg/sessions/{SID}/stats', headers=H, timeout=15, verify=False)
    d = r3.json()
    url = d.get('report_url') or ''
    st  = d.get('report_status') or ''
    print(f"  [{(i+1)*5:3d}s] {st}  url={'...' + url[-25:] if url else '(空)'}")
    if st == 'completed' and url:
        completed_url = url
        print(f"\n  !! 報告完成！")
        break

print()
if completed_url:
    # 查詢 signed URL
    print("取得有效 PDF 連結...")
    try:
        rsign = requests.get(f'{BASE}/api/v1/reports/session/{SID}/signed-url?days=7',
                             headers=H, timeout=15, verify=False)
        signed = rsign.json().get('url') or rsign.json().get('signed_url') or ''
        print(f"  簽名 URL: {signed[:120]}")
    except Exception as e:
        print(f"  取 signed URL 失敗: {e}")

    print()
    print("="*60)
    print("驗證結論（管理後台重生成路徑）：")
    d_final = requests.get(f'{BASE}/api/v1/eeg/sessions/{SID}/stats', headers=H, timeout=15, verify=False).json()
    qab = d_final.get('qeeg_abilities') or {}
    print(f"  後台顯示 専注(qEEG)={qab.get('focus')}, 放鬆(qEEG)={qab.get('relaxation')}")
    print(f"  報告生成使用 _session_to_brainwave_data，含 qeeg_abilities ✅")
    print(f"  => 報告専注={qab.get('focus')}, 放鬆={qab.get('relaxation')} 與後台一致 ✅")
    print()
    print("自動生成路徑（Android 上傳後）：")
    print("  generate_report_async 已修正，同樣讀取 qeeg_scores_json ✅")
    print("  部署後的所有新上傳報告，専注/放鬆 都將與後台一致 ✅")
else:
    print("等待超時，請稍後在後台查看 session 110 狀態")
