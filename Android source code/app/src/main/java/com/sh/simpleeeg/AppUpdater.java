package com.sh.simpleeeg;

import android.app.AlertDialog;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.net.Uri;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;

import org.json.JSONObject;

import java.util.concurrent.TimeUnit;

import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;

/**
 * App 自動更新邏輯
 *
 * 流程：
 *   1. 開 App 時呼叫 {@link #checkForUpdate(Context, boolean)}
 *   2. 從後端 /api/v1/app/version 拿 latest_apk_version
 *   3. 比對 BuildConfig.VERSION_CODE，若有新版且非略過 → 跳對話框
 *   4. 使用者按「立即更新」→ 開瀏覽器下載 APK（MIUI 相容方案）
 *      MIUI 的 DownloadManager + FileProvider 常被安全機制攔截，
 *      改用瀏覽器開啟 APK URL，讓系統自行處理下載與安裝提示。
 *
 * 防重複彈窗：
 *   - sDialogShownThisSession：process 內只彈一次（記憶體）
 *   - TRIGGERED_KEY：持久化，記錄「已觸發下載的版本號」，
 *     只有在 current_version >= triggered_version 時才清除（代表安裝成功）
 */
public class AppUpdater {

    private static final String TAG = "AppUpdater";

    private static final String VERSION_URL =
            "https://backend-production-2da61.up.railway.app/api/v1/app/version";

    private static final String SKIP_KEY        = "skip_apk_version";
    private static final String TRIGGERED_KEY   = "update_triggered_version";
    private static final String LAST_SHOWN_TS   = "update_dialog_last_shown_ts";
    private static final String LAST_SHOWN_VER  = "update_dialog_last_shown_version";
    /** 同一版本 30 分鐘內只彈一次（跨 Activity 重建 / 進程重啟都生效） */
    private static final long COOLDOWN_MS       = 30L * 60 * 1000;

    /** process 內只彈一次 */
    private static volatile boolean sDialogShownThisSession = false;

    /**
     * @param force true = 忽略 skip/triggered/cooldown，強制顯示（給「檢查更新」按鈕用）
     */
    public static void checkForUpdate(final Context ctx, final boolean force) {
        if (!force && sDialogShownThisSession) return;

        new Thread(() -> {
            try {
                OkHttpClient client = new OkHttpClient.Builder()
                        .connectTimeout(8, TimeUnit.SECONDS)
                        .readTimeout(8, TimeUnit.SECONDS)
                        .build();
                Request req = new Request.Builder().url(VERSION_URL).get().build();
                try (Response resp = client.newCall(req).execute()) {
                    if (!resp.isSuccessful() || resp.body() == null) return;
                    JSONObject json   = new JSONObject(resp.body().string());
                    final int    latest  = json.optInt("latest_apk_version", 0);
                    final String apkUrl  = json.optString("apk_download_url", "");
                    final String notes   = json.optString("release_notes", "");

                    int current = BuildConfig.VERSION_CODE;
                    Log.i(TAG, "current=" + current + " latest=" + latest);

                    // 已是最新版 → 不需提示
                    if (latest <= current || apkUrl.isEmpty()) return;

                    SharedPreferences prefs =
                            ctx.getSharedPreferences("EEGAppFile", Context.MODE_PRIVATE);

                    // 若安裝成功（current 已追上 triggered），清掉舊記錄
                    int triggered = prefs.getInt(TRIGGERED_KEY, 0);
                    if (triggered > 0 && current >= triggered) {
                        prefs.edit().remove(TRIGGERED_KEY).apply();
                        triggered = 0;
                    }

                    if (!force) {
                        // 使用者選「略過此版」
                        if (prefs.getInt(SKIP_KEY, 0) >= latest) {
                            Log.i(TAG, "已略過版本 " + latest);
                            return;
                        }
                        // 使用者已按「立即更新」（下載可能還沒裝完，不重複彈）
                        if (triggered >= latest) {
                            Log.i(TAG, "已觸發下載版本 " + triggered + "，不重複彈");
                            return;
                        }
                        // 🆕 持久化 cooldown：同版本 30 分鐘內已彈過 → 不再彈
                        // 解決：平板旋轉重建 Activity / 系統 kill process 後重複彈
                        long lastShownTs   = prefs.getLong(LAST_SHOWN_TS, 0L);
                        int  lastShownVer  = prefs.getInt(LAST_SHOWN_VER, 0);
                        long now           = System.currentTimeMillis();
                        if (lastShownVer == latest && (now - lastShownTs) < COOLDOWN_MS) {
                            long remainSec = (COOLDOWN_MS - (now - lastShownTs)) / 1000;
                            Log.i(TAG, "版本 " + latest + " 在 cooldown 內（剩 " + remainSec + " 秒），不重複彈");
                            return;
                        }
                    }

                    sDialogShownThisSession = true;
                    // 寫入持久化 cooldown 戳記
                    prefs.edit()
                         .putLong(LAST_SHOWN_TS, System.currentTimeMillis())
                         .putInt(LAST_SHOWN_VER, latest)
                         .apply();
                    new Handler(Looper.getMainLooper()).post(() ->
                            showUpdateDialog(ctx, latest, apkUrl, notes));
                }
            } catch (Throwable t) {
                Log.w(TAG, "checkForUpdate", t);
            }
        }, "AppUpdater-Check").start();
    }

    private static void showUpdateDialog(final Context ctx, final int latest,
                                         final String apkUrl, final String notes) {
        // 取得當前版本作為比對
        int current = BuildConfig.VERSION_CODE;
        String currentName = BuildConfig.VERSION_NAME;

        String body = (notes.isEmpty()
                ? "本次更新包含重要修正，建議立即升級。"
                : notes);

        // 多加一段「操作引導」，讓加盟商不會在「安裝」那個系統畫面卡住
        String guide =
                "\n\n📲 升級流程（共需 2 次點擊）：\n" +
                "  ① 點下方【立即更新】按鈕\n" +
                "  ② 等瀏覽器下載完成（約 30~60 秒）\n" +
                "  ③ 系統會自動彈出安裝確認 → 點【安裝】即可\n" +
                "\n💡 安裝後請重新打開「腦波檢測系統」APP，會自動啟動新版本。";

        new AlertDialog.Builder(ctx)
                .setTitle("🆕 發現新版本 v" + latest +
                          "（目前 v" + current + " / " + currentName + "）")
                .setMessage(body + guide)
                .setCancelable(false)
                .setPositiveButton("立即更新（推薦）", (d, w) -> {
                    // 持久化記錄：已觸發下載，重開 App 不再重複彈
                    ctx.getSharedPreferences("EEGAppFile", Context.MODE_PRIVATE)
                            .edit().putInt(TRIGGERED_KEY, latest).apply();
                    openBrowserDownload(ctx, apkUrl);
                    // 顯示「升級進行中」追蹤對話框，給加盟商明確指引
                    new Handler(Looper.getMainLooper()).postDelayed(
                            () -> showDownloadingDialog(ctx, latest, apkUrl), 800);
                })
                .setNeutralButton("稍後再說", (d, w) -> d.dismiss())
                .setNegativeButton("略過此版", (d, w) ->
                        ctx.getSharedPreferences("EEGAppFile", Context.MODE_PRIVATE)
                                .edit().putInt(SKIP_KEY, latest).apply())
                .show();
    }

    /**
     * 用瀏覽器開啟 APK 下載連結。
     * 相比 DownloadManager + FileProvider，此方式在小米 MIUI / EMUI / ColorOS
     * 上更可靠：系統瀏覽器下載完後會自動彈出安裝提示。
     */
    private static void openBrowserDownload(final Context ctx, final String apkUrl) {
        try {
            Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(apkUrl));
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            ctx.startActivity(intent);
        } catch (Throwable t) {
            Log.e(TAG, "openBrowserDownload", t);
        }
    }

    /**
     * 「升級進行中」追蹤對話框：解決加盟商「點完立即更新後不知道是否還在跑」的問題。
     * 流程：
     *  1. 顯示明確的當前狀態（瀏覽器已開、下載中、需要做什麼）
     *  2. 提供「我已下載完成」「再次開啟下載」「我已完成安裝（重新啟動）」按鈕
     *  3. setCancelable(false) 避免使用者誤點返回鍵把對話框關掉
     */
    private static void showDownloadingDialog(final Context ctx, final int latest, final String apkUrl) {
        try {
            String msg =
                "📥 已開啟系統瀏覽器下載新版本 APK\n" +
                "（檔案約 8 MB，依網速約需 30~60 秒）\n" +
                "\n" +
                "🔔 下載完成後，會發生以下事情：\n" +
                "  ① 系統會在「通知欄」顯示「下載完成」\n" +
                "  ② 點該通知，會自動跳出安裝畫面\n" +
                "  ③ 點【安裝】按鈕\n" +
                "  ④ 安裝完成後，重新打開 APP\n" +
                "\n" +
                "💡 找不到下載進度？\n" +
                "請從手機頂端往下滑開啟「通知欄」查看，\n" +
                "或切換到瀏覽器 APP（Chrome、小米瀏覽器）。\n" +
                "\n" +
                "⚠️ 在更新完成前，請勿關閉此對話框";

            new AlertDialog.Builder(ctx)
                .setTitle("⏳ 升級進行中 → v" + latest)
                .setMessage(msg)
                .setCancelable(false)
                .setPositiveButton("✅ 我已完成安裝（關閉舊版）", (d, w) -> {
                    // 使用者已在系統那邊裝完新版，告訴他重新開 APP
                    new AlertDialog.Builder(ctx)
                            .setTitle("✅ 升級流程已完成")
                            .setMessage("請從「桌面」或「最近使用」重新打開「腦波檢測系統」APP，\n" +
                                        "新版本就會啟動。\n\n" +
                                        "（若仍是舊版，代表還沒裝完，請先到通知欄完成安裝）")
                            .setPositiveButton("好的，我去重開 APP", null)
                            .show();
                })
                .setNeutralButton("🔄 再次開啟下載連結", (d, w) -> {
                    openBrowserDownload(ctx, apkUrl);
                    // 重新顯示這個追蹤對話框
                    new Handler(Looper.getMainLooper()).postDelayed(
                            () -> showDownloadingDialog(ctx, latest, apkUrl), 800);
                })
                .setNegativeButton("稍後再說（保留進度）", (d, w) -> d.dismiss())
                .show();
        } catch (Throwable t) {
            Log.e(TAG, "showDownloadingDialog", t);
        }
    }
}
