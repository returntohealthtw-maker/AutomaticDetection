#!/usr/bin/env python3
import urllib3, requests, sys
urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8')

BASE = 'https://backend-production-2da61.up.railway.app'
FIREBASE_API_BASE = 'https://asia-east1-gen-lang-client-0435688289.cloudfunctions.net/api/api'
FIREBASE_API_KEY  = 'AIzaSyBc-ZEcT8fvyn-dBZ0Bhm5IsakncVp1ngQ'
SID = 87

r = requests.post(f'{BASE}/api/v1/auth/login',
    json={'phone': '0900000000', 'password': 'admin123'}, verify=False, timeout=15)
rh = {'Authorization': 'Bearer ' + r.json()['token']}

r2 = requests.post(
    f'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}',
    json={'email': 'migration@returntohealthtw.com', 'password': 'MigrateEEG@2026', 'returnSecureToken': True},
    verify=False, timeout=15)
fh = {'Authorization': 'Bearer ' + r2.json()['idToken']}

# ── PostgreSQL ──────────────────────────────────────────────
print(f'=== PostgreSQL session {SID} ===')
r3 = requests.get(f'{BASE}/api/v1/sessions/{SID}/captures', headers=rh, verify=False, timeout=15)
if r3.status_code == 200:
    cd   = r3.json()
    caps = cd.get('captures', cd) if isinstance(cd, dict) else cd
    total = cd.get('total', len(caps)) if isinstance(cd, dict) else len(caps)
    print(f'captures 總數 : {total} 筆逐秒腦波')
    if caps:
        c = caps[0]
        print(f'第 1 筆 (seq={c.get("seq_num")}):')
        print(f'  attention={c.get("attention")}, meditation={c.get("meditation")}')
        print(f'  delta={c.get("delta")}, theta={c.get("theta")}')
        print(f'  low_alpha={c.get("low_alpha")}, high_alpha={c.get("high_alpha")}')
        print(f'  low_beta={c.get("low_beta")},  high_beta={c.get("high_beta")}')
        print(f'  low_gamma={c.get("low_gamma")}, high_gamma={c.get("high_gamma")}')
    if total > 1:
        c2 = caps[-1]
        print(f'最後1筆 (seq={c2.get("seq_num")}): attn={c2.get("attention")}, medi={c2.get("meditation")}')
else:
    print(f'查詢失敗: {r3.status_code} {r3.text[:200]}')

# ── Firebase ────────────────────────────────────────────────
print()
print(f'=== Firebase session (railway_id={SID}) ===')
r4 = requests.get(f'{FIREBASE_API_BASE}/sessions?limit=300', headers=fh, verify=False, timeout=20)
fb_list = r4.json().get('sessions', [])
fb_found = None
for s in fb_list:
    if not isinstance(s, dict): continue
    meta = s.get('metadata') or {}
    if meta.get('railway_session_id') == SID:
        fb_found = s
        break

if fb_found:
    print(f'Firebase ID  : {fb_found.get("id")}')
    print(f'status       : {fb_found.get("status")}')
    print(f'durationSec  : {fb_found.get("durationSec")} 筆腦波')
    print(f'受測者       : {(fb_found.get("metadata") or {}).get("subject_name")}')
else:
    print('未在 Firebase 找到')

# ── 比對 ────────────────────────────────────────────────────
print()
pg_n = total if r3.status_code == 200 else 0
fb_n = fb_found.get('durationSec', 0) if fb_found else 0
match = abs((pg_n or 0) - (fb_n or 0)) <= 5
print(f'PostgreSQL captures : {pg_n} 筆')
print(f'Firebase durationSec: {fb_n} 筆')
print(f'兩庫一致性          : {"✅ 一致" if match else "⚠️  有差異"}')
