"""
BrainDNA 移植版腦波分析演算法

核心流程：
    EEG 8 頻段時序資料
        ↓ MindColorAlgorithm.calc → 4 色腦人 (橘/綠/藍/黃)
        ↓ Bagua.calcBagua / calcType → 8 卦類型
        ↓ Personality.getPersonalityFromBagua → MBTI 16 型
        ↓ Report.getData → 整合報告（含中文文案、評語、分數）

模組對應：
    brainwave.py  - MindColor / MindBalance / MindEnergy / MindStress 演算法
    bagua.py      - 八卦推算（3 種方式）
    mbti.py       - MBTI 16 型推算
    data_stats.py - 人口腦波對數值 mean/std 標準化常數
    report.py     - 完整報告生成器（整合 + 文案）

來源：
    BrainDNA-master (NeuroSky ThinkGear EEG 設備搭配)
    原始碼為 Python 2 + Django，本版本已轉 Python 3 + 移除 Django 相依。
"""
from app.algorithms.brainwave import (
    MindColorAlgorithm,
    MindBalanceAlgorithm,
    MindEnergyAlgorithm,
    MindStressAlgorithm,
    MindValueAlgorithm,
    MindValueCalcHelper,
    MindValueTop,
    ReportResult,
)
from app.algorithms.bagua import Bagua
from app.algorithms.mbti import Personality
from app.algorithms.data_stats import DATA_STATS, DATA_VALUES
from app.algorithms.report import generate_report, generate_quick_mbti

__all__ = [
    "MindColorAlgorithm",
    "MindBalanceAlgorithm",
    "MindEnergyAlgorithm",
    "MindStressAlgorithm",
    "MindValueAlgorithm",
    "MindValueCalcHelper",
    "MindValueTop",
    "ReportResult",
    "Bagua",
    "Personality",
    "DATA_STATS",
    "DATA_VALUES",
    "generate_report",
    "generate_quick_mbti",
]
