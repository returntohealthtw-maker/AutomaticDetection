#!/usr/bin/env python3
"""即時監控腦波檢測的 PostgreSQL + Firebase 雙寫"""
import urllib3, requests, sys, time
urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8')

BASE              = 'https://backend-production-2da61.up.railway.app'
FIREBASE_API_BASE = 'https://asia-east1-gen-lang-client-0435688289.cloudfunctions.net/api/api'
FIREBASE_API_KEY  = 'AIzaSyBc-ZEcT8fvyn-dBZ0Bhm5IsakncVp1ngQ'

# --- 登入 ---
print("登入中...")
r = requests.post(f'{BASE}/api/v1/auth/login',
    json={'phone': '0900000000', 'password': 'admin123'}, verify=False, timeout=15)
token = r.json()['token']
rh = {'Authorization': f'Bearer {token}'}

r2 = requests.post(
    f'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}',
    json={'email': 'migration@returntohealthtw.com', 'password': 'MigrateEEG@2026', 'returnSecureToken': True},
    verify=False, timeout=15)
ftoken = r2.json()['idToken']
fh = {'Authorization': f'Bearer {ftoken}'}

# --- 取得目前最新 session_id ---
r3 = requests.get(f'{BASE}/api/v1/reports/list?limit=5', headers=rh, verify=False, timeout=15)
rpts = r3.json().get('reports', [])
max_sid = max((x.get('session_id', 0) or 0 for x in rpts), default=0)

r4 = requests.get(f'{FIREBASE_API_BASE}/sessions?limit=300', headers=fh, verify=False, timeout=20)
fb_list = r4.json().get('sessions', [])
fb_existing = set()
for s in fb_list:
    rid = (s.get('metadata') or {}).get('railway_session_id')
    if rid and rid > 0:
        fb_existing.add(int(rid))
max_fb = max(fb_existing) if fb_existing else 0

print(f'[監控啟動] PostgreSQL 目前最新 session_id: {max_sid}')
print(f'[監控啟動] Firebase   目前最新 railway_id : {max_fb}')
print('[等待中] 請開始腦波檢測... 每 15 秒掃描一次，最多等 60 分鐘')
print()

found_pg = None
found_fb = None

for scan in range(240):
    time.sleep(15)
    ts = time.strftime('%H:%M:%S')

    # ── PostgreSQL 掃描 ──────────────────────────────────────
    if not found_pg:
        try:
            r5 = requests.get(f'{BASE}/api/v1/reports/list?limit=10', headers=rh, verify=False, timeout=15)
            new_rpts = [x for x in r5.json().get('reports', [])
                        if (x.get('session_id') or 0) > max_sid]
            if new_rpts:
                found_pg = new_rpts[0]
                sid  = found_pg['session_id']
                name = found_pg.get('subject_name', '?')
                rtype= found_pg.get('report_type', '?')
                caps = found_pg.get('total_captures', '?')
                print(f'[{ts}] ✅ PostgreSQL 發現新 session!')
                print(f'  session_id  : {sid}')
                print(f'  受測者姓名  : {name}')
                print(f'  報告類型    : {rtype}')
                print(f'  captures 數 : {caps}')

                # 查逐秒原始腦波
                r6 = requests.get(f'{BASE}/api/v1/sessions/{sid}/captures',
                                   headers=rh, verify=False, timeout=15)
                if r6.status_code == 200:
                    cd   = r6.json()
                    caps_list = cd.get('captures', cd) if isinstance(cd, dict) else cd
                    total     = cd.get('total', len(caps_list)) if isinstance(cd, dict) else len(caps_list)
                    print(f'  原始腦波    : {total} 筆逐秒資料')
                    if caps_list:
                        c0 = caps_list[0]
                        print(f'  第1秒樣本   : attention={c0.get("attention")}, '
                              f'meditation={c0.get("meditation")}, '
                              f'delta={c0.get("delta")}, theta={c0.get("theta")}')
                print()
        except Exception as e:
            print(f'[{ts}] PostgreSQL 查詢例外: {e}')

    # ── Firebase 掃描 ────────────────────────────────────────
    if found_pg and not found_fb:
        try:
            sid = found_pg['session_id']
            r7 = requests.get(f'{FIREBASE_API_BASE}/sessions?limit=300',
                               headers=fh, verify=False, timeout=20)
            for s in r7.json().get('sessions', []):
                if not isinstance(s, dict): continue
                meta = s.get('metadata') or {}
                if meta.get('railway_session_id') == sid:
                    found_fb = s
                    print(f'[{ts}] ✅ Firebase 同步成功!')
                    print(f'  Firebase ID : {s.get("id")}')
                    print(f'  status      : {s.get("status")}')
                    print(f'  durationSec : {s.get("durationSec")} 筆')
                    print(f'  受測者      : {meta.get("subject_name")}')
                    print(f'  data_format : {meta.get("data_format")}')
                    print()
                    break
        except Exception as e:
            print(f'[{ts}] Firebase 查詢例外: {e}')

    # ── 兩庫都找到 → 結束 ────────────────────────────────────
    if found_pg and found_fb:
        sid    = found_pg['session_id']
        pg_n   = found_pg.get('total_captures', 0)
        fb_n   = found_fb.get('durationSec', 0)
        match  = '✅ 一致' if abs((pg_n or 0) - (fb_n or 0)) <= 5 else '⚠️  有差異'
        print('=' * 60)
        print('✅✅ 雙寫驗證完成！')
        print(f'  PostgreSQL  : session {sid}, {pg_n} 筆 captures')
        print(f'  Firebase    : {found_fb.get("id","")[:12]}..., {fb_n} 筆腦波')
        print(f'  資料一致性  : {match}')
        print('=' * 60)
        break

    if (scan + 1) % 4 == 0:
        pg_st = '已找到' if found_pg else '等待中'
        fb_st = '已找到' if found_fb else '等待中'
        print(f'[{ts}] 掃描第 {scan+1} 次 — PostgreSQL: {pg_st} / Firebase: {fb_st}')
else:
    print('\n[逾時] 60 分鐘內未偵測到新 session，監控結束。')
