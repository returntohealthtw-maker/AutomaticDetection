package com.sh.simpleeeg;

import android.content.Context;
import android.graphics.Color;
import android.graphics.Paint;
import android.view.View;

import org.achartengine.ChartFactory;
import org.achartengine.model.XYMultipleSeriesDataset;
import org.achartengine.model.XYSeries;
import org.achartengine.renderer.XYMultipleSeriesRenderer;
import org.achartengine.renderer.XYSeriesRenderer;

/**
 * Created by user on 2017/12/25.
 */

public class CLS_LineChart
{
    CLS_DATA clsData = new CLS_DATA();

    View m_View;
    XYMultipleSeriesRenderer m_XYMultipleSeriesRenderer;
    XYSeriesRenderer m_XYSeriesRenderer1;
    XYSeriesRenderer m_XYSeriesRenderer2;

    XYMultipleSeriesDataset m_XYMultipleSeriesDataset;
    XYSeries m_XYSeries1;
    XYSeries m_XYSeries2;


    //boolean bEnable1stLine = true;
    //boolean bEnable2ndLine = false;

    int iLineNumber = 1;


    //============================================================
    public CLS_LineChart(int iVal)
    {
        iLineNumber = iVal;
    }
    //============================================================
    View viewDrawAppearance(Context _context, boolean bShowGrid, int _iXMax, int _iYMax,
                            int _iLine1Color, int _iLine2Color, float _fScale)
    {
        //建立外觀
        m_XYMultipleSeriesRenderer = new XYMultipleSeriesRenderer();


        //第一條線
        m_XYSeriesRenderer1 = new XYSeriesRenderer();
        m_XYSeriesRenderer1.setColor(_iLine1Color);//Color.GREEN);
        //m_XYSeriesRenderer1.setPointStyle(PointStyle.CIRCLE); //沒有指定就是沒有
        m_XYSeriesRenderer1.setFillPoints(true);
        m_XYSeriesRenderer1.setLineWidth(5);
        m_XYMultipleSeriesRenderer.addSeriesRenderer(m_XYSeriesRenderer1);

        //第二條線
        if(iLineNumber > 1)
        {
            m_XYSeriesRenderer2 = new XYSeriesRenderer();
            m_XYSeriesRenderer2.setColor(_iLine2Color);//Color.GREEN);
            //m_XYSeriesRenderer2.setPointStyle(PointStyle.CIRCLE);
            m_XYSeriesRenderer2.setFillPoints(true);
            m_XYSeriesRenderer2.setLineWidth(5);
            //m_XYSeriesRenderer2.setChartValuesTextSize(30);// 數值的文字大小
            m_XYMultipleSeriesRenderer.addSeriesRenderer(m_XYSeriesRenderer2);
        }

        //X,Y軸設定
        //m_XYMultipleSeriesRenderer.setChartTitle("專注+放鬆  专注+放松");
        //m_XYMultipleSeriesRenderer.setXTitle("X");
        //m_XYMultipleSeriesRenderer.setYTitle("Y");
        m_XYMultipleSeriesRenderer.setXAxisMin(0);
        m_XYMultipleSeriesRenderer.setXAxisMax(_iXMax);
        m_XYMultipleSeriesRenderer.setYAxisMin(0);
        m_XYMultipleSeriesRenderer.setYAxisMax(_iYMax);
        m_XYMultipleSeriesRenderer.setAxesColor(Color.WHITE);
        m_XYMultipleSeriesRenderer.setLabelsColor(Color.WHITE);
        if(bShowGrid)
            m_XYMultipleSeriesRenderer.setShowGrid(true);
        else
            m_XYMultipleSeriesRenderer.setShowGrid(false);
        m_XYMultipleSeriesRenderer.setYLabels(10);//*(int)(clsData.fGetScale()));
        m_XYMultipleSeriesRenderer.setMargins(new int[] {
                (int)(60f*clsData.fLineChartTextScale()), (int)(150*clsData.fLineChartTextScale()),
                (int)(100f*clsData.fLineChartTextScale()), (int)(100*clsData.fLineChartTextScale()) });//上,左,下,右
        m_XYMultipleSeriesRenderer.setXLabelsAlign(Paint.Align.CENTER);  //設定X軸文字置中
        m_XYMultipleSeriesRenderer.setYLabelsAlign(Paint.Align.RIGHT);
        m_XYMultipleSeriesRenderer.setBackgroundColor(Color.BLACK); // ?置背景色透明
        m_XYMultipleSeriesRenderer.setApplyBackgroundColor(true); // 使背景色生效
        m_XYMultipleSeriesRenderer.setGridColor(Color.WHITE);
        if(bShowGrid)
            m_XYMultipleSeriesRenderer.setLabelsTextSize(60f*clsData.fLineChartTextScale());// 設定XY軸顯示數字的文字大小
        else
            m_XYMultipleSeriesRenderer.setLabelsTextSize(0f);// 設定XY軸顯示數字的文字大小

        m_XYMultipleSeriesRenderer.setLegendTextSize(80f*clsData.fLineChartTextScale());//左下方線條文字名稱大小



        //m_XYMultipleSeriesRenderer.setAxisTitleTextSize(60f);
        //m_XYMultipleSeriesRenderer.setChartTitleTextSize(60f);
        //建立資料串
        m_XYMultipleSeriesDataset = new XYMultipleSeriesDataset();

        //第一條線
        m_XYSeries1 = new XYSeries("專注");
        m_XYMultipleSeriesDataset.addSeries(m_XYSeries1);

        //第二條線
        if(iLineNumber > 1)
        {
            m_XYSeries2 = new XYSeries("放鬆");
            m_XYMultipleSeriesDataset.addSeries(m_XYSeries2);
        }

        m_View = ChartFactory.getLineChartView(_context, m_XYMultipleSeriesDataset, m_XYMultipleSeriesRenderer);

        return m_View;
    }

    //============================================================
    void AddPoint(int _iLineNumber, double _dX, double _dY)
    {
        switch(_iLineNumber)
        {
            case 1:
                m_XYSeries1.add(_dX, _dY);
                if(_dX >= 30)
                {
                    m_XYMultipleSeriesRenderer.setXAxisMin(_dX-30);
                    m_XYMultipleSeriesRenderer.setXAxisMax(_dX);
                }
                break;
            case 2:
                m_XYSeries2.add(_dX, _dY);
                if(_dX >= 30)
                {
                    m_XYMultipleSeriesRenderer.setXAxisMin(_dX-30);
                    m_XYMultipleSeriesRenderer.setXAxisMax(_dX);
                }
                break;
        }
    }
    //============================================================
    void Clear()
    {
        m_XYSeries1.clear();
        m_XYSeries2.clear();
        /*
        //m_XYMultipleSeriesDataset.removeSeries(m_XYSeries1);
        m_XYSeries1.clear();
        //m_XYSeries2.clear();
        m_XYMultipleSeriesDataset.clear();
        m_XYSeries1 = null;
        //m_XYSeries2 = null;
        m_XYMultipleSeriesDataset = null;
        m_XYSeriesRenderer1 = null;
        //m_XYSeriesRenderer2 = null;
        m_XYMultipleSeriesRenderer = null;
        */
    }
    //============================================================
}
