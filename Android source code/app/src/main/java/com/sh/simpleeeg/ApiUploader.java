package com.sh.simpleeeg;

import android.util.Log;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.List;
import java.util.concurrent.TimeUnit;

import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;

/**
 * 將檢測完成的腦波數據上傳到後端 API
 *
 * 使用方式：
 *   ApiUploader.upload(session, captures, callback);
 */
public class ApiUploader {

    private static final String TAG = "ApiUploader";

    // ── 修改成你的電腦 WiFi IP ────────────────────────────────────────────────
    // 手機與電腦必須在同一 WiFi 網路下
    public static final String BASE_URL = "https://backend-production-2da61.up.railway.app";
    // ──────────────────────────────────────────────────────────────────────────

    private static final MediaType JSON = MediaType.get("application/json; charset=utf-8");

    private static final OkHttpClient client = new OkHttpClient.Builder()
            .connectTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(90, TimeUnit.SECONDS)
            .readTimeout(90, TimeUnit.SECONDS)
            .build();

    public interface UploadCallback {
        void onSuccess(int sessionId, int reportId);
        void onFailure(String error);
    }

    private static final int MAX_RETRY = 3;

    /**
     * 上傳整場腦波資料（在背景執行緒呼叫，不會阻塞 UI）
     * 失敗時自動重試最多 3 次（間隔 5 秒）
     */
    public static void upload(SessionEntity session,
                              List<EegCaptureEntity> captures,
                              UploadCallback callback) {
        new Thread(() -> {
            Exception lastEx = null;
            for (int attempt = 1; attempt <= MAX_RETRY; attempt++) {
                try {
                    JSONObject body = buildRequestBody(session, captures);
                    RequestBody reqBody = RequestBody.create(body.toString(), JSON);
                    Request request = new Request.Builder()
                            .url(BASE_URL + "/api/v1/sessions/upload")
                            .post(reqBody)
                            .build();

                    try (Response response = client.newCall(request).execute()) {
                        String respStr = response.body() != null ? response.body().string() : "";
                        if (response.isSuccessful()) {
                            JSONObject resp = new JSONObject(respStr);
                            int sid = resp.getInt("session_id");
                            int rid = resp.getInt("report_id");
                            Log.i(TAG, "Upload success (attempt " + attempt + "): session=" + sid + " report=" + rid);
                            if (callback != null) callback.onSuccess(sid, rid);
                            return;
                        } else {
                            Log.e(TAG, "Upload failed HTTP " + response.code() + " (attempt " + attempt + "): " + respStr);
                            // HTTP 4xx 不重試（資料問題，重試也沒用）
                            if (response.code() >= 400 && response.code() < 500) {
                                if (callback != null) callback.onFailure("HTTP " + response.code());
                                return;
                            }
                        }
                    }
                } catch (Exception e) {
                    lastEx = e;
                    Log.e(TAG, "Upload exception (attempt " + attempt + "): " + e.getMessage(), e);
                }

                if (attempt < MAX_RETRY) {
                    try { Thread.sleep(5000L * attempt); } catch (InterruptedException ignored) {}
                }
            }
            if (callback != null) callback.onFailure(lastEx != null ? lastEx.getMessage() : "上傳失敗，已重試 " + MAX_RETRY + " 次");
        }).start();
    }

    private static JSONObject buildRequestBody(SessionEntity s,
                                               List<EegCaptureEntity> captures)
            throws Exception {
        JSONObject body = new JSONObject();
        body.put("consultant_name",  s.consultantName  != null ? s.consultantName  : "");
        body.put("subject_name",     s.subjectName     != null ? s.subjectName     : "");
        body.put("subject_birthday", s.subjectBirthday != null ? s.subjectBirthday : "");
        body.put("subject_gender",   s.subjectGender   != null ? s.subjectGender   : "M");
        body.put("subject_age",      s.subjectAge);
        body.put("report_type",      s.reportType      != null ? s.reportType      : "adult");
        body.put("start_time",       s.startTime);
        body.put("end_time",         s.endTime);
        body.put("total_captures",   s.totalCaptures);
        body.put("is_success",       s.status == 1);
        body.put("failure_reason",   s.failureReason != null ? s.failureReason : "");

        JSONArray arr = new JSONArray();
        for (EegCaptureEntity c : captures) {
            JSONObject item = new JSONObject();
            item.put("seq_num",     c.seqNum);
            item.put("is_baseline", c.isBaseline);
            item.put("captured_at", c.capturedAt);
            item.put("good_signal", c.goodSignal);
            item.put("attention",   c.attention);
            item.put("meditation",  c.meditation);
            item.put("delta",       c.delta);
            item.put("theta",       c.theta);
            item.put("low_alpha",   c.lowAlpha);
            item.put("high_alpha",  c.highAlpha);
            item.put("low_beta",    c.lowBeta);
            item.put("high_beta",   c.highBeta);
            item.put("low_gamma",   c.lowGamma);
            item.put("high_gamma",  c.highGamma);
            item.put("feedback",    c.feedback);
            arr.put(item);
        }
        body.put("captures", arr);
        return body;
    }
}
