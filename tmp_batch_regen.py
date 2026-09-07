"""
批次重新生成 21 個不一致 session 的報告
每次最多觸發 3 個，等完成再繼續
"""
import requests, sys, time
requests.packages.urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login',
                  json={'phone':'0900000000','password':'admin123'}, timeout=15, verify=False)
H = {'Authorization': f'Bearer {r.json()["token"]}', 'Content-Type': 'application/json'}

# 21 個需要重新生成的 session（已跳過 111，因為它還在 generating）
TARGETS = [
    (109, '李雅華'), (108, '莊子渝'), (107, '張育銓'), (106, '王琇瑩'),
    (105, '李肯欣'), (104, '鄭佳宜'), (103, 'Lily Chen'), (102, '許允約'),
    (101, '許睿恩'), (100, '許恩蕊'), (99, '薛秉蕙'), (98, '蔡宛蓉'),
    (97, '鄭靜怡'), (96, '楊女毓'), (95, '鄭靜怡'), (94, '鄭靜怡'),
    (93, '楊女毓'), (92, '鄭靜怡'), (90, '黃映筑'), (89, '楊女毓'),
    # 110 已在 generating，跳過等它自然完成
]

print(f"準備批次重生成 {len(TARGETS)} 個 session")
print("策略：每批最多 3 個，觸發後等 5 分鐘再繼續\n")

BATCH_SIZE = 3
triggered = []

for i, (sid, name) in enumerate(TARGETS):
    # 確認目前狀態
    rs = requests.get(f'{BASE}/api/v1/eeg/sessions/{sid}/stats', headers=H, timeout=15, verify=False)
    ds = rs.json()
    cur_status = ds.get('report_status', '?')
    
    # 若已在 generating，跳過（避免重複觸發）
    if cur_status == 'generating':
        print(f"  sid={sid} {name}: 已在 generating，跳過")
        continue
    
    # 觸發重生成
    rr = requests.post(f'{BASE}/api/v1/reports/sessions/{sid}/regenerate',
                       headers=H, json={}, timeout=20, verify=False)
    if rr.status_code == 200:
        job_id = rr.json().get('job_id', '?')
        print(f"  ✅ sid={sid} {name}: 已觸發 job_id={job_id}")
        triggered.append(sid)
    else:
        print(f"  ❌ sid={sid} {name}: HTTP {rr.status_code} {rr.text[:100]}")
    
    # 每 3 個批次後，等待 5 分鐘讓 headless 有空間
    if len(triggered) % BATCH_SIZE == 0 and len(triggered) > 0:
        print(f"\n  ── 已觸發 {len(triggered)} 個，等待 5 分鐘讓系統處理 ──")
        for w in range(10):
            time.sleep(30)
            completed = 0
            for tsid in triggered[-BATCH_SIZE:]:
                rck = requests.get(f'{BASE}/api/v1/eeg/sessions/{tsid}/stats', headers=H, timeout=10, verify=False)
                if rck.json().get('report_status') == 'completed':
                    completed += 1
            print(f"  [{(w+1)*30}s] 最近批次 {BATCH_SIZE} 個中有 {completed} 個已完成")
            if completed >= BATCH_SIZE:
                break
        print()

print(f"\n共觸發 {len(triggered)} 個 session 重生成")
print("報告生成需要 5-20 分鐘（Gemini 生成 24 個章節）")
print("完成後所有 session 的報告専注/放鬆 將與後台 qEEG 值一致")
print()
print("待確認完成的 session：")
for sid, name in TARGETS:
    print(f"  sid={sid} {name}")
