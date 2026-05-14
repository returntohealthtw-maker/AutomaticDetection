"""
腦波分析 API（移植自 BrainDNA 演算法庫）

端點：
    POST /api/v1/analysis/mbti          快速 MBTI 推算（給 8 個頻段平均值）
    POST /api/v1/analysis/full-report   完整報告生成（給時序資料）
    GET  /api/v1/analysis/demo          sanity check（用內建假資料跑一次）
"""
from typing import List, Optional
import random

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.algorithms import generate_quick_mbti, generate_report

router = APIRouter(prefix="/api/v1/analysis", tags=["腦波分析"])


# ─── Pydantic 模型 ──────────────────────────────────────────────────────────

class EEGMeans(BaseModel):
    """8 個頻段的平均值（NeuroSky ThinkGear 標準）"""
    delta:     float = Field(0, ge=0, description="Delta 0.5-3 Hz")
    theta:     float = Field(0, gt=0, description="Theta 4-7 Hz")
    lowAlpha:  float = Field(0, gt=0, description="Low Alpha 8-9 Hz")
    highAlpha: float = Field(0, gt=0, description="High Alpha 10-12 Hz")
    lowBeta:   float = Field(0, gt=0, description="Low Beta 13-17 Hz")
    highBeta:  float = Field(0, gt=0, description="High Beta 18-30 Hz")
    lowGamma:  float = Field(0, gt=0, description="Low Gamma 31-40 Hz")
    midGamma:  float = Field(0, gt=0, description="Mid Gamma 41-50 Hz")


class EEGRow(BaseModel):
    """單筆腦波時序資料（每秒一筆）"""
    ts:         Optional[float] = 0
    attention:  float = Field(0, ge=0, le=100)
    meditation: float = Field(0, ge=0, le=100)
    delta:      float = 0
    theta:      float = 0
    lowAlpha:   float = 0
    highAlpha:  float = 0
    lowBeta:    float = 0
    highBeta:   float = 0
    lowGamma:   float = 0
    midGamma:   float = 0


class FullReportRequest(BaseModel):
    rows: List[EEGRow] = Field(..., min_length=10, description="至少 10 秒的腦波資料")


# ─── 端點 ───────────────────────────────────────────────────────────────────

@router.post("/mbti", summary="快速 MBTI 推算")
def quick_mbti(eeg: EEGMeans):
    """
    給定 8 個頻段平均值，立刻回傳 MBTI 16 型 + 4 色腦人 + 八卦類型。

    適合用在「腦波檢測完成、準備跳轉到報告頁」前的快速判讀。
    """
    try:
        return generate_quick_mbti(eeg.model_dump())
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"分析失敗：{e}")


@router.post("/full-report", summary="完整腦波分析報告")
def full_report(req: FullReportRequest):
    """
    完整版：給時序腦波資料（至少 10 筆，建議 60-150 筆 = 1-2.5 分鐘），
    回傳 4 色腦人 + 八卦 + MBTI + 三大分數（平衡/能量/壓力）+ 8 頻段 strip
    + 評語 + 職業建議 + attention/meditation 比例 + quadrant 象限。
    """
    try:
        rows = [r.model_dump() for r in req.rows]
        return generate_report(rows)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"報告生成失敗：{e}")


@router.get("/demo", summary="使用內建假資料跑一次完整報告（sanity check）")
def demo_report(seconds: int = 90, seed: int = 42):
    """
    產生 N 秒的假腦波資料並跑完整報告。
    驗證演算法移植是否正確、API 是否正常運作。

    Args:
        seconds: 模擬秒數，建議 90 秒
        seed:    隨機種子，確保結果可重現
    """
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
    try:
        return {
            "note": f"這是用 seed={seed} 產生的 {seconds} 秒假資料報告，僅供驗證演算法",
            "report": generate_report(rows),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"demo 失敗：{e}")
