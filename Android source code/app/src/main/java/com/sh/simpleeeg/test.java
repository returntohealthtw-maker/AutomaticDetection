package com.sh.simpleeeg;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ActivityInfo;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Handler;
import android.util.TypedValue;
import android.view.View;
import android.view.WindowManager;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;

import com.bumptech.glide.Glide;
import com.bumptech.glide.request.RequestOptions;

import java.util.ArrayList;
import java.util.Calendar;
import java.util.Date;
import java.util.List;

public class test extends Activity {
    CLS_PARAM S = new CLS_PARAM();
    CLS_BrainWave clsBrainwave = new CLS_BrainWave();
    CLS_DATA clsData = new CLS_DATA();
    CLS_LineChart clsLineChart;

    Context mContext;

    LinearLayout layoutChart;
    View viewLineChart;
    ImageView ivBG,ivStopTest;
    TextView tvCountDown;

    RequestOptions myGdiOptions = new RequestOptions().fitCenter();

    static double dX = 0;

    /** 腦波儀目前是否在送資料；給 ThreadCount 即時顯示「無訊號」警示 */
    static volatile long lLastSignalTimeMs = 0;
    /** 連線狀態文字（顯示在倒數計時下方） */
    static volatile String strLinkState = "等待腦波儀訊號…";
    /** 是否已彈過「無訊號」警告 */
    static volatile boolean bWarnedNoSignal = false;

    static ThreadMsg mThreadMsg;//改用自訂thread方式處理msg,取代原有 static msg 複雜的方式
    static Handler mHandlerMsg = new Handler();
    static List<Integer> listMsg = new ArrayList<Integer>();
    static boolean bQuit = false;

    static private ThreadCount mThreadCount;
    static private Handler mHandlerCount = new Handler();
    static int iRecordingTotalSeconds = 0;

    @SuppressLint("SourceLockedOrientationActivity")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_PORTRAIT);
        setContentView(R.layout.test);

        mContext = this;

        ivBG = (ImageView)findViewById(R.id.ivBG);
        ivStopTest = (ImageView)findViewById(R.id.ivStopTest);
        layoutChart = (LinearLayout)findViewById(R.id.layoutChart);
        tvCountDown = (TextView)findViewById(R.id.tvCountDown);

        tvCountDown.setTextSize(TypedValue.COMPLEX_UNIT_PX, 100f*clsData.fTextScale());

        SetCallback();

        // 重置「無訊號保護」狀態（這些是 static，進入新的場次必須清乾淨）
        lLastSignalTimeMs = 0;
        bWarnedNoSignal   = false;
        strLinkState      = "等待腦波儀訊號…";

        listMsg.clear();
        mThreadMsg = new ThreadMsg();



        if(clsData.listRecordingTime().size() > 0) {
            iRecordingTotalSeconds =
                    //clsData.listRecordingTime().get(clsData.iCurrentSection()).iRecordingMin*10;
                    clsData.listRecordingTime().get(clsData.iCurrentSection()).iRecordingHour*3600
                            + clsData.listRecordingTime().get(clsData.iCurrentSection()).iRecordingMin*60;

            mThreadCount = new ThreadCount();
            mHandlerCount.postDelayed(mThreadCount, 0);

            int iMin = (iRecordingTotalSeconds / 60) % 60;
            String str = String.format("時間  %02d : %02d : %02d",
                    iRecordingTotalSeconds/3600, iMin, iRecordingTotalSeconds%60);
            tvCountDown.setText(str);
            tvCountDown.setVisibility(View.VISIBLE);
        }
        else{
            tvCountDown.setVisibility(View.INVISIBLE);
        }
    }
    @Override
    protected void onStart()
    {
        super.onStart();

        bQuit = false;

        Glide.with(mContext).load(R.drawable.bg_0).apply(myGdiOptions).into(ivBG);
        Glide.with(mContext).load(R.drawable.stop_test).apply(myGdiOptions).into(ivStopTest);

        dX = 0;
        layoutChart.removeAllViews();
        clsLineChart = new CLS_LineChart(2);
        viewLineChart = clsLineChart.viewDrawAppearance(this, true, 30, 100, Color.RED, Color.GREEN, 1.0f);
        layoutChart.addView(viewLineChart,
                new LinearLayout.LayoutParams(
                        LinearLayout.LayoutParams.FILL_PARENT,
                        LinearLayout.LayoutParams.FILL_PARENT));
        clsLineChart.AddPoint(1, 0, 0);//要有資料才有辦法調整大小
        clsLineChart.AddPoint(2, 0, 0);

        clsData.EnableRecording(true);

        // ── 開始新的腦波擷取場次，儲存至資料庫 ─────────────────────────
        CLS_DB.getInstance().setConsultantName(clsData.strGetTeacherName());

        // 優先使用從 WebApp 傳入的受測者姓名（付款時填寫）
        String subjectName = clsData.getSubjectName();
        if (subjectName == null || subjectName.isEmpty()) {
            subjectName = clsData.strName(); // fallback 到舊版填寫欄位
        }
        String reportType = clsData.getReportType();
        if (reportType == null || reportType.isEmpty()) {
            reportType = "adult";
        }

        String gender = (clsData.iGetGender() == 1) ? "M" : "F";
        CLS_DB.getInstance().startSession(
                subjectName,
                clsData.strGetBirthday(),
                gender,
                0,
                reportType,
                null
        );
        // ─────────────────────────────────────────────────────────────────
    }
    @Override
    protected void onResume()
    {
        super.onResume();
    }
    @Override
    protected void onPause()
    {
        super.onPause();
    }
    @Override
    protected void onStop() {
        super.onStop();
        Glide.with(this).clear(ivBG);
        Glide.with(this).clear(ivStopTest);
    }
    @Override
    protected void onDestroy()
    {
        super.onDestroy();
        bQuit = true;
        mHandlerCount.removeCallbacks(mThreadCount);
        clsLineChart = null;
    }
    @Override
    protected void onRestart()
    {
        super.onRestart();
    }
    /*
    @Override
    public void onBackPressed() //不讓user按螢幕左下方的 "退回上一層"
    {
        Intent intent = new Intent();
        intent.setClass(this, Main.class);//input info
        startActivity(intent);
    }
    */
    //==============================================================================================
    //==============================================================================================
    //==============================================================================================
    public void SetCallback() {
        clsBrainwave.SetCallback(new CLS_BrainWave.Brainwave_Callback() {
            //@Override
            public void Do(int iCmd, int iVal) {
                if(iCmd == S.BrainwaveValue) {
                    lLastSignalTimeMs = System.currentTimeMillis();
                    strLinkState = "腦波儀已連線";
                    PostMyMsg(S.BrainwaveValue);
                }
                else if (iCmd == S.SIGNAL_GOOD) {
                    lLastSignalTimeMs = System.currentTimeMillis();
                    strLinkState = "訊號品質良好";
                }
                else if (iCmd == S.BrainwaveConnected) {
                    strLinkState = "腦波儀已連線（訊號擷取中…）";
                }
                else if (iCmd == S.BrainwaveDisconnected) {
                    strLinkState = "⚠ 腦波儀已斷線";
                }
                else if (iCmd == S.BluetoothClosed) {
                    strLinkState = "⚠ 藍牙未開啟或腦波儀未配對";
                }
            }
        });
    }
    //===================================================
    static int iPrevSec = -1;
    private class ThreadCount extends Thread {
        @Override
        public void run() {
            if(bQuit)
                return;

            try {
                Date currentTime = Calendar.getInstance().getTime();
                //int iHour = currentTime.getHours();
                //int iMin = currentTime.getMinutes();
                int iSec = currentTime.getSeconds();

                mHandlerCount.postDelayed(mThreadCount, 500);

                if (iPrevSec != iSec) {
                    iPrevSec = iSec;
                    PostMyMsg(S.ShowCountDown);
                    iRecordingTotalSeconds--;

                    // ── 無訊號保護：開始 10 秒後若仍未收到任何 BrainwaveValue，
                    //    暫停倒數並彈出對話框，避免使用者付費後跑了 3 分鐘空跡。
                    long now = System.currentTimeMillis();
                    boolean noSignalLong = (lLastSignalTimeMs == 0 || (now - lLastSignalTimeMs) > 10000);
                    if (noSignalLong && !bWarnedNoSignal && iRecordingTotalSeconds > 0) {
                        bWarnedNoSignal = true;
                        warnNoSignal();
                    }

                    if (iRecordingTotalSeconds < 0) {
                        bQuit = true;
                        clsData.EnableRecording(false);

                        // ── 檢測完成，結束場次並寫入資料庫 ─────────────────
                        CLS_DB.getInstance().endSession(null);
                        // ────────────────────────────────────────────────────

                        if (clsData.bNextSection()) {
                            Intent intent = new Intent();
                            intent.setClass(mContext, waiting.class);
                            startActivity(intent);
                            overridePendingTransition(0, 0);
                        } else {
                            Intent intent = new Intent();
                            intent.setClass(mContext, report.class);
                            startActivity(intent);
                            overridePendingTransition(0, 0);
                        }

                    }
                }
            }
            catch(Exception ex){
                String str = ex.toString();
            }
        }
    }
    //==============================================================================================
    /**
     * 開始檢測 10 秒後仍無腦波訊號 → 彈出對話框讓使用者選擇：
     *   1) 重試連線並繼續
     *   2) 仍要繼續（若手動操作，會生成空白報告）
     *   3) 中止本次檢測（不扣秒數，回到 WebApp）
     */
    void warnNoSignal() {
        runOnUiThread(() -> {
            // 暫停倒數
            mHandlerCount.removeCallbacks(mThreadCount);
            new AlertDialog.Builder(mContext)
                    .setTitle("無腦波訊號")
                    .setMessage("已超過 10 秒沒有收到腦波儀訊號。\n"
                              + "可能原因：腦波儀電量不足、未戴好、藍牙連線中斷。\n\n"
                              + "目前狀態：" + strLinkState)
                    .setCancelable(false)
                    .setPositiveButton("重新連線並繼續", (d, w) -> {
                        try { clsBrainwave.Connect(test.this); } catch (Throwable ignore) {}
                        bWarnedNoSignal = false; // 重置警告，給使用者另一次 10 秒緩衝
                        lLastSignalTimeMs = System.currentTimeMillis();
                        mHandlerCount.postDelayed(mThreadCount, 500); // 恢復倒數
                    })
                    .setNeutralButton("仍要繼續", (d, w) -> {
                        mHandlerCount.postDelayed(mThreadCount, 500);
                    })
                    .setNegativeButton("中止檢測", (d, w) -> {
                        bQuit = true;
                        clsData.EnableRecording(false);
                        CLS_DB.getInstance().failSession("no_signal", null);
                        finish(); // 回到 WebAppActivity
                    })
                    .show();
        });
    }
    //==============================================================================================
    void StopTest() {
        try {
            clsData.EnableRecording(false);

            // ── 使用者手動停止，標記場次失敗/中止 ──────────────────────
            int captured = CLS_DB.getInstance().getCaptureSeqNum();
            // 【測試模式：≥5筆視為成功】正式上線改回 150
            if (captured >= 5) {
                CLS_DB.getInstance().endSession(null);
            } else {
                CLS_DB.getInstance().failSession("user_stopped", null);
            }
            // ─────────────────────────────────────────────────────────────

            Intent intent = new Intent();
            intent.setClass(this, report.class);
            startActivity(intent);
            overridePendingTransition(0, 0);
        }
        catch(Exception ex) {
            System.out.println(ex.getMessage().toString());
        }
    }
    //==============================================================================================
    public void ivStopTest_OnClick(View view) {
        StopTest();
    }

    //===================================================
    //===================================================
    //===================================================
    void PostMyMsg(int _iMsg) {
        listMsg.add(_iMsg);
        if(listMsg.size() == 1)//如果只有剛加的這一個,表示剛剛是停止狀態,所以現在要重新啟動
            mHandlerMsg.postDelayed(mThreadMsg, 0);
    }

    private class ThreadMsg extends Thread {
        @Override
        public void run() {
            try {
                if (bQuit)
                    return;
                if (listMsg.size() == 0)
                    return;

                if (listMsg.get(0) == S.BrainwaveValue) {
                    if (clsLineChart == null)
                        return;

                    dX += 1;
                    clsLineChart.AddPoint(1, dX, clsData.iGetAttention());
                    clsLineChart.AddPoint(2, dX, clsData.iGetMeditation());
                    viewLineChart.invalidate();
                }
                if (listMsg.get(0) == S.ShowCountDown) {
                    int iMin = (iRecordingTotalSeconds / 60) % 60;
                    String str = String.format("時間  %02d : %02d : %02d",
                            iRecordingTotalSeconds / 3600, iMin, iRecordingTotalSeconds % 60);
                    tvCountDown.setText(str);
                }
                //
                listMsg.remove(0);
                if (listMsg.size() > 0)//如果還有,繼續處理
                    mHandlerMsg.postDelayed(mThreadMsg, 0);
            }
            catch(Exception ex){
                String str = ex.toString();
            }
        }
    }
    //===================================================
}