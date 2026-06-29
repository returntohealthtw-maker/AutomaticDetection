"""
composite_index_engine.py
──────────────────────────
複合心理功能指標計算模組

七項指標（依需求文件）：
  1. CCR  - Cognitive Control Ratio（認知控制比）
  2. EBI  - Energy Balance Index（能量平衡指數）
  3. REB  - Rational–Emotional Balance（理性情緒平衡）
  4. RRR  - Relaxation Recovery Ratio（放鬆恢復比）
  5. SLI  - Stress Load Index（壓力負荷指數）
  6. EDC  - Emotional Delay Coefficient（情緒延遲係數）
  7. ISI  - Interpersonal Synchrony Index（人際同步指數）

注意：SLI 與 EDC 為「風險型」指標，分數越高代表風險越高。
"""
from typing import Dict
from .score_transform import sigmoid_0_100
from .score_interpretation_rules import interpret_score, get_score_type


def _get(z_dict: Dict[str, dict], band: str) -> float:
    entry = z_dict.get(band)
    if entry is None:
        return 0.0
    return float(entry.get("z_score", 0.0))


def _make(z: float, indicator: str) -> dict:
    score_type = get_score_type(indicator)
    score = sigmoid_0_100(z)
    status = interpret_score(score, score_type)
    return {"score": score, "z_composite": round(z, 4), "status": status}


# ──────────────────────────────────────────────────────────────
# 1. CCR — Cognitive Control Ratio
# ──────────────────────────────────────────────────────────────

def calc_ccr(z: Dict[str, dict]) -> dict:
    """
    認知控制比：理性控制（beta）與直覺整合（theta）的平衡

    REB flag：balanced / rational_dominant / emotional_dominant
    """
    composite = (
        0.45 * _get(z, "low_beta")
        + 0.35 * _get(z, "high_beta")
        + 0.20 * _get(z, "theta")
    )
    return _make(composite, "ccr")


# ──────────────────────────────────────────────────────────────
# 2. EBI — Energy Balance Index
# ──────────────────────────────────────────────────────────────

def calc_ebi(z: Dict[str, dict]) -> dict:
    """
    能量平衡指數：回復力 vs 輸出負荷

    分數越高 → 能量回補越好
    分數越低 → 高輸出低恢復（burnout 風險）
    """
    output_load = (
        0.50 * _get(z, "high_beta")
        + 0.30 * _get(z, "theta")
        + 0.20 * _get(z, "low_beta")
    )
    recovery = (
        0.50 * (0.5 * _get(z, "high_alpha") + 0.5 * _get(z, "low_beta"))  # high_sigma approx
        + 0.50 * _get(z, "low_alpha")
    )
    composite = recovery - output_load
    return _make(composite, "ebi")


# ──────────────────────────────────────────────────────────────
# 3. REB — Rational–Emotional Balance
# ──────────────────────────────────────────────────────────────

def calc_reb(z: Dict[str, dict]) -> dict:
    """
    理性情緒平衡：正值 → 理性主導；負值 → 情感主導

    額外輸出 reb_flag
    """
    rational = (
        0.50 * _get(z, "low_beta")
        + 0.50 * _get(z, "high_beta")
    )
    emotional_sync = (
        0.50 * _get(z, "low_gamma")
        + 0.30 * _get(z, "high_gamma")
        + 0.20 * _get(z, "low_alpha")
    )
    composite = rational - emotional_sync
    result = _make(composite, "reb")

    # flag
    score = result["score"]
    if 40 <= score <= 60:
        result["reb_flag"] = "balanced"
    elif score > 60:
        result["reb_flag"] = "rational_dominant"
    else:
        result["reb_flag"] = "emotional_dominant"

    return result


# ──────────────────────────────────────────────────────────────
# 4. RRR — Relaxation Recovery Ratio
# ──────────────────────────────────────────────────────────────

def calc_rrr(z: Dict[str, dict]) -> dict:
    """放鬆恢復能力：alpha 主導，high_beta 過高扣分"""
    composite = (
        0.50 * _get(z, "low_alpha")
        + 0.30 * (0.5 * _get(z, "high_alpha") + 0.5 * _get(z, "low_beta"))  # high_sigma approx
        - 0.20 * max(_get(z, "high_beta"), 0)
    )
    return _make(composite, "rrr")


# ──────────────────────────────────────────────────────────────
# 5. SLI — Stress Load Index（風險型）
# ──────────────────────────────────────────────────────────────

def calc_sli(z: Dict[str, dict]) -> dict:
    """
    壓力負荷指數（風險型）：分數越高 = 壓力越大

    high_beta + theta 主導；低 alpha 與低 high_sigma 加重壓力
    """
    z_hs = 0.5 * _get(z, "high_alpha") + 0.5 * _get(z, "low_beta")
    composite = (
        0.45 * _get(z, "high_beta")
        + 0.25 * _get(z, "theta")
        - 0.20 * _get(z, "low_alpha")
        - 0.10 * z_hs
    )
    return _make(composite, "sli")


# ──────────────────────────────────────────────────────────────
# 6. EDC — Emotional Delay Coefficient（風險型）
# ──────────────────────────────────────────────────────────────

def calc_edc(z: Dict[str, dict]) -> dict:
    """
    情緒延遲係數（風險型）：分數越高 = 情緒處理越容易延遲

    theta 過高 + high_beta 激活 + low_gamma 不足 → 延遲增加
    """
    composite = (
        0.45 * _get(z, "theta")
        + 0.35 * _get(z, "high_beta")
        - 0.20 * _get(z, "low_gamma")
    )
    return _make(composite, "edc")


# ──────────────────────────────────────────────────────────────
# 7. ISI — Interpersonal Synchrony Index
# ──────────────────────────────────────────────────────────────

def calc_isi(z: Dict[str, dict]) -> dict:
    """人際同步能力：gamma + low_alpha 主導，high_beta 過高扣分"""
    composite = (
        0.45 * _get(z, "low_gamma")
        + 0.25 * _get(z, "high_gamma")
        + 0.20 * _get(z, "low_alpha")
        - 0.10 * max(_get(z, "high_beta"), 0)
    )
    return _make(composite, "isi")


# ──────────────────────────────────────────────────────────────
# 統一入口
# ──────────────────────────────────────────────────────────────

def calculate_all_composites(z_dict: Dict[str, dict]) -> Dict[str, dict]:
    """
    計算全部七項複合心理功能指標。

    Args:
        z_dict: normative_zscore.calculate_zscores() 的輸出
    """
    return {
        "ccr": calc_ccr(z_dict),
        "ebi": calc_ebi(z_dict),
        "reb": calc_reb(z_dict),
        "rrr": calc_rrr(z_dict),
        "sli": calc_sli(z_dict),
        "edc": calc_edc(z_dict),
        "isi": calc_isi(z_dict),
    }
