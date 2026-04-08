package com.sh.simpleeeg;

import android.app.Activity;
import android.os.Handler;

/**
 * Created by user on 2017/12/28.
 */

public class CLS_BrainWave
{
    CLS_PARAM S = new CLS_PARAM();
    CLS_DATA clsData = new CLS_DATA();
    CLS_EEG clsEeg = new CLS_EEG();

    static Brainwave_Callback m_Callback;

    static private ThreadProcess mThreadProcess;
    static private Handler mProcessHandler = new Handler();

    static boolean bQuit = false;
    static boolean bDoConnect = true;
    static boolean bStart1stTime = true;

    //===================================================
    //===================================================
    //===================================================
    public CLS_BrainWave()
    {
        if(!bDoConnect)
            return;

        bQuit = false;

        if(bStart1stTime){
            bStart1stTime = false;
            mThreadProcess = new ThreadProcess();
            mProcessHandler.postDelayed(mThreadProcess, 0);
        }
    }
    //===================================================
    public void Destroy()
    {
        bQuit = true;
    }
    //===================================================
    public interface Brainwave_Callback
    {
        void Do(int iCmd, int iVal);
    }
    public void SetCallback(Brainwave_Callback _callback)
    {
        this.m_Callback = _callback;
    }
    //===================================================
    public void Connect(Activity _activity){
        if(!clsEeg.bConnect(_activity))
            m_Callback.Do(S.BluetoothClosed, 0);
    }
    //===================================================
    private class ThreadProcess extends Thread
    {
        @Override
        public void run()
        {
            if(bQuit)
                return;
            mProcessHandler.postDelayed(mThreadProcess, 1000);

            if(clsEeg.bConnected()){
                bDoConnect = false;
                if (clsEeg.iGoodSignal() > 90) {
                    if (m_Callback != null)
                        m_Callback.Do(S.SIGNAL_GOOD, 0);
                }
                else {
                    if (m_Callback != null)
                        m_Callback.Do(S.BrainwaveConnected, 0);
                }
                clsData.SetBrainData(clsEeg.iGoodSignal(), clsEeg.iAttention(), clsEeg.iMeditation(),
                        clsEeg.iDelta(), clsEeg.iTheta(),clsEeg.iLowAlpha(), clsEeg.iHighAlpha(),
                        clsEeg.iLowBeta(), clsEeg.iHighBeta(), clsEeg.iLowGamma(), clsEeg.iHighGamma());
                m_Callback.Do(S.BrainwaveValue, 0);
            }
            else{
                m_Callback.Do(S.BrainwaveDisconnected, 0);
            }
        }
    }
    //===================================================
}
