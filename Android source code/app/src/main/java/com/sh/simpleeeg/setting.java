package com.sh.simpleeeg;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.ActivityInfo;
import android.os.Bundle;
import android.util.TypedValue;
import android.view.View;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.RadioButton;
import android.widget.SeekBar;
import android.widget.TextView;

import com.bumptech.glide.Glide;
import com.bumptech.glide.request.RequestOptions;

public class setting extends Activity {
    CLS_DATA clsData = new CLS_DATA();

    RequestOptions myGdiOptions;
    Context mContext;

    ImageView ivBG;
    TextView tvTextSize, tvLineChartTextSize, tvBarChartTextSize, tvVersion,tvPieChartTextSize;
    TextView tvLanguage, tvName, tvGender, tvBirthday;
    SeekBar sbTextSize, sbLineChartTextSize, sbBarChartTextSize, sbPieChartTextSize;
    RadioButton rbtn_tc,rbtn_sc,rbtn_eng;
    EditText etName, etGender, etBirthday;
    Button btn_manual;

    static boolean bQuit = false;
    static int iTextSize = 5, iLineChartTextSize = 5, iBarChartTextSize=5 , iPieChartTextSize=5;
    static int i_Language = 1;//1:tc, 2:sc, 3:eng
    static String strName, strBirthday;
    static int iGender = 0;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_PORTRAIT);
        setContentView(R.layout.setting);

        mContext = this;
        myGdiOptions = new RequestOptions().fitCenter();

        ivBG = (ImageView)findViewById(R.id.ivBG);
        rbtn_tc = (RadioButton)findViewById(R.id.rbtn_tc);
        rbtn_sc = (RadioButton)findViewById(R.id.rbtn_sc);
        rbtn_eng = (RadioButton)findViewById(R.id.rbtn_eng);
        tvVersion = (TextView) findViewById(R.id.tvVersion);
        tvLanguage = (TextView) findViewById(R.id.tvLanguage);
        tvName = (TextView) findViewById(R.id.tvName);
        tvGender = (TextView) findViewById(R.id.tvGender);
        tvBirthday = (TextView) findViewById(R.id.tvBirthday);
        tvTextSize = (TextView) findViewById(R.id.tvTextSize);
        sbTextSize = (SeekBar) findViewById(R.id.sbTextSize);
        tvLineChartTextSize = (TextView) findViewById(R.id.tvLineChartTextSize);
        sbLineChartTextSize = (SeekBar) findViewById(R.id.sbLineChartTextSize);
        tvBarChartTextSize = (TextView) findViewById(R.id.tvBarChartTextSize);
        sbBarChartTextSize = (SeekBar) findViewById(R.id.sbBarChartTextSize);

        tvPieChartTextSize = (TextView) findViewById(R.id.tvPieChartTextSize);
        sbPieChartTextSize = (SeekBar) findViewById(R.id.sbPieChartTextSize);
        btn_manual = (Button)findViewById(R.id.btn_manual);

        etName = (EditText) findViewById(R.id.etName);
        etGender = (EditText) findViewById(R.id.etGender);
        etBirthday = (EditText) findViewById(R.id.etBirthday);

        SharedPreferences prefer = getSharedPreferences("EEGAppFile", MODE_PRIVATE);
        i_Language = prefer.getInt("Language", 1);
        iTextSize = prefer.getInt("TextSize", 5);
        iLineChartTextSize = prefer.getInt("LineChartTextSize", 5);
        iBarChartTextSize = prefer.getInt("BarChartTextSize", 5);
        iPieChartTextSize = prefer.getInt("PieChartTextSize", 5);
        strName = prefer.getString("Name", "");
        iGender = prefer.getInt("Gender", 0);
        strBirthday = prefer.getString("Birthday", "");

        //clsData.SetLanguage(i_Language);
        clsData.SetTextSize(iTextSize);
        clsData.SetLineChartTextSize(iLineChartTextSize);
        clsData.SetBarChartTextSize(iBarChartTextSize);
        clsData.SetPieChartTextSize(iPieChartTextSize);

        sbTextSize.setProgress(iTextSize);
        sbTextSize.setOnSeekBarChangeListener(textOnSeekBarChange);
        sbLineChartTextSize.setProgress(iLineChartTextSize);
        sbLineChartTextSize.setOnSeekBarChangeListener(LineChartTextOnSeekBarChange);
        sbBarChartTextSize.setProgress(iBarChartTextSize);
        sbBarChartTextSize.setOnSeekBarChangeListener(BarChartTextOnSeekBarChange);

        sbPieChartTextSize.setProgress(iPieChartTextSize);
        sbPieChartTextSize.setOnSeekBarChangeListener(PieChartTextOnSeekBarChange);
        ChangeTextSize();

        getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_HIDDEN);//不要每次一進畫面就跳出鍵盤

        tvVersion.setVisibility(View.INVISIBLE);
        tvLanguage.setVisibility(View.INVISIBLE);

        rbtn_tc.setVisibility(View.INVISIBLE);
        rbtn_sc.setVisibility(View.INVISIBLE);
        rbtn_eng.setVisibility(View.INVISIBLE);
        tvName.setVisibility(View.INVISIBLE);
        etName.setVisibility(View.INVISIBLE);
        tvGender.setVisibility(View.INVISIBLE);
        etGender.setVisibility(View.INVISIBLE);
        tvBirthday.setVisibility(View.INVISIBLE);
        etBirthday.setVisibility(View.INVISIBLE);
        btn_manual.setVisibility(View.INVISIBLE);

        //tvLineChartTextSize.setVisibility(View.INVISIBLE);
        //sbLineChartTextSize.setVisibility(View.INVISIBLE);
        tvBarChartTextSize.setVisibility(View.INVISIBLE);
        sbBarChartTextSize.setVisibility(View.INVISIBLE);
    }
    @Override
    protected void onStart() {
        super.onStart();

        bQuit = false;
        Glide.with(mContext).load(R.drawable.bg_0).apply(myGdiOptions).into(ivBG);
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
        intent.setClass(this, main.class);
        startActivity(intent);
        overridePendingTransition(0, 0);
    }
    //===================================================
    //===================================================
    //===================================================
    void SaveData() {
        SharedPreferences prefer = getSharedPreferences("EEGAppFile", MODE_PRIVATE);
        strName = etName.getText().toString();
        iGender = Integer.parseInt(etGender.getText().toString());
        strBirthday = etBirthday.getText().toString();
        SharedPreferences.Editor editor = prefer.edit();
        editor.putInt("Language", i_Language);
        editor.putString("Name", strName);
        editor.putInt("Gender", iGender);
        editor.putString("Birthday", strBirthday);
        editor.putInt("TextSize", iTextSize);
        editor.putInt("LineChartTextSize", iLineChartTextSize);
        editor.putInt("BarChartTextSize", iBarChartTextSize);
        editor.putInt("PieChartTextSize", iPieChartTextSize);
        editor.commit();

        clsData.SetPersonalData(strName,strBirthday,"","",iGender);
    }
    //===================================================
    public void rbtn_tc_OnClick(View view) {
        i_Language = 1;
        //clsData.SetLanguage(1);
        ChangeTextSize();
    }
    //===================================================
    public void rbtn_sc_OnClick(View view) {
        i_Language = 2;
        //clsData.SetLanguage(2);
        ChangeTextSize();
    }
    //===================================================
    public void rbtn_eng_OnClick(View view) {
        i_Language = 3;
        //clsData.SetLanguage(3);
        ChangeTextSize();
    }
    //===================================================
    private SeekBar.OnSeekBarChangeListener textOnSeekBarChange = new SeekBar.OnSeekBarChangeListener() {
        @Override
        public void onStopTrackingTouch(SeekBar seekBar) {}
        @Override
        public void onStartTrackingTouch(SeekBar seekBar) {}
        @Override
        public void onProgressChanged(SeekBar seekBar, int progress, boolean fromUser) {
            iTextSize = progress;
            if(iTextSize < 1)
                iTextSize = 1;
            clsData.SetTextSize(iTextSize);
            ChangeTextSize();
        }
    };
    private SeekBar.OnSeekBarChangeListener LineChartTextOnSeekBarChange = new SeekBar.OnSeekBarChangeListener() {
        @Override
        public void onStopTrackingTouch(SeekBar seekBar) {}
        @Override
        public void onStartTrackingTouch(SeekBar seekBar) {}
        @Override
        public void onProgressChanged(SeekBar seekBar, int progress, boolean fromUser) {
            iLineChartTextSize = progress;
            if(iLineChartTextSize < 1) {
                iLineChartTextSize = 1;
                sbLineChartTextSize.setProgress(iLineChartTextSize);
            }
            //clsData.SetLineChartTextRatio((float)iLineChartTextSize / 10.0f);
            clsData.SetLineChartTextSize(iLineChartTextSize);
            ChangeTextSize();
        }
    };
    private SeekBar.OnSeekBarChangeListener BarChartTextOnSeekBarChange = new SeekBar.OnSeekBarChangeListener() {
        @Override
        public void onStopTrackingTouch(SeekBar seekBar) {}
        @Override
        public void onStartTrackingTouch(SeekBar seekBar) {}
        @Override
        public void onProgressChanged(SeekBar seekBar, int progress, boolean fromUser) {
            iBarChartTextSize = progress;
            if(iBarChartTextSize < 1)
                iBarChartTextSize = 1;
            clsData.SetBarChartTextSize(iBarChartTextSize);
            ChangeTextSize();
        }
    };
    private SeekBar.OnSeekBarChangeListener PieChartTextOnSeekBarChange = new SeekBar.OnSeekBarChangeListener() {
        @Override
        public void onStopTrackingTouch(SeekBar seekBar) {}
        @Override
        public void onStartTrackingTouch(SeekBar seekBar) {}
        @Override
        public void onProgressChanged(SeekBar seekBar, int progress, boolean fromUser) {
            iPieChartTextSize = progress;
            if(iPieChartTextSize < 1)
                iPieChartTextSize = 1;
            clsData.SetPieChartTextSize(iPieChartTextSize);
            ChangeTextSize();
        }
    };
    //===================================================
    void ChangeTextSize() {
        tvVersion.setTextSize(TypedValue.COMPLEX_UNIT_PX, 100f * clsData.fTextScale());

        tvLanguage.setTextSize(TypedValue.COMPLEX_UNIT_PX, 100f * clsData.fTextScale());
        tvName.setTextSize(TypedValue.COMPLEX_UNIT_PX, 100f * clsData.fTextScale());
        tvGender.setTextSize(TypedValue.COMPLEX_UNIT_PX, 100f * clsData.fTextScale());
        tvBirthday.setTextSize(TypedValue.COMPLEX_UNIT_PX, 100f * clsData.fTextScale());
        rbtn_tc.setTextSize(TypedValue.COMPLEX_UNIT_PX, 100f * clsData.fTextScale());
        rbtn_sc.setTextSize(TypedValue.COMPLEX_UNIT_PX, 100f * clsData.fTextScale());
        rbtn_eng.setTextSize(TypedValue.COMPLEX_UNIT_PX, 100f * clsData.fTextScale());

        etName.setTextSize(TypedValue.COMPLEX_UNIT_PX, 100f * clsData.fTextScale());
        etGender.setTextSize(TypedValue.COMPLEX_UNIT_PX, 100f * clsData.fTextScale());
        etBirthday.setTextSize(TypedValue.COMPLEX_UNIT_PX, 100f * clsData.fTextScale());

        tvTextSize.setTextSize(TypedValue.COMPLEX_UNIT_PX, 100f * clsData.fTextScale());
        tvLineChartTextSize.setTextSize(TypedValue.COMPLEX_UNIT_PX, 100f * clsData.fTextScale());
        tvBarChartTextSize.setTextSize(TypedValue.COMPLEX_UNIT_PX, 100f * clsData.fTextScale());
        tvPieChartTextSize.setTextSize(TypedValue.COMPLEX_UNIT_PX, 100f * clsData.fTextScale());

        etName.setText(strName);
        etGender.setText(""+iGender);
        etBirthday.setText(strBirthday);
        btn_manual.setTextSize(TypedValue.COMPLEX_UNIT_PX, 80f * clsData.fTextScale());

        tvTextSize.setText("字體大小 " + iTextSize);
        tvLineChartTextSize.setText("折線圖字體大小 " + iLineChartTextSize);
        tvBarChartTextSize.setText("條狀圖字體大小 " + iBarChartTextSize);
        tvPieChartTextSize.setText("圓餅圖字體大小 " + iPieChartTextSize);
        /*
        switch(i_Language){
            case 1:
                rbtn_tc.setChecked(true);
                rbtn_sc.setChecked(false);
                rbtn_eng.setChecked(false);
                tvVersion.setText("版本 1.0");
                tvLanguage.setText("語言");
                tvName.setText("姓名");
                tvGender.setText("性別");
                tvBirthday.setText("生日");
                tvTextSize.setText("字體大小 " + iTextSize);
                tvLineChartTextSize.setText("折線圖字體大小 " + iLineChartTextSize);
                tvBarChartTextSize.setText("條狀圖字體大小 " + iBarChartTextSize);
                tvPieChartTextSize.setText("條狀圖字體大小 " + iPieChartTextSize);
                btn_manual.setText("操作手冊");
                break;
            case 2:
                rbtn_tc.setChecked(false);
                rbtn_sc.setChecked(true);
                rbtn_eng.setChecked(false);
                tvVersion.setText("版本 1.0");
                tvLanguage.setText("语言");
                tvName.setText("姓名");
                tvGender.setText("性別");
                tvBirthday.setText("生日");
                tvTextSize.setText("字体大小 " + iTextSize);
                tvLineChartTextSize.setText("折线图字体大小 " + iLineChartTextSize);
                tvBarChartTextSize.setText("条状图字体大小 " + iBarChartTextSize);
                btn_manual.setText("操作手冊");
                break;
            case 3:
                rbtn_tc.setChecked(false);
                rbtn_sc.setChecked(false);
                rbtn_eng.setChecked(true);
                tvVersion.setText("Version 1.0");
                tvLanguage.setText("Language");
                tvName.setText("Name");
                tvGender.setText("Gender");
                tvBirthday.setText("Birthday");
                tvTextSize.setText("Font Size " + iTextSize);
                tvLineChartTextSize.setText("Line Chart Font Size " + iLineChartTextSize);
                tvBarChartTextSize.setText("Bar Chart Font Size " + iBarChartTextSize);
                btn_manual.setText("manual");
                break;
        }
        */
    }
    //===================================================
    public void btn_manual_OnClick(View view) {
        /*
        Intent intent = new Intent();
        intent.setClass(this, manual.class);
        startActivity(intent);
        */
    }
    //===================================================
}