package com.sh.simpleeeg;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.AlertDialog;
import android.bluetooth.BluetoothAdapter;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.ActivityInfo;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.net.Uri;
import android.net.http.SslError;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.KeyEvent;
import android.view.View;
import android.view.WindowManager;
import android.webkit.CookieManager;
import android.webkit.JavascriptInterface;
import android.webkit.SslErrorHandler;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.ProgressBar;
import android.widget.RelativeLayout;
import android.widget.TextView;

import androidx.core.app.ActivityCompat;

import com.sh.simpleeeg.BuildConfig;

public class WebAppActivity extends Activity {

    private static final String APP_URL =
            "https://backend-production-2da61.up.railway.app/app";

    private static final int REQUEST_BRAINWAVE = 101;

    private WebView webView;
    private ProgressBar progressBar;
    private TextView tvLoading;

    private final CLS_DATA clsData = new CLS_DATA();

    /** 全域單一藍牙物件，否則每次 new CLS_BrainWave 雖然 static thread 還在，
     *  但 m_Callback / clsEeg 可能被 GC，導致連線資訊遺失。 */
    private CLS_BrainWave ble;

    private static final int REQ_PERMISSION_BLE     = 1111;
    private static final int REQ_PERMISSION_STORAGE = 1;

    @SuppressLint({"SetJavaScriptEnabled", "SourceLockedOrientationActivity"})
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        getWindow().addFlags(
                WindowManager.LayoutParams.FLAG_FULLSCREEN |
                WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON
        );
        setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_PORTRAIT);

        // 初始化資料庫（只需執行一次）
        CLS_DB.getInstance().init(this);

        // 讀取顧問姓名
        SharedPreferences pref = getSharedPreferences("EEGAppFile", MODE_PRIVATE);
        String consultant = pref.getString("ConsultantName", "顧問");
        clsData.setTeacherName(consultant);
        CLS_DB.getInstance().setConsultantName(consultant);

        // 先請求權限 → 再嘗試藍牙連線（首次安裝最關鍵的一步）
        ensureRuntimePermissions();
        connectBrainwaveSafely();

        // 啟動時自動檢查 APK 是否有新版（背景執行，不阻塞主畫面）
        try {
            AppUpdater.checkForUpdate(this, false);
        } catch (Throwable t) {
            android.util.Log.w("WebAppActivity", "checkForUpdate", t);
        }

        // 建立 Layout
        RelativeLayout root = new RelativeLayout(this);
        root.setBackgroundColor(0xFF1a1a2e);

        webView = new WebView(this);
        root.addView(webView, new RelativeLayout.LayoutParams(
                RelativeLayout.LayoutParams.MATCH_PARENT,
                RelativeLayout.LayoutParams.MATCH_PARENT));

        // 載入中提示
        tvLoading = new TextView(this);
        tvLoading.setText("🧠 腦波檢測系統載入中...");
        tvLoading.setTextColor(0xFFFFFFFF);
        tvLoading.setTextSize(16f);
        RelativeLayout.LayoutParams lp = new RelativeLayout.LayoutParams(
                RelativeLayout.LayoutParams.WRAP_CONTENT,
                RelativeLayout.LayoutParams.WRAP_CONTENT);
        lp.addRule(RelativeLayout.CENTER_IN_PARENT);
        root.addView(tvLoading, lp);

        // 進度條
        progressBar = new ProgressBar(this, null,
                android.R.attr.progressBarStyleHorizontal);
        progressBar.setMax(100);
        progressBar.setProgressTintList(
                android.content.res.ColorStateList.valueOf(0xFF00BCD4));
        RelativeLayout.LayoutParams pbLp = new RelativeLayout.LayoutParams(
                RelativeLayout.LayoutParams.MATCH_PARENT, 8);
        pbLp.addRule(RelativeLayout.ALIGN_PARENT_TOP);
        root.addView(progressBar, pbLp);

        setContentView(root);
        setupWebView();

        // 每次啟動 App 都清掉 WebView 快取，確保拿到最新前端版本
        // （加盟商不用重灌 APK，就能拿到最新的網頁邏輯／報告版型）
        try {
            webView.clearCache(true);
            webView.clearHistory();
            CookieManager.getInstance().removeAllCookies(null);
        } catch (Throwable t) {
            android.util.Log.w("WebAppActivity", "clearCache failed", t);
        }

        // 啟動載入時加上時間戳 query 強制破壞中介快取
        webView.loadUrl(APP_URL + "?t=" + System.currentTimeMillis());
    }

    @SuppressLint("SetJavaScriptEnabled")
    private void setupWebView() {
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        // 改用 LOAD_NO_CACHE：每次都向 server 拉最新 HTML/JS，達到「網頁自動更新」
        s.setCacheMode(WebSettings.LOAD_NO_CACHE);
        s.setLoadWithOverviewMode(true);
        s.setUseWideViewPort(true);
        s.setBuiltInZoomControls(false);
        s.setDisplayZoomControls(false);
        s.setSupportZoom(false);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);

        // 注入 Android Bridge（讓 HTML 可以呼叫原生功能）
        webView.addJavascriptInterface(new AndroidBridge(), "AndroidBridge");

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onProgressChanged(WebView view, int p) {
                progressBar.setProgress(p);
                progressBar.setVisibility(p == 100 ? View.GONE : View.VISIBLE);
            }
        });

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageStarted(WebView view, String url, Bitmap fav) {
                progressBar.setVisibility(View.VISIBLE);
                tvLoading.setVisibility(View.VISIBLE);
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                progressBar.setVisibility(View.GONE);
                tvLoading.setVisibility(View.GONE);
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view,
                                                    WebResourceRequest req) {
                return false;
            }

            @Override
            public void onReceivedSslError(WebView view,
                                           SslErrorHandler handler, SslError e) {
                handler.proceed();
            }

            @Override
            public void onReceivedError(WebView view, int code,
                                        String desc, String url) {
                view.loadData(
                    "<html><body style='background:#1a1a2e;color:white;" +
                    "text-align:center;padding-top:40%;font-family:sans-serif;'>" +
                    "<div style='font-size:48px'>🌐</div>" +
                    "<h2>無法連線</h2><p>請確認網路後重試</p>" +
                    "<button onclick='location.reload()' style='margin-top:20px;" +
                    "padding:12px 32px;font-size:16px;background:#00BCD4;" +
                    "color:white;border:none;border-radius:12px;'>重新載入</button>" +
                    "</body></html>",
                    "text/html", "UTF-8");
            }
        });
    }

    // ── Android Bridge：讓 HTML 付款成功後呼叫原生腦波檢測 ─────────────────────
    private class AndroidBridge {

        /**
         * HTML 付款成功後呼叫此方法，啟動原生腦波檢測流程
         *
         * @param subjectName 受測者姓名
         * @param reportType  報告類型（life_trial / test_1 ...）
         * @param orderId     綠界訂單編號
         */
        @JavascriptInterface
        public void startBrainwaveDetection(final String subjectName,
                                            final String reportType,
                                            final String orderId) {
            // JavaScript 是在子執行緒呼叫的，需要回到主執行緒操作 UI / Intent
            new Handler(Looper.getMainLooper()).post(() -> {
                // 儲存受測者資訊到全域 CLS_DATA
                clsData.setSubjectName(subjectName);
                clsData.setReportType(reportType);
                clsData.setOrderId(orderId);
                CLS_DB.getInstance().setConsultantName(
                        clsData.strGetTeacherName()
                );

                // 設定錄製時間（正式 3 分鐘，test_1 使用 1 分鐘快速測試）
                clsData.listRecordingTime().clear();
                clsData.ClearListSectionData();
                int minutes = "test_1".equals(reportType) ? 1 : 3;
                CLS_RECORDING_TIME rt = new CLS_RECORDING_TIME(0, 0, 0, minutes);
                clsData.listRecordingTime().add(rt);
                clsData.NewListSectionData();

                // ── 連線檢查：避免「跑 3 分鐘卻沒有任何訊號」的空轉檢測 ─────
                if (!isBrainwaveReady()) {
                    showBrainwaveNotReadyDialog(subjectName, reportType, orderId);
                    return;
                }

                launchBrainwaveActivity(subjectName, reportType, orderId);
            });
        }

        /** HTML 端可隨時詢問腦波儀是否已就緒（藍牙開啟+權限+裝置已配對+連線中） */
        @JavascriptInterface
        public boolean isBrainwaveConnected() {
            return isBrainwaveReady();
        }

        /** 由 HTML 呼叫主動嘗試重連（使用者按「重新連線腦波儀」時） */
        @JavascriptInterface
        public void reconnectBrainwave() {
            new Handler(Looper.getMainLooper()).post(() -> connectBrainwaveSafely());
        }

        /**
         * 回傳腦波儀目前電量（0-100）；未連線或無資料時回傳 -1。
         * HTML 每 10 秒輪詢一次，顯示在 status bar 右上角。
         */
        @JavascriptInterface
        public int getDeviceBattery() {
            if (ble == null) return -1;
            return ble.getBatteryLevel();
        }

        /** 供 HTML 查詢顧問姓名 */
        @JavascriptInterface
        public String getConsultantName() {
            return clsData.strGetTeacherName();
        }

        /** 供 HTML 取得後端 URL（動態切換測試/正式環境） */
        @JavascriptInterface
        public String getBackendUrl() {
            return "https://backend-production-2da61.up.railway.app";
        }

        /**
         * Debug 組建顯示「開發測試／模擬付款」；Release（加盟商版）隱藏。
         */
        @JavascriptInterface
        public boolean isDebugBuild() {
            return BuildConfig.DEBUG;
        }

        /**
         * 點「立即付款」時 HTML 會呼叫這個方法。
         * 我們用系統瀏覽器（Chrome）開付款頁，避免在 WebView 內遇到
         * 第三方金流頁面（PayUni / ECPay）相容性問題。
         * 付款完成後使用者回到 App，輪詢機制會立即偵測到 paid 狀態。
         */
        @JavascriptInterface
        public void openPayUrl(final String url) {
            if (url == null || url.isEmpty()) return;
            new Handler(Looper.getMainLooper()).post(() -> {
                try {
                    Intent i = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                    i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                    startActivity(i);
                } catch (Throwable t) {
                    android.util.Log.e("WebAppActivity", "openPayUrl", t);
                }
            });
        }

        /** 顯示版本資訊（debug 用） */
        @JavascriptInterface
        public String getAppInfo() {
            try {
                return "versionName=" + BuildConfig.VERSION_NAME
                     + ";versionCode=" + BuildConfig.VERSION_CODE;
            } catch (Throwable t) { return ""; }
        }
    }

    /** 腦波檢測完成後回到 WebApp，重新載入首頁 */
    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == REQUEST_BRAINWAVE) {
            // 回到 WebApp，顯示完成畫面（重新載入）
            webView.loadUrl(APP_URL + "#screen-home");
        }
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_BACK && webView.canGoBack()) {
            webView.goBack();
            return true;
        }
        return super.onKeyDown(keyCode, event);
    }

    @Override
    protected void onPause()   { super.onPause();   webView.onPause();  }
    @Override
    protected void onResume()  { super.onResume();  webView.onResume(); }
    @Override
    protected void onDestroy() {
        if (webView != null) {
            webView.destroy();
            webView = null;
        }
        super.onDestroy();
    }

    // ═══════════════════════════════════════════════════════════════════
    //  權限請求（Android 12+ 必須動態要 BLUETOOTH_CONNECT/SCAN，否則
    //  ble.Connect() 會 silently fail，使用者付完款後腦波儀完全連不上）
    // ═══════════════════════════════════════════════════════════════════
    private void ensureRuntimePermissions() {
        try {
            if (Build.VERSION.SDK_INT < 23) return;

            if (Build.VERSION.SDK_INT <= 29) {
                if (checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE)
                        != PackageManager.PERMISSION_GRANTED) {
                    ActivityCompat.requestPermissions(this, new String[]{
                            Manifest.permission.READ_EXTERNAL_STORAGE,
                            Manifest.permission.WRITE_EXTERNAL_STORAGE
                    }, REQ_PERMISSION_STORAGE);
                }
            } else {
                java.util.List<String> need = new java.util.ArrayList<>();
                if (checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT)
                        != PackageManager.PERMISSION_GRANTED) {
                    need.add(Manifest.permission.BLUETOOTH_CONNECT);
                }
                if (checkSelfPermission(Manifest.permission.BLUETOOTH_SCAN)
                        != PackageManager.PERMISSION_GRANTED) {
                    need.add(Manifest.permission.BLUETOOTH_SCAN);
                }
                if (!need.isEmpty()) {
                    ActivityCompat.requestPermissions(this,
                            need.toArray(new String[0]), REQ_PERMISSION_BLE);
                }
            }
        } catch (Throwable t) {
            android.util.Log.e("WebAppActivity", "ensureRuntimePermissions", t);
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == REQ_PERMISSION_BLE || requestCode == REQ_PERMISSION_STORAGE) {
            // 權限結果不論是否全給，都嘗試一次連線；若被拒，後續流程會在
            // startBrainwaveDetection 時跳「未就緒」對話框引導使用者重試
            connectBrainwaveSafely();
        }
    }

    /** 嘗試藍牙連線（容錯：權限不足/藍牙關閉/腦波儀未配對都不會 crash） */
    private void connectBrainwaveSafely() {
        try {
            if (ble == null) ble = new CLS_BrainWave();
            ble.SetCallback((cmd, val) -> { /* 啟動頁不需處理具體訊號 */ });
            ble.Connect(this);
        } catch (Throwable t) {
            android.util.Log.e("WebAppActivity", "connectBrainwaveSafely", t);
        }
    }

    /**
     * 判斷腦波儀是否就緒：
     *  1. Android 12+ 需有 BLUETOOTH_CONNECT 權限
     *  2. 藍牙必須開啟
     *  3. CLS_EEG 已連線（clsRaw.bConnected()）
     */
    private boolean isBrainwaveReady() {
        try {
            if (Build.VERSION.SDK_INT >= 31) {
                if (checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT)
                        != PackageManager.PERMISSION_GRANTED) return false;
            }
            BluetoothAdapter adapter = BluetoothAdapter.getDefaultAdapter();
            if (adapter == null || !adapter.isEnabled()) return false;

            // CLS_BrainWave 內部的 clsEeg 是 instance 欄位，但 bConnected() 走 clsRaw（static）
            CLS_BrainWave probe = (ble != null) ? ble : new CLS_BrainWave();
            return probe.bConnectedSafe();
        } catch (Throwable t) {
            return false;
        }
    }

    /**
     * 腦波儀未就緒時的友善對話框（避免使用者付完款卻看到「空跡 3 分鐘」）。
     * 提供：重新連線 / 仍要繼續 / 取消三個選項。
     */
    private void showBrainwaveNotReadyDialog(final String subjectName,
                                             final String reportType,
                                             final String orderId) {
        BluetoothAdapter adapter = null;
        try { adapter = BluetoothAdapter.getDefaultAdapter(); } catch (Throwable ignore) {}
        boolean btOff = (adapter == null || !adapter.isEnabled());
        boolean noPerm = (Build.VERSION.SDK_INT >= 31)
                && (checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT)
                != PackageManager.PERMISSION_GRANTED);

        String reason;
        if (noPerm)       reason = "尚未授權藍牙連線權限";
        else if (btOff)   reason = "藍牙尚未開啟";
        else              reason = "尚未偵測到腦波儀（請確認 BrainLink/MindWave 已開機並完成藍牙配對）";

        new AlertDialog.Builder(this)
                .setTitle("腦波儀尚未就緒")
                .setMessage("檢測無法立即啟動，原因：\n  " + reason
                        + "\n\n您的付款已完成，可以稍後在此頁面重新開始檢測。")
                .setCancelable(false)
                .setPositiveButton("重新連線", (d, w) -> {
                    if (noPerm) ensureRuntimePermissions();
                    connectBrainwaveSafely();
                    // 隔 1.5 秒再讓使用者點開始（給藍牙握手時間）
                    new Handler(Looper.getMainLooper()).postDelayed(() -> {
                        if (isBrainwaveReady()) {
                            launchBrainwaveActivity(subjectName, reportType, orderId);
                        } else {
                            showBrainwaveNotReadyDialog(subjectName, reportType, orderId);
                        }
                    }, 1500);
                })
                .setNeutralButton("仍要繼續（無腦波訊號）", (d, w) ->
                        launchBrainwaveActivity(subjectName, reportType, orderId))
                .setNegativeButton("稍後再說", (d, w) -> { /* 留在 WebView 首頁 */ })
                .show();
    }

    private void launchBrainwaveActivity(String subjectName, String reportType, String orderId) {
        Intent intent = new Intent(WebAppActivity.this, test.class);
        intent.putExtra("subjectName", subjectName);
        intent.putExtra("reportType",  reportType);
        intent.putExtra("orderId",     orderId);
        startActivityForResult(intent, REQUEST_BRAINWAVE);
        overridePendingTransition(0, 0);
    }
}
