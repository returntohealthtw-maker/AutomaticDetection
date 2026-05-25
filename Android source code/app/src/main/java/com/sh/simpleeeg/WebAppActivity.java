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

            // target="_blank" 連結（PDF 預覽、外部付款頁）→ 用系統瀏覽器開啟
            @Override
            public boolean onCreateWindow(WebView view, boolean isDialog,
                                          boolean isUserGesture, android.os.Message resultMsg) {
                WebView.HitTestResult result = view.getHitTestResult();
                String url = result.getExtra();
                if (url != null && !url.isEmpty()) {
                    try {
                        Intent i = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                        i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                        startActivity(i);
                    } catch (Throwable t) {
                        android.util.Log.e("WebAppActivity", "onCreateWindow open url", t);
                    }
                }
                return false;
            }
        });

        // 允許 WebView 彈出新視窗（讓 onCreateWindow 能被觸發）
        webView.getSettings().setSupportMultipleWindows(true);

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

                // ── 啟動腦波檢測畫面 ────────────────────────────────────────
                // test.class 本身有完整的掃描/連線 UI（圖2），負責處理 BrainLink 連線。
                // 這裡只檢查：藍牙開啟 + 有必要權限；其餘交給 test.class 自己處理。
                // 舊的 isBrainwaveReady()（含 bConnected() 檢查）太嚴格，會在 GATT
                // 握手後 ThinkGear 資料流尚未啟動的 3-5 秒內誤判「未就緒」並彈對話框。
                if (!isBluetoothOnAndPermitted()) {
                    showBrainwaveNotReadyDialog(subjectName, reportType, orderId);
                } else {
                    connectBrainwaveSafely(); // 預先嘗試連線（加速 test.class 內的掃描）
                    launchBrainwaveActivity(subjectName, reportType, orderId);
                }
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
         * HTML screen-detect 進入時呼叫。
         * 啟動 CLS_BrainWave 並將每秒一筆的腦波資料透過 evaluateJavascript
         * 推入 WebApp：window.JSBridge.onEegSample({attn,medi,delta,theta,alpha,beta,gamma})
         * 如此 screen-detect 就能顯示真實資料，不再需要跳到 test.class。
         */
        @JavascriptInterface
        public void startStreamingEeg() {
            new Handler(Looper.getMainLooper()).post(() -> {
                try {
                    if (ble == null) ble = new CLS_BrainWave();
                    ble.SetCallback((cmd, val) -> {
                        CLS_PARAM sp = new CLS_PARAM();
                        if (cmd == sp.BrainwaveValue) {
                            int attn  = CLS_DATA.iAttention;
                            int medi  = CLS_DATA.iMeditation;
                            int delta = bandTo100(CLS_DATA.iDelta);
                            int theta = bandTo100(CLS_DATA.iTheta);
                            int alpha = bandTo100((CLS_DATA.iLowAlpha + CLS_DATA.iHighAlpha) / 2);
                            int beta  = bandTo100((CLS_DATA.iLowBeta  + CLS_DATA.iHighBeta)  / 2);
                            int gamma = bandTo100((CLS_DATA.iLowGamma + CLS_DATA.iHighGamma) / 2);
                            int bat   = ble.getBatteryLevel();
                            String json = String.format(
                                "{\"attn\":%d,\"medi\":%d,\"delta\":%d,\"theta\":%d," +
                                "\"alpha\":%d,\"beta\":%d,\"gamma\":%d,\"bat\":%d}",
                                attn, medi, delta, theta, alpha, beta, gamma, bat);
                            webView.post(() -> webView.evaluateJavascript(
                                "window.JSBridge&&window.JSBridge.onEegSample('" + json + "')", null));
                        }
                    });
                    ble.Connect(WebAppActivity.this);
                } catch (Throwable t) {
                    android.util.Log.e("WebAppActivity", "startStreamingEeg", t);
                }
            });
        }

        /** screen-detect 離開（結束採集）時呼叫，停止推送並恢復空 callback。 */
        @JavascriptInterface
        public void stopStreamingEeg() {
            new Handler(Looper.getMainLooper()).post(() -> {
                try {
                    if (ble != null) ble.SetCallback((cmd, val) -> { /* idle */ });
                } catch (Throwable t) {
                    android.util.Log.e("WebAppActivity", "stopStreamingEeg", t);
                }
            });
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

            java.util.List<String> need = new java.util.ArrayList<>();

            // ── Android 6 ~ 11（API 23~30）：BLE 掃描需要 LOCATION 權限 ──
            //   小米/紅米/OPPO 等 OEM 沒有這個權限會 silently fail，
            //   getBondedDevices() 取得到裝置但 GATT 連線失敗 → 電量顯示「--」。
            if (Build.VERSION.SDK_INT <= 30) {
                if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)
                        != PackageManager.PERMISSION_GRANTED) {
                    need.add(Manifest.permission.ACCESS_FINE_LOCATION);
                }
                if (checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION)
                        != PackageManager.PERMISSION_GRANTED) {
                    need.add(Manifest.permission.ACCESS_COARSE_LOCATION);
                }
            }

            // ── 儲存權限（Android 9 及以下需要）──
            if (Build.VERSION.SDK_INT <= 28) {
                if (checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE)
                        != PackageManager.PERMISSION_GRANTED) {
                    need.add(Manifest.permission.WRITE_EXTERNAL_STORAGE);
                }
            }

            // ── Android 12+（API 31）BLE 新權限模型 ──
            if (Build.VERSION.SDK_INT >= 31) {
                if (checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT)
                        != PackageManager.PERMISSION_GRANTED) {
                    need.add(Manifest.permission.BLUETOOTH_CONNECT);
                }
                if (checkSelfPermission(Manifest.permission.BLUETOOTH_SCAN)
                        != PackageManager.PERMISSION_GRANTED) {
                    need.add(Manifest.permission.BLUETOOTH_SCAN);
                }
            }

            if (!need.isEmpty()) {
                ActivityCompat.requestPermissions(this,
                        need.toArray(new String[0]), REQ_PERMISSION_BLE);
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
     * BrainLink 頻帶原始功率值（0 ~ ~1,000,000）→ 0-100 log 正規化。
     * log10(1+1)≈0.3 → ~5；log10(100001)≈5 → ~83；log10(1000001)≈6 → 100
     */
    private int bandTo100(int raw) {
        if (raw <= 0) return 0;
        double normalized = Math.log10(raw + 1) / 6.0 * 100.0;
        return (int) Math.max(0, Math.min(100, normalized));
    }

    /**
     * 只檢查「藍牙是否開啟 + 有沒有 BLUETOOTH_CONNECT 權限」。
     * 不檢查 ThinkGear 資料流狀態（bConnected()），
     * 因為 test.class 本身有連線掃描 UI，會自己處理 EEG 連線。
     */
    private boolean isBluetoothOnAndPermitted() {
        try {
            if (Build.VERSION.SDK_INT >= 31) {
                if (checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT)
                        != PackageManager.PERMISSION_GRANTED) return false;
            }
            BluetoothAdapter adapter = BluetoothAdapter.getDefaultAdapter();
            return adapter != null && adapter.isEnabled();
        } catch (Throwable t) {
            return false;
        }
    }

    /**
     * 完整就緒檢查（藍牙 + 權限 + ThinkGear 資料流已建立）。
     * 僅供 isBrainwaveConnected() JavascriptInterface 使用（狀態列電量顯示）。
     */
    private boolean isBrainwaveReady() {
        try {
            if (!isBluetoothOnAndPermitted()) return false;
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
                    // 只要藍牙開啟就直接啟動 test.class（它自己有連線 UI）
                    new Handler(Looper.getMainLooper()).postDelayed(() -> {
                        if (isBluetoothOnAndPermitted()) {
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

    /**
     * 每秒輪詢腦波儀是否就緒，最多重試 maxRetries 次。
     * 就緒 → 直接啟動；用完次數 → 再顯示「未就緒」對話框。
     * 這解決了 BrainLink 「逼逼兩聲」後 ThinkGear 資料流需要額外 3-5 秒才啟動的問題。
     */
    private void pollBrainwaveReady(final String subjectName,
                                    final String reportType,
                                    final String orderId,
                                    final int remainingRetries) {
        if (remainingRetries <= 0) {
            showBrainwaveNotReadyDialog(subjectName, reportType, orderId);
            return;
        }
        new Handler(Looper.getMainLooper()).postDelayed(() -> {
            if (isBrainwaveReady()) {
                launchBrainwaveActivity(subjectName, reportType, orderId);
            } else {
                pollBrainwaveReady(subjectName, reportType, orderId, remainingRetries - 1);
            }
        }, 1000);
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
