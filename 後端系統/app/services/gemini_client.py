"""
Gemini API 客戶端薄包裝

- 懶載入 + 自動讀最新 API_KEY（不用重啟服務）
- 取出回應文字時跳過 thinking parts
- 統一錯誤分類（quota / api_key / rate_limit / 503 / 其他）
- 沒設 KEY 時自動 fallback 到 mock 文字（讓前端可以先測 UI）
"""
from __future__ import annotations
import os
import time
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# 懶載入
_client = None
_key_cache: Optional[str] = None


def _current_key() -> str:
    """Settings + 環境變數雙保險（Railway 改 env 後不需重啟）"""
    return (os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY or "").strip()


def key_is_set() -> bool:
    k = _current_key()
    return bool(k) and k != "your-gemini-api-key-here"


def get_client():
    """回傳 genai.Client；金鑰改變時自動重建"""
    global _client, _key_cache
    try:
        from google import genai  # type: ignore
    except ImportError:
        raise RuntimeError("google-genai 套件未安裝。請執行：pip install google-genai")

    key = _current_key()
    if not key:
        raise RuntimeError("GEMINI_API_KEY 尚未設定。請至 Railway 設定 GEMINI_API_KEY 環境變數。")

    if _client is None or key != _key_cache:
        _client = genai.Client(api_key=key)
        _key_cache = key
    return _client


def _get_response_text(response) -> Optional[str]:
    """取回應文字，跳過 thinking parts"""
    if getattr(response, "text", None):
        return response.text
    if getattr(response, "candidates", None):
        for candidate in response.candidates:
            content = getattr(candidate, "content", None)
            if content and getattr(content, "parts", None):
                for part in content.parts:
                    if getattr(part, "thought", False):
                        continue
                    if getattr(part, "text", None):
                        return part.text
    return None


# ──────────────────────────────────────────────────────────────────────────
# 主要對外函數
# ──────────────────────────────────────────────────────────────────────────
def generate_text(
    prompt: str,
    system_instruction: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.78,
    max_output_tokens: int = 8192,
    retries: int = 3,
) -> str:
    """
    呼叫 Gemini 生成文字。沒設 API_KEY 時回傳 mock 提示。

    成功 → 回傳純文字
    失敗 → 拋 RuntimeError，內含使用者友善的訊息
    """
    if not key_is_set():
        return (
            "⚠️ GEMINI_API_KEY 尚未設定，以下為 mock 範例文字：\n\n"
            "您的情緒穩定（Low Alpha）為 45%，這個數字直接揭示了一個值得正視的現象："
            "您的神經系統長期處於警戒狀態，容忍之窗（Window of Tolerance）相對狹窄，"
            "微小的壓力刺激就容易觸發過度反應或情緒解離。\n\n"
            "以多重迷走神經理論（Polyvagal Theory）的視角來看，您的腦波活躍度（High Beta，48%）"
            "加上偏低的情緒穩定，顯示交感神經長期佔上風——這就是為什麼您常常感覺"
            "「明明在休息，卻無法真正放鬆」。\n\n"
            "（這是 mock 文字。請至 Railway 設定 GEMINI_API_KEY 環境變數後重試，"
            "就會看到 Gemini 2.5 Pro 為您量身打造的真實分析。）"
        )

    from google.genai import types  # type: ignore

    model = model or settings.GEMINI_TEXT_MODEL
    cfg_kwargs = {
        "temperature": temperature,
        "max_output_tokens": max_output_tokens,
    }
    if system_instruction:
        cfg_kwargs["system_instruction"] = system_instruction

    last_err: Optional[Exception] = None
    for attempt in range(retries):
        try:
            response = get_client().models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(**cfg_kwargs),
            )
            text = _get_response_text(response)
            if not text:
                fr = (
                    response.candidates[0].finish_reason
                    if getattr(response, "candidates", None)
                    else "unknown"
                )
                raise ValueError(f"Gemini 回傳空內容（finish_reason={fr}）")
            return text.strip()
        except Exception as e:  # noqa
            last_err = e
            err_str = str(e)
            is_503 = "503" in err_str or "UNAVAILABLE" in err_str or "high demand" in err_str
            is_429 = "429" in err_str or "RATE_LIMIT" in err_str or "quota" in err_str.lower()
            if attempt < retries - 1:
                wait = 30 * (attempt + 1) if (is_503 or is_429) else 5 * (attempt + 1)
                logger.warning(
                    "[GEMINI RETRY %d/%d] %s: %.120s ── sleep %ds",
                    attempt + 1, retries, type(e).__name__, err_str, wait,
                )
                time.sleep(wait)
            else:
                logger.error("[GEMINI FAIL] %s", err_str[:300])
    raise RuntimeError(f"Gemini 生成失敗：{type(last_err).__name__}: {str(last_err)[:200]}")
