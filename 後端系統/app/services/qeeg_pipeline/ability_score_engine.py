"""
ability_score_engine.py
────────────────────────
七大能力分數計算模組（ThinkGear 單導程適配版）

所有公式以需求文件為基準，針對 ThinkGear 無 high_sigma / 單導程的情況做最小調整：
  - high_sigma → 0.5 * z_high_alpha + 0.5 * z_low_beta  的加權近似
  - "frontal" 與 "midline" 因只有 Fp1，視同同一通道
  - artifact_risk 由 signal_quality.quality_grade 推算（A=0, B=0.3, C=0.6, D=1.0）

輸出格式：
    {
      "intuition": {"score": 83, "z_composite": 1.75, "status": "high_activation"},
      "energy":    {"score": 35, "z_composite": -0.69, "status": "low"},
      ...
    }
"""
from typing import Dict, Optional
from .score_transform import sigmoid_0_100
from .score_interpretation_rules import interpret_score


def _get(z_dict: Dict[str, dict], band: str) -> float:
    """安全取得 Z-score 值，找不到返回 0"""
    entry = z_dict.get(band)
    if entry is None:
        return 0.0
    return float(entry.get("z_score", 0.0))


def _high_sigma_approx(z_dict: Dict[str, dict]) -> float:
    """ThinkGear 無 high_sigma，以 high_alpha 與 low_beta 加權近似"""
    return 0.5 * _get(z_dict, "high_alpha") + 0.5 * _get(z_dict, "low_beta")


def _artifact_risk_from_grade(quality_grade: str) -> float:
    """訊號品質轉為 artifact_risk 係數（0=完美, 1=極差）"""
    return {"A": 0.0, "B": 0.3, "C": 0.6, "D": 1.0}.get(quality_grade or "B", 0.3)


def _make_score(z: float, score_type: str = "ability_type") -> dict:
    score = sigmoid_0_100(z)
    status = interpret_score(score, score_type)
    return {"score": score, "z_composite": round(z, 4), "status": status}


# ──────────────────────────────────────────────────────────────
# 七大能力
# ──────────────────────────────────────────────────────────────

def calc_intuition(z: Dict[str, dict]) -> dict:
    """
    直覺能力 Intuition：內在洞察力與潛意識整合
    主要來源：theta midline / frontal（ThinkGear 只有 Fp1，視為同源）
    """
    z_theta   = _get(z, "theta")
    # 穩定性懲罰：theta 波動 → 使用 low_alpha 抵消過高 theta（避免誤判噪音）
    z_penalty = max(_get(z, "low_alpha") * -0.10, -0.5)
    composite = 0.70 * z_theta + 0.30 * _get(z, "low_alpha") + z_penalty
    return _make_score(composite)


def calc_energy(z: Dict[str, dict]) -> dict:
    """
    氣血飽滿／能量續航 Energy：
    high_sigma（近似）+ low_alpha；high_beta 過高扣分
    """
    z_hs = _high_sigma_approx(z)
    composite = (
        0.55 * z_hs
        + 0.25 * _get(z, "low_alpha")
        - 0.20 * max(_get(z, "high_beta"), 0)
    )
    return _make_score(composite)


def calc_relaxation(z: Dict[str, dict]) -> dict:
    """
    內在安定 Relaxation：alpha 主導，high_beta 過高扣分
    """
    composite = (
        0.55 * _get(z, "low_alpha")
        + 0.25 * _get(z, "high_alpha")
        - 0.20 * max(_get(z, "high_beta"), 0)
    )
    return _make_score(composite)


def calc_focus(z: Dict[str, dict], quality_grade: str = "B") -> dict:
    """
    高度專注 Focus：
    high_beta + low_beta；theta 過高與訊號品質差扣分
    注意：high_beta 高不一定是好，可能是焦慮或肌電污染
    """
    artifact_risk = _artifact_risk_from_grade(quality_grade)
    z_theta = _get(z, "theta")
    composite = (
        0.45 * _get(z, "high_beta")
        + 0.30 * _get(z, "low_beta")
        - 0.15 * max(z_theta - 1.5, 0)
        - 0.10 * artifact_risk
    )
    return _make_score(composite)


def calc_logic(z: Dict[str, dict]) -> dict:
    """
    邏輯分析 Logical Processing：
    low_beta 主導；單導程無法拆分 frontal_beta，以 low_alpha 穩定度輔助
    """
    composite = (
        0.65 * _get(z, "low_beta")
        + 0.20 * _get(z, "high_beta")
        + 0.15 * _get(z, "low_alpha")
    )
    return _make_score(composite)


def calc_awareness(z: Dict[str, dict]) -> dict:
    """
    外界覺察 Environmental Awareness：gamma 主導
    """
    composite = (
        0.55 * _get(z, "high_gamma")
        + 0.35 * _get(z, "low_gamma")
        + 0.10 * _get(z, "high_beta")
    )
    return _make_score(composite)


def calc_empathy(z: Dict[str, dict]) -> dict:
    """
    慈悲柔軟 Empathy / Softness：
    low_gamma + low_alpha；high_beta 過高扣分
    """
    composite = (
        0.45 * _get(z, "low_gamma")
        + 0.30 * _get(z, "low_alpha")
        - 0.25 * max(_get(z, "high_beta"), 0)
    )
    return _make_score(composite)


# ──────────────────────────────────────────────────────────────
# 統一入口
# ──────────────────────────────────────────────────────────────

def calculate_all_abilities(
    z_dict: Dict[str, dict],
    quality_grade: str = "B",
) -> Dict[str, dict]:
    """
    計算全部七大能力分數。

    Args:
        z_dict: normative_zscore.calculate_zscores() 的輸出
        quality_grade: 訊號品質等級（影響 focus 的 artifact_risk）

    Returns:
        七大能力分數 dict（含 score、z_composite、status）
    """
    return {
        "intuition":  calc_intuition(z_dict),
        "energy":     calc_energy(z_dict),
        "relaxation": calc_relaxation(z_dict),
        "focus":      calc_focus(z_dict, quality_grade),
        "logic":      calc_logic(z_dict),
        "awareness":  calc_awareness(z_dict),
        "empathy":    calc_empathy(z_dict),
    }
