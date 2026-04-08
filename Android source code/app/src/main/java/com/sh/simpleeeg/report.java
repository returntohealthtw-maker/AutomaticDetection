package com.sh.simpleeeg;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ActivityInfo;
import android.database.Cursor;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.pdf.PdfDocument;
import android.net.Uri;
import android.os.Handler;
import android.os.Bundle;
import android.provider.OpenableColumns;
import android.util.TypedValue;
import android.view.View;
import android.view.WindowManager;
import android.widget.ImageView;
import android.widget.ProgressBar;
import android.widget.TextView;

import com.bumptech.glide.Glide;
import com.bumptech.glide.request.RequestOptions;
import com.github.mikephil.charting.charts.PieChart;
import com.github.mikephil.charting.components.Description;
import com.github.mikephil.charting.components.Legend;
import com.github.mikephil.charting.data.PieData;
import com.github.mikephil.charting.data.PieDataSet;
import com.github.mikephil.charting.data.PieEntry;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;

public class report extends Activity {
    CLS_DATA clsData = new CLS_DATA();
    CLS_PARAM S = new CLS_PARAM();

    RequestOptions myGdiOptions;

    PieChart chartPreAtt, chartPreMed;
    TextView tv1, tv2, tv3, tv4, tv5, tv6,tv7,tv8,tv9,tv10,tv11;
    TextView tvDelta, tvTheta, tvLowAlpha, tvHighAlpha, tvLowBeta, tvHighBeta, tvLowGamma, tvHighGamma;
    TextView tvPressure, tvFatigue, tvSleepQuality;
    ProgressBar pbDelta, pbTheta, pbLowAlpha, pbHighAlpha, pbLowBeta, pbHighBeta, pbLowGamma, pbHighGamma;
    ProgressBar pbPressure, pbFatigue, pbSleepQuality;
    TextView tvTimeSection;
    ImageView ivLeft,ivRight;

    Context mContext;

    int iCurrentDisplaySection = 0;

    @SuppressLint("SourceLockedOrientationActivity")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_PORTRAIT);
        setContentView(R.layout.report);

        mContext = this;
        myGdiOptions = new RequestOptions().fitCenter();

        chartPreAtt = (PieChart) findViewById(R.id.pieChartAtt);
        chartPreMed = (PieChart) findViewById(R.id.pieChartMed);
        tvPressure = (TextView)findViewById(R.id.tvPressure);
        tvFatigue = (TextView)findViewById(R.id.tvFatigue);
        tvSleepQuality = (TextView)findViewById(R.id.tvSleepQuality);
        tvDelta = (TextView)findViewById(R.id.tvDelta);
        tvTheta = (TextView)findViewById(R.id.tvTheta);
        tvLowAlpha = (TextView)findViewById(R.id.tvLowAlpha);
        tvHighAlpha = (TextView)findViewById(R.id.tvHighAlpha);
        tvLowBeta = (TextView)findViewById(R.id.tvLowBeta);
        tvHighBeta = (TextView)findViewById(R.id.tvHighBeta);
        tvLowGamma = (TextView)findViewById(R.id.tvLowGamma);
        tvHighGamma = (TextView)findViewById(R.id.tvHighGamma);
        pbPressure = (ProgressBar)findViewById(R.id.pbPressure);
        pbFatigue = (ProgressBar)findViewById(R.id.pbFatigue);
        pbSleepQuality = (ProgressBar)findViewById(R.id.pbSleepQuality);
        pbDelta = (ProgressBar)findViewById(R.id.pbDelta);
        pbTheta = (ProgressBar)findViewById(R.id.pbTheta);
        pbLowAlpha = (ProgressBar)findViewById(R.id.pbLowAlpha);
        pbHighAlpha = (ProgressBar)findViewById(R.id.pbHighAlpha);
        pbLowBeta = (ProgressBar)findViewById(R.id.pbLowBeta);
        pbHighBeta = (ProgressBar)findViewById(R.id.pbHighBeta);
        pbLowGamma = (ProgressBar)findViewById(R.id.pbLowGamma);
        pbHighGamma = (ProgressBar)findViewById(R.id.pbHighGamma);
        tv1 = (TextView)findViewById(R.id.tv1);
        tv2 = (TextView)findViewById(R.id.tv2);
        tv3 = (TextView)findViewById(R.id.tv3);
        tv4 = (TextView)findViewById(R.id.tv4);
        tv5 = (TextView)findViewById(R.id.tv5);
        tv6 = (TextView)findViewById(R.id.tv6);
        tv7 = (TextView)findViewById(R.id.tv7);
        tv8 = (TextView)findViewById(R.id.tv8);
        tv9 = (TextView)findViewById(R.id.tv9);
        tv10 = (TextView)findViewById(R.id.tv10);
        tv11 = (TextView)findViewById(R.id.tv11);
        tvTimeSection = (TextView)findViewById(R.id.tvTimeSection);
        ivLeft = (ImageView)findViewById(R.id.ivLeft);
        ivRight = (ImageView)findViewById(R.id.ivRight);

        float fSize = 70f;
        tv1.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize*clsData.fTextScale());
        tv2.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize*clsData.fTextScale());
        tv3.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize*clsData.fTextScale());
        tv4.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize*clsData.fTextScale());
        tv5.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize*clsData.fTextScale());
        tv6.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize*clsData.fTextScale());
        tv7.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize*clsData.fTextScale());
        tv8.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize*clsData.fTextScale());
        tv9.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize*clsData.fTextScale());
        tv10.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize*clsData.fTextScale());
        tv11.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize*clsData.fTextScale());
        tvPressure.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize*clsData.fTextScale());
        tvFatigue.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize*clsData.fTextScale());
        tvSleepQuality.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize*clsData.fTextScale());
        tvDelta.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize*clsData.fTextScale());
        tvTheta.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize*clsData.fTextScale());
        tvLowAlpha.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize*clsData.fTextScale());
        tvHighAlpha.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize*clsData.fTextScale());
        tvLowBeta.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize*clsData.fTextScale());
        tvHighBeta.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize*clsData.fTextScale());
        tvLowGamma.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize*clsData.fTextScale());
        tvHighGamma.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize*clsData.fTextScale());
        tvTimeSection.setTextSize(TypedValue.COMPLEX_UNIT_PX, fSize*clsData.fTextScale());


        for(int ss=0; ss<clsData.listSectionData().size(); ss++){
            clsData.DoRawCalculation(ss);
        }

        ShowReport(iCurrentDisplaySection);
        if(clsData.listRecordingTime().size() == 0)
            tvTimeSection.setText("");
        else {
            String str = String.format("%d.   %02d:%02d",
                    iCurrentDisplaySection + 1,
                    clsData.listRecordingTime().get(iCurrentDisplaySection).iStartHour,
                    clsData.listRecordingTime().get(iCurrentDisplaySection).iStartMin);
            tvTimeSection.setText(str);
        }

        SAF_CreateFile();
    }
    @Override
    protected void onStart() {
        super.onStart();
        Glide.with(mContext).load(R.drawable.left).apply(myGdiOptions).into(ivLeft);
        Glide.with(mContext).load(R.drawable.right).apply(myGdiOptions).into(ivRight);
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
        Glide.with(this).clear(ivLeft);
        Glide.with(this).clear(ivRight);
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
    void ShowReport(int _iSection) {
        int ss = _iSection;
        int iZero = 0;

        int iii = clsData.iGetRawPercentage(ss, S.MEDITATION);
        tvPressure.setText(String.valueOf(100-clsData.iGetRawPercentage(ss, S.MEDITATION))+" % ");
        pbPressure.setProgress(100-clsData.iGetRawPercentage(ss, S.MEDITATION));

        tvFatigue.setText(iZero+" % ");
        pbFatigue.setProgress(iZero);

        tvSleepQuality.setText(String.valueOf(iZero)+" % ");
        pbSleepQuality.setProgress(iZero);



        tvDelta.setText(String.valueOf(clsData.iGetRawPercentage(ss, S.DELTA))+" % ");
        pbDelta.setProgress(clsData.iGetRawPercentage(ss, S.DELTA));

        tvTheta.setText(String.valueOf(clsData.iGetRawPercentage(ss, S.THETA))+" % ");
        pbTheta.setProgress(clsData.iGetRawPercentage(ss, S.THETA));

        tvLowAlpha.setText(String.valueOf(clsData.iGetRawPercentage(ss, S.LOWALPHA))+" % ");
        pbLowAlpha.setProgress(clsData.iGetRawPercentage(ss, S.LOWALPHA));

        tvHighAlpha.setText(String.valueOf(clsData.iGetRawPercentage(ss, S.HIGHALPHA))+" % ");
        pbHighAlpha.setProgress(clsData.iGetRawPercentage(ss, S.HIGHALPHA));

        tvLowBeta.setText(String.valueOf(clsData.iGetRawPercentage(ss, S.LOWBETA))+" % ");
        pbLowBeta.setProgress(clsData.iGetRawPercentage(ss, S.LOWBETA));

        tvHighBeta.setText(String.valueOf(clsData.iGetRawPercentage(ss, S.HIGHBETA))+" % ");
        pbHighBeta.setProgress(clsData.iGetRawPercentage(ss, S.HIGHBETA));

        tvLowGamma.setText(String.valueOf(clsData.iGetRawPercentage(ss, S.LOWGAMMA))+" % ");
        pbLowGamma.setProgress(clsData.iGetRawPercentage(ss, S.LOWGAMMA));

        tvHighGamma.setText(String.valueOf(clsData.iGetRawPercentage(ss, S.HIGHGAMMA))+" % ");
        pbHighGamma.setProgress(clsData.iGetRawPercentage(ss, S.HIGHGAMMA));

        CreatePieChart(ss);
    }
    //==============================================================================================
    void CreatePieChart(int _iSection) {
        int ss = _iSection;


        PieDataSet pieDataSetPreAtt, pieDataSetPostAtt, pieDataSetPreMed, pieDataSetPostMed;
        PieData pieDataPreAtt, pieDataPostAtt, pieDataPreMed, pieDataPostMed;
        ArrayList<PieEntry> _entriesPreAtt, _entriesPostAtt, _entriesPreMed, _entriesPostMed;
        Description _descriptionPreAtt, _descriptionPostAtt, _descriptionPreMed, _descriptionPostMed;

        String str;

        //---------------------------
        /*
        final int[] MY_COLORS = {Color.rgb(255,180,180), Color.rgb(0,255,0), Color.rgb(0,255,255)};
        ArrayList<Integer> colors = new ArrayList<Integer>();
        for(int c: MY_COLORS)
            colors.add(c);
        */
        //---------------------------
        //--------------------------- Pre Att
        //---------------------------
        _entriesPreAtt = new ArrayList<>();
        if(clsData.fGetPart(1,1) > 0)
            _entriesPreAtt.add(new PieEntry(clsData.fGetPart(1,1), "低"));//顏色無效
        if(clsData.fGetPart(1,2) > 0)
            _entriesPreAtt.add(new PieEntry(clsData.fGetPart(1,2), "中"));
        if(clsData.fGetPart(1,3) > 0)
            _entriesPreAtt.add(new PieEntry(clsData.fGetPart(1,3), "高"));
        pieDataSetPreAtt = new PieDataSet(_entriesPreAtt, "");
        pieDataSetPreAtt.setValueTextSize(40f*clsData.fPieChartTextScale());//每片裡面的文字大小

        pieDataSetPreAtt.setFormSize(30f*clsData.fPieChartTextScale());//圖下方高中低顏色塊的大小

        if(clsData.fGetPart(1,1) > 0 && clsData.fGetPart(1,2) > 0 && clsData.fGetPart(1,3) > 0)
            pieDataSetPreAtt.setColors(Color.rgb(255,180,180), Color.rgb(0,255,0), Color.rgb(0,255,255));
        else if(clsData.fGetPart(1,1) > 0 && clsData.fGetPart(1,2) > 0)
            pieDataSetPreAtt.setColors(Color.rgb(255,180,180), Color.rgb(0,255,0));
        else if(clsData.fGetPart(1,2) > 0 && clsData.fGetPart(1,3) > 0)
            pieDataSetPreAtt.setColors(Color.rgb(0,255,0), Color.rgb(0,255,255));
        else if(clsData.fGetPart(1,1) > 0 && clsData.fGetPart(1,3) > 0)
            pieDataSetPreAtt.setColors(Color.rgb(255,180,180), Color.rgb(0,255,255));
        else if(clsData.fGetPart(1,1) > 0)
            pieDataSetPreAtt.setColors(Color.rgb(255,180,180));
        else if(clsData.fGetPart(1,2) > 0)
            pieDataSetPreAtt.setColors(Color.rgb(0,255,0));
        else if(clsData.fGetPart(1,3) > 0)
            pieDataSetPreAtt.setColors(Color.rgb(0,255,255));


        //pieDataSetPreAtt.setValueLineColor(Color.DKGRAY);
        pieDataSetPreAtt.setValueTextColor(Color.BLUE);//每片裡面的數值的顏色

        pieDataPreAtt = new PieData();
        pieDataPreAtt.addDataSet(pieDataSetPreAtt);
        //---------------------------每片裡面的文字
        chartPreAtt.setDrawSliceText(true);//每片裡面的中文的文字
        chartPreAtt.setEntryLabelColor(Color.BLUE);//每片裡面的中文的顏色
        chartPreAtt.setData(pieDataPreAtt);
        //---------------------------中間洞洞
        str = String.valueOf(clsData.iGetRawPercentage(ss, S.ATTENTION));
        //pieChart.setHoleRadius(25f);
        chartPreAtt.setCenterText("專注\n"+str+"%");
        chartPreAtt.setCenterTextSize(50f*clsData.fPieChartTextScale());//正中間文字的大小
        chartPreAtt.setCenterTextColor(Color.RED);
        //---------------------------左下方的文字標示
        chartPreAtt.getLegend().setEnabled(true);//隱藏圖片左下方的文字標示
        chartPreAtt.getLegend().setTextSize(50f*clsData.fPieChartTextScale());
        chartPreAtt.getLegend().setTextColor(Color.WHITE);
        chartPreAtt.getLegend().setPosition(Legend.LegendPosition.BELOW_CHART_CENTER );
        //---------------------------右下方的文字標示
        //pieChart.setDescription("");//圖片右下角的文字
        _descriptionPreAtt = new Description();
        _descriptionPreAtt.setTextColor(Color.GREEN);
        _descriptionPreAtt.setTextSize(50f*clsData.fPieChartTextScale());
        _descriptionPreAtt.setText("");
        chartPreAtt.setDescription(_descriptionPreAtt);//圖片右下角的文字
        //---------------------------
        chartPreAtt.animateY(1500);//可以手動轉圈圈的旋轉動畫
        chartPreAtt.setRotationEnabled(false);//可以手動轉圈圈
        //---------------------------
        //--------------------------- pre med
        //---------------------------
        _entriesPreMed = new ArrayList<>();
        if(clsData.fGetPart(2,1) > 0)
            _entriesPreMed.add(new PieEntry(clsData.fGetPart(2,1), "低"));//顏色無效
        if(clsData.fGetPart(2,2) > 0)
            _entriesPreMed.add(new PieEntry(clsData.fGetPart(2,2), "中"));
        if(clsData.fGetPart(2,3) > 0)
            _entriesPreMed.add(new PieEntry(clsData.fGetPart(2,3), "高"));
        pieDataSetPreMed = new PieDataSet(_entriesPreMed, "");
        pieDataSetPreMed.setValueTextSize(40f*clsData.fPieChartTextScale());//每片裡面的文字大小

        pieDataSetPreMed.setFormSize(30f*clsData.fPieChartTextScale());//圖下方高中低顏色塊的大小


        if(clsData.fGetPart(2,1) > 0 && clsData.fGetPart(2,2) > 0 && clsData.fGetPart(2,3) > 0)
            pieDataSetPreMed.setColors(Color.rgb(255,180,180), Color.rgb(0,255,0), Color.rgb(0,255,255));
        else if(clsData.fGetPart(2,1) > 0 && clsData.fGetPart(2,2) > 0)
            pieDataSetPreMed.setColors(Color.rgb(255,180,180), Color.rgb(0,255,0));
        else if(clsData.fGetPart(2,2) > 0 && clsData.fGetPart(2,3) > 0)
            pieDataSetPreMed.setColors(Color.rgb(0,255,0), Color.rgb(0,255,255));
        else if(clsData.fGetPart(2,1) > 0 && clsData.fGetPart(2,3) > 0)
            pieDataSetPreMed.setColors(Color.rgb(255,180,180), Color.rgb(0,255,255));
        else if(clsData.fGetPart(2,1) > 0)
            pieDataSetPreMed.setColors(Color.rgb(255,180,180));
        else if(clsData.fGetPart(2,2) > 0)
            pieDataSetPreMed.setColors(Color.rgb(0,255,0));
        else if(clsData.fGetPart(2,3) > 0)
            pieDataSetPreMed.setColors(Color.rgb(0,255,255));



        //pieDataSetPreMed.setValueLineColor(Color.DKGRAY);
        pieDataSetPreMed.setValueTextColor(Color.BLUE);//每片裡面的數值的顏色

        pieDataPreMed = new PieData();
        pieDataPreMed.addDataSet(pieDataSetPreMed);
        //---------------------------每片裡面的文字
        chartPreMed.setDrawSliceText(true);//每片裡面的中文的文字
        chartPreMed.setEntryLabelColor(Color.BLUE);//每片裡面的中文的顏色
        chartPreMed.setData(pieDataPreMed);
        //---------------------------中間洞洞
        str = String.valueOf(clsData.iGetRawPercentage(ss, S.MEDITATION));
        //pieChart.setHoleRadius(25f);
        chartPreMed.setCenterText("放鬆\n"+str+"%");
        chartPreMed.setCenterTextSize(50f*clsData.fPieChartTextScale());//正中間文字的大小
        chartPreMed.setCenterTextColor(Color.RED);
        //---------------------------左下方的文字標示
        chartPreMed.getLegend().setEnabled(true);//隱藏圖片左下方的文字標示
        chartPreMed.getLegend().setTextSize(50f*clsData.fPieChartTextScale());
        chartPreMed.getLegend().setTextColor(Color.WHITE);
        chartPreMed.getLegend().setPosition(Legend.LegendPosition.BELOW_CHART_CENTER );
        //---------------------------右下方的文字標示
        //pieChart.setDescription("");//圖片右下角的文字
        _descriptionPreMed = new Description();
        _descriptionPreMed.setTextColor(Color.GREEN);
        _descriptionPreMed.setTextSize(50f*clsData.fPieChartTextScale());
        _descriptionPreMed.setText("");
        chartPreMed.setDescription(_descriptionPreMed);//圖片右下角的文字
        //---------------------------
        chartPreMed.animateY(1500);//可以手動轉圈圈的旋轉動畫
        chartPreMed.setRotationEnabled(false);//可以手動轉圈圈
    }
    //==============================================================================================
    public void ivLeft_OnClick(View view) {
        if(iCurrentDisplaySection == 0)
            return;

        iCurrentDisplaySection--;
        //clsData.DoRawCalculation(iCurrentDisplaySection);
        ShowReport(iCurrentDisplaySection);
        String str = String.format("%d.   %02d:%02d",
                iCurrentDisplaySection+1,
                clsData.listRecordingTime().get(iCurrentDisplaySection).iStartHour,
                clsData.listRecordingTime().get(iCurrentDisplaySection).iStartMin);
        tvTimeSection.setText(str);
    }
    //==============================================================================================
    public void ivRight_OnClick(View view) {
        if(iCurrentDisplaySection >= clsData.listSectionData().size()-1)
            return;
        iCurrentDisplaySection++;
        //clsData.DoRawCalculation(iCurrentDisplaySection);
        ShowReport(iCurrentDisplaySection);
        String str = String.format("%d.   %02d:%02d",
                iCurrentDisplaySection+1,
                clsData.listRecordingTime().get(iCurrentDisplaySection).iStartHour,
                clsData.listRecordingTime().get(iCurrentDisplaySection).iStartMin);
        tvTimeSection.setText(str);
    }
    //===================================================
    void SAF_CreateFile(){
        Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("application/vnd.ms-excel");

        SimpleDateFormat dateFormat = new SimpleDateFormat("_yyyyMMdd_HHmmss");
        Date curDate = new Date(System.currentTimeMillis()) ; // 獲取當前時間
        String strDateTime = dateFormat.format(curDate);
        String strFileName = clsData.strName() + strDateTime;

        intent.putExtra(Intent.EXTRA_TITLE, strFileName);
        startActivityForResult(intent, S.ID_CREATE_FILE);
    }
    //===================================================
    @Override
    protected void onActivityResult(int _iRequestCode, int _iResultCode, Intent _iReturnIntent) {
        super.onActivityResult(_iRequestCode, _iResultCode, _iReturnIntent);
        if (_iRequestCode == S.ID_CREATE_FILE) {
            if (_iReturnIntent == null || _iResultCode != Activity.RESULT_OK) {
                return;
            }

            Uri uriExcelFile = _iReturnIntent.getData();

            Cursor _cursorReturn = getContentResolver().query(uriExcelFile, null, null, null, null);
            int _iFileNameIndex = _cursorReturn.getColumnIndex(OpenableColumns.DISPLAY_NAME);
            int _iFileSizeIndex = _cursorReturn.getColumnIndex(OpenableColumns.SIZE);
            _cursorReturn.moveToFirst();

            String str = _cursorReturn.getString(_iFileNameIndex);

            clsData.WriteXLS(mContext, uriExcelFile);
        }
    }
    //==============================================================================================
}
