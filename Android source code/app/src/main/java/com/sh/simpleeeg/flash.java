package com.sh.simpleeeg;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ActivityInfo;
import android.os.Handler;
//import android.support.v7.app.AppCompatActivity;
import android.os.Bundle;
import android.view.WindowManager;
import android.widget.ImageView;

import com.bumptech.glide.Glide;
import com.bumptech.glide.request.RequestOptions;

public class flash extends Activity {

    ImageView ivBG;

    Context mContext;
    RequestOptions myGdiOptions;
    private ClockThread mClockThread;
    private Handler mClockHandler = new Handler();

    @SuppressLint("SourceLockedOrientationActivity")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_PORTRAIT);
        setContentView(R.layout.flash);

        mContext = this;
        myGdiOptions = new RequestOptions().fitCenter();

        ivBG = (ImageView)findViewById(R.id.ivBG);

        mClockThread = new ClockThread();
        mClockHandler.postDelayed(mClockThread, 3000);
    }

    @Override
    protected void onStart() {
        super.onStart();
        Glide.with(this).load(R.drawable.bg_flash).apply(myGdiOptions).into(ivBG);
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
    protected void onStop() {
        super.onStop();
        Glide.with(this).clear(ivBG);
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

    /*
    @Override
    public void onBackPressed()
    {
        moveTaskToBack(true);
        android.os.Process.killProcess(android.os.Process.myPid());
    }
    */
    //===================================================
    //===================================================
    //===================================================
    private class ClockThread extends Thread {
        @Override
        public void run() {
            try {
                Intent intent = new Intent();
                intent.setClass(mContext, main.class);
                startActivity(intent);
                overridePendingTransition(0, 0);
            }
            catch(Exception ex) {
                System.out.println(ex.getMessage());
            }
        }
    }
    //===================================================
}
