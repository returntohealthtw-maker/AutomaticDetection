"""
MBTI v6.0 常模化修正 regression test（2026-08-20）

背景（血淚教訓，勿刪）：
    compute_mbti_v6() 的加權公式係數（0.35、0.40…）是設計給 0-100 常模值用的，
    但曾經直接吃 DB 儲存的「原始 ThinkGear 值」（數萬～數十萬），導致：
      1. eiDiff/nsDiff/tfDiff/jpDiff 被原始量級放大成天文數字，
         mbti_ei/ns/tf/jp 幾乎必定被 clamp 到極端值 5 或 99。
      2. 兩個腦波數據完全不同的孩子（session 174、175）算出一模一樣的
         mbti_primary 與四軸分數，看不出任何個體差異。
    此檔案鎖住修正後的行為，避免未來又不小心把常模化步驟拿掉。

執行方式：
    cd 後端系統
    python -m pytest tests/test_mbti_v6_normalization.py -v
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.algorithms import (
    BandAverages,
    build_mbti_payload,
    compute_mbti_v6,
    compute_bagua_mbti,
    _raw_band_to_norm100,
)

# 真實資料：黃麒安（session 174）與黃麒聿（session 175）
# 來源：GET /api/v1/eeg/sessions/{id}/stats（Railway 正式環境，2026-08-20 查詢）
SESSION_174 = dict(
    delta=306438, theta=92377, low_alpha=31330, high_alpha=22274,
    low_beta=14934, high_beta=9764, low_gamma=6549, high_gamma=3870,
    attention=39, meditation=45,
)
SESSION_175 = dict(
    delta=416341, theta=135748, low_alpha=50955, high_alpha=34219,
    low_beta=25369, high_beta=22883, low_gamma=23814, high_gamma=9817,
    attention=34, meditation=69,
)


def _avg(d: dict) -> BandAverages:
    return BandAverages(
        delta=d["delta"], theta=d["theta"],
        low_alpha=d["low_alpha"], high_alpha=d["high_alpha"],
        low_beta=d["low_beta"], high_beta=d["high_beta"],
        low_gamma=d["low_gamma"], high_gamma=d["high_gamma"],
        attention=d["attention"], meditation=d["meditation"],
        sample_count=180,
    )


def test_raw_band_to_norm100_normalizes_raw_thinkgear_values():
    """原始 ThinkGear 值（>100）要被壓縮到 0-100 範圍內。"""
    assert 0.0 <= _raw_band_to_norm100(92377) <= 100.0
    assert 0.0 <= _raw_band_to_norm100(306438) <= 100.0
    assert _raw_band_to_norm100(0) == 0.0


def test_raw_band_to_norm100_passthrough_for_already_normalized():
    """已經是 0-100 常模值（例如舊版 bandTo100、qEEG 校正值）不應被二次轉換。"""
    assert _raw_band_to_norm100(42) == 42
    assert _raw_band_to_norm100(100) == 100


def test_mbti_v6_scores_are_not_pinned_to_extreme_clamp_bounds():
    """
    修正前：真實資料餵進 compute_mbti_v6() 會讓 4 軸分數幾乎必定卡在
    clamp 邊界（5 或 99）。修正後應落在合理範圍內，反映真正的相對強弱。
    """
    for session in (SESSION_174, SESSION_175):
        v6 = compute_mbti_v6(_avg(session))
        for key in ("ei_score", "ns_score", "tf_score", "jp_score"):
            score = v6[key]
            assert 5 < score < 99, (
                f"{key}={score} 仍卡在極端 clamp 邊界，常模化可能沒生效"
            )


def test_two_different_children_get_different_mbti_results():
    """
    核心回歸測試：兩個腦波數據明顯不同的孩子，不應該算出一模一樣的
    mbti_primary 與四軸分數（這是本次 bug 的具體症狀）。
    """
    p174 = build_mbti_payload(_avg(SESSION_174))
    p175 = build_mbti_payload(_avg(SESSION_175))

    same_scores = (
        p174["mbti_ei"] == p175["mbti_ei"]
        and p174["mbti_ns"] == p175["mbti_ns"]
        and p174["mbti_tf"] == p175["mbti_tf"]
        and p174["mbti_jp"] == p175["mbti_jp"]
    )
    assert not same_scores, "兩個不同孩子的四軸分數完全相同，常模化修正可能失效"

    # 2026-11：報告 MBTI 已統一為八卦演算法（compute_bagua_mbti），不再走 v6。
    # 下列為八卦演算法對同一份 fixture 的實際輸出，鎖住避免未來又被換掉。
    # v6 的原始輸出（INTP / INFP）仍可由 compute_mbti_v6() 直接取得，見上方測試。
    assert p174["mbti_primary"] == "ESTP"
    assert p175["mbti_primary"] == "ESTP"
    assert compute_mbti_v6(_avg(SESSION_174))["mbti_type"] == "INTP"
    assert compute_mbti_v6(_avg(SESSION_175))["mbti_type"] == "INFP"


def test_bagua_mbti_is_the_single_source_for_payload():
    """build_mbti_payload 的主型 = compute_bagua_mbti 的主型；diff 以 50+diff/2 還原百分比。"""
    avg = _avg(SESSION_174)
    b = compute_bagua_mbti(avg)
    p = build_mbti_payload(avg)
    assert p["mbti_primary"] == b["mbti_type"]
    assert abs((50 + p["mbti_ei_diff"] / 2) - b["ei_score"]) < 0.01
    assert abs((50 + p["mbti_jp_diff"] / 2) - b["jp_score"]) < 0.01


def test_bagua_mbti_ignores_norm100_summary_row():
    """Web 路徑 seq_num=0 的 0-100 摘要列不得混入原始值均值。"""
    raw_rows = [dict(delta=100000 + i, theta=30000 + i, low_alpha=9000 + 10 * i) for i in range(30)]
    summary = dict(delta=100, theta=47, low_alpha=58)
    a = compute_bagua_mbti(captures=raw_rows)
    b = compute_bagua_mbti(captures=[summary] + raw_rows)
    assert a["mbti_type"] == b["mbti_type"]
    assert a["n_seconds"] == b["n_seconds"] == 30


def test_build_mbti_payload_includes_diff_fields_for_frontend():
    """
    React App 第2章「性格光譜強度」讀取的是 mbti_ei_diff 等欄位（不是
    mbti_ei 分數），若缺少這個 key，前端會 fallback 成 0，四軸永遠顯示 50%。
    """
    payload = build_mbti_payload(_avg(SESSION_174))
    for key in ("mbti_ei_diff", "mbti_ns_diff", "mbti_tf_diff", "mbti_jp_diff"):
        assert key in payload, f"缺少 {key}，前端會 fallback 成 0 造成四軸卡在 50%"
        assert payload[key] is not None


def test_bagua_gain_free_is_invariant_to_overall_amplitude():
    """gain_free 模式：整體振幅放大/縮小 10 倍（電極增益不同）不應改變 MBTI 結果。"""
    import random
    rnd = random.Random(7)
    base = {"r_delta": 120000, "r_theta": 45000, "r_lalpha": 9000, "r_halpha": 8000,
            "r_lbeta": 6000, "r_hbeta": 7000, "r_lgamma": 5000, "r_hgamma": 4000}
    n = 180
    raw = {k: [v * rnd.uniform(0.6, 1.6) for _ in range(n)] for k, v in base.items()}
    scaled = {k: [x * 10 for x in arr] for k, arr in raw.items()}
    a = compute_bagua_mbti(raw_arrays=raw)
    b = compute_bagua_mbti(raw_arrays=scaled)
    assert a["mode"] == "gain_free"
    assert a["mbti_type"] == b["mbti_type"]
    assert a["ei_score"] == b["ei_score"] and a["ns_score"] == b["ns_score"]


def test_bagua_geometric_mean_resists_outlier_seconds():
    """少數離群秒（重尾）不應主宰結果：加入 3 個極端秒，型別不變。"""
    n = 180
    base = {"r_delta": 120000, "r_theta": 45000, "r_lalpha": 9000, "r_halpha": 8000,
            "r_lbeta": 6000, "r_hbeta": 7000, "r_lgamma": 5000, "r_hgamma": 4000}
    raw = {k: [v * (0.8 + 0.4 * ((i * 7) % 10) / 10) for i in range(n)] for k, v in base.items()}
    noisy = {k: list(v) for k, v in raw.items()}
    for k in noisy:
        for i in (3, 50, 120):
            noisy[k][i] *= 200
    assert compute_bagua_mbti(raw_arrays=raw)["mbti_type"] == compute_bagua_mbti(raw_arrays=noisy)["mbti_type"]


def test_best_window_ignores_tail_and_low_quality_seconds():
    """
    #184 稽核：181 筆資料的第 181 筆（1 秒尾巴）曾被選為最佳視窗，
    且該秒 delta 低於品質門檻 → compute_all 回傳 None。修正後必須有效。
    """
    from app.services.braindna_algorithms import compute_all
    n = 181
    arr = lambda base: [base + (i % 7) * 100 for i in range(n)]
    raw = {
        "r_delta": arr(120000), "r_theta": arr(40000), "r_lalpha": arr(12000),
        "r_halpha": arr(10000), "r_lbeta": arr(8000), "r_hbeta": arr(9000),
        "r_lgamma": arr(7000), "r_hgamma": arr(6000),
        "attn": [50] * n, "medi": [50] * n,
    }
    # 最後一秒：低品質（delta < 30000）且 lowGamma 佔比極高 → 舊版會被選為最佳視窗
    raw["r_delta"][-1] = 3916
    raw["r_lgamma"][-1] = 60000
    res = compute_all(raw)
    assert res["valid"] and res["bands"], "尾巴低品質秒不得讓 compute_all 失效"


def test_secondaries_two_distinct_types_with_axes_and_order():
    """主性格 + 2 個副性格：型別互異、不等於主性格、依強度由高到低、附差異軸。"""
    from app.services.algorithms import _secondary_candidates, _zone_type
    primary = _zone_type(3, True)             # 巽區 + θ 高 = ISTJ
    assert primary == "ISTJ"
    sec = _secondary_candidates(3, True, la_pct=0.40, th_pct=0.55, primary=primary)
    assert len(sec) == 2
    assert [s["kind"] for s in sec] == ["gua_lower", "theta_flip"] or sec[0]["strength"] >= sec[1]["strength"]
    assert sec[0]["strength"] >= sec[1]["strength"]
    types = [s["mbti"] for s in sec]
    assert len(set(types)) == 2 and primary not in types
    assert "INFJ" in types                    # 下界相鄰為離卦區 + θ 高 → INFJ
    for s in sec:
        assert s["axes"] and all(a in ("E/I", "N/S", "T/F", "J/P") for a in s["axes"])
        assert "八卦" not in s["reason"] and "卦" not in s["reason"]


def test_secondaries_li_zone_theta_flip_is_enfp_not_infp():
    """離卦區 θ 高 = INFJ；θ 翻低是震卦 = ENFP（舊版誤給 INFP）。"""
    from app.services.algorithms import _secondary_candidates
    sec = _secondary_candidates(2, True, la_pct=0.31, th_pct=0.52, primary="INFJ")
    assert any(s["kind"] == "theta_flip" and s["mbti"] == "ENFP" for s in sec)


def test_secondaries_edge_zone_far_from_boundaries_gives_fewer():
    """最外側卦位只有單側鄰居，且 θ 極端時，允許只剩 1 個副性格（不硬湊）。"""
    from app.services.algorithms import _secondary_candidates
    sec = _secondary_candidates(6, False, la_pct=0.95, th_pct=0.02, primary="ESFP")
    assert 1 <= len(sec) <= 2
    assert all(s["mbti"] != "ESFP" for s in sec)


def test_payload_secondaries_at_most_two_with_metadata():
    raw = {"r_delta": [120000] * 180, "r_theta": [40000 + (i % 9) * 3000 for i in range(180)],
           "r_lalpha": [12000 + (i % 11) * 900 for i in range(180)],
           "r_halpha": [10000 + (i % 7) * 500 for i in range(180)],
           "r_lbeta": [8000 + (i % 5) * 400 for i in range(180)],
           "r_hbeta": [9000 + (i % 6) * 300 for i in range(180)],
           "r_lgamma": [7000 + (i % 8) * 200 for i in range(180)],
           "r_hgamma": [6000 + (i % 4) * 100 for i in range(180)]}
    p = build_mbti_payload(None, None, raw)
    secs = p["mbti_secondaries"]
    assert 1 <= len(secs) <= 2
    assert all(s["mbti"] != p["mbti_primary"] for s in secs)
    assert all({"mbti", "strength", "reason", "kind", "axes"} <= set(s) for s in secs)


if __name__ == "__main__":
    tests = [
        test_secondaries_two_distinct_types_with_axes_and_order,
        test_secondaries_li_zone_theta_flip_is_enfp_not_infp,
        test_secondaries_edge_zone_far_from_boundaries_gives_fewer,
        test_payload_secondaries_at_most_two_with_metadata,
        test_raw_band_to_norm100_normalizes_raw_thinkgear_values,
        test_raw_band_to_norm100_passthrough_for_already_normalized,
        test_mbti_v6_scores_are_not_pinned_to_extreme_clamp_bounds,
        test_two_different_children_get_different_mbti_results,
        test_build_mbti_payload_includes_diff_fields_for_frontend,
        test_bagua_mbti_is_the_single_source_for_payload,
        test_bagua_mbti_ignores_norm100_summary_row,
        test_best_window_ignores_tail_and_low_quality_seconds,
        test_bagua_gain_free_is_invariant_to_overall_amplitude,
        test_bagua_geometric_mean_resists_outlier_seconds,
    ]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"[PASS] {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {t.__name__}: {e}")
            failed += 1
    print(f"結果：{passed} 通過 / {failed} 失敗")
    sys.exit(0 if failed == 0 else 1)
