"""
qeeg_pipeline
──────────────
qEEG Z-score 演算法模組（ThinkGear 單導程 Fp1 適配版）

使用方式：
    from app.services.qeeg_pipeline import run_qeeg_pipeline

    result = run_qeeg_pipeline(
        raw_arrays   = payload.raw_arrays,
        captures     = None,
        subject_info = {"name": "王小明", "age": 35, "sex": "male"},
    )
"""
from .main_pipeline import run_qeeg_pipeline
from .normative_zscore import update_internal_norms_from_sessions

__all__ = ["run_qeeg_pipeline", "update_internal_norms_from_sessions"]
