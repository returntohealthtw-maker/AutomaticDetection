package com.sh.simpleeeg;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.ActivityInfo;
//import android.support.v7.app.AppCompatActivity;
import android.os.Bundle;
import android.util.TypedValue;
import android.view.View;
import android.view.WindowManager;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.TextView;

import com.bumptech.glide.Glide;
import com.bumptech.glide.request.RequestOptions;

public class multi_time extends Activity {
    CLS_PARAM S = new CLS_PARAM();
    CLS_DATA clsData = new CLS_DATA();

    RequestOptions myGdiOptions;

    EditText etStartHour1,etStartMin1,etRecordingHour1,etRecordingMin1;
    EditText etStartHour2,etStartMin2,etRecordingHour2,etRecordingMin2;
    EditText etStartHour3,etStartMin3,etRecordingHour3,etRecordingMin3;
    EditText etStartHour4,etStartMin4,etRecordingHour4,etRecordingMin4;
    EditText etStartHour5,etStartMin5,etRecordingHour5,etRecordingMin5;
    CheckBox cboxStartTime1,cboxStartTime2,cboxStartTime3,cboxStartTime4,cboxStartTime5;
    TextView tvRecordingTime1,tvRecordingTime2,tvRecordingTime3,tvRecordingTime4,tvRecordingTime5;
    ImageView ivStartTest,ivThreshold;
    TextView tvH1,tvH2,tvH3,tvH4,tvH5,tvH6,tvH7,tvH8,tvH9,tvH10,tvH11,tvH12,tvH13,tvH14,tvH15,tvH16,tvH17,tvH18,tvH19,tvH20;


    Context mContext;

    boolean bQuit = false;

    int iTextSize = 5;
    float fBiggerScale = 2.0f;

    @SuppressLint("SourceLockedOrientationActivity")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_PORTRAIT);
        setContentView(R.layout.multi_time);

        mContext = this;
        myGdiOptions = new RequestOptions().fitCenter();

        ivStartTest = (ImageView)findViewById(R.id.ivStartTest);
        ivThreshold = (ImageView)findViewById(R.id.ivThreshold);

        etStartHour1 = (EditText)findViewById(R.id.etStartHour1);
        etStartHour2 = (EditText)findViewById(R.id.etStartHour2);
        etStartHour3 = (EditText)findViewById(R.id.etStartHour3);
        etStartHour4 = (EditText)findViewById(R.id.etStartHour4);
        etStartHour5 = (EditText)findViewById(R.id.etStartHour5);

        etStartMin1 = (EditText)findViewById(R.id.etStartMin1);
        etStartMin2 = (EditText)findViewById(R.id.etStartMin2);
        etStartMin3 = (EditText)findViewById(R.id.etStartMin3);
        etStartMin4 = (EditText)findViewById(R.id.etStartMin4);
        etStartMin5 = (EditText)findViewById(R.id.etStartMin5);

        etRecordingHour1 = (EditText)findViewById(R.id.etRecordingHour1);
        etRecordingHour2 = (EditText)findViewById(R.id.etRecordingHour2);
        etRecordingHour3 = (EditText)findViewById(R.id.etRecordingHour3);
        etRecordingHour4 = (EditText)findViewById(R.id.etRecordingHour4);
        etRecordingHour5 = (EditText)findViewById(R.id.etRecordingHour5);

        etRecordingMin1 = (EditText)findViewById(R.id.etRecordingMin1);
        etRecordingMin2 = (EditText)findViewById(R.id.etRecordingMin2);
        etRecordingMin3 = (EditText)findViewById(R.id.etRecordingMin3);
        etRecordingMin4 = (EditText)findViewById(R.id.etRecordingMin4);
        etRecordingMin5 = (EditText)findViewById(R.id.etRecordingMin5);

        cboxStartTime1 = (CheckBox)findViewById(R.id.cboxStartTime1);
        cboxStartTime2 = (CheckBox)findViewById(R.id.cboxStartTime2);
        cboxStartTime3 = (CheckBox)findViewById(R.id.cboxStartTime3);
        cboxStartTime4 = (CheckBox)findViewById(R.id.cboxStartTime4);
        cboxStartTime5 = (CheckBox)findViewById(R.id.cboxStartTime5);

        tvRecordingTime1 = (TextView)findViewById(R.id.tvRecordingTime1);
        tvRecordingTime2 = (TextView)findViewById(R.id.tvRecordingTime2);
        tvRecordingTime3 = (TextView)findViewById(R.id.tvRecordingTime3);
        tvRecordingTime4 = (TextView)findViewById(R.id.tvRecordingTime4);
        tvRecordingTime5 = (TextView)findViewById(R.id.tvRecordingTime5);

        tvH1 = (TextView)findViewById(R.id.tvH1);
        tvH2 = (TextView)findViewById(R.id.tvH2);
        tvH3 = (TextView)findViewById(R.id.tvH3);
        tvH4 = (TextView)findViewById(R.id.tvH4);
        tvH5 = (TextView)findViewById(R.id.tvH5);
        tvH6 = (TextView)findViewById(R.id.tvH6);
        tvH7 = (TextView)findViewById(R.id.tvH7);
        tvH8 = (TextView)findViewById(R.id.tvH8);
        tvH9 = (TextView)findViewById(R.id.tvH9);
        tvH10 = (TextView)findViewById(R.id.tvH10);
        tvH11 = (TextView)findViewById(R.id.tvH11);
        tvH12 = (TextView)findViewById(R.id.tvH12);
        tvH13 = (TextView)findViewById(R.id.tvH13);
        tvH14 = (TextView)findViewById(R.id.tvH14);
        tvH15 = (TextView)findViewById(R.id.tvH15);
        tvH16 = (TextView)findViewById(R.id.tvH16);
        tvH17 = (TextView)findViewById(R.id.tvH17);
        tvH18 = (TextView)findViewById(R.id.tvH18);
        tvH19 = (TextView)findViewById(R.id.tvH19);
        tvH20 = (TextView)findViewById(R.id.tvH20);

        ChangeTextSize();

        //不要每次一進畫面就跳出鍵盤
        getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_HIDDEN);

        ivThreshold.setVisibility(View.INVISIBLE);
    }
    @Override
    protected void onStart() {
        super.onStart();

        RestoreData();
        bQuit = false;
        //Glide.with(mContext).load(R.drawable.bg_main).apply(myGdiOptions).into(ivBG);
        Glide.with(mContext).load(R.drawable.start_test).apply(myGdiOptions).into(ivStartTest);
        Glide.with(mContext).load(R.drawable.btn_threshold).apply(myGdiOptions).into(ivThreshold);
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
        Glide.with(this).clear(ivStartTest);
        Glide.with(this).clear(ivThreshold);
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
        SaveData();
        Intent intent = new Intent();
        intent.setClass(this, main.class);//input info
        startActivity(intent);
        overridePendingTransition(0, 0);
    }
    //==============================================================================================
    //==============================================================================================
    //==============================================================================================
    void RestoreData() {
        SharedPreferences prefer = getSharedPreferences("EEGAppFile", MODE_PRIVATE);
        cboxStartTime1.setChecked(prefer.getBoolean("Checked1",false));
        cboxStartTime2.setChecked(prefer.getBoolean("Checked2",false));
        cboxStartTime3.setChecked(prefer.getBoolean("Checked3",false));
        cboxStartTime4.setChecked(prefer.getBoolean("Checked4",false));
        cboxStartTime5.setChecked(prefer.getBoolean("Checked5",false));
        etStartHour1.setText(prefer.getString("StartHour1", ""));
        etStartHour2.setText(prefer.getString("StartHour2", ""));
        etStartHour3.setText(prefer.getString("StartHour3", ""));
        etStartHour4.setText(prefer.getString("StartHour4", ""));
        etStartHour5.setText(prefer.getString("StartHour5", ""));
        etStartMin1.setText(prefer.getString("StartMin1", ""));
        etStartMin2.setText(prefer.getString("StartMin2", ""));
        etStartMin3.setText(prefer.getString("StartMin3", ""));
        etStartMin4.setText(prefer.getString("StartMin4", ""));
        etStartMin5.setText(prefer.getString("StartMin5", ""));
        etRecordingHour1.setText(prefer.getString("RecordingHour1", ""));
        etRecordingHour2.setText(prefer.getString("RecordingHour2", ""));
        etRecordingHour3.setText(prefer.getString("RecordingHour3", ""));
        etRecordingHour4.setText(prefer.getString("RecordingHour4", ""));
        etRecordingHour5.setText(prefer.getString("RecordingHour5", ""));
        etRecordingMin1.setText(prefer.getString("RecordingMin1", ""));
        etRecordingMin2.setText(prefer.getString("RecordingMin2", ""));
        etRecordingMin3.setText(prefer.getString("RecordingMin3", ""));
        etRecordingMin4.setText(prefer.getString("RecordingMin4", ""));
        etRecordingMin5.setText(prefer.getString("RecordingMin5", ""));
    }
    //==============================================================================================
    void SaveData(){
        SharedPreferences prefer = getSharedPreferences("EEGAppFile", MODE_PRIVATE);
        SharedPreferences.Editor editor = prefer.edit();
        //editor.putInt("TextSize", iTextSize);
        editor.putBoolean("Checked1",cboxStartTime1.isChecked());
        editor.putBoolean("Checked2",cboxStartTime2.isChecked());
        editor.putBoolean("Checked3",cboxStartTime3.isChecked());
        editor.putBoolean("Checked4",cboxStartTime4.isChecked());
        editor.putBoolean("Checked5",cboxStartTime5.isChecked());
        editor.putString("StartHour1", etStartHour1.getText().toString());
        editor.putString("StartHour2", etStartHour2.getText().toString());
        editor.putString("StartHour3", etStartHour3.getText().toString());
        editor.putString("StartHour4", etStartHour4.getText().toString());
        editor.putString("StartHour5", etStartHour5.getText().toString());
        editor.putString("StartMin1", etStartMin1.getText().toString());
        editor.putString("StartMin2", etStartMin2.getText().toString());
        editor.putString("StartMin3", etStartMin3.getText().toString());
        editor.putString("StartMin4", etStartMin4.getText().toString());
        editor.putString("StartMin5", etStartMin5.getText().toString());
        editor.putString("RecordingHour1", etRecordingHour1.getText().toString());
        editor.putString("RecordingHour2", etRecordingHour2.getText().toString());
        editor.putString("RecordingHour3", etRecordingHour3.getText().toString());
        editor.putString("RecordingHour4", etRecordingHour4.getText().toString());
        editor.putString("RecordingHour5", etRecordingHour5.getText().toString());
        editor.putString("RecordingMin1", etRecordingMin1.getText().toString());
        editor.putString("RecordingMin2", etRecordingMin2.getText().toString());
        editor.putString("RecordingMin3", etRecordingMin3.getText().toString());
        editor.putString("RecordingMin4", etRecordingMin4.getText().toString());
        editor.putString("RecordingMin5", etRecordingMin5.getText().toString());
        editor.commit();
    }
    //==============================================================================================
    public void ivStartTest_OnClick(View view) {
        // ── 固定 3 分鐘檢測（180秒），直接啟動不需手動填寫 ─────────────
        clsData.listRecordingTime().clear();
        clsData.ClearListSectionData();

        // 【測試模式：1分鐘】正式上線改回 (0, 0, 0, 3) → 3分鐘
        CLS_RECORDING_TIME clsRecordingTime = new CLS_RECORDING_TIME(0, 0, 0, 1);
        clsData.listRecordingTime().add(clsRecordingTime);
        clsData.NewListSectionData();
        // ─────────────────────────────────────────────────────────────────

        Intent intent = new Intent();
        intent.setClass(this, test.class);
        startActivity(intent);
        overridePendingTransition(0, 0);
    }

    //==============================================================================================
    void ChangeTextSize(){

        float fBiggerScale = 1.5f;
        //先把 方框放大，再把字縮小
        cboxStartTime1.setScaleX(fBiggerScale);
        cboxStartTime1.setScaleY(fBiggerScale);
        cboxStartTime1.setTextSize(TypedValue.COMPLEX_UNIT_PX, 90f*clsData.fTextScale()/fBiggerScale);
        cboxStartTime2.setScaleX(fBiggerScale);
        cboxStartTime2.setScaleY(fBiggerScale);
        cboxStartTime2.setTextSize(TypedValue.COMPLEX_UNIT_PX, 90f*clsData.fTextScale()/fBiggerScale);
        cboxStartTime3.setScaleX(fBiggerScale);
        cboxStartTime3.setScaleY(fBiggerScale);
        cboxStartTime3.setTextSize(TypedValue.COMPLEX_UNIT_PX, 90f*clsData.fTextScale()/fBiggerScale);
        cboxStartTime4.setScaleX(fBiggerScale);
        cboxStartTime4.setScaleY(fBiggerScale);
        cboxStartTime4.setTextSize(TypedValue.COMPLEX_UNIT_PX, 90f*clsData.fTextScale()/fBiggerScale);
        cboxStartTime5.setScaleX(fBiggerScale);
        cboxStartTime5.setScaleY(fBiggerScale);
        cboxStartTime5.setTextSize(TypedValue.COMPLEX_UNIT_PX, 90f*clsData.fTextScale()/fBiggerScale);

        float fSize2 = 100f;
        /*
        cboxStartTime1.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        cboxStartTime2.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        cboxStartTime3.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        cboxStartTime4.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        cboxStartTime5.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
*/
        tvRecordingTime1.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        tvRecordingTime2.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        tvRecordingTime3.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        tvRecordingTime4.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        tvRecordingTime5.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());

        etStartHour1.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        etStartHour2.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        etStartHour3.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        etStartHour4.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        etStartHour5.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());

        etStartMin1.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        etStartMin2.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        etStartMin3.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        etStartMin4.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        etStartMin5.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());

        etRecordingHour1.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        etRecordingHour2.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        etRecordingHour3.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        etRecordingHour4.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        etRecordingHour5.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());

        etRecordingMin1.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        etRecordingMin2.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        etRecordingMin3.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        etRecordingMin4.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        etRecordingMin5.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());

        tvH1.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        tvH2.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        tvH3.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        tvH4.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        tvH5.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        tvH6.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        tvH7.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        tvH8.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        tvH9.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        tvH10.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        tvH11.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        tvH12.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        tvH13.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        tvH14.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        tvH15.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        tvH16.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        tvH17.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        tvH18.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        tvH19.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
        tvH20.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize2*clsData.fTextScale());
    }
    //==============================================================================================
    public void ivThreshold_OnClick(View view) {
        Intent intent = new Intent();
        intent.setClass(this, threshold.class);
        startActivity(intent);
        overridePendingTransition(0, 0);
    }
    //==============================================================================================
}