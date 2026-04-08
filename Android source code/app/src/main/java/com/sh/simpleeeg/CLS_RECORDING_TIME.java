package com.sh.simpleeeg;

public class CLS_RECORDING_TIME {
    public int iStartHour = 0;
    public int iStartMin = 0;
    public int iRecordingHour = 0;
    public int iRecordingMin = 0;

    public CLS_RECORDING_TIME(int ish, int ism, int irh, int irm){
        iStartHour = ish;
        iStartMin = ism;
        iRecordingHour = irh;
        iRecordingMin = irm;
    }
}
