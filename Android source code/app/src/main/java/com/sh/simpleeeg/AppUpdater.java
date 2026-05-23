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

    private static final String SKIP_KEY      = "skip_apk_version";
    private static final String TRIGGERED_KEY = "update_triggered_version";

    /** process 內只彈一次 */
    private static volatile boolean sDialogShownThisSession = false;

    /**
     * @param force true = 忽略 skip/triggered 記錄，強制顯示（給「檢查更新」按鈕用）
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
                    }

                    sDialogShownThisSession = true;
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
        new AlertDialog.Builder(ctx)
                .setTitle("發現新版本 (v" + latest + ")")
                .setMessage((notes.isEmpty()
                        ? "有更新可用，建議立即更新以取得最新功能與修正。"
                        : notes)
                        + "\n\n點「立即更新」後會開啟瀏覽器下載，下載完請點安裝。")
                .setCancelable(false)
                .setPositiveButton("立即更新", (d, w) -> {
                    // 持久化記錄：已觸發下載，重開 App 不再重複彈
                    ctx.getSharedPreferences("EEGAppFile", Context.MODE_PRIVATE)
                            .edit().putInt(TRIGGERED_KEY, latest).apply();
                    openBrowserDownload(ctx, apkUrl);
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
}
