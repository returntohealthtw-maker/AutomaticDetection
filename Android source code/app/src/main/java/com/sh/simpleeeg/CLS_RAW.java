package com.sh.simpleeeg;

public class CLS_RAW {
    static int i_GoodSignal0 = 0,i_Att0 = 0,i_Med0 = 0,i_Delta0 = 0,i_Theta0 = 0,i_LowAlpha0 = 0,i_HighAlpha0 = 0;
    static int i_LowBeta0 = 0,i_HighBeta0 = 0,i_LowGamma0 = 0,i_HighGamma0 = 0;
    static int i_Left0 = 0,i_Right0=0,i_Down0=0,i_Up0=0;
    static int i_Battery0 = 100;

    static int i_GoodSignal1 = 0,i_Att1 = 0,i_Med1 = 0,i_Delta1 = 0,i_Theta1 = 0,i_LowAlpha1 = 0,i_HighAlpha1 = 0;
    static int i_LowBeta1 = 0,i_HighBeta1 = 0,i_LowGamma1 = 0,i_HighGamma1 = 0;
    static int i_Left1 = 0,i_Right1=0,i_Down1=0,i_Up1=0;
    static int i_Battery1 = 100;

    static boolean bDataSw = false; //0

    static boolean b_Connected = false;


    static double dDownScale = 0.02;//0.2;
    static double dDeltaHigh = 2500000 * dDownScale;
    static double dThetaHigh = 450000 * dDownScale;
    static double dLowAlphaHigh = 150000 * dDownScale;
    static double dHighAlphaHigh = 150000 * dDownScale;
    static double dLowBetaHigh = 150000 * dDownScale;
    static double dHighBetaHigh = 150000 * dDownScale;
    static double dLowGammaHigh = 150000 * dDownScale;
    static double dHighGammaHigh = 150000 * dDownScale;
    //===================================================
    public CLS_RAW(){

    }
    //===================================================
    public void Set(int iG,int iA,int iM,int iD,int iT,int iLA,int iHA,int iLB,int iHB,int iLG,int iHG,int iB){
        if(bDataSw){
            i_GoodSignal0 = iG;
            i_Att0 = iA;
            i_Med0 = iM;
            i_Delta0 = iD;
            i_Theta0 = iT;
            i_LowAlpha0 = iLA;
            i_HighAlpha0 = iHA;
            i_LowBeta0 = iLB;
            i_HighBeta0 = iHB;
            i_LowGamma0 = iLG;
            i_HighGamma0 = iHG;
            i_Battery0 = iB;
        }
        else{
            i_GoodSignal1 = iG;
            i_Att1 = iA;
            i_Med1 = iM;
            i_Delta1 = iD;
            i_Theta1 = iT;
            i_LowAlpha1 = iLA;
            i_HighAlpha1 = iHA;
            i_LowBeta1 = iLB;
            i_HighBeta1 = iHB;
            i_LowGamma1 = iLG;
            i_HighGamma1 = iHG;
            i_Battery1 = iB;
        }
        bDataSw = !bDataSw;//上面設定是顛倒設定,為的是配合這一行,讓讀取能讀到更新後的資料
    }
    //===================================================
    public int iGoodSignal(){
        if(bDataSw)
            return i_GoodSignal1;
        return i_GoodSignal0;
    }
    public int iAttention(){
        if(bDataSw)
            return i_Att1;
        return i_Att0;
    }
    public int iMeditation(){
        if(bDataSw)
            return i_Med1;
        return i_Med0;
    }
    public int iDelta(){
        if(bDataSw)
            return i_Delta1;
        return i_Delta0;
    }
    public int iTheta(){
        if(bDataSw)
            return i_Theta1;
        return i_Theta0;
    }
    public int iLowAlpha(){
        if(bDataSw)
            return i_LowAlpha1;
        return i_LowAlpha0;
    }
    public int iHighAlpha(){
        if(bDataSw)
            return i_HighAlpha1;
        return i_HighAlpha0;
    }
    public int iLowBeta(){
        if(bDataSw)
            return i_LowBeta1;
        return i_LowBeta0;
    }
    public int iHighBeta(){
        if(bDataSw)
            return i_HighBeta1;
        return i_HighBeta0;
    }
    public int iLowGamma(){
        if(bDataSw)
            return i_LowGamma1;
        return i_LowGamma0;
    }
    public int iHighGamma(){
        if(bDataSw)
            return i_HighGamma1;
        return i_HighGamma0;
    }
    public int iBattery(){
        if(bDataSw)
            return i_Battery1;
        return i_Battery0;
    }

    public int iDeltaPercent(){
        int iP;
        if(bDataSw)
            iP = (int)((double)i_Delta1/dDeltaHigh);
        else
            iP = (int)((double)i_Delta0/dDeltaHigh);
        if(iP > 100)
            iP = 100;
        return iP;
    }
    public int iThetaPercent(){
        int iP;
        if(bDataSw)
            iP = (int)((double)i_Theta1/dThetaHigh);
        else
            iP = (int)((double)i_Theta0/dThetaHigh);
        if(iP > 100)
            iP = 100;
        return iP;
    }
    public int iLowAlphaPercent(){
        int iP;
        if(bDataSw)
            iP = (int)((double)i_LowAlpha1/dLowAlphaHigh);
        else
            iP = (int)((double)i_LowAlpha0/dLowAlphaHigh);
        if(iP > 100)
            iP = 100;
        return iP;
    }
    public int iHighAlphaPercent(){
        int iP;
        if(bDataSw)
            iP = (int)((double)i_HighAlpha1/dHighAlphaHigh);
        else
            iP = (int)((double)i_HighAlpha0/dHighAlphaHigh);
        if(iP > 100)
            iP = 100;
        return iP;
    }
    public int iLowBetaPercent(){
        int iP;
        if(bDataSw)
            iP = (int)((double)i_LowBeta1/dLowBetaHigh);
        else
            iP = (int)((double)i_LowBeta0/dLowBetaHigh);
        if(iP > 100)
            iP = 100;
        return iP;
    }
    public int iHighBetaPercent(){
        int iP;
        if(bDataSw)
            iP = (int)((double)i_HighBeta1/dHighBetaHigh);
        else
            iP = (int)((double)i_HighBeta0/dHighBetaHigh);
        if(iP > 100)
            iP = 100;
        return iP;
    }
    public int iLowGammaPercent(){
        int iP;
        if(bDataSw)
            iP = (int)((double)i_LowGamma1/dLowGammaHigh);
        else
            iP = (int)((double)i_LowGamma0/dLowGammaHigh);
        if(iP > 100)
            iP = 100;
        return iP;
    }
    public int iHighGammaPercent(){
        int iP;
        if(bDataSw)
            iP = (int)((double)i_HighGamma1/dHighGammaHigh);
        else
            iP = (int)((double)i_HighGamma0/dHighGammaHigh);
        if(iP > 100)
            iP = 100;
        return iP;
    }
    //===================================================
    public void SetConnection(boolean _bState){b_Connected = _bState;}
    public boolean bConnected(){return b_Connected;}
    //===================================================
}




















