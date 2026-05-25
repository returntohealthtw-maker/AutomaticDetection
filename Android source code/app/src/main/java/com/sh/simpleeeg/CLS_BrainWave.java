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
        if(!clsEeg.bConnect(_activity)) {
            if (m_Callback != null)
                m_Callback.Do(S.BluetoothClosed, 0);
        }
    }
    //===================================================
    /** 安全查詢：腦波儀是否已連線（不會丟出例外） */
    public boolean bConnectedSafe(){
        try { return clsEeg.bConnected(); }
        catch (Throwable t) { return false; }
    }
    //===================================================
    /**
     * 取得腦波儀電量（0-100）；未連線或無法取得時回傳 -1。
     *
     * 小米/紅米/OPPO/部分平板修正：
     *  - 不再強制 bConnected()==true 才回傳
     *    （某些 ROM 在 BLE 已連線但 ThinkGear 資料流尚未啟動的窗口會回報 false，
     *    導致使用者一直看到「🧠--」即使腦波儀已正常連上）
     *  - 用 static 快取最後一次有效讀數，BLE 暫時斷線時仍能顯示
     *  - 只要曾經讀過一次合理電量（1~100），之後就持續顯示，不會跳回「--」
     */
    private static int sLastValidBattery = -1;     // 上次成功讀到的電量（never read = -1）
    private static long sLastValidBatteryTs = 0L;  // 讀到的時間

    public int getBatteryLevel(){
        try {
            // 1) 嘗試取得即時值（無論 bConnected 狀態）
            int now = -1;
            try { now = clsEeg.iBattery(); } catch (Throwable ignore) {}

            // 2) 合理範圍才採用作為快取
            if (now >= 1 && now <= 100) {
                sLastValidBattery   = now;
                sLastValidBatteryTs = System.currentTimeMillis();
                return now;
            }

            // 3) 即時值無效時，若快取仍在合理時間內（30 分鐘）就回傳快取
            if (sLastValidBattery > 0 &&
                (System.currentTimeMillis() - sLastValidBatteryTs) < 30L * 60 * 1000) {
                return sLastValidBattery;
            }

            // 4) 從未讀到 → -1（UI 顯示「🧠--」）
            return -1;
        } catch (Throwable t) { return -1; }
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
                if (m_Callback != null)
                    m_Callback.Do(S.BrainwaveValue, 0);
            }
            else{
                if (m_Callback != null)
                    m_Callback.Do(S.BrainwaveDisconnected, 0);
            }
        }
    }
    //===================================================
}
