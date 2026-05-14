"""
BrainDNA 演算法移植版 sanity check

執行方式：
    cd 後端系統
    python -m pytest tests/test_algorithms.py -v

或直接：
    cd 後端系統
    python tests/test_algorithms.py
"""
import os
import random
import sys

# 讓 tests/ 能 import app.*
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.algorithms import (
    Bagua,
    Personality,
    MindColorAlgorithm,
    MindBalanceAlgorithm,
    MindEnergyAlgorithm,
    MindStressAlgorithm,
    generate_quick_mbti,
    generate_report,
)


# ─── 個別演算法 ───────────────────────────────────────────────────────────

def test_mind_color_returns_valid_index():
    color = MindColorAlgorithm.calc(
        highAlpha=10000, lowAlpha=12000,
        highBeta=8000,   lowBeta=7000,
        lowGamma=2000,   midGamma=1800,
    )
    assert color in (0, 1, 2, 3), f"無效顏色 index: {color}"


def test_mind_balance_in_range():
    attention  = [55, 60, 70, 65, 50, 45, 75, 80, 60, 55] * 3
    meditation = [50, 55, 60, 65, 50, 45, 60, 65, 55, 50] * 3
    score = MindBalanceAlgorithm.calc(attention, meditation)
    assert 0 <= score <= 100, f"分數超出 0~100: {score}"


def test_mind_energy_in_range():
    attention  = [55, 60, 70] * 10
    meditation = [50, 55, 60] * 10
    score = MindEnergyAlgorithm.calc(attention, meditation)
    assert 0 <= score <= 100


def test_mind_stress_in_range():
    mid_gamma = [3000, 3500, 4000, 2800, 3200] * 6
    low_alpha = [10000, 12000, 9000, 11000, 13000] * 6
    score = MindStressAlgorithm.calc(mid_gamma, low_alpha)
    assert 0 <= score <= 100


# ─── Bagua + MBTI ───────────────────────────────────────────────────────

def test_bagua_calcBagua_returns_valid():
    bagua = Bagua.calcBagua(MindColorAlgorithm.BLUE, lowAlphaMean=8000)
    assert bagua.id in ("qian", "dui", "li", "zhen", "xun", "kan", "gen", "kun")


def test_mbti_getPersonalityFromBagua_returns_valid():
    mbti = Personality.getPersonalityFromBagua(Bagua.QIAN, thetaMean=5000)
    valid = {p.id for p in [
        Personality.INTJ, Personality.INTP, Personality.ENTJ, Personality.ENTP,
        Personality.INFJ, Personality.INFP, Personality.ENFJ, Personality.ENFP,
        Personality.ISTJ, Personality.ISFJ, Personality.ESTJ, Personality.ESFJ,
        Personality.ISTP, Personality.ISFP, Personality.ESTP, Personality.ESFP,
    ]}
    assert mbti.id in valid


# ─── 高階 API ────────────────────────────────────────────────────────────

def test_quick_mbti_returns_complete_dict():
    result = generate_quick_mbti({
        "delta":     30000, "theta":     8000,
        "lowAlpha":  10000, "highAlpha": 9000,
        "lowBeta":   7000,  "highBeta":  6000,
        "lowGamma":  2000,  "midGamma":  1800,
    })
    assert "mbti" in result and len(result["mbti"]) == 4
    assert "mbti_zh" in result
    assert "bagua" in result
    assert "mind_color" in result
    print(f"\n   快速 MBTI 結果：{result['mbti']} ({result['mbti_zh']}) · "
          f"{result['mind_color_name']} · {result['bagua_name']}卦")


def test_full_report_returns_complete_structure(seed=42, seconds=90):
    rng = random.Random(seed)
    rows = []
    for i in range(seconds):
        rows.append({
            "ts":         float(i),
            "attention":  rng.randint(35, 80),
            "meditation": rng.randint(30, 75),
            "delta":      rng.randint(8000, 90000),
            "theta":      rng.randint(5000, 60000),
            "lowAlpha":   rng.randint(2000, 30000),
            "highAlpha":  rng.randint(2000, 30000),
            "lowBeta":    rng.randint(2000, 30000),
            "highBeta":   rng.randint(2000, 25000),
            "lowGamma":   rng.randint(500,   8000),
            "midGamma":   rng.randint(500,   8000),
        })
    report = generate_report(rows)

    expected_keys = [
        "overall_score", "score_comment", "therapy_suggestion",
        "mind_balance", "mind_energy", "mind_stress",
        "mind_color", "mind_color_name", "mind_color_character",
        "bagua", "bagua_name",
        "mbti", "mbti_zh", "mbti_en",
        "bands",
        "attention_percentage", "meditation_percentage",
        "quadrant",
    ]
    for k in expected_keys:
        assert k in report, f"缺少關鍵欄位：{k}"
    assert len(report["bands"]) == 8

    print(f"\n   完整報告：{report['mbti']} ({report['mbti_zh']}) · "
          f"{report['mind_color_name']} · {report['bagua_name']}卦")
    print(f"   平衡 {report['mind_balance']} | 能量 {report['mind_energy']} | "
          f"壓力 {report['mind_stress']} | 整體 {report['overall_score']}")
    print(f"   {report['mind_color_character']} - {report['mind_color_post']}")


def test_report_minimum_data_raises():
    try:
        generate_report([])
    except ValueError:
        return  # 預期會丟錯
    raise AssertionError("空資料應該丟 ValueError")


# ─── 直接執行（非 pytest） ──────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("BrainDNA 演算法移植版 sanity check")
    print("=" * 60)

    tests = [
        test_mind_color_returns_valid_index,
        test_mind_balance_in_range,
        test_mind_energy_in_range,
        test_mind_stress_in_range,
        test_bagua_calcBagua_returns_valid,
        test_mbti_getPersonalityFromBagua_returns_valid,
        test_quick_mbti_returns_complete_dict,
        test_full_report_returns_complete_structure,
        test_report_minimum_data_raises,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print(f"[PASS] {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {t.__name__}: {e}")
            failed += 1

    print("=" * 60)
    print(f"結果：{passed} 通過 / {failed} 失敗")
    print("=" * 60)
    sys.exit(0 if failed == 0 else 1)
