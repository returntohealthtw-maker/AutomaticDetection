"""
normative_zscore.py
────────────────────
Z-score 計算模組。

常模比對優先順序：
  1. 內部常模（internal_norms）：sample_count >= 30 且有對應頻段
  2. 文獻適配常模（literature_adapted）：按年齡組細分
  3. 全域文獻常模（literature_adapted.by_band）：無年齡細分
  4. 若找不到：返回 z=0（常模平均）並標記 insufficient_norm

Z-score = (subject_log_power - norm_mean) / norm_sd
"""
import json
import math
import os
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple

_CONFIG_DIR = Path(__file__).parent / "config"
_NORM_DB_PATH = _CONFIG_DIR / "normative_database.json"

ALL_BAND_KEYS = [
    "delta", "theta", "low_alpha", "high_alpha",
    "low_beta", "high_beta", "low_gamma", "high_gamma"
]

# 年齡分組對照表
_AGE_GROUPS = [
    (18,  29, "18-29"),
    (30,  44, "30-44"),
    (45,  59, "45-59"),
    (60, 200, "60+"),
]


def _load_norm_db() -> dict:
    try:
        with open(_NORM_DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_norm_db(db: dict):
    try:
        with open(_NORM_DB_PATH, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _get_age_group(age: Optional[int]) -> Optional[str]:
    if not age:
        return None
    for lo, hi, label in _AGE_GROUPS:
        if lo <= age <= hi:
            return label
    return None


def calculate_zscores(
    log_power: Dict[str, float],
    age: Optional[int] = None,
    sex: Optional[str] = None,
) -> Dict[str, dict]:
    """
    輸入：log_power dict（各頻段的 log 相對功率）
    輸出：各頻段 Z-score dict

    Returns:
        {
          "theta": {
            "log_power": -1.55,
            "norm_mean": -1.61,
            "norm_sd":   0.40,
            "z_score":   0.15,
            "norm_match_quality": "internal | literature_age | literature_global",
            "source": "...",
            "warning": null
          },
          ...
        }
    """
    db = _load_norm_db()
    internal = db.get("internal_norms", {})
    internal_count = internal.get("sample_count", 0)
    min_for_internal = db.get("min_samples_for_internal", 30)
    lit = db.get("literature_adapted", {})
    age_group = _get_age_group(age)

    results = {}
    for band in ALL_BAND_KEYS:
        lp = log_power.get(band)
        if lp is None:
            continue

        norm_mean, norm_sd, match_quality, source, warning = None, None, None, None, None

        # 優先：內部常模
        if internal_count >= min_for_internal:
            internal_band = internal.get("by_band", {}).get(band)
            if internal_band:
                norm_mean = internal_band["log_mean"]
                norm_sd   = internal_band["log_sd"]
                match_quality = "internal"
                source = f"internal_norms (n={internal_count})"

        # 次選：文獻常模（年齡分組）
        if norm_mean is None and age_group:
            age_band = lit.get("by_age_group", {}).get(age_group, {}).get(band)
            if age_band:
                norm_mean = age_band["log_mean"]
                norm_sd   = age_band["log_sd"]
                match_quality = "literature_age"
                source = f"literature_adapted age={age_group}"

        # 回退：全域文獻常模
        if norm_mean is None:
            global_band = lit.get("by_band", {}).get(band)
            if global_band:
                norm_mean = global_band["log_mean"]
                norm_sd   = global_band["log_sd"]
                match_quality = "literature_global"
                source = "literature_adapted global"
                if not age_group:
                    warning = "年齡未提供，使用全年齡常模"

        # 無常模：z=0 並標記
        if norm_mean is None or norm_sd is None or norm_sd <= 0:
            results[band] = {
                "log_power": round(lp, 4),
                "norm_mean": None, "norm_sd": None, "z_score": 0.0,
                "norm_match_quality": "insufficient_norm",
                "source": "no_norm_available",
                "warning": "常模缺失，此頻段 Z-score 設為 0"
            }
            continue

        z = (lp - norm_mean) / norm_sd
        z = max(-4.0, min(4.0, z))  # 截斷極端值，避免分數過於極端

        results[band] = {
            "log_power":          round(lp, 4),
            "norm_mean":          round(norm_mean, 4),
            "norm_sd":            round(norm_sd, 4),
            "z_score":            round(z, 4),
            "norm_match_quality": match_quality,
            "source":             source,
            "warning":            warning,
        }

    return results


# ──────────────────────────────────────────────────────────────
# 內部常模更新（每次新 session 完成後呼叫）
# ──────────────────────────────────────────────────────────────

def update_internal_norms_from_sessions(sessions_log_powers: list[Dict[str, float]]):
    """
    從多筆 session 的 log_power 重新計算並更新內部常模。

    Args:
        sessions_log_powers: list of log_power dicts，每個元素是一筆 session 的各頻段 log 值
    """
    if not sessions_log_powers:
        return

    by_band: Dict[str, list] = {k: [] for k in ALL_BAND_KEYS}
    for lp_dict in sessions_log_powers:
        for k in ALL_BAND_KEYS:
            v = lp_dict.get(k)
            if v is not None:
                by_band[k].append(v)

    db = _load_norm_db()
    internal = db.setdefault("internal_norms", {})
    internal["sample_count"] = len(sessions_log_powers)
    internal["_last_updated"] = datetime.now(timezone.utc).isoformat()
    by_band_out = {}
    for k, vals in by_band.items():
        if len(vals) >= 5:
            by_band_out[k] = {
                "log_mean": round(statistics.mean(vals), 4),
                "log_sd":   round(statistics.stdev(vals), 4) if len(vals) > 1 else 0.3,
                "n":        len(vals),
            }
    internal["by_band"] = by_band_out
    _save_norm_db(db)
