package com.sh.simpleeeg;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Environment;
import android.util.DisplayMetrics;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.FrameLayout;
import android.widget.TextView;
import android.widget.Toast;

import org.apache.poi.hssf.usermodel.HSSFWorkbook;
import org.apache.poi.ss.usermodel.Cell;
import org.apache.poi.ss.usermodel.Row;
import org.apache.poi.ss.usermodel.Sheet;
import org.apache.poi.ss.usermodel.Workbook;

import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStream;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;

/**
 * Created by user on 2017/12/13.
 */

public class CLS_DATA
{
    CLS_PARAM S = new CLS_PARAM();

    Bitmap bmpScreenshot;


    static String strMAC = "";
    static String strNumber = "";
    static int  iGoodSignal = 0;
    static int  iAttention = 0;
    static int  iMeditation = 0;
    static int  iDelta = 0;
    static int  iTheta = 0;
    static int  iLowAlpha = 0;
    static int  iHighAlpha = 0;
    static int  iLowBeta = 0;
    static int  iHighBeta = 0;
    static int  iLowGamma = 0;
    static int  iHighGamma = 0;
    static int  iFeedbackGQD = 0;

    static boolean bfNeuroskyConnected = false;
    static boolean bSendDataOk = false;

    static int iBWTestModel = 0;
    static int iBVRTestModel = 0;

    public static int iScreenWidth = 1;
    public static int iScreenHeight = 1;

    static float fScale = 1;

    static int iMaxVomume = 10;
    static int iVolume = 50;

    static Context m_Context;

    static List<CLS_SECTION_DATA> list_SectionData = new ArrayList<CLS_SECTION_DATA>();


    static double dThetaSum=0,dDeltaSum=0,dLowAlphaSum=0,dHighAlphaSum=0,
        dLowBetaSum=0,dHighBetaSum=0,dLowGammaSum=0,dHighGammaSum=0,
        dAttentionSum=0,dMeditationSum=0;
    static double dThetaAvg=0,dDeltaAvg=0,dLowAlphaAvg=0,dHighAlphaAvg=0,
        dLowBetaAvg=0,dHighBetaAvg=0,dLowGammaAvg=0,dHighGammaAvg=0,
        dAttentionAvg=0,dMeditationAvg=0;

    static int iVersion = 2;

    static int iTrainingNum = 0;

    static String str_Name, strPhone, strBirthday, strEmail;
    static String strTeacherName  = "";   // 登入的顧問姓名
    static String strSubjectName  = "受測者"; // 受測者姓名（付款時填寫）
    static String strReportType   = "";   // 報告類型（life_trial / test_1 ...）
    static String strOrderId      = "";   // 綠界訂單編號
    static int iGender=1;

    public static int iThreadProcess = 0;

    static float fAttLowPart=0, fAttMediumPart=0, fAttHighPart=0;
    static float fMedLowPart=0, fMedMediumPart=0, fMedHighPart=0;

    static int i_CurrentSection = 0;

    static boolean b_EnableRecording = false;

    static int iFeedbackCount = 0;
    static int iFeedbackCountPrev = 0;

    //==============================================================================================
    //==============================================================================================
    //==============================================================================================
    public CLS_DATA() {
    }
    //==============================================================================================
    public void EnableRecording(boolean _bState){
        b_EnableRecording = _bState;
        b_EnableRecording = _bState;
    }
    public boolean bEnableRecording(){return b_EnableRecording;}
    public List<CLS_SECTION_DATA> listSectionData(){return list_SectionData;}
    public int iCurrentSection(){return i_CurrentSection;}
    public boolean bNextSection(){
        if(i_CurrentSection >= list_SectionData.size()-1)
            return false;
        i_CurrentSection++;
        return true;
    }
    //==============================================================================================
    public void ClearListSectionData(){
        for(int ii=0; ii<list_SectionData.size(); ii++) {
            list_SectionData.get(ii).list_RawData.clear();
        }
        list_SectionData.clear();
    }
    //===================================================
    public void NewListSectionData(){
        i_CurrentSection = 0;

        CLS_SECTION_DATA _list_section = new CLS_SECTION_DATA();
        _list_section.list_RawData.clear();
        list_SectionData.add(_list_section);
    }
    //==============================================================================================
    public void SetMemberInfo(String _strName, String _strBirthday, String _strEmail, String _strPhone)
    {
        str_Name = _strName;
        strBirthday = _strBirthday;
        strEmail = _strEmail;
        strPhone = _strPhone;
    }
    public void SetPersonalData(String _strName, String _strBirthday, String _strEmail,
                                String _strPhone, int _iGender)
    {
        str_Name = _strName;
        strBirthday = _strBirthday;
        strEmail = _strEmail;
        strPhone = _strPhone;
        iGender = _iGender;
    }
    public String strName(){return str_Name;}
    public String strGetBirthday(){return strBirthday;}
    public String strGetEmail(){return strEmail;}
    public String strGetPhone(){return strPhone;}
    public int  iGetGender(){return iGender;}
    public void setTeacherName(String name)  { strTeacherName = (name != null) ? name : ""; }
    public String strGetTeacherName()        { return strTeacherName; }

    public void setSubjectName(String name)  { strSubjectName = (name != null && !name.isEmpty()) ? name : "受測者"; }
    public String getSubjectName()           { return strSubjectName; }

    public void setReportType(String type)   { strReportType = (type != null) ? type : ""; }
    public String getReportType()            { return strReportType; }

    public void setOrderId(String id)        { strOrderId = (id != null) ? id : ""; }
    public String getOrderId()               { return strOrderId; }
    public void SetScale(float _fScale){fScale = _fScale;}
    public float fGetScale(){return fScale;}
    public void SendDataOk(boolean bVal){bSendDataOk = bVal;}
    public boolean bIsSendDataOk(){return bSendDataOk;}
    //==============================================================================================
    public void SetMAC(String _strMAC)
    {
        strMAC = _strMAC;
    }
    public String strGetMac(){return strMAC;}
    //==============================================================================================
    public void SetBrainData(int _iGoodSignal, int _iAtt, int _iMed, int _iDelta, int _iTheta,
                            int _iLowAlpha, int _iHighAlpha, int _iLowBeta, int _iHighBeta,
                            int _iLowGamma, int _iHighGamma)
    {
        try {
            iGoodSignal = _iGoodSignal;
            iAttention = _iAtt;
            iMeditation = _iMed;
            iDelta = _iDelta;
            iTheta = _iTheta;
            iLowAlpha = _iLowAlpha;
            iHighAlpha = _iHighAlpha;
            iLowBeta = _iLowBeta;
            iHighBeta = _iHighBeta;
            iLowGamma = _iLowGamma;
            iHighGamma = _iHighGamma;

            bfNeuroskyConnected = true;//有設定代表有收到腦波資料

            CLS_RAWDATA _raw = new CLS_RAWDATA();
            _raw.iGoodSignal = iGoodSignal;
            _raw.iTheta = iTheta;
            _raw.iDelta = iDelta;
            _raw.iLowAlpha = iLowAlpha;
            _raw.iHighAlpha = iHighAlpha;
            _raw.iLowBeta = iLowBeta;
            _raw.iHighBeta = iHighBeta;
            _raw.iLowGamma = iLowGamma;
            _raw.iHighGamma = iHighGamma;
            _raw.iAttention = iAttention;
            _raw.iMeditation = iMeditation;
            if(iFeedbackCount != iFeedbackCountPrev){
                iFeedbackCountPrev = iFeedbackCount;
                _raw.iFeedback = 1;
            }
            else
                _raw.iFeedback = 0;

            if (list_SectionData.size() > 0 && b_EnableRecording==true) {
                list_SectionData.get(i_CurrentSection).list_RawData.add((_raw));

                // ── 同步寫入本地 SQLite 資料庫 ──────────────────────────────
                CLS_DB.getInstance().saveCapture(
                        iGoodSignal, iAttention, iMeditation,
                        iDelta,    iTheta,
                        iLowAlpha, iHighAlpha,
                        iLowBeta,  iHighBeta,
                        iLowGamma, iHighGamma,
                        _raw.iFeedback
                );
                // ─────────────────────────────────────────────────────────────
            }
        }
        catch(Exception ex){
            String str = ex.toString();
        }
    }
    //==============================================================================================
    public float fGetPart(int _iCmd, int _iPart)
    {
        float fAttSum=fAttLowPart+fAttMediumPart+fAttHighPart;
        float fMedSum=fMedLowPart+fMedMediumPart+fMedHighPart;

        switch(_iCmd)
        {
            case 1://att
                switch(_iPart)
                {
                    case 1://low
                        return (fAttLowPart/fAttSum)*100;
                    case 2://med
                        return (fAttMediumPart/fAttSum)*100;
                    case 3://high
                        return (fAttHighPart/fAttSum)*100;
                }
                break;
            case 2://med
                switch(_iPart)
                {
                    case 1://low
                        return (fMedLowPart/fMedSum)*100;
                    case 2://med
                        return (fMedMediumPart/fMedSum)*100;
                    case 3://high
                        return (fMedHighPart/fMedSum)*100;
                }
                break;
        }
        return 0;
    }
    //==============================================================================================
    public void DoRawCalculation(int _iSection)
    {
        int iSize, ii;
        double _dTheta = 0, _dDelta = 0, _dLowAlpha = 0, _dHighAlpha = 0, _dLowBeta = 0, _dHighBeta = 0;
        double _dLowGamma = 0, _dHighGamma = 0;
        int _iAtt = 0, _iMed = 0;

        double _dDeltaHigh = 2500000;
        double _dThetaHigh = 450000;
        double _dLowAlphaHigh = 150000;
        double _dHighAlphaHigh = 150000;
        double _dLowBetaHigh = 150000;
        double _dHighBetaHigh = 150000;
        double _dLowGammaHigh = 150000;
        double _dHighGammaHigh = 150000;

        dThetaSum = 0;
        dDeltaSum = 0;
        dLowAlphaSum = 0;
        dHighAlphaSum = 0;
        dLowBetaSum = 0;
        dHighBetaSum = 0;
        dLowGammaSum = 0;
        dHighGammaSum = 0;
        dAttentionSum = 0;
        dMeditationSum = 0;

        List<CLS_RAWDATA> _list_RawData = list_SectionData.get(_iSection).list_RawData;
        for (int kk = 0; kk < _list_RawData.size(); kk++) {
            if (_list_RawData.get(kk).iDelta == 0 ||
                    _list_RawData.get(kk).iTheta == 0 ||
                    _list_RawData.get(kk).iLowAlpha == 0 ||
                    _list_RawData.get(kk).iHighAlpha == 0 ||
                    _list_RawData.get(kk).iLowBeta == 0 ||
                    _list_RawData.get(kk).iHighBeta == 0 ||
                    _list_RawData.get(kk).iLowGamma == 0 ||
                    _list_RawData.get(kk).iHighGamma == 0 ||
                    _list_RawData.get(kk).iAttention == 0 ||
                    _list_RawData.get(kk).iMeditation == 0 )
            {
                //_list_RawData.remove(kk);
            }
        }

        iSize = _list_RawData.size();
        if (iSize == 0)
            return;

        fAttLowPart = 0;
        fAttMediumPart = 0;
        fAttHighPart = 0;
        fMedLowPart = 0;
        fMedMediumPart = 0;
        fMedHighPart = 0;

        for (ii = 0; ii < iSize; ii++) {
            _dDelta = _list_RawData.get(ii).iDelta;
            _dTheta = _list_RawData.get(ii).iTheta;
            _dLowAlpha = _list_RawData.get(ii).iLowAlpha;
            _dHighAlpha = _list_RawData.get(ii).iHighAlpha;
            _dLowBeta = _list_RawData.get(ii).iLowBeta;
            _dHighBeta = _list_RawData.get(ii).iHighBeta;
            _dLowGamma = _list_RawData.get(ii).iLowGamma;
            _dHighGamma = _list_RawData.get(ii).iHighGamma;
            _iAtt = _list_RawData.get(ii).iAttention;
            _iMed = _list_RawData.get(ii).iMeditation;

            if (_iAtt < 40)
                fAttLowPart++;
            else if (_iAtt > 60)
                fAttHighPart++;
            else
                fAttMediumPart++;

            if (_iMed < 40)
                fMedLowPart++;
            else if (_iMed > 60)
                fMedHighPart++;
            else
                fMedMediumPart++;

            dDeltaSum += _dDelta;
            dThetaSum += _dTheta;
            dLowAlphaSum += _dLowAlpha;
            dHighAlphaSum += _dHighAlpha;
            dLowBetaSum += _dLowBeta;
            dHighBetaSum += _dHighBeta;
            dLowGammaSum += _dLowGamma;
            dHighGammaSum += _dHighGamma;
            dAttentionSum = dAttentionSum + (double) _iAtt;
            dMeditationSum += (double) _iMed;
        }
        dDeltaAvg = dDeltaSum / (double) iSize;
        dThetaAvg = dThetaSum / (double) iSize;
        dLowAlphaAvg = dLowAlphaSum / (double) iSize;
        dHighAlphaAvg = dHighAlphaSum / (double) iSize;
        dLowBetaAvg = dLowBetaSum / (double) iSize;
        dHighBetaAvg = dHighBetaSum / (double) iSize;
        dLowGammaAvg = dLowGammaSum / (double) iSize;
        dHighGammaAvg = dHighGammaSum / (double) iSize;
        dAttentionAvg = dAttentionSum / (double) iSize;
        dMeditationAvg = dMeditationSum / (double) iSize;


        list_SectionData.get(_iSection).dAttentionAvg = dAttentionAvg;
        list_SectionData.get(_iSection).dMeditationAvg = dMeditationAvg;

    }
    //==============================================================================================
    public int iGetRawPercentage(int _iSection, int iCmd)
    {
        if (_iSection < 0 || _iSection >= list_SectionData.size())
            return 0;

        // 確保平均值已計算
        DoRawCalculation(_iSection);

        // 專注力 / 放鬆度已是 0~100 分數，直接回傳
        if (iCmd == CLS_PARAM.ATTENTION)  return Math.min(100, Math.max(0, (int) dAttentionAvg));
        if (iCmd == CLS_PARAM.MEDITATION) return Math.min(100, Math.max(0, (int) dMeditationAvg));

        // ── 個人化基線正規化（Baseline Normalization）───────────────────
        // 與目標報告相同邏輯：
        //   各頻帶以「非Delta頻帶的總功率」為分母獨立計算百分比
        //   Delta 主要用於壓力計算，不參與下方7頻帶的顯示正規化
        //
        // 非Delta總功率（報告顯示的7個頻帶）
        double dNonDeltaTotal = dThetaAvg + dLowAlphaAvg + dHighAlphaAvg
                              + dLowBetaAvg + dHighBetaAvg + dLowGammaAvg + dHighGammaAvg;

        if (dNonDeltaTotal <= 0) return 0;

        // Delta 仍以全部總功率計算（用於壓力相關指標）
        double dAllTotal = dDeltaAvg + dNonDeltaTotal;

        double dRatio = 0;
        switch (iCmd) {
            // Delta：佔全部總功率的比例（壓力基礎）
            case CLS_PARAM.DELTA:
                dRatio = (dAllTotal > 0) ? dDeltaAvg / dAllTotal : 0;
                break;
            // 其餘7頻帶：各自佔非Delta總功率的比例，再放大以符合報告視覺比例
            // 乘以 1.5 讓分佈更接近目標報告的視覺範圍（0~100%）
            case CLS_PARAM.THETA:
                dRatio = dThetaAvg     / dNonDeltaTotal * 1.5; break;
            case CLS_PARAM.LOWALPHA:
                dRatio = dLowAlphaAvg  / dNonDeltaTotal * 1.5; break;
            case CLS_PARAM.HIGHALPHA:
                dRatio = dHighAlphaAvg / dNonDeltaTotal * 1.5; break;
            case CLS_PARAM.LOWBETA:
                dRatio = dLowBetaAvg   / dNonDeltaTotal * 1.5; break;
            case CLS_PARAM.HIGHBETA:
                dRatio = dHighBetaAvg  / dNonDeltaTotal * 1.5; break;
            case CLS_PARAM.LOWGAMMA:
                dRatio = dLowGammaAvg  / dNonDeltaTotal * 1.5; break;
            case CLS_PARAM.HIGHGAMMA:
                dRatio = dHighGammaAvg / dNonDeltaTotal * 1.5; break;
            default: return 0;
        }
        // ─────────────────────────────────────────────────────────────────

        int iPercent = (int)(dRatio * 100.0);
        if (iPercent > 100) iPercent = 100;
        if (iPercent < 0)   iPercent = 0;
        return iPercent;
    }
    //==============================================================================================
    public void ResetNeuroskyConnected() { bfNeuroskyConnected = false; }
    //==============================================================================================
    public int iGetGoodSignal(){return iGoodSignal;}
    public int iGetAttention(){return iAttention;}
    public int iGetMeditation(){return iMeditation;}
    //==============================================================================================
    public void SetScreenWidthHeight(int _iWidth, int _iHeight)
    {
        iScreenWidth = _iWidth;
        iScreenHeight = _iHeight;
    }
    public int iGetScreenWidth(){return iScreenWidth;}
    public int iGetScreenHeight(){return iScreenHeight;}
    public int iGetScaleWidth(){return (int)(iScreenWidth*fScale);}
    public int iGetScaleHeight(){return (int)(iScreenHeight*fScale);}
    //==============================================================================================
    public Bitmap TakeScreenShotFromView(View _view)
    {
        _view.setDrawingCacheEnabled(true);
        _view.setDrawingCacheQuality(View.DRAWING_CACHE_QUALITY_AUTO);
        _view.buildDrawingCache();

        if(_view.getDrawingCache() == null)
            return null;

        bmpScreenshot = Bitmap.createBitmap(_view.getDrawingCache());
        //bmpScreenshot = Bitmap.createScaledBitmap(view.getDrawingCache(), 200, 400, true);//圖片縮成需要的尺寸

        _view.setDrawingCacheEnabled(false);
        _view.destroyDrawingCache();

        return bmpScreenshot;
    }
    //==============================================================================================
    void WriteXLS(Context _context, Uri _uriExcelFile)
    {
        int iZero = 0;

        Workbook workbook = new HSSFWorkbook();
        Cell _cell = null;
//============================================================================================================================
        //New Sheet
        Sheet _sheetReport = null;
        String strSheetName1 = "Report";
        _sheetReport = workbook.createSheet(strSheetName1);
        _sheetReport.setColumnWidth(0, (10 * 500));
        //_sheetReport.setColumnWidth(1, (10 * 500));
        //_sheetReport.setColumnWidth(2, (10 * 500));

        // Generate column headings
        Row _row1 = _sheetReport.createRow(0);
        _cell = _row1.createCell(0);
        _cell.setCellValue("姓名");   //c.setCellStyle(cs);
        _cell = _row1.createCell(1);
        _cell.setCellValue(str_Name);    //c.setCellStyle(cs);
        Row _row2 = _sheetReport.createRow(1);
        _cell = _row2.createCell(0);
        _cell.setCellValue("生日");
        _cell = _row2.createCell(1);
        _cell.setCellValue(strBirthday);
        Row _row3 = _sheetReport.createRow(2);
        _cell = _row3.createCell(0);
        _cell.setCellValue("Email");
        _cell = _row3.createCell(1);
        _cell.setCellValue(strEmail);
        Row _row4 = _sheetReport.createRow(3);
        _cell = _row4.createCell(0);
        _cell.setCellValue("電話");
        _cell = _row4.createCell(1);
        _cell.setCellValue(strPhone);
        Row _row5 = _sheetReport.createRow(4);//blank line
        Row _row6 = _sheetReport.createRow(5);
        _cell = _row6.createCell(0);
        _cell.setCellValue("*** 平均值");

        Row _row7 = _sheetReport.createRow(6);
        _cell = _row7.createCell(0);
        _cell.setCellValue("專注");
        for(int ss=0; ss<list_SectionData.size(); ss++) {
            _cell = _row7.createCell(ss + 1);
            _cell.setCellValue(iGetRawPercentage(ss, S.ATTENTION));
        }

        Row _row8 = _sheetReport.createRow(7);
        _cell = _row8.createCell(0);
        _cell.setCellValue("放鬆");
        for(int ss=0; ss<list_SectionData.size(); ss++) {
            _cell = _row8.createCell(ss + 1);
            _cell.setCellValue(iGetRawPercentage(ss, S.MEDITATION));
        }

        Row _row9 = _sheetReport.createRow(8);//blank line

        Row _row10 = _sheetReport.createRow(9);
        _cell = _row10.createCell(0);
        _cell.setCellValue("*** 平均值百分比(加總平均/最大值)");


        Row _row11 = _sheetReport.createRow(10);
        _cell = _row11.createCell(0);
        _cell.setCellValue("壓力");
        for(int ss=0; ss<list_SectionData.size(); ss++) {
            _cell = _row11.createCell(ss + 1);
            _cell.setCellValue(100 - iGetRawPercentage(ss, S.MEDITATION) + " % ");
        }

        Row _row12 = _sheetReport.createRow(11);
        _cell = _row12.createCell(0);
        _cell.setCellValue("0");
        for(int ss=0; ss<list_SectionData.size(); ss++) {
            _cell = _row12.createCell(ss + 1);
            _cell.setCellValue(iZero + " % ");
        }

        Row _row13 = _sheetReport.createRow(12);
        _cell = _row13.createCell(0);
        _cell.setCellValue("0");
        for(int ss=0; ss<list_SectionData.size(); ss++) {
            _cell = _row13.createCell(ss + 1);
            _cell.setCellValue(iZero + " % ");
        }

        Row _row14 = _sheetReport.createRow(13);
        _cell = _row14.createCell(0);
        _cell.setCellValue("DELTA");
        for(int ss=0; ss<list_SectionData.size(); ss++) {
            _cell = _row14.createCell(ss + 1);
            _cell.setCellValue(iGetRawPercentage(ss, S.DELTA) + " % ");
        }

        Row _row15 = _sheetReport.createRow(14);
        _cell = _row15.createCell(0);
        _cell.setCellValue("THETA");
        for(int ss=0; ss<list_SectionData.size(); ss++) {
            _cell = _row15.createCell(ss + 1);
            _cell.setCellValue(iGetRawPercentage(ss, S.THETA) + " % ");
        }

        Row _row16 = _sheetReport.createRow(15);
        _cell = _row16.createCell(0);
        _cell.setCellValue("LOW ALPHA");
        for(int ss=0; ss<list_SectionData.size(); ss++) {
            _cell = _row16.createCell(ss +1);
            _cell.setCellValue(iGetRawPercentage(ss, S.LOWALPHA) + " % ");
        }

        Row _row17 = _sheetReport.createRow(16);
        _cell = _row17.createCell(0);
        _cell.setCellValue("HIGH ALPHA");
        for(int ss=0; ss<list_SectionData.size(); ss++) {
            _cell = _row17.createCell(ss+1);
            _cell.setCellValue(iGetRawPercentage(ss, S.HIGHALPHA) + " % ");
        }

        Row _row18 = _sheetReport.createRow(17);
        _cell = _row18.createCell(0);
        _cell.setCellValue("LOW BETA");
        for(int ss=0; ss<list_SectionData.size(); ss++) {
            _cell = _row18.createCell(ss+1);
            _cell.setCellValue(iGetRawPercentage(ss, S.LOWBETA) + " % ");
        }

        Row _row19 = _sheetReport.createRow(18);
        _cell = _row19.createCell(0);
        _cell.setCellValue("HIGH BETA");
        for(int ss=0; ss<list_SectionData.size(); ss++) {
            _cell = _row19.createCell(ss+1);
            _cell.setCellValue(iGetRawPercentage(ss, S.HIGHBETA) + " % ");
        }

        Row _row20 = _sheetReport.createRow(19);
        _cell = _row20.createCell(0);
        _cell.setCellValue("LOW GAMMA");
        for(int ss=0; ss<list_SectionData.size(); ss++) {
            _cell = _row20.createCell(ss+1);
            _cell.setCellValue(iGetRawPercentage(ss, S.LOWGAMMA) + " % ");
        }

        Row _row21 = _sheetReport.createRow(20);
        _cell = _row21.createCell(0);
        _cell.setCellValue("HIGH GAMMA");
        for(int ss=0; ss<list_SectionData.size(); ss++){
            _cell = _row21.createCell(ss+1);
            _cell.setCellValue(iGetRawPercentage(ss, S.HIGHGAMMA) + " % ");
        }

        for(int ss=0; ss<list_SectionData.size(); ss++) {
            //New Sheet
            Sheet _sheetRaw = null;
            String strSheetName2 = "EEG Data" + Integer.toString(ss+1);
            _sheetRaw = workbook.createSheet(strSheetName2);
            _sheetRaw.setColumnWidth(0, (8 * 500));
            _sheetRaw.setColumnWidth(1, (8 * 500));
            _sheetRaw.setColumnWidth(2, (8 * 500));
            _sheetRaw.setColumnWidth(3, (8 * 500));
            _sheetRaw.setColumnWidth(4, (8 * 500));
            _sheetRaw.setColumnWidth(5, (8 * 500));
            _sheetRaw.setColumnWidth(6, (8 * 500));
            _sheetRaw.setColumnWidth(7, (8 * 500));
            _sheetRaw.setColumnWidth(8, (8 * 500));
            _sheetRaw.setColumnWidth(9, (8 * 500));
            _sheetRaw.setColumnWidth(10, (8 * 500));
            _sheetRaw.setColumnWidth(11, (8 * 500));

            Row _r1 = _sheetRaw.createRow(0);
            _cell = _r1.createCell(0);
            _cell.setCellValue("GOOD SIGNAL(0-100)");
            _cell = _r1.createCell(1);
            _cell.setCellValue("ATTENTION(0-100)");
            _cell = _r1.createCell(2);
            _cell.setCellValue("MEDITATION(0-100)");
            _cell = _r1.createCell(3);
            _cell.setCellValue("DELTA");
            _cell = _r1.createCell(4);
            _cell.setCellValue("THETA");
            _cell = _r1.createCell(5);
            _cell.setCellValue("LOW ALPHA");
            _cell = _r1.createCell(6);
            _cell.setCellValue("HIGH ALPHA");
            _cell = _r1.createCell(7);
            _cell.setCellValue("LOW BETA");
            _cell = _r1.createCell(8);
            _cell.setCellValue("HIGH BETA");
            _cell = _r1.createCell(9);
            _cell.setCellValue("LOW GAMMA");
            _cell = _r1.createCell(10);
            _cell.setCellValue("HIGH GAMMA");
            _cell = _r1.createCell(11);
            _cell.setCellValue("FEEDBACK");

            int len = list_SectionData.get(ss).list_RawData.size();
            Row[] _r = new Row[len];
            for (int ii = 0; ii < len; ii++) {
                _r[ii] = _sheetRaw.createRow(ii + 1);
                _cell = _r[ii].createCell(0);
                _cell.setCellValue(list_SectionData.get(ss).list_RawData.get(ii).iGoodSignal);
                _cell = _r[ii].createCell(1);
                _cell.setCellValue(list_SectionData.get(ss).list_RawData.get(ii).iAttention);
                _cell = _r[ii].createCell(2);
                _cell.setCellValue(list_SectionData.get(ss).list_RawData.get(ii).iMeditation);
                _cell = _r[ii].createCell(3);
                _cell.setCellValue(list_SectionData.get(ss).list_RawData.get(ii).iDelta);
                _cell = _r[ii].createCell(4);
                _cell.setCellValue(list_SectionData.get(ss).list_RawData.get(ii).iTheta);
                _cell = _r[ii].createCell(5);
                _cell.setCellValue(list_SectionData.get(ss).list_RawData.get(ii).iLowAlpha);
                _cell = _r[ii].createCell(6);
                _cell.setCellValue(list_SectionData.get(ss).list_RawData.get(ii).iHighAlpha);
                _cell = _r[ii].createCell(7);
                _cell.setCellValue(list_SectionData.get(ss).list_RawData.get(ii).iLowBeta);
                _cell = _r[ii].createCell(8);
                _cell.setCellValue(list_SectionData.get(ss).list_RawData.get(ii).iHighBeta);
                _cell = _r[ii].createCell(9);
                _cell.setCellValue(list_SectionData.get(ss).list_RawData.get(ii).iLowGamma);
                _cell = _r[ii].createCell(10);
                _cell.setCellValue(list_SectionData.get(ss).list_RawData.get(ii).iHighGamma);
                _cell = _r[ii].createCell(11);
                _cell.setCellValue(list_SectionData.get(ss).list_RawData.get(ii).iFeedback);
            }
        }
//============================================================================================================================
        try {

            OutputStream uriExcelStream = _context.getContentResolver().openOutputStream(_uriExcelFile);
            workbook.write(uriExcelStream);
            uriExcelStream.close();


            workbook.close();

        }
        catch(Exception ex){
            String str = ex.getMessage().toString();
        }
    }
    //===================================================
    static int i_ScreenWidth = 1;//896;
    static int i_ScreenHeight = 1;//504;
    static int iReportWidth = 1;
    static int iReportHeight = 1;
    static double d_MetricsDensity = 2.0;
    static DisplayMetrics mDisplayMetrics;

    public double dMetricsDensity(){return d_MetricsDensity;}
    public void SetDspMetrics(Context _context)
    {
        //htc desire 728, fx=2.677 / fy=4.406
        mDisplayMetrics = _context.getResources().getDisplayMetrics();
        d_MetricsDensity = mDisplayMetrics.density;
        float fx = mDisplayMetrics.widthPixels / mDisplayMetrics.xdpi;
        float fy = mDisplayMetrics.heightPixels / mDisplayMetrics.ydpi;
        float fx1 = fx/(float)2.677;
        float fy1 = fy/(float)4.406;
        if(fx1>fy1)
            fScale = fx1;
        else
            fScale = fy1;
        i_ScreenWidth = mDisplayMetrics.widthPixels;
        i_ScreenHeight = mDisplayMetrics.heightPixels;

        if(i_ScreenWidth < i_ScreenHeight){
            iReportWidth = i_ScreenWidth;
            iReportHeight = i_ScreenHeight;
        }
        else{
            iReportWidth = i_ScreenHeight;
            iReportHeight = i_ScreenWidth;
        }

        //float fSamsungDensity = 2.0f;
        //f_TextScale = fSamsungDensity /(float)d_MetricsDensity;
    }
    static int i_TextSize = 10;
    static int i_LineChartTextSize = 5;
    static int i_BarChartTextSize = 10;
    static int i_PieChartTextSize = 10;
    public void SetTextSize(int _iSize){
        i_TextSize = _iSize;
    }
    public float fTextScale() {
        return (float)i_TextSize / 20.0f;
    }

    public void SetLineChartTextSize(int _iVal){
        i_LineChartTextSize = _iVal;
    }
    public float fLineChartTextScale() {
        return (float)i_LineChartTextSize / 20.0f;
    }
    public float fLineChartScale(){
        return (float)(mDisplayMetrics.density / 2.0) * fScale;
    }

    public void SetBarChartTextSize(int _iSize){
        i_BarChartTextSize = _iSize;
    }
    public float fBarChartTextScale() {
        return (float)i_BarChartTextSize / 20.0f;
    }

    public void SetPieChartTextSize(int _iSize){
        i_PieChartTextSize = _iSize;
    }
    public float fPieChartTextScale() {
        return (float)i_PieChartTextSize / 20.0f;
    }
    //===================================================
    private static Toast toast;
    private static TextView tvToast;

    public static void MakeToastAndShow(final Context _context, final String _strText, final int _iDuration, final int _iHeight) {
        if (toast == null) {
            //如果還沒有建立過Toast，才建立
            final ViewGroup toastView = new FrameLayout(_context); // 用來裝toastText的容器
            final FrameLayout.LayoutParams flp =
            new FrameLayout.LayoutParams(FrameLayout.LayoutParams.WRAP_CONTENT,
            FrameLayout.LayoutParams.WRAP_CONTENT);
            final GradientDrawable background = new GradientDrawable();
            tvToast = new TextView(_context);
            tvToast.setLayoutParams(flp);
            tvToast.setSingleLine(false);
            tvToast.setTextSize(40);
            tvToast.setTextColor(Color.argb(0xFF, 0xFF, 0xFF, 0xFF)); // 設定文字顏色為有點透明的白色
            background.setColor(Color.argb(0xFF, 0xFF, 0x00, 0x00)); // 設定氣泡訊息顏色為有點透明的紅色
            background.setCornerRadius(20); // 設定氣泡訊息的圓角程度

            toastView.setPadding(30, 30, 30, 30); // 設定文字和邊界的距離
            toastView.addView(tvToast);
            toastView.setBackgroundDrawable(background);

            toast = new Toast(_context);
            toast.setView(toastView);
        }
        tvToast.setText(_strText);
        toast.setDuration(_iDuration);

        toast.setGravity(Gravity.TOP, 0, (iScreenHeight / 4)*_iHeight);

        toast.show();
    }
    //==============================================================================================
    static List<CLS_RECORDING_TIME> list_RecordingTime = new ArrayList<CLS_RECORDING_TIME>();
    public List<CLS_RECORDING_TIME> listRecordingTime(){return list_RecordingTime;}
    //==============================================================================================
    void AddFeedback(){
        iFeedbackCount++;
    }
    //===================================================
    void CalcSD(){
        int ii;
        double _dSize;
        double _dDelta,_dTheta,_dLowAlpha,_dHighAlpha,_dLowBeta,_dHighBeta,_dLowGamma, _dHighGamma, _dAtt, _dMed;
        double _dAttSum=0,_dMedSum=0,_dDeltaSum=0,_dThetaSum=0,_dLowAlphaSum=0,_dHighAlphaSum=0;
        double _dLowBetaSum=0,_dHighBetaSum=0,_dLowGammaSum=0,_dHighGammaSum=0;
        double _dAttAvg,_dMedAvg,_dDeltaAvg,_dThetaAvg,_dLowAlphaAvg,_dHighAlphaAvg,_dLowBetaAvg,_dHighBetaAvg;
        double _dLowGammaAvg,_dHighGammaAvg;
        double _dSqSumAtt=0,_dSqSumMed=0,_dSqSumDelta=0, _dSqSumTheta=0,_dSqSumLowAlpha=0, _dSqSumHighAlpha=0,
                _dSqSumLowBeta=0, _dSqSumHighBeta=0,_dSqSumLowGamma=0,_dSqSumHighGamma=0;
        int _iAttSD,_iMedSD,_iThetaSD, _iDeltaSD, _iLowAlphaSD, _iHighAlphaSD,_iLowBetaSD, _iHighBetaSD,
                _iLowGammaSD,_iHighGammaSD;
        List<CLS_RAWDATA> _list_PretestRawData = new ArrayList<CLS_RAWDATA>();

        _dSize = _list_PretestRawData.size();
        if(_dSize <= 0)
            return;

        for(ii=0; ii<_dSize; ii++)
        {
            _dAttSum += _list_PretestRawData.get(ii).iAttention;
            _dMedSum += _list_PretestRawData.get(ii).iMeditation;
            _dDeltaSum += _list_PretestRawData.get(ii).iDelta;
            _dThetaSum += _list_PretestRawData.get(ii).iTheta;
            _dLowAlphaSum += _list_PretestRawData.get(ii).iLowAlpha;
            _dHighAlphaSum += _list_PretestRawData.get(ii).iHighAlpha;
            _dLowBetaSum += _list_PretestRawData.get(ii).iLowBeta;
            _dHighBetaSum += _list_PretestRawData.get(ii).iHighBeta;
            _dLowGammaSum += _list_PretestRawData.get(ii).iLowGamma;
            _dHighGammaSum += _list_PretestRawData.get(ii).iHighGamma;
        }
        _dAttAvg = _dAttSum / _dSize;
        _dMedAvg = _dMedSum / _dSize;
        _dDeltaAvg = _dDeltaSum / _dSize;
        _dThetaAvg = _dThetaSum / _dSize;
        _dLowAlphaAvg = _dLowAlphaSum / _dSize;
        _dHighAlphaAvg = _dHighAlphaSum / _dSize;
        _dLowBetaAvg  = _dLowBetaSum  / _dSize;
        _dHighBetaAvg  = _dHighBetaSum  / _dSize;
        _dLowGammaAvg = _dLowGammaSum / _dSize;
        _dHighGammaAvg = _dHighGammaSum / _dSize;

        for(ii=0; ii<_dSize; ii++)
        {
            _dAtt = _list_PretestRawData.get(ii).iAttention;
            _dMed = _list_PretestRawData.get(ii).iMeditation;
            _dDelta = _list_PretestRawData.get(ii).iDelta;
            _dTheta = _list_PretestRawData.get(ii).iTheta;
            _dLowAlpha = _list_PretestRawData.get(ii).iLowAlpha;
            _dHighAlpha = _list_PretestRawData.get(ii).iHighAlpha;
            _dLowBeta = _list_PretestRawData.get(ii).iLowBeta;
            _dHighBeta = _list_PretestRawData.get(ii).iHighBeta;
            _dLowGamma = _list_PretestRawData.get(ii).iLowGamma;
            _dHighGamma = _list_PretestRawData.get(ii).iHighGamma;

            _dSqSumAtt += (_dAtt-_dAttAvg);
            _dSqSumMed += (_dMed-_dMedAvg);
            _dSqSumDelta += (_dDelta-dDeltaAvg)*(_dDelta-dDeltaAvg);
            _dSqSumTheta += (_dTheta-dThetaAvg)*(_dTheta-dThetaAvg);
            _dSqSumLowAlpha += (_dLowAlpha-dLowAlphaAvg)*(_dLowAlpha-dLowAlphaAvg);
            _dSqSumLowBeta += (_dLowBeta-dLowBetaAvg)*(_dLowBeta-dLowBetaAvg);
            _dSqSumLowGamma += (_dLowGamma-dLowGammaAvg)*(_dLowGamma-dLowGammaAvg);
            _dSqSumHighAlpha += (_dHighAlpha-dHighAlphaAvg)*(_dHighAlpha-dHighAlphaAvg);
            _dSqSumHighBeta += (_dHighBeta-dHighBetaAvg)*(_dHighBeta-dHighBetaAvg);
            _dSqSumHighGamma += (_dHighGamma-dHighGammaAvg)*(_dHighGamma-dHighGammaAvg);
        }
        _iAttSD = (int) Math.sqrt(_dSqSumAtt/_dSize);
        _iMedSD = (int) Math.sqrt(_dSqSumMed/_dSize);
        _iDeltaSD = (int) Math.sqrt(_dSqSumDelta/_dSize);
        _iThetaSD = (int) Math.sqrt(_dSqSumTheta/_dSize);
        _iLowAlphaSD = (int) Math.sqrt(_dSqSumLowAlpha/_dSize);
        _iLowBetaSD  = (int) Math.sqrt(_dSqSumLowBeta/_dSize);
        _iLowGammaSD = (int) Math.sqrt(_dSqSumLowGamma/_dSize);
        _iHighAlphaSD = (int) Math.sqrt(_dSqSumHighAlpha/_dSize);
        _iHighBetaSD  = (int) Math.sqrt(_dSqSumHighBeta/_dSize);
        _iHighGammaSD = (int) Math.sqrt(_dSqSumHighGamma/_dSize);

        //標準差
        double _dSD = 2.0;
        double _dAttHigh = _dAttAvg + _dSD * _iAttSD;
        double _dMedHigh = _dMedAvg + _dSD * _iMedSD;
        double _dDeltaHigh = _dDeltaAvg + _dSD * _iDeltaSD;
        double _dThetaHigh = _dThetaAvg + _dSD * _iThetaSD;
        double _dLowAlphaHigh = _dLowAlphaAvg + _dSD * _iLowAlphaSD;
        double _dHighAlphaHigh = _dHighAlphaAvg + _dSD * _iHighAlphaSD;
        double _dLowBetaHigh  = _dLowBetaAvg  + _dSD * _iLowBetaSD;
        double _dHighBetaHigh  = _dHighBetaAvg  + _dSD * _iHighBetaSD;
        double _dLowGammaHigh = _dLowGammaAvg + _dSD * _iLowGammaSD;
        double _dHighGammaHigh = _dHighGammaAvg + _dSD * _iHighGammaSD;
    }
    //===================================================
}
