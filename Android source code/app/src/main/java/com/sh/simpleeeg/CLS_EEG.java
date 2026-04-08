package com.sh.simpleeeg;

import android.app.Activity;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;

import java.util.Set;

public class CLS_EEG {
    CLS_PARAM S = new CLS_PARAM();
    CLS_RAW clsRaw = new CLS_RAW();
    CLS_BT clsBt = new CLS_BT();
    CLS_BLE clsBle = new CLS_BLE();

    static BluetoothAdapter mBluetoothAdapter;
    static String strMacAddress = "";
    static String strDeviceName = "";
    static boolean bIsBleDevice = false;

    static boolean bBT = false;
    static boolean bBLE = false;

    static boolean bDoConnect = true;
    //===================================================
    public CLS_EEG(){ }
    //===================================================
    public boolean bConnect(Activity _activity){
        if(!bDoConnect)
            return true;

        // 检查蓝牙开关
        BluetoothAdapter adapter = BluetoothAdapter.getDefaultAdapter();
        if (adapter == null) {
            //"本机没有找到蓝牙硬件或驱动！", 0);
            return false;
        }
        else if (!adapter.isEnabled()) {
            //20220519 不要開啟,用return false,因為盡量少開藍芽權限
            //adapter.enable();//直接开启蓝牙
            return false;
        }

        Set<BluetoothDevice> PairedDevices = adapter.getBondedDevices();
        for (BluetoothDevice bt : PairedDevices) {
            strDeviceName = bt.getName();
            if(strDeviceName.contains("BrainLink") || strDeviceName.contains("MindWave")){
                bBT = true;
            }
            else if(strDeviceName.contains("Mindsensor") ){
                bBLE = true;
            }
        }

        if(bBT & !bBLE) {
            clsBt.Connect(_activity);
            bDoConnect = false;
            return true;
        }
        else if(!bBT & bBLE) {
            clsBle.Connect(_activity);
            bDoConnect = false;
            return true;
        }
        return false;
    }
    //===================================================
    public void Disconnect(){
        if(bBT & !bBLE)
            clsBt.Disconnect();
        else if(!bBT & bBLE)
            clsBle.Disconnect();
    }
    //===================================================
    public int iGoodSignal(){ return clsRaw.iGoodSignal(); }
    public int iAttention(){ return clsRaw.iAttention(); }
    public int iMeditation(){ return clsRaw.iMeditation(); }
    public int iDelta(){ return clsRaw.iDelta(); }
    public int iTheta(){ return clsRaw.iTheta(); }
    public int iLowAlpha(){ return clsRaw.iLowAlpha(); }
    public int iHighAlpha(){ return clsRaw.iHighAlpha(); }
    public int iLowBeta(){ return clsRaw.iLowBeta(); }
    public int iHighBeta(){ return clsRaw.iHighBeta(); }
    public int iLowGamma(){ return clsRaw.iLowGamma(); }
    public int iHighGamma(){ return clsRaw.iHighGamma(); }
    public int iBattery(){ return clsRaw.iBattery(); }

    public int iDeltaPercent(){ return clsRaw.iDeltaPercent(); }
    public int iThetaPercent(){ return clsRaw.iThetaPercent(); }
    public int iLowAlphaPercent(){ return clsRaw.iLowAlphaPercent(); }
    public int iHighAlphaPercent(){ return clsRaw.iHighAlphaPercent(); }
    public int iLowBetaPercent(){ return clsRaw.iLowBetaPercent(); }
    public int iHighBetaPercent(){ return clsRaw.iHighBetaPercent(); }
    public int iLowGammaPercent(){ return clsRaw.iLowGammaPercent(); }
    public int iHighGammaPercent(){ return clsRaw.iHighGammaPercent(); }
    //===================================================
    public boolean bConnected(){return clsRaw.bConnected();}
    //===================================================
}
