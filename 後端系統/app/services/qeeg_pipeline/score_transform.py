"""
score_transform.py
──────────────────
EEG 訊號轉換模組：
  1. 原始頻段功率 → 相對功率（relative power）
  2. 相對功率 → log power（自然對數，避免偏態）
  3. Z-score → 0–100 sigmoid 分數

設計原則：
  - 使用相對功率（relative power）作為正規化輸入，使結果與儀器輸出範圍（raw / bandTo100）無關
  - log(x + epsilon) 處理零值
  - sigmoid(k=0.9) 轉換 Z-score 至 0–100，50 = 常模平均
"""
import math
from typing import Dict, Optional

EPSILON = 1e-8
SIGMOID_K = 0.9  # 斜率，決定 Z-score 到分數的敏感度

ALL_BAND_KEYS = [
    "delta", "theta", "low_alpha", "high_alpha",
    "low_beta", "high_beta", "low_gamma", "high_gamma"
]


# ──────────────────────────────────────────────────────────────
# 1.  輸入標準化：轉換為相對功率（0–1）
# ──────────────────────────────────────────────────────────────

def to_relative_power(per_sec_band_values: Dict[str, list]) -> Dict[str, list]:
    """
    輸入：每秒各頻段的功率值陣列（raw 或 bandTo100 均可）
    輸出：每秒各頻段的「相對功率」陣列（各頻段 / 總功率）

    Example input:
        {"delta": [500, 600, ...], "theta": [300, 320, ...], ...}
    Example output:
        {"delta": [0.22, 0.23, ...], "theta": [0.13, 0.12, ...], ...}
    """
    n = max((len(v) for v in per_sec_band_values.values()), default=0)
    result: Dict[str, list] = {k: [] for k in ALL_BAND_KEYS}

    for i in range(n):
        vals = {k: float(per_sec_band_values.get(k, [0])[i]
                         if i < len(per_sec_band_values.get(k, [])) else 0)
                for k in ALL_BAND_KEYS}
        total = sum(vals.values())
        for k in ALL_BAND_KEYS:
            rel = vals[k] / total if total > 0 else 0.0
            result[k].append(rel)

    return result


def aggregate_relative_power(relative_power: Dict[str, list]) -> Dict[str, float]:
    """
    每秒相對功率陣列 → 各頻段「平均相對功率」（scalar）
    使用「每秒先算再平均」（BrainDNA 方法），而非總和除以總和
    """
    out: Dict[str, float] = {}
    for k in ALL_BAND_KEYS:
        arr = relative_power.get(k, [])
        valid = [v for v in arr if v > 0]
        out[k] = sum(valid) / len(valid) if valid else 0.0
    return out


# ──────────────────────────────────────────────────────────────
# 2.  log power 轉換
# ──────────────────────────────────────────────────────────────

def log_transform(rel_power_value: float) -> float:
    """ln(x + epsilon)，避免 log(0)"""
    return math.log(rel_power_value + EPSILON)


def log_transform_dict(rel_power: Dict[str, float]) -> Dict[str, float]:
    """對每個頻段的平均相對功率做 log 轉換"""
    return {k: log_transform(v) for k, v in rel_power.items()}


# ──────────────────────────────────────────────────────────────
# 3.  high_sigma 近似值（ThinkGear 無此頻段直接輸出）
# ──────────────────────────────────────────────────────────────

def compute_high_sigma_approx(rel_power: Dict[str, float]) -> float:
    """
    ThinkGear 無獨立 high_sigma（12-15 Hz）輸出，
    以 high_alpha（10-12 Hz）與 low_beta（13-20 Hz）加權平均近似。
    """
    return 0.5 * rel_power.get("high_alpha", 0.0) + 0.5 * rel_power.get("low_beta", 0.0)


# ──────────────────────────────────────────────────────────────
# 4.  sigmoid → 0–100 分數
# ──────────────────────────────────────────────────────────────

def sigmoid_0_100(z: float, k: float = SIGMOID_K) -> float:
    """
    Z-score 轉 0–100 分數（sigmoid）

    對照：
      Z=-3 → ~6    Z=-2 → ~14   Z=-1 → ~29
      Z= 0 → 50    Z=+1 → ~71   Z=+2 → ~86   Z=+3 → ~94
    """
    try:
        score = 100.0 / (1.0 + math.exp(-k * z))
    except OverflowError:
        score = 0.0 if z < 0 else 100.0
    return round(score, 1)


# ──────────────────────────────────────────────────────────────
# 5.  訊號品質評估（ThinkGear 適配版）
# ──────────────────────────────────────────────────────────────

def assess_signal_quality(good_signal_arr: list, n_samples: int) -> dict:
    """
    ThinkGear good_signal 值 0 = 完美，200 = 無訊號。
    此處將「good_signal == 0」視為高品質秒，計算可用 epoch 比例。

    Args:
        good_signal_arr: 每秒的 good_signal 值（0-200）
        n_samples: 總採集秒數

    Returns:
        signal_quality dict 含 quality_grade（A/B/C/D）
    """
    if not n_samples or n_samples == 0:
        return {"quality_grade": "D", "usable_epoch_ratio": 0.0,
                "total_epochs": 0, "usable_epochs": 0,
                "artifact_ratio": 1.0, "quality_warning": "無採集資料",
                "device": "ThinkGear", "channel": "Fp1"}

    good_arr = good_signal_arr or []

    # WebApp 路徑不提供 good_signal（空陣列），預設 B 級而非 D 級
    if not good_arr:
        return {
            "total_epochs":       n_samples,
            "usable_epochs":      n_samples,
            "usable_epoch_ratio": 1.0,
            "artifact_ratio":     0.0,
            "bad_channels":       [],
            "quality_grade":      "B",
            "quality_warning":    "訊號品質資料不可用（WebApp 路徑），預設 B 級",
            "device":             "ThinkGear",
            "channel":            "Fp1",
        }

    # ThinkGear: good_signal=0 為完美訊號，200 為無訊號；以 <50 為可用
    usable = sum(1 for s in good_arr if s < 50)
    total = n_samples
    ratio = usable / total if total > 0 else 0.0
    artifact_ratio = round(1.0 - ratio, 3)

    if ratio >= 0.90:
        grade, warning = "A", None
    elif ratio >= 0.75:
        grade, warning = "B", "訊號品質略低，建議確認電極接觸"
    elif ratio >= 0.60:
        grade, warning = "C", "訊號品質偏低，結果僅供趨勢參考"
    else:
        grade, warning = "D", "訊號品質不足，建議重新檢測"

    return {
        "total_epochs":        total,
        "usable_epochs":       usable,
        "usable_epoch_ratio":  round(ratio, 3),
        "artifact_ratio":      artifact_ratio,
        "bad_channels":        [],
        "quality_grade":       grade,
        "quality_warning":     warning,
        "device":              "ThinkGear",
        "channel":             "Fp1"
    }
