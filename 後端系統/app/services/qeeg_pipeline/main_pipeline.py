"""
main_pipeline.py
─────────────────
qEEG Z-score 演算法主流程（ThinkGear 單導程適配版）

輸入：
  raw_arrays   - 每秒頻段功率陣列 dict（來自 WebApp）
  captures     - EegCapture 物件列表（來自 Android App）
  subject_info - {"name", "age", "sex", "test_condition"}

輸出：
  {
    "calculation_version": "thinkgear_zscore_sigmoid_v1.0",
    "calculation_quality": "thinkgear_fp1_internal_norm",
    "subject": {...},
    "signal_quality": {...},
    "band_features": {"Fp1": {...}},
    "ability_scores": {...},
    "composite_indices": {...},
    "report_flags": [...],
    "report_summary": "...",
    "report_disclaimer": {...}
  }
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .score_transform import (
    to_relative_power, aggregate_relative_power,
    log_transform_dict, compute_high_sigma_approx,
    assess_signal_quality
)
from .normative_zscore import calculate_zscores
from .ability_score_engine import calculate_all_abilities
from .composite_index_engine import calculate_all_composites
from .report_interpretation_engine import generate_report_flags, generate_report_summary
from .score_transform import sigmoid_0_100

logger = logging.getLogger(__name__)

CALCULATION_VERSION = "thinkgear_zscore_sigmoid_v1.0"
ALL_BAND_KEYS = [
    "delta", "theta", "low_alpha", "high_alpha",
    "low_beta", "high_beta", "low_gamma", "high_gamma"
]


# ──────────────────────────────────────────────────────────────
# 輸入標準化
# ──────────────────────────────────────────────────────────────

def _raw_arrays_to_per_sec(raw_arrays: dict) -> Dict[str, list]:
    """
    WebApp 格式 raw_arrays → ALL_BAND_KEYS 格式
    raw_arrays key 映射：r_delta / r_theta / r_lalpha / r_halpha / r_lbeta / r_hbeta / r_lgamma / r_hgamma
    """
    mapping = {
        "delta":      raw_arrays.get("r_delta")  or [],
        "theta":      raw_arrays.get("r_theta")  or [],
        "low_alpha":  raw_arrays.get("r_lalpha") or raw_arrays.get("r_low_alpha") or [],
        "high_alpha": raw_arrays.get("r_halpha") or raw_arrays.get("r_high_alpha") or [],
        "low_beta":   raw_arrays.get("r_lbeta")  or raw_arrays.get("r_low_beta")  or [],
        "high_beta":  raw_arrays.get("r_hbeta")  or raw_arrays.get("r_high_beta") or [],
        "low_gamma":  raw_arrays.get("r_lgamma") or raw_arrays.get("r_low_gamma") or [],
        "high_gamma": raw_arrays.get("r_hgamma") or raw_arrays.get("r_high_gamma") or [],
    }
    return {k: [float(v) for v in arr if v is not None] for k, arr in mapping.items()}


def _captures_to_per_sec(captures: list) -> tuple[Dict[str, list], list]:
    """
    Android EegCapture 物件列表 → per_sec_band_values + good_signal 陣列
    """
    per_sec: Dict[str, list] = {k: [] for k in ALL_BAND_KEYS}
    good_signal: list = []

    for cap in sorted(captures, key=lambda c: getattr(c, "seq_num", 0)):
        per_sec["delta"].append(float(getattr(cap, "delta", 0) or 0))
        per_sec["theta"].append(float(getattr(cap, "theta", 0) or 0))
        per_sec["low_alpha"].append(float(getattr(cap, "low_alpha", 0) or 0))
        per_sec["high_alpha"].append(float(getattr(cap, "high_alpha", 0) or 0))
        per_sec["low_beta"].append(float(getattr(cap, "low_beta", 0) or 0))
        per_sec["high_beta"].append(float(getattr(cap, "high_beta", 0) or 0))
        per_sec["low_gamma"].append(float(getattr(cap, "low_gamma", 0) or 0))
        per_sec["high_gamma"].append(float(getattr(cap, "high_gamma", 0) or 0))
        good_signal.append(int(getattr(cap, "good_signal", 0) or 0))

    return per_sec, good_signal


# ──────────────────────────────────────────────────────────────
# 主流程
# ──────────────────────────────────────────────────────────────

def run_qeeg_pipeline(
    raw_arrays: Optional[dict] = None,
    captures: Optional[list] = None,
    subject_info: Optional[dict] = None,
) -> Optional[dict]:
    """
    執行完整 qEEG Z-score 演算流程。

    Args:
        raw_arrays:   WebApp 傳來的 raw_arrays dict（含 r_delta, r_theta, ...）
        captures:     Android 上傳的 EegCapture 物件列表
        subject_info: {"name", "age", "sex", "test_condition"}

    Returns:
        完整報告 JSON dict，或 None（資料不足時）
    """
    subject_info = subject_info or {}
    age = subject_info.get("age")
    sex = subject_info.get("sex")
    name = subject_info.get("name", "")

    # ── 1. 整理每秒輸入資料 ──────────────────────────────────────
    per_sec: Dict[str, list] = {}
    good_signal: list = []

    if raw_arrays:
        per_sec = _raw_arrays_to_per_sec(raw_arrays)
        good_signal = raw_arrays.get("r_good_signal") or raw_arrays.get("good_signal") or []
    elif captures:
        per_sec, good_signal = _captures_to_per_sec(captures)

    n_samples = max((len(v) for v in per_sec.values()), default=0)
    if n_samples < 10:
        logger.warning("[qEEG] 樣本數不足（%d 筆），跳過分析", n_samples)
        return None

    # ── 2. 訊號品質評估 ─────────────────────────────────────────
    signal_quality = assess_signal_quality(good_signal, n_samples)
    if signal_quality["quality_grade"] == "D":
        logger.warning("[qEEG] 訊號品質為 D，返回空分析")

    # ── 3. 相對功率 + log 轉換 ───────────────────────────────────
    relative_power_per_sec = to_relative_power(per_sec)
    avg_rel_power = aggregate_relative_power(relative_power_per_sec)
    log_power = log_transform_dict(avg_rel_power)

    # high_sigma 近似
    hs_rel = compute_high_sigma_approx(avg_rel_power)
    import math
    log_power["high_sigma"] = math.log(hs_rel + 1e-8)

    # ── 4. Z-score 計算 ──────────────────────────────────────────
    z_dict = calculate_zscores(log_power, age=age, sex=sex)

    # ── 5. 七大能力分數 ──────────────────────────────────────────
    ability_scores = calculate_all_abilities(
        z_dict,
        quality_grade=signal_quality["quality_grade"]
    )

    # ── 6. 複合心理功能指標 ──────────────────────────────────────
    composite_indices = calculate_all_composites(z_dict)

    # ── 7. Report flags + 摘要 ───────────────────────────────────
    report_flags = generate_report_flags(ability_scores, composite_indices, signal_quality)
    report_summary = generate_report_summary(
        ability_scores, composite_indices, report_flags,
        subject_name=name, age=age
    )

    # ── 8. band_features 輸出（供審計追溯） ─────────────────────
    band_features: Dict[str, dict] = {}
    for band in ALL_BAND_KEYS:
        rel = avg_rel_power.get(band, 0.0)
        z_entry = z_dict.get(band, {})
        score = sigmoid_0_100(z_entry.get("z_score", 0.0))
        status = ("high" if score >= 65 else "low" if score <= 35 else "average")
        band_features[band] = {
            "relative_power": round(rel, 5),
            "log_power":      round(log_power.get(band, 0.0), 4),
            "norm_mean":      z_entry.get("norm_mean"),
            "norm_sd":        z_entry.get("norm_sd"),
            "z_score":        z_entry.get("z_score"),
            "score_0_100":    score,
            "status":         status,
            "norm_match":     z_entry.get("norm_match_quality"),
        }

    # ── 9. 組裝輸出 JSON ────────────────────────────────────────
    return {
        "calculation_version":  CALCULATION_VERSION,
        "calculation_quality":  f"thinkgear_fp1_{z_dict.get('theta', {}).get('norm_match_quality', 'unknown')}_norm",
        "calculated_at":        datetime.now(timezone.utc).isoformat(),
        "subject": {
            "name":           name,
            "age":            age,
            "sex":            sex,
            "test_condition": subject_info.get("test_condition", "eyes_closed"),
            "device":         "ThinkGear",
            "channel":        "Fp1",
            "n_samples":      n_samples,
        },
        "signal_quality":    signal_quality,
        "band_features":     {"Fp1": band_features},
        "ability_scores":    ability_scores,
        "composite_indices": composite_indices,
        "report_flags":      report_flags,
        "report_summary":    report_summary,
        "report_disclaimer": {
            "medical": "本報告僅供教育、心理發展、壓力調節與職能分析參考，非臨床診斷或醫療判定依據。",
            "norm":    "本次分析使用 ThinkGear 單導程（Fp1）內部常模資料庫進行標準化，"
                       "結果適合作為趨勢分析與發展建議參考，不等同於醫療級臨床 qEEG 診斷。"
        }
    }
