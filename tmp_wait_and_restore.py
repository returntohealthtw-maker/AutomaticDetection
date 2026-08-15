import requests, sys, time
requests.packages.urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE   = 'https://backend-production-2da61.up.railway.app'
BUCKET = 'brainwave-child-reports'

OLD_URLS = {
    89: f"https://storage.googleapis.com/{BUCKET}/reports/general/1782808640537_楊女毓_成人腦波報告.pdf",
    90: f"https://storage.googleapis.com/{BUCKET}/reports/general/1782789742499_黃映筑_成人腦波報告.pdf",
    92: f"https://storage.googleapis.com/{BUCKET}/reports/general/1782816378515_鄭靜怡_成人腦波報告.pdf",
    93: f"https://storage.googleapis.com/{BUCKET}/reports/general/1782808640537_楊女毓_成人腦波報告.pdf",
    94: f"https://storage.googleapis.com/{BUCKET}/reports/general/1782816378515_鄭靜怡_成人腦波報告.pdf",
    95: f"https://storage.googleapis.com/{BUCKET}/reports/general/1782816378515_鄭靜怡_成人腦波報告.pdf",
    96: f"https://storage.googleapis.com/{BUCKET}/reports/general/1782808640537_楊女毓_成人腦波報告.pdf",
    97: f"https://storage.googleapis.com/{BUCKET}/reports/general/1782816378515_鄭靜怡_成人腦波報告.pdf",
    98: f"https://storage.googleapis.com/{BUCKET}/reports/general/1782967365745_蔡宛蓉_成人腦波報告.pdf",
}
NAMES = {89:'楊女毓',90:'黃映筑',92:'鄭靜怡',93:'楊女毓',94:'鄭靜怡',
         95:'鄭靜怡',96:'楊女毓',97:'鄭靜怡',98:'蔡宛蓉'}

print("等待 Railway 部署（最多 5 分鐘）...")
r0 = requests.post(f'{BASE}/api/v1/auth/login',
                   json={'phone':'0900000000','password':'admin123'}, timeout=15, verify=False)
H = {'Authorization': f'Bearer {r0.json()["token"]}', 'Content-Type': 'application/json'}

for i in range(30):
    time.sleep(10)
    rt = requests.post(f'{BASE}/api/v1/monitor/sessions/98/restore-pdf-url',
                       headers=H, json={'pdf_url': 'https://test.com/t.pdf'}, timeout=8, verify=False)
    if rt.status_code in [200, 404]:  # 404 = session has no report (ok), 200 = success
        print(f"  ✅ 端點已上線！（{(i+1)*10}秒）")
        break
    elif rt.status_code == 422:
        print(f"  ✅ 端點已上線！（{(i+1)*10}秒）")
        break
    print(f"  [{(i+1)*10}s] HTTP {rt.status_code}，等待中...")
else:
    print("  ❌ 超時，端點仍未上線")
    sys.exit(1)

# 重新登入（token 可能過期）
r0 = requests.post(f'{BASE}/api/v1/auth/login',
                   json={'phone':'0900000000','password':'admin123'}, timeout=15, verify=False)
H = {'Authorization': f'Bearer {r0.json()["token"]}', 'Content-Type': 'application/json'}

print("\n=== 還原舊 GCS URL ===")
for sid, url in sorted(OLD_URLS.items()):
    rr = requests.post(f'{BASE}/api/v1/monitor/sessions/{sid}/restore-pdf-url',
                       headers=H, json={'pdf_url': url}, timeout=15, verify=False)
    ok = rr.status_code == 200
    print(f"  {'✅' if ok else '❌'} sid={sid} {NAMES[sid]}: HTTP {rr.status_code} {'' if ok else rr.text[:60]}")

print("\n=== 確認結果 ===")
all_ok = True
for sid in sorted(OLD_URLS.keys()):
    rs = requests.get(f'{BASE}/api/v1/eeg/sessions/{sid}/stats', headers=H, timeout=10, verify=False)
    d  = rs.json()
    st  = d.get('report_status','?')
    url = bool(d.get('report_url'))
    ok  = st == 'completed' and url
    if not ok: all_ok = False
    print(f"  {'✅' if ok else '❌'} sid={sid} {NAMES[sid]}: status={st} url={url}")

print()
if all_ok:
    print("✅ 全部還原完成！9 個 session 的舊報告已恢復。")
else:
    print("⚠️  部分還原失敗，請查看上方結果。")
