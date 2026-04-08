package com.sh.simpleeeg;



import android.Manifest;
import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.ActivityInfo;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Environment;
import android.os.Handler;
import android.os.Bundle;
import androidx.core.app.ActivityCompat;

import android.util.TypedValue;
import android.view.View;
import android.view.WindowManager;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.SeekBar;
import android.widget.TextView;

import com.bumptech.glide.Glide;
import com.bumptech.glide.request.RequestOptions;

import java.util.ArrayList;
import java.util.List;

import static java.lang.Integer.parseInt;


public class main extends Activity {
    CLS_PARAM S = new CLS_PARAM();
    CLS_DATA clsData = new CLS_DATA();
    CLS_BrainWave clsBrainWave = new CLS_BrainWave();

    RequestOptions myGdiOptions;

    TextView tvName, tvBirthday, tvEmail, tvPhone;
    ImageView ivBG, ivSignal,ivCaption,ivStartTest,ivSetting;
    EditText etName, etBirthday, etEmail, etPhone;


    Context mContext;
    boolean bConnected = false;

    String strName, strBirthday, strEmail, strPhone;

    boolean bQuit = false;
    boolean bBrainwaveConnected = false;

    static ThreadMsg mThreadMsg;
    static Handler mHandlerMsg = new Handler();
    static List<Integer> listMsg = new ArrayList<Integer>();

    @SuppressLint("SourceLockedOrientationActivity")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_PORTRAIT);
        setContentView(R.layout.main);

        mContext = this;
        myGdiOptions = new RequestOptions().fitCenter();

        ivBG = (ImageView)findViewById(R.id.ivBG);
        ivSignal = (ImageView)findViewById(R.id.ivSignal);
        ivCaption = (ImageView)findViewById(R.id.ivCaption);
        ivStartTest = (ImageView)findViewById(R.id.ivStartTest);
        ivSetting = (ImageView)findViewById(R.id.ivSetting);
        tvName = (TextView)findViewById(R.id.tvName);
        tvBirthday = (TextView)findViewById(R.id.tvBirthday);
        tvEmail = (TextView)findViewById(R.id.tvEmail);
        tvPhone = (TextView)findViewById(R.id.tvPhone);
        etName = (EditText)findViewById(R.id.etName);
        etBirthday = (EditText)findViewById(R.id.etBirthday);
        etEmail = (EditText)findViewById(R.id.etEmail);
        etPhone = (EditText)findViewById(R.id.etPhone);

        clsData.SetDspMetrics(this);

        // ── 初始化本地腦波資料庫（只需執行一次）─────────────────────────
        CLS_DB.getInstance().init(this);
        // ─────────────────────────────────────────────────────────────────

        // ── 設定顧問姓名（從 SharedPreferences 讀取，預設"顧問"）─────────
        SharedPreferences pref0 = getSharedPreferences("EEGAppFile", MODE_PRIVATE);
        String savedConsultant = pref0.getString("ConsultantName", "顧問");
        clsData.setTeacherName(savedConsultant);
        CLS_DB.getInstance().setConsultantName(savedConsultant);
        // ─────────────────────────────────────────────────────────────────

        SharedPreferences prefer = getSharedPreferences("EEGAppFile", MODE_PRIVATE);
        int iTextSize = prefer.getInt("TextSize", 8);
        int iLineChartTextSize = prefer.getInt("LineChartTextSize", 5);
        int iPieChartTextSize = prefer.getInt("PieChartTextSize", 5);
        clsData.SetTextSize(iTextSize);
        clsData.SetLineChartTextSize(iLineChartTextSize);
        clsData.SetPieChartTextSize(iPieChartTextSize);

        ChangeTextSize();

        SetBrainwaveCallback();



        //不要每次一進畫面就跳出鍵盤
        getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_HIDDEN);

        listMsg.clear();
        mThreadMsg = new ThreadMsg();


        StoragePermissionGranted();// *** 這一行一定要放在 Connect前,還沒權限ok,不能connect
        clsBrainWave.Connect(this);
    }
    @Override
    protected void onStart() {
        super.onStart();

        RestoreData();
        bQuit = false;
        Glide.with(mContext).load(R.drawable.bg_0).apply(myGdiOptions).into(ivBG);
        Glide.with(mContext).load(R.drawable.caption).apply(myGdiOptions).into(ivCaption);
        Glide.with(mContext).load(R.drawable.start_test).apply(myGdiOptions).into(ivStartTest);
        Glide.with(mContext).load(R.drawable.btn_setting).apply(myGdiOptions).into(ivSetting);
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

        bQuit = true;
        Glide.with(this).clear(ivBG);
        Glide.with(this).clear(ivSignal);
        Glide.with(this).clear(ivCaption);
        Glide.with(this).clear(ivStartTest);
        Glide.with(this).clear(ivSetting);

        strName = etName.getText().toString();
        strBirthday = etBirthday.getText().toString();
        strEmail = etEmail.getText().toString();
        strPhone = etPhone.getText().toString();
        clsData.SetMemberInfo(strName, strBirthday, strEmail, strPhone);

        SharedPreferences prefer = getSharedPreferences("EEGAppFile", MODE_PRIVATE);
        SharedPreferences.Editor editor = prefer.edit();
        editor.putString("Name", strName);
        editor.putString("Birthday", strBirthday);
        editor.putString("Email", strEmail);
        editor.putString("Phone", strPhone);
        editor.commit();
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
    }
    //==============================================================================================
    //==============================================================================================
    //==============================================================================================
    void RestoreData() {
        SharedPreferences prefer = getSharedPreferences("EEGAppFile", MODE_PRIVATE);
        etName.setText(prefer.getString("Name", ""));
        etBirthday.setText(prefer.getString("Birthday", ""));
        etEmail.setText(prefer.getString("Email", ""));
        etPhone.setText(prefer.getString("Phone", ""));
    }
    //==============================================================================================
    public void SetBrainwaveCallback() {
        clsBrainWave.SetCallback(new CLS_BrainWave.Brainwave_Callback() {
            //@Override
            public void Do(int iCmd, int iVal) {
                if(iCmd == S.BrainwaveConnected || iCmd==S.BrainwavePairOk
                || iCmd==S.BrainwaveDisconnected || iCmd==S.SIGNAL_GOOD) {
                    PostMyMsg(iCmd);
                }
            }
        });
    }
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
            //brainwave
            if(listMsg.get(0) == S.SIGNAL_GOOD) {
                Glide.with(mContext).load(R.drawable.signal_good).apply(myGdiOptions).into(ivSignal);
                bBrainwaveConnected = true;
            }
            else if(listMsg.get(0) == S.BrainwaveConnected) {
                Glide.with(mContext).load(R.drawable.signal_connected).apply(myGdiOptions).into(ivSignal);
                bBrainwaveConnected = true;
            }
            else if(listMsg.get(0) == S.BrainwaveDisconnected) {
                Glide.with(mContext).load(R.drawable.signal_disconnected).apply(myGdiOptions).into(ivSignal);
                bBrainwaveConnected = false;
            }
            else if(listMsg.get(0) == S.BrainwaveNotPaired) {
                Glide.with(mContext).load(R.drawable.signal_disconnected).apply(myGdiOptions).into(ivSignal);
                bBrainwaveConnected = false;
            }
            else if(listMsg.get(0) == S.BrainwavePairOk) {
                bBrainwaveConnected = false;
            }
            else if(listMsg.get(0) == S.BluetoothClosed) {
                Glide.with(mContext).load(R.drawable.signal_disconnected).apply(myGdiOptions).into(ivSignal);
                bBrainwaveConnected = false;
            }
            //
            listMsg.remove(0);
            if(listMsg.size() > 0)//如果還有,繼續處理
                mHandlerMsg.postDelayed(mThreadMsg, 0);
        }
    }
    //==============================================================================================
    public void ivStartTest_OnClick(View view) {
        //if(!bBrainwaveConnected)
        //    return;
        Intent intent = new Intent();
        intent.setClass(this, multi_time.class);//input info
        startActivity(intent);
        overridePendingTransition(0, 0);
    }
    //===================================================
    //===================================================
    //===================================================
    void StoragePermissionGranted() {
        if (Build.VERSION.SDK_INT < 23)         //android 6
            return;//23以前的會依據AndroidManifest.xml裡面的設定
        else if (Build.VERSION.SDK_INT <= 29) {  //29:android 10, 30:android 11
            if (checkSelfPermission(android.Manifest.permission.WRITE_EXTERNAL_STORAGE)
                    != PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(this,
                        new String[]{
                                Manifest.permission.READ_EXTERNAL_STORAGE,
                                Manifest.permission.WRITE_EXTERNAL_STORAGE
                        }, 1);
            }
        }
        else{
            //for android 12, 安裝後會動態要求權限
            if (checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT)
                    != PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(this,
                        new String[]{
                                Manifest.permission.BLUETOOTH_CONNECT
                        }, 1111);
            }
            if (checkSelfPermission(Manifest.permission.BLUETOOTH_SCAN)
                    != PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(this,
                        new String[]{
                                Manifest.permission.BLUETOOTH_SCAN
                        }, 1111);
            }
        }
    }
    //===================================================
    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == 123) {
            if (Environment.isExternalStorageManager()) {
                //appendLog("打開了 ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION 權限");
            } else {
                //appendLog("關閉了 ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION 權限");
            }
        }
    }
    //===================================================
    public void ivBG_OnClick(View view) {
        ActivityCompat.requestPermissions(this,
        new String[]{Manifest.permission.WRITE_EXTERNAL_STORAGE}, 1);
    }
    //===================================================
    public void ivSetting_OnClick(View view) {
        Intent intent = new Intent();
        intent.setClass(this, setting.class);
        startActivity(intent);
        overridePendingTransition(0, 0);
    }
    //===================================================
    void ChangeTextSize() {
        float fSize2 = 100f;
        tvName.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        tvBirthday.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        tvEmail.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        tvPhone.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        etName.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        etBirthday.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        etEmail.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        etPhone.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
    }
    //===================================================
}
