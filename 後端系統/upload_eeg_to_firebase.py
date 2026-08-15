"""
補傳 EEG 逐秒原始擷取資料到已建立的 Firebase sessions
每個 session 上傳所有每秒資料（~180 筆），而非平均值

資料來源：Railway PostgreSQL → GET /api/v1/sessions/{id}/captures
目標：Firebase Cloud Functions POST /eeg/batch
"""
import sys, io, json, math, requests, urllib3, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
urllib3.disable_warnings()

FIREBASE_API_KEY  = "AIzaSyBc-ZEcT8fvyn-dBZ0Bhm5IsakncVp1ngQ"
FIREBASE_EMAIL    = "migration@returntohealthtw.com"
FIREBASE_PASSWORD = "MigrateEEG@2026"
CF_BASE      = "https://asia-east1-gen-lang-client-0435688289.cloudfunctions.net/api/api"
RAILWAY_BASE = "https://backend-production-2da61.up.railway.app"

BATCH_SIZE = 50  # Firebase 每次最多接收幾筆（避免請求過大）

# ── 登入 Firebase ──────────────────────────────────────────────────────────────
r = requests.post(
    f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}",
    json={"email": FIREBASE_EMAIL, "password": FIREBASE_PASSWORD, "returnSecureToken": True},
    verify=False, timeout=15)
token = r.json()["idToken"]
fb_hdrs = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
print("✅ Firebase 登入成功")

# ── 登入 Railway ───────────────────────────────────────────────────────────────
rs = requests.Session(); rs.verify = False
rw_tok = rs.post(f"{RAILWAY_BASE}/api/v1/auth/login",
                 json={"phone": "0900000000", "password": "admin123"}, timeout=15).json().get("token", "")
rs.headers["Authorization"] = f"Bearer {rw_tok}"
print("✅ Railway 登入成功")

# ── 讀 migration_report.json 取得 session map ──────────────────────────────────
with open("migration_report.json", encoding="utf-8") as f:
    report = json.load(f)

session_map = {}
for src in report.get("sources", []):
    if "Railway" in src["label"]:
        session_map = src.get("session_map", {})
        break

print(f"📋 已找到 {len(session_map)} 個 Railway→Firebase session 對應\n")


def raw_to_ratio(val, total):
    """原始功率值轉成百分比"""
    return round(float(val) / total * 100, 4) if total > 0 else 0.0


def build_features(caps):
    """把 captures 列表轉成 Firebase eeg/batch 所需的 features 陣列"""
    features = []
    for c in caps:
        d   = float(c.get("delta", 0) or 0)
        th  = float(c.get("theta", 0) or 0)
        la  = float(c.get("low_alpha", 0) or 0)
        ha  = float(c.get("high_alpha", 0) or 0)
        lb  = float(c.get("low_beta", 0) or 0)
        hb  = float(c.get("high_beta", 0) or 0)
        lg  = float(c.get("low_gamma", 0) or 0)
        hg  = float(c.get("high_gamma", 0) or 0)
        total = d + th + la + ha + lb + hb + lg + hg or 1.0

        # captured_at 是毫秒時間戳
        ts_ms = c.get("captured_at") or 0
        try:
            ts_iso = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(ts_ms / 1000))
        except Exception:
            ts_iso = "2026-01-01T00:00:00.000Z"

        features.append({
            "timestamp":       ts_iso,
            "windowSec":       1.0,
            "deltaRatio":      raw_to_ratio(d, total),
            "thetaRatio":      raw_to_ratio(th, total),
            "alphaRatio":      raw_to_ratio(la + ha, total),
            "betaRatio":       raw_to_ratio(lb + hb, total),
            "gammaRatio":      raw_to_ratio(lg + hg, total),
            "lowAlphaRatio":   raw_to_ratio(la, total),
            "highAlphaRatio":  raw_to_ratio(ha, total),
            "lowBetaRatio":    raw_to_ratio(lb, total),
            "highBetaRatio":   raw_to_ratio(hb, total),
            "lowGammaRatio":   raw_to_ratio(lg, total),
            "highGammaRatio":  raw_to_ratio(hg, total),
            "attentionIndex":  float(c.get("attention", 0) or 0),
            "relaxationIndex": float(c.get("meditation", 0) or 0),
            "signalQuality":   max(0.0, round((100 - float(c.get("good_signal", 200) or 200)) / 100 * 100, 1)),
            "isBaseline":      bool(c.get("is_baseline", 0)),
            "seqNum":          int(c.get("seq_num", 0) or 0),
        })
    return features


ok_sessions = 0; fail_sessions = 0; total_feats = 0

for rw_sid_str, fb_sid in session_map.items():
    rw_sid = int(rw_sid_str)

    # 取逐秒原始資料
    caps_r = rs.get(f"{RAILWAY_BASE}/api/v1/sessions/{rw_sid}/captures", timeout=30)
    if caps_r.status_code != 200:
        print(f"  ⚠ session {rw_sid}: captures API 失敗 {caps_r.status_code}")
        fail_sessions += 1
        continue

    caps_data = caps_r.json()
    caps = caps_data.get("captures", [])
    n = len(caps)

    if n == 0:
        print(f"  ⚠ session {rw_sid}: 無逐秒資料，跳過")
        fail_sessions += 1
        continue

    features = build_features(caps)

    # 分批上傳（每批 BATCH_SIZE 筆）
    session_ok = True
    for i in range(0, len(features), BATCH_SIZE):
        batch = features[i:i + BATCH_SIZE]
        r2 = requests.post(
            f"{CF_BASE}/eeg/batch",
            json={"sessionId": fb_sid, "features": batch},
            headers=fb_hdrs, verify=False, timeout=30
        )
        if r2.status_code not in (200, 201):
            print(f"  ❌ session {rw_sid} 批次 {i//BATCH_SIZE+1}: {r2.status_code} {r2.text[:100]}")
            session_ok = False
            break
        time.sleep(0.1)  # 避免打爆 Cloud Functions

    if session_ok:
        ok_sessions += 1
        total_feats += n
        print(f"  ✅ session {rw_sid} → {fb_sid[:8]}... 上傳 {n} 筆逐秒資料")
    else:
        fail_sessions += 1

print(f"\n完成！成功 {ok_sessions} 個 session（共 {total_feats} 筆），失敗 {fail_sessions} 個")
