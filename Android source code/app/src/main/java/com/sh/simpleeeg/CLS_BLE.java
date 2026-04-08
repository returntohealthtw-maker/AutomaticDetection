package com.sh.simpleeeg;

import static androidx.core.app.ActivityCompat.requestPermissions;

import android.Manifest;
import android.app.Activity;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothGatt;
import android.bluetooth.BluetoothGattCallback;
import android.bluetooth.BluetoothGattCharacteristic;
import android.bluetooth.BluetoothGattDescriptor;
import android.bluetooth.BluetoothGattService;
import android.bluetooth.BluetoothProfile;
import android.bluetooth.le.BluetoothLeScanner;
import android.bluetooth.le.ScanCallback;
import android.bluetooth.le.ScanResult;
import android.content.Context;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Handler;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Set;
import java.util.UUID;

public class CLS_BLE {
    CLS_RAW clsRaw;

    static BluetoothAdapter mAdapter;
    static BluetoothLeScanner mBluetoothLeScanner;
    static BluetoothGatt mBluetoothGatt;
    static String strDeviceName = "";
    static String strMacAddress = "";
    static Context context;

    static List<ScanResult> listScanResult = new ArrayList<>();
    static Handler mHandler = new Handler();

    static ThreadProcess mThreadProcess;
    static Handler mProcessHandler;

    static boolean b_Connected = false;

    static boolean bDiscoverServiceOk = false;
    static boolean bBrainDataStartOk = false;

    static boolean bQuit = false;
    static int iBattery = 100;
    static int iGoodSignal = 0,iAtt = 0,iMed = 0,iDelta = 0,iTheta = 0,iLowAlpha = 0,iHighAlpha = 0;
    static int iLowBeta = 0,iHighBeta = 0,iLowGamma = 0,iHighGamma = 0;
    static int iLeft = 0,iRight=0,iDown=0,iUp=0;

    static int iGetBatteryCount = 10;

    byte[] byArr;

    BluetoothDevice btDevice = null;

    //===================================================
    public CLS_BLE(){
        clsRaw = new CLS_RAW();
    }
    //===================================================
    public void Connect(Activity _activity){
        context = _activity;

        // 检查是否支持BLE蓝牙
        if (!_activity.getPackageManager().hasSystemFeature(PackageManager.FEATURE_BLUETOOTH_LE)) {
            //APP.toast("本机不支持低功耗蓝牙！", 0);
            return;
        }
        // Android 6.0动态请求权限
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            String[] permissions = {
                    Manifest.permission.WRITE_EXTERNAL_STORAGE,
                    Manifest.permission.READ_EXTERNAL_STORAGE,
                    Manifest.permission.ACCESS_COARSE_LOCATION};
            for (String str : permissions) {
                if (_activity.checkSelfPermission(str) != PackageManager.PERMISSION_GRANTED) {
                    requestPermissions(_activity, permissions, 111);
                    break;
                }
            }
        }

        mAdapter = BluetoothAdapter.getDefaultAdapter();
        strMacAddress = "";
        Set<BluetoothDevice> PairedDevices = mAdapter.getBondedDevices();
        //BluetoothDevice btDevice = null;

        boolean bPass = true;
        for (BluetoothDevice bt : PairedDevices) {
            strDeviceName = bt.getName();
            strMacAddress = bt.getAddress();
            if(strDeviceName.contains("Mindsensor")){
                if(bPass) {
                    btDevice = bt;
                    break;
                }
                else{
                    if (strMacAddress.contains("F4:EC:EA:A8:41:AA")//test

                    ) {
                        btDevice = bt;
                        break;
                    }
                }
            }
        }
        if (btDevice == null)
            return;

        mThreadProcess = new ThreadProcess();
        mProcessHandler = new Handler();
        mProcessHandler.postDelayed(mThreadProcess, 0);
    }
    //===================================================
    public void Disconnect(){
        bQuit = true;
    }
    //===================================================
    // 扫描BLE蓝牙(不会扫描经典蓝牙)
    void ScanBLE() {
        mAdapter = BluetoothAdapter.getDefaultAdapter();
        mBluetoothLeScanner = mAdapter.getBluetoothLeScanner();
        // Android5.0新增的扫描API，扫描返回的结果更友好，比如BLE广播数据以前是byte[] scanRecord，而新API帮我们解析成ScanRecord类
        mBluetoothLeScanner.startScan(mScanCallback);
    }
    //===================================================
    // BLE中心设备连接外围设备的数量有限(大概2~7个)，在建立新连接之前必须释放旧连接资源，否则容易出现连接错误133
    void CloseGattConnection() {
        if (mBluetoothGatt != null) {
            mBluetoothGatt.disconnect();
            mBluetoothGatt.close();
        }
    }
    //===================================================
    static int iThreadStep = 0;
    private class ThreadProcess extends Thread {
        @Override
        public void run() {
            if (bQuit)
                return;

            mProcessHandler.postDelayed(mThreadProcess, 100);

            switch(iThreadStep){
                case 0:
                    mBluetoothGatt = btDevice.connectGatt(context, true, mBluetoothGattCallback);
                    iThreadStep = 100;
                    break;
                case 10:
                    if(b_Connected)
                        iThreadStep = 100;
                    break;
                case 100:
                    if(b_Connected & bDiscoverServiceOk){
                        iThreadStep = 200;
                        break;
                    }
                    break;
                case 200:
                    EnableBrainwaveData();
                    iThreadStep = 300;
                    break;
                case 300:
                    if(!b_Connected)
                        iThreadStep = 400;
                    break;
                case 400:
                    if(b_Connected)
                        iThreadStep = 200;
                    break;
            }
        }
    }
    //===================================================
    // 扫描Callback
    ScanCallback mScanCallback = new ScanCallback() {
        @Override
        public void onScanResult(int callbackType, ScanResult result) {
            listScanResult.add(result);
        }
    };
    //===================================================
    private static final UUID Battery_Service_UUID = UUID.fromString("0000180F-0000-1000-8000-00805f9b34fb");
    private static final UUID Battery_Level_UUID = UUID.fromString("00002a19-0000-1000-8000-00805f9b34fb");

    void GetBatteryLevel() {
        BluetoothGattService batteryService = mBluetoothGatt.getService(Battery_Service_UUID);
        if(batteryService == null) {
            //Log.d(TAG, "Battery service not found!");
            return;
        }
        BluetoothGattCharacteristic characteristicBatteryLevel = batteryService.getCharacteristic(Battery_Level_UUID);
        if(characteristicBatteryLevel == null) {
            //Log.d(TAG, "Battery level not found!");
            return;
        }
        mBluetoothGatt.readCharacteristic(characteristicBatteryLevel);
    }
    //===================================================
    // 与服务端连接的Callback
    public BluetoothGattCallback mBluetoothGattCallback = new BluetoothGattCallback() {
        @Override
        public void onConnectionStateChange(BluetoothGatt gatt, int iStatus, int iNewState) {
            BluetoothDevice dev = gatt.getDevice();
            //Log.i(TAG, String.format("onConnectionStateChange:%s,%s,%s,%s", dev.getName(), dev.getAddress(), status, newState));
            if (iStatus == BluetoothGatt.GATT_SUCCESS && iNewState == BluetoothProfile.STATE_CONNECTED) {
                b_Connected = true;
                gatt.discoverServices(); //启动服务发现
                clsRaw.SetConnection(true);
            }
            else if(iNewState == BluetoothProfile.STATE_DISCONNECTED){
                b_Connected = false;
                clsRaw.SetConnection(false);
            }
            else{
            }
        }
        @Override
        public void onServicesDiscovered(BluetoothGatt gatt, int iStatus) {
            //BLE服务发现成功
            bDiscoverServiceOk = true;
        }
        //  執行 GetBatteryLevel 完成之後，會跳到這裡
        @Override
        public void onCharacteristicRead(BluetoothGatt gatt, BluetoothGattCharacteristic characteristic, int iStatus) {
            UUID uuid = characteristic.getUuid();
            String valueStr = new String(characteristic.getValue());
            if(uuid.equals(Battery_Level_UUID)){
                int iFlag = characteristic.getProperties();
                int iFormat = -1;
                if ((iFlag & 0x01) != 0)
                    iFormat = BluetoothGattCharacteristic.FORMAT_UINT16;
                else
                    iFormat = BluetoothGattCharacteristic.FORMAT_UINT8;
                try {
                    //int iLevel = characteristic.getIntValue(iFormat, 1);
                    byArr = characteristic.getValue();
                }
                catch(Exception ex){
                    String str = ex.toString();
                }
                iBattery = iByteToInt(byArr[0]);
            }
            else if(uuid.equals(Data_Characteristic_UUID)){
                int iFlag = characteristic.getProperties();
            }
        }
        @Override
        public void onCharacteristicWrite(BluetoothGatt gatt, BluetoothGattCharacteristic characteristic, int iStatus) {
            UUID uuid = characteristic.getUuid();
            String valueStr = new String(characteristic.getValue());
        }
        @Override
        public void onCharacteristicChanged(BluetoothGatt gatt, BluetoothGattCharacteristic characteristic) {
            bBrainDataStartOk = true;

            UUID uuid = characteristic.getUuid();

            byte[] byteValue = characteristic.getValue();
            int iLen = byteValue.length;
            if(iLen < 5)
                return;
            if(iByteToInt(byteValue[0]) != 170)
                return;
            if(iByteToInt(byteValue[1]) == 0x01){
                if(iByteToInt(byteValue[2]) == 0x01 && iByteToInt(byteValue[3]) == 0x0F) {
                    iGoodSignal = (200-iByteToInt(byteValue[4]))/2;
                    iAtt = iByteToInt(byteValue[5]);
                    iMed = iByteToInt(byteValue[6]);
                    iDelta = iByteToInt(byteValue[7])*65536 + iByteToInt(byteValue[8])*256 + iByteToInt(byteValue[9]);
                    iTheta = iByteToInt(byteValue[10])*65536 + iByteToInt(byteValue[11])*256 + iByteToInt(byteValue[12]);
                    iLowAlpha = iByteToInt(byteValue[13])*65536 + iByteToInt(byteValue[14])*256 + iByteToInt(byteValue[15]);
                    iHighAlpha = iByteToInt(byteValue[16])*65536 + iByteToInt(byteValue[17])*256 + iByteToInt(byteValue[18]);
                }
                if(iByteToInt(byteValue[2]) == 0x02 && iByteToInt(byteValue[3]) == 0x0C) {
                    iLowBeta = iByteToInt(byteValue[4])*65536 + iByteToInt(byteValue[5])*256 + iByteToInt(byteValue[6]);
                    iHighBeta = iByteToInt(byteValue[7])*65536 + iByteToInt(byteValue[8])*256 + iByteToInt(byteValue[9]);
                    iLowGamma = iByteToInt(byteValue[10])*65536 + iByteToInt(byteValue[11])*256 + iByteToInt(byteValue[12]);
                    iHighGamma = iByteToInt(byteValue[13])*65536 + iByteToInt(byteValue[14])*256 + iByteToInt(byteValue[15]);

                    clsRaw.Set(iGoodSignal,iAtt,iMed,iDelta,iTheta,iLowAlpha,iHighAlpha,iLowBeta,iHighBeta,
                        iLowGamma,iHighGamma,iBattery);

                    iGetBatteryCount++;
                    if(iGetBatteryCount > 10){
                        iGetBatteryCount = 0;
                        GetBatteryLevel();
                    }
                }
            }
            else if(iByteToInt(byteValue[1]) == 0x02){
                //iRawCnt++;
            }
            else if(iByteToInt(byteValue[1]) == 0x03){
                if(iByteToInt(byteValue[2]) == 0x01 && iByteToInt(byteValue[3]) == 0x01) {
                    //iRawCnt++;
                    iLeft = byteValue[4] & 0x01;
                    iRight = byteValue[4] & 0x02;
                    iDown = byteValue[4] & 0x04;
                    iUp = byteValue[4] & 0x08;
                }
            }
        }
        @Override
        public void onDescriptorRead(BluetoothGatt gatt, BluetoothGattDescriptor descriptor, int iStatus) {
            UUID uuid = descriptor.getUuid();
            String valueStr = Arrays.toString(descriptor.getValue());
        }
        @Override
        public void onDescriptorWrite(BluetoothGatt gatt, BluetoothGattDescriptor descriptor, int iStatus) {
            UUID uuid = descriptor.getUuid();
            byte[] byteValue = descriptor.getValue();
        }
    };
    //===================================================
    private static final UUID Data_Service_UUID = UUID.fromString("039AFFF0-2C94-11E3-9E06-0002A5D5C51B");
    private static final UUID Data_Characteristic_UUID = UUID.fromString("039AFFF4-2C94-11E3-9E06-0002A5D5C51B");
    void EnableBrainwaveData() {
        BluetoothGattService dataService = mBluetoothGatt.getService(Data_Service_UUID);
        if(dataService == null)
            return;
        BluetoothGattCharacteristic characteristicData = dataService.getCharacteristic(Data_Characteristic_UUID);
        if(characteristicData == null)
            return;
        boolean tt = mBluetoothGatt.setCharacteristicNotification(characteristicData, true);
        if(tt){
            List<BluetoothGattDescriptor> descriptorList = characteristicData.getDescriptors();
            if(descriptorList != null && descriptorList.size() > 0) {
                for (BluetoothGattDescriptor descriptor : descriptorList) {
                    //要如此做,腦波資料才會每秒做更新
                    descriptor.setValue(BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE);
                    mBluetoothGatt.writeDescriptor(descriptor);
                }
            }
        }
    }
    //===================================================
    int iByteToInt(byte _by){
        int iA = _by & 0xFF;
        return iA;
    }
    //===================================================
}
