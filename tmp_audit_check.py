"""
審核：確認今日所有修改的端點功能正常，且沒有影響到其他流程
"""
import requests, sys, json
requests.packages.urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = 'https://backend-production-2da61.up.railway.app'
PASS = []
FAIL = []

def chk(name, ok, detail=''):
    sym = '✅' if ok else '❌'
    print(f"  {sym} {name}" + (f": {detail}" if detail else ''))
    (PASS if ok else FAIL).append(name)

r0 = requests.post(f'{BASE}/api/v1/auth/login',
                   json={'phone':'0900000000','password':'admin123'}, timeout=15, verify=False)
H = {'Authorization': f'Bearer {r0.json()["token"]}', 'Content-Type': 'application/json'}
print(f"登入: HTTP {r0.status_code}\n")

# ── 1. 基本 API 健康 ──────────────────────────────────────────────────────────
print("【1】基本 API 健康")
r = requests.get(f'{BASE}/api/v1/reports/diag', headers=H, timeout=10, verify=False)
chk("GET /reports/diag", r.status_code == 200, r.json().get('ingest_secret_set'))

r = requests.get(f'{BASE}/api/v1/eeg/sessions?limit=3', headers=H, timeout=10, verify=False)
chk("GET /eeg/sessions", r.status_code == 200, f"count={r.json().get('count')}")

# ── 2. Session stats（含 qeeg_abilities）────────────────────────────────────
print("\n【2】Session stats 含 qeeg_abilities")
for sid in [110, 111]:
    r = requests.get(f'{BASE}/api/v1/eeg/sessions/{sid}/stats', headers=H, timeout=10, verify=False)
    d = r.json()
    qab = d.get('qeeg_abilities')
    chk(f"GET /eeg/sessions/{sid}/stats", r.status_code == 200,
        f"status={d.get('report_status')} qeeg_abilities={'有' if qab else '無'}")

# ── 3. 報告還原後狀態（今日修復的 8 個 session）────────────────────────────
print("\n【3】今日還原的報告狀態")
restored = {90:'黃映筑',92:'鄭靜怡',93:'楊女毓',94:'鄭靜怡',
            95:'鄭靜怡',96:'楊女毓',97:'鄭靜怡',98:'蔡宛蓉'}
for sid, name in sorted(restored.items()):
    r = requests.get(f'{BASE}/api/v1/eeg/sessions/{sid}/stats', headers=H, timeout=10, verify=False)
    d = r.json()
    ok = d.get('report_status') == 'completed' and bool(d.get('report_url'))
    chk(f"sid={sid} {name}", ok, f"status={d.get('report_status')} url={'有' if d.get('report_url') else '無'}")

# ── 4. restore-pdf-url 端點安全性（非 admin 應被擋）──────────────────────
print("\n【4】restore-pdf-url 端點安全性")
r_noauth = requests.post(f'{BASE}/api/v1/monitor/sessions/90/restore-pdf-url',
                         json={'pdf_url': 'https://malicious.com/hack.pdf'}, timeout=10, verify=False)
chk("非 admin 應被 401/403 擋回", r_noauth.status_code in [401, 403],
    f"HTTP {r_noauth.status_code}")

# ── 5. mark-retest 端點仍正常（確認沒有破壞）────────────────────────────
print("\n【5】mark-retest 端點仍正常")
r = requests.post(f'{BASE}/api/v1/monitor/sessions/111/mark-retest',
                  headers=H, json={'reason': 'audit test'}, timeout=10, verify=False)
chk("POST mark-retest", r.status_code == 200, r.json().get('message','')[:20])
r2 = requests.delete(f'{BASE}/api/v1/monitor/sessions/111/mark-retest',
                     headers=H, timeout=10, verify=False)
chk("DELETE mark-retest", r2.status_code == 200, r2.json().get('message','')[:20])

# ── 6. 報告生成流程（不觸發，只讀）────────────────────────────────────────
print("\n【6】報告清單正常讀取")
r = requests.get(f'{BASE}/api/v1/reports/list?limit=5', headers=H, timeout=10, verify=False)
chk("GET /reports/list", r.status_code == 200, f"回傳 {len(r.json() if isinstance(r.json(), list) else [])} 筆")

# ── 7. eeg.py 新欄位不影響舊資料 ──────────────────────────────────────────
print("\n【7】eeg.py get_session_stats 回傳格式完整性")
r = requests.get(f'{BASE}/api/v1/eeg/sessions/111/stats', headers=H, timeout=10, verify=False)
d = r.json()
required_fields = ['session_id','subject_name','report_status','report_url','braindna_result']
all_present = all(f in d for f in required_fields)
chk("必要欄位齊全", all_present,
    [f for f in required_fields if f not in d] or '全部存在')
qab = d.get('qeeg_abilities')
chk("qeeg_abilities 格式正確", qab is None or isinstance(qab, dict),
    f"type={type(qab).__name__} keys={list(qab.keys())[:3] if qab else None}")

# ── 總結 ─────────────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"通過：{len(PASS)} 項  |  失敗：{len(FAIL)} 項")
if FAIL:
    print(f"失敗項目：{FAIL}")
else:
    print("全部正常，無異常！")
