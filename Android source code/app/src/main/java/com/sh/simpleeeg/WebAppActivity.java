package com.sh.simpleeeg;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.ActivityInfo;
import android.graphics.Bitmap;
import android.net.http.SslError;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.KeyEvent;
import android.view.View;
import android.view.WindowManager;
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

public class WebAppActivity extends Activity {

    private static final String APP_URL =
            "https://backend-production-2da61.up.railway.app/app";

    private static final int REQUEST_BRAINWAVE = 101;

    private WebView webView;
    private ProgressBar progressBar;
    private TextView tvLoading;

    private final CLS_DATA clsData = new CLS_DATA();

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

        // 啟動藍牙連線（在背景嘗試連線 EEG 裝置）
        try {
            CLS_BrainWave ble = new CLS_BrainWave();
            ble.Connect(this);
        } catch (Exception ignored) {}

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
        webView.loadUrl(APP_URL);
    }

    @SuppressLint("SetJavaScriptEnabled")
    private void setupWebView() {
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setCacheMode(WebSettings.LOAD_DEFAULT);
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
                view.loadUrl(req.getUrl().toString());
                return true;
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

                // 啟動腦波檢測 Activity（test.java）
                Intent intent = new Intent(WebAppActivity.this, test.class);
                intent.putExtra("subjectName", subjectName);
                intent.putExtra("reportType",  reportType);
                intent.putExtra("orderId",     orderId);
                startActivityForResult(intent, REQUEST_BRAINWAVE);
                overridePendingTransition(0, 0);
            });
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
    protected void onDestroy() { webView.destroy(); super.onDestroy();  }
}
