"""
score_interpretation_rules.py
────────────────────────────────
分數解讀輔助模組（從 score_interpretation_rules.json 讀取規則）
"""
import json
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent / "config" / "score_interpretation_rules.json"

_rules: dict = {}

def _load():
    global _rules
    if not _rules:
        try:
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                _rules = json.load(f)
        except Exception:
            _rules = {}

def interpret_score(score: float, score_type: str = "ability_type") -> str:
    """
    依分數與指標類型返回中文解讀標籤（en key）

    Args:
        score: 0–100 分數
        score_type: "ability_type" | "risk_type" | "balance_type"
    """
    _load()
    bands = _rules.get(score_type, {}).get("bands", [])
    for band in bands:
        if band["min"] <= score <= band["max"]:
            return band["en"]
    return "average"

def get_score_type(indicator: str) -> str:
    """返回指標的分數類型"""
    _load()
    return _rules.get("score_types", {}).get(indicator, "ability_type")
