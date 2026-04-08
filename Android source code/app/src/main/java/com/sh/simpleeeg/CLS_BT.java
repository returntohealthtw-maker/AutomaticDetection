package com.sh.simpleeeg;

import static androidx.core.app.ActivityCompat.requestPermissions;

import android.Manifest;
import android.app.Activity;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Handler;

import com.neurosky.connection.ConnectionStates;
import com.neurosky.connection.DataType.MindDataType;
import com.neurosky.connection.EEGPower;
import com.neurosky.connection.TgStreamHandler;
import com.neurosky.connection.TgStreamReader;

import java.util.Set;

public class CLS_BT {
    CLS_RAW clsRaw;

    static TgStreamReader mTgStreamReader;
    static BluetoothAdapter mAdapter;
    static String strDeviceName = "";

    static boolean b_Connected = false;

    static int  iGoodSignal = 0;
    static int  iAtt = 0;
    static int  iMed = 0;
    static int  iDelta = 0;
    static int  iTheta = 0;
    static int  iLowAlpha = 0;
    static int  iHighAlpha = 0;
    static int  iLowBeta = 0;
    static int  iHighBeta = 0;
    static int  iLowGamma = 0;
    static int  iHighGamma = 0;

    static ThreadProcess mThreadProcess;
    static Handler mProcessHandler;

    static boolean bReconnect = true;

    //===================================================
    public CLS_BT(){
        clsRaw = new CLS_RAW();
    }
    //===================================================
    public void Connect(Activity _activity){
        // Android 6.0动态请求权限
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            String[] permissions = {
                    Manifest.permission.WRITE_EXTERNAL_STORAGE,
                    Manifest.permission.READ_EXTERNAL_STORAGE};
            for (String str : permissions) {
                if (_activity.checkSelfPermission(str) != PackageManager.PERMISSION_GRANTED) {
                    requestPermissions(_activity, permissions, 111);
                    break;
                }
            }
        }

        String strBrainwaveAddress = "";
        boolean bDeviceReady = false;
        mAdapter = BluetoothAdapter.getDefaultAdapter();
        Set<BluetoothDevice> PairedDevices = mAdapter.getBondedDevices();
        boolean bPass = true;
        for (BluetoothDevice bt : PairedDevices) {
            strDeviceName = bt.getName();
            strBrainwaveAddress = bt.getAddress();
            if(strDeviceName.contains("BrainLink") || strDeviceName.contains("MindWave")){
                if(bPass) {
                    bDeviceReady = true;
                    break;
                }
                else {
                    if(strBrainwaveAddress.contains("F4:EC:EA:A8:41:AA")//test

                    ) {
                        bDeviceReady = true;
                        break;
                    }
                }
            }
        }
        if (!bDeviceReady)
            return;

        BluetoothDevice bd = mAdapter.getRemoteDevice(strBrainwaveAddress);
        if(mTgStreamReader == null)
            mTgStreamReader = new TgStreamReader(bd, TgStreamHandlerCallback);

        mThreadProcess = new ThreadProcess();
        mProcessHandler = new Handler();
        mProcessHandler.postDelayed(mThreadProcess, 100);
    }
    //===================================================
    public void Disconnect(){
        if(mTgStreamReader != null) {
            mTgStreamReader.stop();
            mTgStreamReader.close();
            mTgStreamReader = null;
        }
    }
    //===================================================
    private class ThreadProcess extends Thread {
        @Override
        public void run() {
            mProcessHandler.postDelayed(mThreadProcess, 100);
            if(bReconnect){
                if (mTgStreamReader != null)
                    mTgStreamReader.connectAndStart();
            }
        }
    }
    //===================================================
    private TgStreamHandler TgStreamHandlerCallback = new TgStreamHandler() {
        @Override
        public void onStatesChanged(int iConnectionStates) {
            switch (iConnectionStates) {
                case ConnectionStates.STATE_CONNECTED:
                    b_Connected = true;
                    clsRaw.SetConnection(true);
                    bReconnect = false;
                    break;
                case ConnectionStates.STATE_WORKING:
                    break;
                case ConnectionStates.STATE_GET_DATA_TIME_OUT:
                    b_Connected = false;
                    clsRaw.SetConnection(false);
                    bReconnect = true;
                    break;
                case ConnectionStates.STATE_COMPLETE:
                    break;
                case ConnectionStates.STATE_STOPPED:
                    bReconnect = true;
                    break;
                case ConnectionStates.STATE_DISCONNECTED:
                    b_Connected = false;
                    clsRaw.SetConnection(false);
                    bReconnect = true;
                    break;
                case ConnectionStates.STATE_ERROR:
                    break;
                case ConnectionStates.STATE_FAILED:
                    break;
            }
        }
        @Override
        public void onRecordFail(int a) { }
        @Override
        public void onChecksumFail(byte[] payload, int length, int checksum) { }
        @Override
        public void onDataReceived(int iDataType, int iData, Object obj) {
            switch (iDataType) {
                case MindDataType.CODE_FILTER_TYPE:
                    break;
                case MindDataType.CODE_RAW:
                    break;
                case MindDataType.CODE_POOR_SIGNAL:
                    iGoodSignal = (200 - iData) / 2;
                    break;
                case MindDataType.CODE_ATTENTION:
                    iAtt = iData;
                    break;
                case MindDataType.CODE_MEDITATION:
                    iMed = iData;
                    clsRaw.Set(iGoodSignal,iAtt,iMed,iDelta,iTheta,iLowAlpha,iHighAlpha,iLowBeta,iHighBeta,
                            iLowGamma,iHighGamma,88);
                    break;
                case MindDataType.CODE_EEGPOWER:
                    EEGPower power = (EEGPower)obj;
                    if (power.isValidate()) {
                        iDelta = power.delta;
                        iTheta = power.theta;
                        iLowAlpha = power.lowAlpha;
                        iHighAlpha = power.highAlpha;
                        iLowBeta = power.lowBeta;
                        iHighBeta = power.highBeta;
                        iLowGamma = power.lowGamma;
                        iHighGamma = power.middleGamma;
                    }
                    break;
            }
        }
    };
    //===================================================
}
