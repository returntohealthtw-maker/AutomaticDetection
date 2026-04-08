package com.sh.simpleeeg;

import android.annotation.SuppressLint;
import android.app.Activity;
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

public class pretest extends Activity {
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
        setContentView(R.layout.pretest);

        mContext = this;

        ivBG = (ImageView)findViewById(R.id.ivBG);
        ivStopTest = (ImageView)findViewById(R.id.ivStopTest);
        layoutChart = (LinearLayout)findViewById(R.id.layoutChart);
        tvCountDown = (TextView)findViewById(R.id.tvCountDown);

        tvCountDown.setTextSize(TypedValue.COMPLEX_UNIT_PX, 100f*clsData.fTextScale());

        SetCallback();

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
        clsLineChart = new CLS_LineChart(2);
        viewLineChart = clsLineChart.viewDrawAppearance(this, true, 30, 100, Color.RED, Color.GREEN, 1.0f);
        layoutChart.addView(viewLineChart,
                new LinearLayout.LayoutParams(
                        LinearLayout.LayoutParams.FILL_PARENT,
                        LinearLayout.LayoutParams.FILL_PARENT));
        clsLineChart.AddPoint(1, 0, 0);//要有資料才有辦法調整大小
        clsLineChart.AddPoint(2, 0, 0);

        clsData.EnableRecording(true);
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
                    PostMyMsg(S.BrainwaveValue);
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
                    if (iRecordingTotalSeconds < 0) {
                        bQuit = true;
                        clsData.EnableRecording(false);


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
    void StopTest() {
        try {
            clsData.EnableRecording(false);

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