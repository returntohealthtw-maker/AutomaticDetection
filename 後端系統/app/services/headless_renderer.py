"""
Headless Chromium 渲染器（Playwright）

用途：背景開啟你部署在 Vercel/Railway 的 React 報告 App
      以保留你原本的設計，同時：
        ✅ 使用者完全看不到外部 UI
        ✅ 使用者可關閉 APP（生成繼續在主後端跑）
        ✅ Vercel App 內建的 ?auto=1 流程不變動

每個任務：
  1. 開新 browser context（隔離 cookies/localStorage 避免互相干擾）
  2. 開新 page → 訪問 {vercel_url}?auto=1&name=...&email=...&api_base=...
  3. 監聽：
       - page.url 變化（不會發生，SPA）
       - 主後端 /reports/record 收到對應 session 的 callback
       - 或 Vercel page 顯示「✅ 已寄送至 ...」的文字（DOM 偵測）
       - 或設定的 timeout（預設 25 分鐘）
  4. 關閉 page 與 context

併發策略：
  - 用 asyncio.Semaphore 限制同時最多 N 個瀏覽器
  - 每個 worker 持有一個 Chromium binary（共用單一 chromium 程序）
  - 超出 N 的任務 await，不會丟掉

設定環境變數：
  HEADLESS_MAX_CONCURRENT  = 同時跑幾個（預設 3，Hobby 建議 3-5，Pro 建議 5-10）
  HEADLESS_TIMEOUT_SEC     = 單一任務上限（預設 1500 = 25 分鐘）
"""
from __future__ import annotations
import asyncio
import logging
import os
import threading
import time
from typing import Optional, Dict, Any
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


# ── 設定 ─────────────────────────────────────────────────────────────
def _max_concurrent() -> int:
    try:
        return max(1, int(os.environ.get("HEADLESS_MAX_CONCURRENT", "1")))
    except ValueError:
        return 1


def _timeout_sec() -> int:
    try:
        return max(60, int(os.environ.get("HEADLESS_TIMEOUT_SEC", "2700")))  # 預設 45 分鐘
    except ValueError:
        return 2700


# ── 模組級狀態（單一 event loop 跨 thread 共用）──────────────────────
_loop: Optional[asyncio.AbstractEventLoop] = None
_loop_thread: Optional[threading.Thread] = None
_semaphore: Optional[asyncio.Semaphore] = None
_active_jobs: Dict[str, Dict[str, Any]] = {}
_active_lock = threading.Lock()


def _ensure_loop():
    """確保有一個 background asyncio loop 在跑（讓 sync FastAPI 也能 schedule async）"""
    global _loop, _loop_thread, _semaphore
    if _loop and _loop.is_running():
        return
    _loop = asyncio.new_event_loop()

    def _run():
        asyncio.set_event_loop(_loop)
        _loop.run_forever()

    _loop_thread = threading.Thread(target=_run, name="headless-renderer-loop", daemon=True)
    _loop_thread.start()
    # 在新 loop 裡建 semaphore（必須在 loop 內）
    fut = asyncio.run_coroutine_threadsafe(_create_semaphore(), _loop)
    fut.result(timeout=5)
    logger.info("✅ Headless renderer loop 啟動，併發上限：%d", _max_concurrent())


async def _create_semaphore():
    global _semaphore
    _semaphore = asyncio.Semaphore(_max_concurrent())


# ── Playwright 可用性檢查 ────────────────────────────────────────────
def is_available() -> bool:
    """Playwright + Chromium 是否可用"""
    try:
        from playwright.async_api import async_playwright  # noqa: F401
        return True
    except ImportError:
        return False


def diag() -> dict:
    info = {
        "playwright_installed":  is_available(),
        "max_concurrent":        _max_concurrent(),
        "timeout_sec":           _timeout_sec(),
        "active_jobs":           len(_active_jobs),
    }
    # 試著開瀏覽器探一下 chromium 是否有裝
    if info["playwright_installed"]:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                ver = p.chromium.executable_path
                info["chromium_path"] = ver
        except Exception as e:
            info["chromium_error"] = f"{type(e).__name__}: {e}"
    return info


# ── 主要 API：建立 background job ────────────────────────────────────
def start_headless_job(
    report_type:   str,                # life_script / child
    vercel_base:   str,                # https://brianave-report-image.vercel.app
    subject_name:  str,
    subject_email: str,
    brainwave_data: Optional[Dict[str, Any]],
    variant:       str = "full",
    session_id:    Optional[int] = None,
    api_base:      str = "",
    job_id:        Optional[str] = None,
) -> Dict[str, Any]:
    """
    在背景啟動一個 headless Chromium 任務，立即回傳 job_id。
    呼叫端不需等待。完成後 Vercel App 會自己 callback /reports/record。
    """
    if not is_available():
        return {
            "ok": False,
            "error": "Playwright 未安裝。請執行 pip install playwright + playwright install chromium",
        }

    import uuid
    job_id = job_id or f"hl-{uuid.uuid4().hex[:12]}"

    # 組裝 ?auto=1&... URL（與舊 vite_prefill 相同 schema）
    ba = (brainwave_data or {}).get("bands_avg") or {}
    params = {
        "auto":       "1",
        "name":       subject_name or "",
        "email":      subject_email or "",
        "variant":    variant,
        "api_base":   api_base or "",
        "session_id": str(session_id or ""),
        "focus":      int((brainwave_data or {}).get("attention_percentage", 50)),
        "relaxation": int((brainwave_data or {}).get("meditation_percentage", 50)),
        "theta":      int(ba.get("theta", 50)),
        "highAlpha":  int(min(100, ba.get("alpha", 50) * 1.1)),
        "lowAlpha":   int(max(0,   ba.get("alpha", 50) * 0.9)),
        "highBeta":   int(min(100, ba.get("beta",  50) * 1.1)),
        "lowBeta":    int(max(0,   ba.get("beta",  50) * 0.9)),
        "highGamma":  int(min(100, ba.get("gamma", 50) * 1.1)),
        "lowGamma":   int(max(0,   ba.get("gamma", 50) * 0.9)),
    }
    target_url = f"{vercel_base.rstrip('/')}/?{urlencode(params)}"

    # 紀錄
    with _active_lock:
        _active_jobs[job_id] = {
            "job_id":        job_id,
            "report_type":   report_type,
            "subject_name":  subject_name,
            "subject_email": subject_email,
            "vercel_url":    target_url,
            "status":        "queued",
            "started_at":    time.time(),
            "ended_at":      None,
            "error":         None,
        }

    _ensure_loop()
    asyncio.run_coroutine_threadsafe(_run_job(job_id, target_url, session_id, api_base), _loop)

    return {"ok": True, "job_id": job_id, "mode": "headless", "vercel_url": target_url}


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    with _active_lock:
        return dict(_active_jobs.get(job_id) or {}) or None


def list_jobs() -> list:
    with _active_lock:
        return list(_active_jobs.values())


# ── 內部：實際的 async job ──────────────────────────────────────────
async def _run_job(job_id: str, target_url: str, session_id: Optional[int], api_base: str):
    from playwright.async_api import async_playwright

    timeout_sec = _timeout_sec()

    async with _semaphore:
        with _active_lock:
            _active_jobs[job_id]["status"] = "running"

        logger.info("[%s] 開始 headless 渲染 → %s", job_id, target_url)
        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--no-zygote",
                        "--disable-extensions",
                        "--disable-background-networking",
                        "--disable-background-timer-throttling",
                        "--disable-renderer-backgrounding",
                        "--js-flags=--max-old-space-size=3072",
                    ],
                )
                ctx = await browser.new_context(
                    viewport={"width": 1366, "height": 900},
                    user_agent="AutomaticDetection-Headless/1.0 (Playwright)",
                )
                page = await ctx.new_page()

                # 把 console log 也吐到我們的 logger，方便 debug
                page.on("console", lambda msg: logger.debug("[%s][page] %s", job_id, msg.text))
                page.on("pageerror", lambda err: logger.warning("[%s][pageerror] %s", job_id, err))

                try:
                    await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
                except Exception as e:
                    raise RuntimeError(f"無法打開 Vercel 頁面：{e}")

                # 等待「✅ 已寄送」或「✅ 報告已上傳」這類完成訊號
                # 也接受「✅」開頭的 status 訊息，或寄信成功（藉由監聽 page.url 不會變動）
                # 策略：每 5 秒 poll 一次 page.evaluate 看 document.body.innerText 是否有完成字串
                deadline = time.time() + timeout_sec
                done_keywords = [
                    "✅ 報告下載連結已寄送至",
                    "報告已上傳：",
                    "✅ 報告下載連結已寄送",
                    "Email 已寄送",
                    "已寄送",
                    "全部完成",
                    "已完成",
                ]
                err_keywords = [
                    "❌",
                    "失敗",
                    "GEMINI_API_KEY 未設定",
                    "AI 模型未能",
                ]
                final_msg = ""
                while time.time() < deadline:
                    try:
                        txt = await page.evaluate("() => document.body && document.body.innerText || ''")
                    except Exception:
                        txt = ""
                    # 完成偵測
                    for kw in done_keywords:
                        if kw in txt:
                            final_msg = kw
                            break
                    if final_msg:
                        break
                    # 早期失敗偵測（但 ❌ 可能只是 UI 提示，不一定 fatal — 仍續等）
                    await asyncio.sleep(5)

                if not final_msg:
                    raise TimeoutError(f"等待 Vercel App 完成超時（{timeout_sec}s）")

                # 多等 5 秒讓 Vercel app 完成 callback /reports/record + sendEmail
                await asyncio.sleep(5)

                await ctx.close()
                await browser.close()

            with _active_lock:
                _active_jobs[job_id]["status"]   = "completed"
                _active_jobs[job_id]["ended_at"] = time.time()
            logger.info("[%s] ✅ headless 完成 (%s)", job_id, final_msg)
        except Exception as e:
            logger.exception("[%s] headless 失敗", job_id)
            with _active_lock:
                _active_jobs[job_id]["status"]   = "failed"
                _active_jobs[job_id]["ended_at"] = time.time()
                _active_jobs[job_id]["error"]    = f"{type(e).__name__}: {e}"
