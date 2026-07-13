"""
recalc_all_braindna.py
~~~~~~~~~~~~~~~~~~~~~~
重新用最新 _PROP_RANGE 計算所有 sessions 的 BrainDNA 結果，
並直接更新 PostgreSQL sessions 表的儲存值。

用法（在 Railway backend Console 執行）：
    python recalc_all_braindna.py
    python recalc_all_braindna.py --dry-run   # 只列印結果，不寫入
    python recalc_all_braindna.py --session 104  # 只算一筆
"""
from __future__ import annotations
import argparse, os, sys, time
import sqlalchemy as sa

# ── 讀取環境 ─────────────────────────────────────────────────────────────────
DB_URL = os.getenv("DATABASE_URL", "")
if not DB_URL:
    sys.exit("[ERROR] DATABASE_URL 未設定")

# ── 把 app 目錄加入 path，讓 import 能正常運作 ────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from services.braindna_algorithms import (
    compute_all, CAP, _PROP_RANGE, _clamp, _proportion_range,
    MIN_DELTA_QUALITY, RAW_KEYS,
)

ATTR_MAP = {
    "r_delta":  "delta",     "r_theta":  "theta",
    "r_lalpha": "low_alpha", "r_halpha": "high_alpha",
    "r_lbeta":  "low_beta",  "r_hbeta":  "high_beta",
    "r_lgamma": "low_gamma", "r_hgamma": "high_gamma",
}

engine = sa.create_engine(DB_URL, pool_pre_ping=True)


def get_sessions(only_sid=0):
    with engine.connect() as conn:
        if only_sid:
            q = "SELECT session_id, report_type FROM sessions WHERE session_id = :sid"
            rows = conn.execute(sa.text(q), {"sid": only_sid}).mappings().all()
        else:
            q = "SELECT session_id, report_type FROM sessions ORDER BY session_id DESC"
            rows = conn.execute(sa.text(q)).mappings().all()
    return [dict(r) for r in rows]


def get_captures(sid):
    with engine.connect() as conn:
        q = """SELECT delta, theta, low_alpha, high_alpha,
                      low_beta, high_beta, low_gamma, high_gamma,
                      attention, meditation
               FROM eeg_captures
               WHERE session_id = :sid AND is_baseline = false
               ORDER BY seq_num ASC"""
        rows = conn.execute(sa.text(q), {"sid": sid}).mappings().all()
        if not rows:
            q2 = """SELECT delta, theta, low_alpha, high_alpha,
                           low_beta, high_beta, low_gamma, high_gamma,
                           attention, meditation
                    FROM eeg_captures
                    WHERE session_id = :sid
                    ORDER BY seq_num ASC"""
            rows = conn.execute(sa.text(q2), {"sid": sid}).mappings().all()
    return [dict(r) for r in rows]


def build_raw_arrays(caps):
    """把 eeg_captures 轉成 compute_all 需要的 raw_arrays 格式"""
    return {
        "r_delta":  [float(c.get("delta",      0) or 0) for c in caps],
        "r_theta":  [float(c.get("theta",      0) or 0) for c in caps],
        "r_lalpha": [float(c.get("low_alpha",  0) or 0) for c in caps],
        "r_halpha": [float(c.get("high_alpha", 0) or 0) for c in caps],
        "r_lbeta":  [float(c.get("low_beta",   0) or 0) for c in caps],
        "r_hbeta":  [float(c.get("high_beta",  0) or 0) for c in caps],
        "r_lgamma": [float(c.get("low_gamma",  0) or 0) for c in caps],
        "r_hgamma": [float(c.get("high_gamma", 0) or 0) for c in caps],
        "attn":     [float(c.get("attention",  0) or 0) for c in caps],
        "medi":     [float(c.get("meditation", 0) or 0) for c in caps],
    }


def calc_band_scores(caps):
    """與後台 monitor.py / report_gen.py 完全相同的逐秒計算"""
    if not caps:
        return {}

    _delta_max = max((float(c.get("delta", 0) or 0) for c in caps), default=0)
    _is_raw = _delta_max > 1000

    if _is_raw:
        good = [c for c in caps if (float(c.get("delta", 0) or 0)) >= MIN_DELTA_QUALITY]
        if len(good) < 15:
            good = caps
    else:
        good = caps

    prop_sum = {k: 0.0 for k in RAW_KEYS}
    n = 0
    for c in good:
        uncapped_total = sum(float(c.get(ATTR_MAP[k], 0) or 0) for k in RAW_KEYS)
        if uncapped_total == 0:
            continue
        for k in RAW_KEYS:
            prop_sum[k] += _clamp(float(c.get(ATTR_MAP[k], 0) or 0), CAP[k]) / uncapped_total
        n += 1

    if n == 0:
        return {}

    scores = {}
    for k in RAW_KEYS:
        name = ATTR_MAP[k].replace("_", "").replace("low", "low_").replace("high", "high_")
        scores[ATTR_MAP[k]] = round(_proportion_range(prop_sum[k] / n, *_PROP_RANGE[k]) * 100)
    return scores


_COLOR_STR = {0: "orange", 1: "green", 2: "blue", 3: "yellow"}


def update_session(sid, result, band_scores, dry_run):
    if dry_run:
        return
    with engine.begin() as conn:
        conn.execute(sa.text("""
            UPDATE sessions SET
                mind_stress   = :stress,
                mind_balance  = :balance,
                mind_energy   = :energy,
                mind_color    = :color,
                overall_score = :overall,
                mbti          = :mbti,
                bagua         = :bagua
            WHERE session_id  = :sid
        """), {
            "stress":  result.get("stress"),
            "balance": result.get("balance"),
            "energy":  result.get("energy"),
            "color":   result.get("color"),
            "overall": result.get("overall_score"),
            "mbti":    result.get("mbti"),
            "bagua":   result.get("bagua"),
            "sid":     sid,
        })


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run",  action="store_true")
    parser.add_argument("--session",  type=int, default=0)
    args = parser.parse_args()

    sessions = get_sessions(only_sid=args.session)
    print(f"{'='*60}")
    print(f"BrainDNA 重新計算  sessions={len(sessions)}  dry_run={args.dry_run}")
    print(f"{'='*60}\n")

    ok = fail = skip = 0

    for row in sessions:
        sid       = row["session_id"]
        rtype     = row.get("report_type") or "adult"
        is_child  = rtype.lower().startswith("child")

        caps = get_captures(sid)
        if len(caps) < 5:
            print(f"  session={sid}  ⏭ 資料不足（{len(caps)} 筆），跳過")
            skip += 1
            continue

        try:
            raw_arrays = build_raw_arrays(caps)
            result     = compute_all(raw_arrays, is_child=is_child)

            if not result.get("valid"):
                print(f"  session={sid}  ⏭ BrainDNA 無效（{result.get('input_scale')}），跳過")
                skip += 1
                continue

            band_scores = calc_band_scores(caps)

            color_str = _COLOR_STR.get(result.get("color"), "orange")

            print(f"  session={sid} ({rtype})"
                  f"  stress={result.get('stress')}  balance={result.get('balance')}"
                  f"  energy={result.get('energy')}  color={color_str}"
                  f"  overall={result.get('overall_score')}  mbti={result.get('mbti')}")
            print(f"    bands: δ={band_scores.get('delta')} θ={band_scores.get('theta')}"
                  f" Lα={band_scores.get('low_alpha')} Hα={band_scores.get('high_alpha')}"
                  f" Lβ={band_scores.get('low_beta')}  Hβ={band_scores.get('high_beta')}"
                  f" Lγ={band_scores.get('low_gamma')} Hγ={band_scores.get('high_gamma')}")

            update_session(sid, result, band_scores, args.dry_run)
            print(f"    {'[DRY] 未寫入' if args.dry_run else '✅ 已更新 DB'}")
            ok += 1

        except Exception as e:
            print(f"  session={sid}  ❌ 例外: {e}")
            fail += 1

        time.sleep(0.05)

    print(f"\n{'='*60}")
    print(f"完成：成功 {ok}  跳過 {skip}  失敗 {fail}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
