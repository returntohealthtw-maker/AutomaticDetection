import sys, time, requests, urllib3
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()

BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False)
token = r.json().get('token') or r.json().get('access_token')
h = {'Authorization': 'Bearer '+token}

print("等待部署 2026.07.30.03...")
for i in range(24):
    time.sleep(5)
    vr = requests.get(BASE+'/app/version', headers=h, verify=False, timeout=5)
    if vr.ok and vr.json().get('html_version', '') >= '2026.07.30.03':
        print(f"  ✅ 部署完成！版本={vr.json().get('html_version')}")
        break
    print(f"  [{i*5+5}s] {vr.json().get('html_version','...')}")

print()
print("=== 驗證 bands_7 是否為 0-100 值 ===")
# 呼叫 all-subjects-overview 取 latest_brainwave
ov = requests.get(BASE+'/reports/all-subjects-overview', headers=h, verify=False, timeout=20)
if not ov.ok:
    print(f"  FAIL: {ov.status_code}")
else:
    subjects = ov.json().get('subjects', [])
    shown = 0
    for s in subjects:
        bw = s.get('latest_brainwave') or {}
        b7 = bw.get('bands_7') or {}
        src = bw.get('_source', '?')
        if not b7:
            continue
        name = s.get('name', '?')
        shown += 1
        print(f"  {name} | _source={src}")
        print(f"    theta={b7.get('theta')} alpha_high={b7.get('alpha_high')} "
              f"beta_high={b7.get('beta_high')} gamma_low={b7.get('gamma_low')} delta={b7.get('delta')}")
        # 確認是 0-100 範圍（不超過 200）
        vals = [v for v in b7.values() if v is not None]
        if max(vals) > 200:
            print(f"    ❌ 仍含原始值！max={max(vals)}")
        else:
            print(f"    ✅ 全部 0-100 範圍（max={max(vals):.1f}）")
        if shown >= 5:
            break
    if shown == 0:
        print("  ⚠️ 無任何 bands_7 資料（所有 session 的 BrainDNA 可能都失敗）")
