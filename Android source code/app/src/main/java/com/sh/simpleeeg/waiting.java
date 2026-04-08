package com.sh.simpleeeg;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ActivityInfo;
import android.os.Handler;
//import android.support.v7.app.AppCompatActivity;
import android.os.Bundle;
import android.util.TypedValue;
import android.view.WindowManager;
import android.widget.ImageView;
import android.widget.TextView;

import com.bumptech.glide.Glide;
import com.bumptech.glide.request.RequestOptions;

import java.util.ArrayList;
import java.util.Calendar;
import java.util.Date;
import java.util.List;

public class waiting extends Activity {
    CLS_PARAM S = new CLS_PARAM();
    CLS_BrainWave clsBrainwave = new CLS_BrainWave();
    CLS_DATA clsData = new CLS_DATA();

    Context mContext;
    RequestOptions myGdiOptions;

    ImageView ivBG;
    TextView tvMsg,tvAtt,tvMed,tvTime;

    static ThreadMsg mThreadMsg;//改用自訂thread方式處理msg,取代原有 static msg 複雜的方式
    static Handler mHandlerMsg = new Handler();
    static List<Integer> listMsg = new ArrayList<Integer>();

    static private ThreadCount mThreadCount;
    static private Handler mHandlerCount = new Handler();
    static int iThreadStep = 0;

    static int iStartHour = 0;
    static int iStartMin = 0;

    boolean bQuit = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_PORTRAIT);
        setContentView(R.layout.waiting);

        mContext = this;
        myGdiOptions = new RequestOptions().fitCenter();

        ivBG = (ImageView)findViewById(R.id.ivBG);
        tvMsg = (TextView)findViewById(R.id.tvMsg);
        tvAtt = (TextView)findViewById(R.id.tvAtt);
        tvMed = (TextView)findViewById(R.id.tvMed);
        tvTime = (TextView)findViewById(R.id.tvTime);

        tvMsg.setTextSize(TypedValue.COMPLEX_UNIT_PX, 160f*clsData.fTextScale());
        tvAtt.setTextSize(TypedValue.COMPLEX_UNIT_PX, 120f*clsData.fTextScale());
        tvMed.setTextSize(TypedValue.COMPLEX_UNIT_PX, 120f*clsData.fTextScale());
        tvTime.setTextSize(TypedValue.COMPLEX_UNIT_PX, 160f*clsData.fTextScale());

        SetCallback();

        listMsg.clear();
        mThreadMsg = new ThreadMsg();

        int ss = clsData.iCurrentSection();
        iStartHour = clsData.listRecordingTime().get(ss).iStartHour;
        iStartMin = clsData.listRecordingTime().get(ss).iStartMin;
        String str = String.format("%02d:%02d 開始記錄", iStartHour, iStartMin);
        tvMsg.setText(str);

        mThreadCount = new ThreadCount();
        mHandlerCount.postDelayed(mThreadCount, 0);
    }
    @Override
    protected void onStart() {
        super.onStart();

        Glide.with(mContext).load(R.drawable.bg_0).apply(myGdiOptions).into(ivBG);

        bQuit = false;
        iThreadStep = 0;
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
    protected void onStop()
    {
        super.onStop();

        bQuit = true;
        mHandlerCount.removeCallbacks(mThreadCount);
        Glide.with(this).clear(ivBG);
    }
    @Override
    protected void onDestroy()
    {
        super.onDestroy();
    }
    @Override
    protected void onRestart()
    {
        super.onRestart();
    }
    @Override
    public void onBackPressed(){
        Intent intent = new Intent();
        intent.setClass(this, main.class);//input info
        startActivity(intent);
        overridePendingTransition(0, 0);
    }
    //==============================================================================================
    //==============================================================================================
    //==============================================================================================
    public void SetCallback() {
        clsBrainwave.SetCallback(new CLS_BrainWave.Brainwave_Callback() {
            //@Override
            public void Do(int iCmd, int iVal) {
                switch(iCmd) {
                    case 0:
                        //System.out.println("work");
                        //ShowToast("!! data callback ok !!");
                        break;
                }
                //
                if(iCmd == S.BrainwaveValue) {
                    PostMyMsg(S.BrainwaveValue);
                }
            }
        });
    }
    //===================================================
    static int iHour=0,iMin=0,iSec=0;
    static int iPrevSec = -1;
    private class ThreadCount extends Thread {
        @Override
        public void run() {
            if(bQuit)
                return;

            mHandlerCount.postDelayed(mThreadCount, 200);

            try {
                Date currentTime = Calendar.getInstance().getTime();
                iHour = currentTime.getHours();
                iMin = currentTime.getMinutes();
                iSec = currentTime.getSeconds();

                if (iPrevSec != iSec) {
                    iPrevSec = iSec;
                    PostMyMsg(S.CurrentTime);
                }

                if (iHour == iStartHour && iMin == iStartMin) {
                    //tvMsg.setVisibility(View.INVISIBLE);
                    bQuit = true;
                    Intent intent = new Intent();
                    intent.setClass(mContext, test.class);
                    startActivity(intent);
                    overridePendingTransition(0, 0);
                }
            }
            catch(Exception ex){
                String str = ex.toString();
            }
        }
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
            if(bQuit)
                return;
            if(listMsg.size() == 0)
                return;

            try {
                if (listMsg.get(0) == S.BrainwaveValue) {
                    tvAtt.setText("專注 : " + clsData.iGetAttention());
                    tvMed.setText("放鬆 : " + clsData.iGetMeditation());
                } else if (listMsg.get(0) == S.CurrentTime) {
                    String str = String.format("%02d : %02d : %02d", iHour, iMin, iSec);
                    tvTime.setText(str);
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