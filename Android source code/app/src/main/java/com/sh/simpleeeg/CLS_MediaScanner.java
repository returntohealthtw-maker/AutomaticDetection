package com.sh.simpleeeg;

/**
 * Created by user on 2018/9/26.
 */

import android.content.Context;
import android.media.MediaScannerConnection;
import android.media.MediaScannerConnection.MediaScannerConnectionClient;
import android.net.Uri;

public class CLS_MediaScanner implements MediaScannerConnectionClient
{
    private MediaScannerConnection mMs;
    private String strFile;
    CLS_MediaScanner(Context _context, String _strFile)
    {
        strFile = _strFile;
        mMs = new MediaScannerConnection(_context, this);
        mMs.connect();
    }
    @Override
    public void onMediaScannerConnected() {
        mMs.scanFile(strFile, null);
    }

    @Override
    public void onScanCompleted(String path, Uri uri) {
        mMs.disconnect();
    }
}
