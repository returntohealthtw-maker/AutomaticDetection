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
        return max(60, int(os.environ.get("HEADLESS_TIMEOUT_SEC", "3600")))  # 預設 60 分鐘（BrianaveReportImage Imagen 生成需時）
    except ValueError:
        return 3600


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

    # 組裝 ?auto=1&... URL（同時支援 camelCase + snake_case，避免命名漂移）
    bw_present = bool(brainwave_data and (brainwave_data.get("bands_avg") or brainwave_data.get("attention_percentage")))
    ba = (brainwave_data or {}).get("bands_avg") or {}

    # 取值函式：有資料就用實際值，無資料時回傳 None（明確區分「缺資料」vs「值為 0」）
    def _opt(d, k):
        try:
            x = d.get(k) if isinstance(d, dict) else None
            if x is None or x == "":
                return None
            return int(round(float(x)))
        except Exception:
            return None

    def _val_or_50(v):
        """只在 None 時 fallback 為 50（0 是合法值，不替換）"""
        return 50 if v is None else max(0, min(100, int(v)))

    attn_opt  = _opt(brainwave_data, "attention_percentage")
    medi_opt  = _opt(brainwave_data, "meditation_percentage")
    delta_opt = _opt(ba, "delta")
    theta_opt = _opt(ba, "theta")
    alpha_opt = _opt(ba, "alpha")
    beta_opt  = _opt(ba, "beta")
    gamma_opt = _opt(ba, "gamma")

    attn_val  = _val_or_50(attn_opt)
    medi_val  = _val_or_50(medi_opt)
    delta_val = _val_or_50(delta_opt)
    theta_val = _val_or_50(theta_opt)
    alpha_val = _val_or_50(alpha_opt)
    beta_val  = _val_or_50(beta_opt)
    gamma_val = _val_or_50(gamma_opt)

    # 醒目記錄真正進入 URL 的值（防止下次再被指控不知資料跑去哪了）
    missing_keys = [
        k for k, v in [
            ("attention", attn_opt), ("meditation", medi_opt),
            ("delta", delta_opt), ("theta", theta_opt), ("alpha", alpha_opt),
            ("beta", beta_opt), ("gamma", gamma_opt),
        ] if v is None
    ]
    if missing_keys:
        logger.warning(
            "[headless] brainwave_data 缺欄位 %s（將用 50% 替代）— session=%s",
            missing_keys, session_id,
        )
    logger.info(
        "[headless] session=%s URL 帶腦波：attn=%d medi=%d δ=%d θ=%d α=%d β=%d γ=%d (bw_present=%s)",
        session_id, attn_val, medi_val, delta_val, theta_val,
        alpha_val, beta_val, gamma_val, "1" if bw_present else "0",
    )

    # 同時把整包 brainwave_data 以 base64-encoded JSON 塞進 URL
    # → 即使單獨 key 命名漂移，Vercel 仍可從這裡解出完整 payload
    import base64, json as _json
    bw_payload = {
        "attention_percentage":  attn_val,
        "meditation_percentage": medi_val,
        # 5-band 平均
        "bands_avg": {
            "delta": delta_val, "theta": theta_val, "alpha": alpha_val,
            "beta":  beta_val,  "gamma": gamma_val,
        },
        # 7 子頻帶（依設計文件 06）
        "bands_7": {
            "theta":      theta_val,
            "alpha_high": min(100, int(alpha_val * 1.1)),
            "alpha_low":  max(0,   int(alpha_val * 0.9)),
            "beta_high":  min(100, int(beta_val  * 1.1)),
            "beta_low":   max(0,   int(beta_val  * 0.9)),
            "gamma_high": min(100, int(gamma_val * 1.1)),
            "gamma_low":  max(0,   int(gamma_val * 0.9)),
        },
        "attention":      attn_val,
        "relaxation":     medi_val,
        "sample_count":   (brainwave_data or {}).get("sample_count"),
        "session_id":     session_id,
        "bw_present":     bw_present,
    }
    bw_b64 = base64.urlsafe_b64encode(_json.dumps(bw_payload).encode("utf-8")).decode("ascii")

    params = {
        "auto":        "1",
        "name":        subject_name or "",
        "email":       subject_email or "",
        "variant":     variant,
        "api_base":    api_base or "",
        "session_id":  str(session_id or ""),
        "report_type": report_type,

        # ── 主要欄位（舊 camelCase schema，保留向下相容）──
        "focus":       attn_val,
        "relaxation":  medi_val,
        "theta":       theta_val,
        "highAlpha":   min(100, int(alpha_val * 1.1)),
        "lowAlpha":    max(0,   int(alpha_val * 0.9)),
        "highBeta":    min(100, int(beta_val  * 1.1)),
        "lowBeta":     max(0,   int(beta_val  * 0.9)),
        "highGamma":   min(100, int(gamma_val * 1.1)),
        "lowGamma":    max(0,   int(gamma_val * 0.9)),

        # ── snake_case 別名（符合設計文件 06_腦波資料格式規格）──
        "alpha_high":  min(100, int(alpha_val * 1.1)),
        "alpha_low":   max(0,   int(alpha_val * 0.9)),
        "beta_high":   min(100, int(beta_val  * 1.1)),
        "beta_low":    max(0,   int(beta_val  * 0.9)),
        "gamma_high":  min(100, int(gamma_val * 1.1)),
        "gamma_low":   max(0,   int(gamma_val * 0.9)),

        # ── 通用別名（attention / meditation / 5-band 平均）──
        "attention":             attn_val,
        "attention_percentage":  attn_val,
        "attention_score":       attn_val,
        "concentration":         attn_val,
        "concentration_pct":     attn_val,
        "meditation":            medi_val,
        "meditation_percentage": medi_val,
        "meditation_score":      medi_val,
        "relaxation_pct":        medi_val,
        "relaxation_score":      medi_val,
        "delta":                 delta_val,
        "alpha":                 alpha_val,
        "beta":                  beta_val,
        "gamma":                 gamma_val,

        # ── 結構化 payload（最強保障：URL key 漂移時這個還在）──
        "brainwave_data":  bw_b64,
        "bw_b64":          bw_b64,
        "bw_present":      "1" if bw_present else "0",
    }
    # 把 REPORTS_INGEST_SECRET 一併帶到 URL，讓 React app 在 callback /events 與 /record 時
    # 能加上 X-Ingest-Secret header（否則後端有設 secret 時會被 401 擋掉，導致監看 + 報告管理都看不到資料）
    ingest_secret = os.environ.get("REPORTS_INGEST_SECRET", "").strip()
    if ingest_secret:
        params["ingest_secret"] = ingest_secret
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
                        # 在 Docker / Railway Linux 容器中最穩定的最小 flag 組合：
                        "--no-sandbox",             # 容器內必須（無 root isolation）
                        "--disable-setuid-sandbox", # 同上
                        "--disable-dev-shm-usage",  # /dev/shm 小時的容器必須
                        "--disable-gpu",            # headless 不需 GPU
                        # ⚠️ 移除所有可能造成 crash 的 flags：
                        # --no-zygote      → 某些 kernel 版本會 SIGILL
                        # --single-process → Linux 完全不支援，必 crash
                        # --memory-pressure-off → 非標準 flag
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
                    raise RuntimeError(f"無法打開報告頁面：{e}")

                # ── 完成偵測策略（雙軌並行，任一先到即視為完成）────────────────
                # 主軌：輪詢 DB — Vercel app 完成後會 POST /reports/record，
                #        DB 裡 Report.status 會從 generating → completed。
                #        這個訊號 100% 可靠，不依賴頁面文字。
                # 副軌：頁面文字關鍵字 — 作為額外保險，匹配舊版 Vercel app。
                # 致命錯誤：Vercel app 頁面出現已知的失敗字串 → 立即放棄。

                deadline = time.time() + timeout_sec
                # ⚠️  關鍵字必須足夠具體，避免 Gemini 生成的章節文字（含「已完成」「待管理員」等普通詞語）
                #     誤觸發提前退出。只比對出現在 status bar 的特定格式字串。
                done_keywords = [
                    # React app auto-mode 成功完成後的最終 status 訊息
                    "本頁可關閉。\n連結：",          # App.tsx 唯一出現此格式的地方
                    "本頁可關閉。",                   # 備用（無換行版）
                    "✅ 報告下載連結已寄送至",         # 舊 Vercel app 完成訊息
                    "✅ 報告下載連結已寄送",
                    "報告已上傳：https://",           # 含 https 確保不是章節內文
                    "Report uploaded: https://",
                ]
                fatal_err_keywords = [
                    "GEMINI_API_KEY 未設定", "AI 模型未能初始化",
                    "GCS 設定錯誤", "上傳 GCS 失敗",
                    "API key not valid", "quota exceeded",
                    "上傳雲端失敗",                   # React app GCS 失敗訊息
                    "❌ PDF 渲染失敗",
                ]
                final_msg = ""
                fatal_err_msg = ""
                poll_interval = 15   # 每 15 秒查一次 DB

                while time.time() < deadline:
                    # ── 主軌：DB 輪詢 ──────────────────────────────────────
                    if session_id:
                        try:
                            from app.core.database import SessionLocal
                            from app.core import models as _M
                            with SessionLocal() as _db:
                                rep = _db.query(_M.Report).filter(
                                    _M.Report.session_id == session_id
                                ).first()
                                if rep and rep.status == "completed" and rep.pdf_url:
                                    final_msg = f"DB callback 確認完成 (pdf_url={rep.pdf_url[:60]})"
                                    break
                        except Exception as _dbe:
                            logger.debug("[%s] DB poll 例外: %s", job_id, _dbe)

                    # ── 副軌：頁面文字 ─────────────────────────────────────
                    try:
                        txt = await page.evaluate("() => document.body && document.body.innerText || ''")
                    except Exception:
                        txt = ""

                    for kw in done_keywords:
                        if kw in txt:
                            final_msg = f"頁面文字：{kw}"
                            break
                    if final_msg:
                        break

                    for ekw in fatal_err_keywords:
                        if ekw in txt:
                            fatal_err_msg = f"Vercel app 回報錯誤：{ekw}"
                            break
                    if fatal_err_msg:
                        break

                    await asyncio.sleep(poll_interval)

                if fatal_err_msg:
                    raise RuntimeError(fatal_err_msg)

                if not final_msg:
                    raise TimeoutError(f"等待 Vercel App 完成超時（{timeout_sec}s）")

                logger.info("[%s] ✅ 完成訊號：%s", job_id, final_msg)
                # 若是頁面文字觸發（非 DB poll），多等 15 秒讓 React app 完成 callback
                if "頁面文字" in final_msg:
                    await asyncio.sleep(15)
                else:
                    await asyncio.sleep(3)

                await ctx.close()
                await browser.close()

            with _active_lock:
                _active_jobs[job_id]["status"]   = "completed"
                _active_jobs[job_id]["ended_at"] = time.time()
            logger.info("[%s] ✅ headless 完成 (%s)", job_id, final_msg)
        except Exception as e:
            logger.exception("[%s] headless 失敗", job_id)
            err_msg = f"{type(e).__name__}: {e}"
            with _active_lock:
                _active_jobs[job_id]["status"]   = "failed"
                _active_jobs[job_id]["ended_at"] = time.time()
                _active_jobs[job_id]["error"]    = err_msg
            # ── 立即把 DB 的 generating/pending Report 標記為 failed ──
            # 同時把錯誤原因塞進 client_summary，讓管理員後台能看到
            if session_id:
                try:
                    import json as _json
                    from app.core.database import SessionLocal
                    from app.core import models as _M
                    with SessionLocal() as _db:
                        rep = _db.query(_M.Report).filter(
                            _M.Report.session_id == session_id
                        ).first()
                        if rep and rep.status in ("generating", "pending"):
                            rep.status = "failed"
                            # 把失敗原因寫入 client_summary（這欄有存在）
                            try:
                                existing = _json.loads(rep.client_summary or "{}")
                            except Exception:
                                existing = {}
                            existing["headless_error"] = err_msg[:600]
                            existing["headless_failed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                            rep.client_summary = _json.dumps(existing, ensure_ascii=False)
                            _db.commit()
                            logger.info("[%s] DB Report(session=%s) 已標記 failed（原因：%s）", job_id, session_id, err_msg[:120])
                except Exception as db_err:
                    logger.warning("[%s] 更新 DB failed 狀態失敗: %s", job_id, db_err)
