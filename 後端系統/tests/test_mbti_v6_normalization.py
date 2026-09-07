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

    # 已知（修正後）正確結果，鎖住避免未來再度跑掉
    assert p174["mbti_primary"] == "INTP"
    assert p175["mbti_primary"] == "INFP"


def test_build_mbti_payload_includes_diff_fields_for_frontend():
    """
    React App 第2章「性格光譜強度」讀取的是 mbti_ei_diff 等欄位（不是
    mbti_ei 分數），若缺少這個 key，前端會 fallback 成 0，四軸永遠顯示 50%。
    """
    payload = build_mbti_payload(_avg(SESSION_174))
    for key in ("mbti_ei_diff", "mbti_ns_diff", "mbti_tf_diff", "mbti_jp_diff"):
        assert key in payload, f"缺少 {key}，前端會 fallback 成 0 造成四軸卡在 50%"
        assert payload[key] is not None


if __name__ == "__main__":
    tests = [
        test_raw_band_to_norm100_normalizes_raw_thinkgear_values,
        test_raw_band_to_norm100_passthrough_for_already_normalized,
        test_mbti_v6_scores_are_not_pinned_to_extreme_clamp_bounds,
        test_two_different_children_get_different_mbti_results,
        test_build_mbti_payload_includes_diff_fields_for_frontend,
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
