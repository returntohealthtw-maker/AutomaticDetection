"""診斷 鄭靜怡 報告生成失敗原因（查詢 Railway 生產 API）"""
import sys, io, json, requests, urllib3
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
urllib3.disable_warnings()

BASE = "https://backend-production-2da61.up.railway.app"
NAME = "鄭靜怡"

s = requests.Session()
s.verify = False
TOKEN = s.post(f"{BASE}/api/v1/auth/login",
               json={"phone": "0900000000", "password": "admin123"}, timeout=15).json().get("token", "")
if not TOKEN:
    print("登入失敗"); sys.exit(1)
s.headers["Authorization"] = f"Bearer {TOKEN}"
print("✅ 登入成功\n")

def get(path, **kw):
    r = s.get(f"{BASE}{path}", timeout=30, **kw)
    return r.status_code, r.json() if r.headers.get("content-type","").startswith("application/json") else r.text

print("=" * 70)
print(f"診斷：{NAME} 報告生成狀況")
print("=" * 70)

# 1. 從 reports/list 找
code, data = get("/api/v1/reports/list")
reports = data.get("reports", []) if isinstance(data, dict) else []
matched_reports = [r for r in reports if NAME in (r.get("subject_name") or "")]
print(f"\n[Reports/list] 全部 {len(reports)} 筆，符合 {len(matched_reports)} 筆")
for r in matched_reports:
    print(f"  report_id={r.get('report_id')} session_id={r.get('session_id')}")
    print(f"    status={r.get('status')} kind={r.get('report_kind')} kind_zh={r.get('report_kind_zh')}")
    print(f"    completed_at={r.get('completed_at')}")
    print(f"    error_message={r.get('error_message')}")
    print(f"    headless_error={r.get('headless_error')}")
    print(f"    email={r.get('subject_email')} age={r.get('subject_age')} gender={r.get('subject_gender')}")
    print(f"    consultant={r.get('consultant')}")

# 2. 從 eeg/sessions 找
code, data = get("/api/v1/eeg/sessions?limit=500")
sessions = data.get("sessions", []) if isinstance(data, dict) else []
matched_sessions = [x for x in sessions if NAME in (x.get("subject_name") or "")]
print(f"\n[EEG Sessions] 全部 {len(sessions)} 筆，符合 {len(matched_sessions)} 筆")
for x in matched_sessions:
    print(f"  session_id={x.get('session_id')} status={x.get('status')} report_type={x.get('report_type')}")
    print(f"    captures={x.get('total_captures')} created_at={x.get('created_at')}")
    print(f"    report_status={x.get('report_status')} report_url={'有' if x.get('report_url') else '無'}")
    print(f"    failure_reason={x.get('failure_reason')}")
    print(f"    bdna_mode={x.get('bdna_mode')}")

# 3. 查各 session 的 stats
for x in matched_sessions:
    sid = x.get("session_id")
    code, stats = get(f"/api/v1/eeg/sessions/{sid}/stats")
    if code == 200 and isinstance(stats, dict):
        es = stats.get("eeg_stats") or {}
        ba = es.get("bands_avg") or {}
        print(f"\n  [Session {sid} Stats]")
        print(f"    sample_count={es.get('sample_count')} attention={es.get('attention_percentage')} meditation={es.get('meditation_percentage')}")
        print(f"    bands_avg: delta={ba.get('delta')} theta={ba.get('theta')} alpha={ba.get('alpha')} beta={ba.get('beta')} gamma={ba.get('gamma')}")
        print(f"    report_status={stats.get('report_status')} report_url={'有' if stats.get('report_url') else '無'}")

# 4. 查 generation events（最近 200 個 session，篩 name）
code, data = get("/api/v1/reports/events/sessions?limit=200&only_failed=true")
ev_sessions = data.get("sessions", []) if isinstance(data, dict) else []
matched_events = [e for e in ev_sessions if NAME in (e.get("subject_name") or "")]
print(f"\n[Generation Events - failed sessions] 符合 {len(matched_events)} 筆")
for e in matched_events:
    print(f"  cid={e.get('correlation_id')} session_id={e.get('session_id')}")
    print(f"    report_type={e.get('report_type')} variant={e.get('variant')}")
    print(f"    last_phase={e.get('last_phase')} is_failed={e.get('is_failed')} is_done={e.get('is_done')}")
    print(f"    chapter_done={e.get('chapter_done')}/{e.get('chapter_max')}")
    print(f"    last_error={e.get('last_error')}")
    print(f"    first_at={e.get('first_at')} last_at={e.get('last_at')}")

# 5. 若找到 correlation_id，拉完整 timeline
if matched_events:
    cid = matched_events[0].get("correlation_id")
    code, tl = get(f"/api/v1/reports/events/{cid}")
    if code == 200 and isinstance(tl, dict):
        print(f"\n[Event Timeline] correlation_id={cid}")
        for ev in tl.get("events", []):
            err = ev.get("error_message") or ""
            print(f"  [{ev.get('created_at')}] phase={ev.get('phase')} ch={ev.get('chapter_num')} sec={ev.get('section_id')} dur={ev.get('duration_ms')}ms")
            if err:
                print(f"    ERROR: {err[:500]}")

# 6. 查 headless job status（若有 session_id）
for x in matched_sessions:
    sid = x.get("session_id")
    # 查 admin headless jobs if endpoint exists
    code, hj = get(f"/api/v1/reports/headless-jobs?session_id={sid}")
    if code == 200:
        print(f"\n[Headless Jobs] session {sid}: {json.dumps(hj, ensure_ascii=False)[:800]}")

# 7. 也查全部 events（不只 failed）以防漏掉
code, data = get("/api/v1/reports/events/sessions?limit=300")
ev_all = data.get("sessions", []) if isinstance(data, dict) else []
matched_all = [e for e in ev_all if NAME in (e.get("subject_name") or "")]
if matched_all and not matched_events:
    print(f"\n[Generation Events - all] 符合 {len(matched_all)} 筆")
    for e in matched_all:
        print(f"  cid={e.get('correlation_id')} last_phase={e.get('last_phase')} is_failed={e.get('is_failed')} last_error={e.get('last_error')}")

print("\n" + "=" * 70)
print("診斷完成")
