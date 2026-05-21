package com.sh.simpleeeg;

import android.app.AlertDialog;
import android.app.DownloadManager;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.net.Uri;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;

import androidx.core.content.FileProvider;

import org.json.JSONObject;

import java.io.File;
import java.io.IOException;
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
 *   4. 使用者按「立即更新」→ DownloadManager 下載 APK 到 app cache
 *   5. 下載完 → FileProvider URI + ACTION_VIEW + apk MIME type → 觸發系統安裝程式
 *
 * 加盟商只需要點「更新」就能裝新版，免去自己找檔案、開啟未知來源等步驟。
 */
public class AppUpdater {

    private static final String TAG = "AppUpdater";

    private static final String VERSION_URL =
            "https://backend-production-2da61.up.railway.app/api/v1/app/version";

    private static final String SKIP_KEY = "skip_apk_version";

    /**
     * @param force 為 true 時忽略「使用者按過稍後再說」，強制檢查（例如使用者點「檢查更新」按鈕）
     */
    public static void checkForUpdate(final Context ctx, final boolean force) {
        new Thread(() -> {
            try {
                OkHttpClient client = new OkHttpClient.Builder()
                        .connectTimeout(8, TimeUnit.SECONDS)
                        .readTimeout(8, TimeUnit.SECONDS)
                        .build();
                Request req = new Request.Builder().url(VERSION_URL).get().build();
                try (Response resp = client.newCall(req).execute()) {
                    if (!resp.isSuccessful() || resp.body() == null) return;
                    JSONObject json = new JSONObject(resp.body().string());
                    final int    latest      = json.optInt("latest_apk_version", 0);
                    final String htmlVersion = json.optString("html_version", "");
                    final String apkUrl      = json.optString("apk_download_url", "");
                    final String notes       = json.optString("release_notes", "");

                    int current = BuildConfig.VERSION_CODE;
                    Log.i(TAG, "current=" + current + " latest=" + latest + " html=" + htmlVersion);

                    if (latest <= current || apkUrl.isEmpty()) return;

                    if (!force) {
                        int skipped = ctx.getSharedPreferences("EEGAppFile", Context.MODE_PRIVATE)
                                .getInt(SKIP_KEY, 0);
                        if (skipped >= latest) {
                            Log.i(TAG, "使用者已選擇略過版本 " + skipped);
                            return;
                        }
                    }

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
                .setMessage(notes.isEmpty()
                        ? "有更新可用，建議立即更新以取得最新功能與修正。"
                        : notes)
                .setCancelable(false)
                .setPositiveButton("立即更新", (d, w) -> downloadAndInstall(ctx, apkUrl))
                .setNeutralButton("稍後再說", (d, w) -> d.dismiss())
                .setNegativeButton("略過此版", (d, w) -> {
                    ctx.getSharedPreferences("EEGAppFile", Context.MODE_PRIVATE)
                            .edit().putInt(SKIP_KEY, latest).apply();
                })
                .show();
    }

    private static void downloadAndInstall(final Context ctx, final String apkUrl) {
        try {
            File apkDir = new File(ctx.getCacheDir(), "apk");
            if (!apkDir.exists() && !apkDir.mkdirs()) {
                Log.w(TAG, "mkdir failed: " + apkDir);
            }
            File apkFile = new File(apkDir, "update.apk");
            if (apkFile.exists()) apkFile.delete();

            final DownloadManager dm =
                    (DownloadManager) ctx.getSystemService(Context.DOWNLOAD_SERVICE);
            if (dm == null) return;

            DownloadManager.Request req = new DownloadManager.Request(Uri.parse(apkUrl))
                    .setTitle("腦波檢測系統更新")
                    .setDescription("正在下載新版 APK ...")
                    .setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE)
                    .setDestinationUri(Uri.fromFile(apkFile))
                    .setMimeType("application/vnd.android.package-archive");
            req.setAllowedOverMetered(true);
            req.setAllowedOverRoaming(true);

            final long id = dm.enqueue(req);

            // 監聽下載完成
            BroadcastReceiver receiver = new BroadcastReceiver() {
                @Override
                public void onReceive(Context context, Intent intent) {
                    long doneId = intent.getLongExtra(DownloadManager.EXTRA_DOWNLOAD_ID, -1);
                    if (doneId != id) return;
                    ctx.unregisterReceiver(this);

                    DownloadManager.Query q = new DownloadManager.Query().setFilterById(id);
                    Cursor c = dm.query(q);
                    if (c != null && c.moveToFirst()) {
                        int status = c.getInt(c.getColumnIndex(DownloadManager.COLUMN_STATUS));
                        c.close();
                        if (status != DownloadManager.STATUS_SUCCESSFUL) {
                            Log.w(TAG, "download failed status=" + status);
                            return;
                        }
                    }
                    triggerInstall(ctx, apkFile);
                }
            };
            // Android 14 (API 34+) 要求明確指定 RECEIVER_NOT_EXPORTED
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                ctx.registerReceiver(receiver,
                        new IntentFilter(DownloadManager.ACTION_DOWNLOAD_COMPLETE),
                        Context.RECEIVER_NOT_EXPORTED);
            } else {
                ctx.registerReceiver(receiver,
                        new IntentFilter(DownloadManager.ACTION_DOWNLOAD_COMPLETE));
            }
        } catch (Throwable t) {
            Log.e(TAG, "downloadAndInstall", t);
        }
    }

    private static void triggerInstall(Context ctx, File apkFile) {
        try {
            // Android 8.0+ 需要 REQUEST_INSTALL_PACKAGES + 使用者授權「安裝未知來源」
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                PackageManager pm = ctx.getPackageManager();
                if (!pm.canRequestPackageInstalls()) {
                    // 跳到設定頁，讓使用者勾選允許本 App 安裝
                    Intent setting = new Intent(
                            android.provider.Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                            Uri.parse("package:" + ctx.getPackageName()));
                    setting.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                    ctx.startActivity(setting);
                    return;
                }
            }

            Uri apkUri = FileProvider.getUriForFile(
                    ctx,
                    ctx.getPackageName() + ".fileprovider",
                    apkFile);
            Intent install = new Intent(Intent.ACTION_VIEW);
            install.setDataAndType(apkUri, "application/vnd.android.package-archive");
            install.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION
                    | Intent.FLAG_ACTIVITY_NEW_TASK
                    | Intent.FLAG_ACTIVITY_CLEAR_TOP);
            ctx.startActivity(install);
        } catch (Throwable t) {
            Log.e(TAG, "triggerInstall", t);
        }
    }
}
