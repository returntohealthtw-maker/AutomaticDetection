#!/usr/bin/env python3
"""
補同步 session 73-83 的真實受測者資料到 Firebase。
排除純測試資料（Firebase雙寫測試、受測者、診斷測試等）。
"""
import sys, time, asyncio, urllib3, requests, json
urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8')

RAILWAY_BASE      = 'https://backend-production-2da61.up.railway.app'
FIREBASE_API_BASE = 'https://asia-east1-gen-lang-client-0435688289.cloudfunctions.net/api/api'
FIREBASE_API_KEY  = 'AIzaSyBc-ZEcT8fvyn-dBZ0Bhm5IsakncVp1ngQ'
RAILWAY_PHONE     = '0900000000'
RAILWAY_PASSWORD  = 'admin123'
FIREBASE_EMAIL    = 'migration@returntohealthtw.com'
FIREBASE_PASSWORD = 'MigrateEEG@2026'

# 跳過測試/除錯受測者名稱
SKIP_NAMES = {
    'Firebase雙寫測試', '受測者', '端對端測試者', '診斷測試',
    'debug', 'debug-sk', 'debug-bt', 'Firebase同步測試',
    'test', 'Test', 'TEST', '測試模式', '陳小明',
}

TARGET_SESSIONS = list(range(73, 87))  # 73–86

print("=" * 70)
print("補同步 session 73-86 到 Firebase")
print("=" * 70)

# --- Railway 登入 ---
print("\n【1】登入 Railway...")
r = requests.post(f'{RAILWAY_BASE}/api/v1/auth/login',
    json={'phone': RAILWAY_PHONE, 'password': RAILWAY_PASSWORD},
    verify=False, timeout=15)
railway_token = r.json()['token']
rh = {'Authorization': f'Bearer {railway_token}'}
print("✅ Railway 登入成功")

# --- Firebase 登入 ---
print("\n【2】登入 Firebase...")
r = requests.post(
    f'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}',
    json={'email': FIREBASE_EMAIL, 'password': FIREBASE_PASSWORD, 'returnSecureToken': True},
    verify=False, timeout=15)
firebase_token = r.json()['idToken']
fh = {'Authorization': f'Bearer {firebase_token}'}
print("✅ Firebase 登入成功")

# --- 查詢 Firebase 已有的 session ---
print("\n【3】查詢 Firebase 已有的 railway_session_id...")
r = requests.get(f'{FIREBASE_API_BASE}/sessions?limit=300', headers=fh, verify=False, timeout=20)
data = r.json()
fb_sessions = data.get('sessions', data) if isinstance(data, dict) else data
already_synced = set()
for s in fb_sessions:
    if isinstance(s, dict):
        meta = s.get('metadata') or {}
        rid = meta.get('railway_session_id')
        if rid and rid > 0:
            already_synced.add(int(rid))
print(f"Firebase 已有 railway_session_id: {sorted(already_synced & set(TARGET_SESSIONS))}")

# --- 取得報告列表（含受測者名稱）---
print("\n【4】取得 Railway 報告列表...")
r = requests.get(f'{RAILWAY_BASE}/api/v1/reports/list?limit=200', headers=rh, verify=False, timeout=15)
rpts = r.json().get('reports', [])
session_info = {}  # session_id -> {subject_name, report_type, ...}
for rpt in rpts:
    sid = rpt.get('session_id')
    if sid and sid in TARGET_SESSIONS:
        session_info[sid] = rpt

print(f"找到 {len(session_info)} 個目標 session 的報告資訊")

# --- 匯入 firebase_sync ---
import os, sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('FIREBASE_API_KEY', FIREBASE_API_KEY)
os.environ.setdefault('FIREBASE_SYNC_EMAIL', FIREBASE_EMAIL)
os.environ.setdefault('FIREBASE_SYNC_PASSWORD', FIREBASE_PASSWORD)

from app.services.firebase_sync import sync_captures_to_firebase
from app.core.database import SessionLocal
from app.core import models

db = SessionLocal()

# --- 同步每個 session ---
print("\n【5】開始同步...")
results = {'success': [], 'skip_test': [], 'skip_exists': [], 'skip_no_captures': [], 'failed': []}

for sid in TARGET_SESSIONS:
    info = session_info.get(sid, {})
    subject_name = info.get('subject_name', '')

    # 跳過測試資料
    if not subject_name or subject_name in SKIP_NAMES:
        print(f"  session {sid}: 跳過（測試資料: {subject_name!r}）")
        results['skip_test'].append(sid)
        continue

    # 已在 Firebase 中
    if sid in already_synced:
        print(f"  session {sid}: 已在 Firebase，跳過（{subject_name}）")
        results['skip_exists'].append(sid)
        continue

    # 取得 captures
    sess_obj = db.query(models.Session).filter(models.Session.session_id == sid).first()
    if not sess_obj:
        print(f"  session {sid}: PostgreSQL 中不存在")
        results['failed'].append(sid)
        continue

    captures = db.query(models.EegCapture).filter(
        models.EegCapture.session_id == sid
    ).order_by(models.EegCapture.seq_num).all()

    if not captures:
        print(f"  session {sid}: 無 captures，跳過（{subject_name}）")
        results['skip_no_captures'].append(sid)
        continue

    print(f"  session {sid}: 同步 {len(captures)} 筆 captures（{subject_name}）...", end='', flush=True)
    try:
        ok = asyncio.run(sync_captures_to_firebase(
            subject_name=subject_name,
            session_id=sid,
            captures=captures,
        ))
        if ok:
            print(" ✅")
            results['success'].append(sid)
        else:
            print(" ❌ (sync returned False)")
            results['failed'].append(sid)
    except Exception as e:
        print(f" ❌ ({e})")
        results['failed'].append(sid)

    time.sleep(0.5)

db.close()

# --- 總結 ---
print("\n" + "=" * 70)
print("補同步結果")
print("=" * 70)
print(f"✅ 成功同步: {results['success']}")
print(f"⏭  已存在跳過: {results['skip_exists']}")
print(f"🧪 測試資料跳過: {results['skip_test']}")
print(f"⚠️  無 captures: {results['skip_no_captures']}")
print(f"❌ 失敗: {results['failed']}")
print("=" * 70)
