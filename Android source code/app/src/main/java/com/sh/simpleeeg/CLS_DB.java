package com.sh.simpleeeg;

import android.content.Context;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;

import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import android.content.Context;

/**
 * 腦波資料庫管理員（全域單例）
 *
 * 使用方式：
 *   1. 在 Application / MainActivity.onCreate() 呼叫 CLS_DB.getInstance().init(context)
 *   2. 開始檢測前呼叫 startSession()
 *   3. 每秒資料回呼時呼叫 saveCapture()（由 CLS_DATA.SetBrainData 觸發）
 *   4. 檢測結束後呼叫 endSession()
 *
 * 所有資料庫操作皆在背景執行緒執行，不阻塞 UI。
 */
public class CLS_DB {

    private static final String TAG = "CLS_DB";

    // ─── 單例 ────────────────────────────────────────────────────────────────
    private static volatile CLS_DB INSTANCE;

    public static CLS_DB getInstance() {
        if (INSTANCE == null) {
            synchronized (CLS_DB.class) {
                if (INSTANCE == null) {
                    INSTANCE = new CLS_DB();
                }
            }
        }
        return INSTANCE;
    }

    private CLS_DB() {}
    // ─────────────────────────────────────────────────────────────────────────

    private EegDatabase db;
    private Context appContext;

    /** 當前登入的顧問姓名（登入後呼叫 setConsultantName 設定） */
    private String consultantName = "";

    /** 設定顧問姓名（登入後呼叫） */
    public void setConsultantName(String name) {
        consultantName = (name != null) ? name : "";
    }

    /** 取得顧問姓名 */
    public String getConsultantName() { return consultantName; }

    /** 背景單執行緒，確保資料庫寫入順序 */
    private final ExecutorService executor = Executors.newSingleThreadExecutor();

    /** UI 執行緒 Handler，供 Callback 回呼 */
    private final Handler mainHandler = new Handler(Looper.getMainLooper());

    /** 當前進行中的場次 ID（-1 = 無場次） */
    private long currentSessionId = -1;

    /** 當前場次已擷取的秒數序號（從 1 開始） */
    private int captureSeqNum = 0;

    /** 基線期秒數（前 30 秒為基線） */
    public static final int BASELINE_SECONDS = 30;

    // ─────────────────────────────────────────────────────────────────────────
    // 初始化
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * 初始化資料庫連線（在 Application 或 MainActivity.onCreate 呼叫一次即可）
     */
    public void init(Context context) {
        appContext = context.getApplicationContext();
        db = EegDatabase.getInstance(appContext);
        Log.i(TAG, "EegDatabase initialized.");
    }

    private boolean isReady() {
        if (db == null) {
            Log.w(TAG, "Database not initialized! Call init(context) first.");
            return false;
        }
        return true;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // 場次管理
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * 開始新的檢測場次
     *
     * @param subjectName     受測者姓名
     * @param subjectBirthday 受測者生日（yyyy-MM-dd）
     * @param subjectGender   受測者性別（M/F）
     * @param subjectAge      受測者年齡
     * @param reportType      報告類型（"adult" / "child"）
     * @param callback        建立完成回呼，帶回 session_id（主執行緒）
     */
    public void startSession(String subjectName, String subjectBirthday,
                             String subjectGender, int subjectAge,
                             String reportType,
                             Callback<Long> callback) {
        if (!isReady()) return;

        executor.execute(() -> {
            SessionEntity s = new SessionEntity();
            s.consultantName  = consultantName;
            s.subjectName     = subjectName;
            s.subjectBirthday = subjectBirthday;
            s.subjectGender   = subjectGender;
            s.subjectAge      = subjectAge;
            s.reportType      = reportType;
            s.startTime       = System.currentTimeMillis();
            s.endTime         = 0;
            s.totalCaptures   = 0;
            s.status          = 0; // 進行中
            s.failureReason   = null;
            s.createdAt       = System.currentTimeMillis();

            long id = db.sessionDao().insert(s);
            currentSessionId = id;
            captureSeqNum    = 0;

            Log.i(TAG, "Session started, id=" + id);

            if (callback != null) {
                mainHandler.post(() -> callback.onResult(id));
            }
        });
    }

    /**
     * 快速開始場次（不填受測者資料，可事後更新）
     */
    public void startSession(Callback<Long> callback) {
        startSession("", "", "", 0, "adult", callback);
    }

    /**
     * 更新受測者資料（可在場次建立後補填）
     */
    public void updateSubjectInfo(long sessionId,
                                  String name, String birthday,
                                  String gender, int age, String reportType) {
        if (!isReady()) return;
        executor.execute(() -> {
            SessionEntity s = db.sessionDao().getById(sessionId);
            if (s == null) return;
            s.subjectName     = name;
            s.subjectBirthday = birthday;
            s.subjectGender   = gender;
            s.subjectAge      = age;
            s.reportType      = reportType;
            db.sessionDao().update(s);
        });
    }

    /**
     * 標記場次成功完成（≥150 有效筆即視為成功）
     *
     * @param callback 完成後回呼（主執行緒）
     */
    public void endSession(Callback<Void> callback) {
        if (!isReady() || currentSessionId < 0) return;

        final long sid    = currentSessionId;
        final int  total  = captureSeqNum;

        executor.execute(() -> {
            db.sessionDao().completeSession(sid, System.currentTimeMillis(), total);
            Log.i(TAG, "Session completed, id=" + sid + ", captures=" + total);
            currentSessionId = -1;
            captureSeqNum    = 0;

            // 場次成功（測試模式：≥5 筆即上傳；正式上線改回 150）
            if (total >= 5) {
                SessionEntity session  = db.sessionDao().getById(sid);
                List<EegCaptureEntity> caps = db.eegCaptureDao().getBySessionId(sid);
                ApiUploader.upload(session, caps, new ApiUploader.UploadCallback() {
                    @Override public void onSuccess(int remoteSid, int reportId) {
                        Log.i(TAG, "Backend upload OK: remote session=" + remoteSid + " report=" + reportId);
                    }
                    @Override public void onFailure(String error) {
                        Log.e(TAG, "Backend upload FAILED: " + error);
                    }
                });
            }

            if (callback != null) {
                mainHandler.post(() -> callback.onResult(null));
            }
        });
    }

    /**
     * 標記場次失敗中斷
     *
     * @param reason   失敗原因（例如 "bluetooth_disconnected"）
     * @param callback 完成後回呼（主執行緒）
     */
    public void failSession(String reason, Callback<Void> callback) {
        if (!isReady() || currentSessionId < 0) return;

        final long sid   = currentSessionId;
        final int  total = captureSeqNum;

        executor.execute(() -> {
            db.sessionDao().failSession(sid, System.currentTimeMillis(), total, reason);
            Log.i(TAG, "Session failed, id=" + sid + ", reason=" + reason);
            currentSessionId = -1;
            captureSeqNum    = 0;

            if (callback != null) {
                mainHandler.post(() -> callback.onResult(null));
            }
        });
    }

    // ─────────────────────────────────────────────────────────────────────────
    // 擷取資料儲存（每秒呼叫一次）
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * 儲存一筆腦波擷取資料（由 CLS_DATA.SetBrainData 觸發，每秒一次）
     *
     * @param goodSignal 訊號品質（0=良好，200=無訊號）
     * @param attention  專注力（0–100）
     * @param meditation 放鬆度（0–100）
     * @param delta      Delta 波功率
     * @param theta      Theta 波功率
     * @param lowAlpha   Low Alpha 波功率
     * @param highAlpha  High Alpha 波功率
     * @param lowBeta    Low Beta 波功率
     * @param highBeta   High Beta 波功率
     * @param lowGamma   Low Gamma 波功率
     * @param highGamma  High Gamma 波功率
     * @param feedback   回饋值
     */
    public void saveCapture(int goodSignal, int attention, int meditation,
                            int delta,     int theta,
                            int lowAlpha,  int highAlpha,
                            int lowBeta,   int highBeta,
                            int lowGamma,  int highGamma,
                            int feedback) {
        if (!isReady() || currentSessionId < 0) return;

        captureSeqNum++;
        final int  seq        = captureSeqNum;
        final long sid        = currentSessionId;
        final long ts         = System.currentTimeMillis();
        final int  isBaseline = (seq <= BASELINE_SECONDS) ? 1 : 0;

        executor.execute(() -> {
            EegCaptureEntity c = new EegCaptureEntity();
            c.sessionId  = sid;
            c.seqNum     = seq;
            c.isBaseline = isBaseline;
            c.capturedAt = ts;
            c.goodSignal = goodSignal;
            c.attention  = attention;
            c.meditation = meditation;
            c.delta      = delta;
            c.theta      = theta;
            c.lowAlpha   = lowAlpha;
            c.highAlpha  = highAlpha;
            c.lowBeta    = lowBeta;
            c.highBeta   = highBeta;
            c.lowGamma   = lowGamma;
            c.highGamma  = highGamma;
            c.feedback   = feedback;

            db.eegCaptureDao().insert(c);
        });
    }

    // ─────────────────────────────────────────────────────────────────────────
    // 查詢
    // ─────────────────────────────────────────────────────────────────────────

    /** 取得所有場次清單（背景查詢，主執行緒回呼） */
    public void getAllSessions(Callback<List<SessionEntity>> callback) {
        if (!isReady() || callback == null) return;
        executor.execute(() -> {
            List<SessionEntity> list = db.sessionDao().getAll();
            mainHandler.post(() -> callback.onResult(list));
        });
    }

    /** 取得指定場次的所有腦波擷取資料（背景查詢，主執行緒回呼） */
    public void getCapturesBySession(long sessionId, Callback<List<EegCaptureEntity>> callback) {
        if (!isReady() || callback == null) return;
        executor.execute(() -> {
            List<EegCaptureEntity> list = db.eegCaptureDao().getBySessionId(sessionId);
            mainHandler.post(() -> callback.onResult(list));
        });
    }

    /** 取得指定場次的統計摘要（背景查詢，主執行緒回呼） */
    public void getSessionSummary(long sessionId, Callback<SessionSummary> callback) {
        if (!isReady() || callback == null) return;
        executor.execute(() -> {
            SessionSummary summary = new SessionSummary();
            summary.sessionId      = sessionId;
            summary.totalCaptures  = db.eegCaptureDao().getCountBySessionId(sessionId);
            summary.goodSignalCount= db.eegCaptureDao().getGoodSignalCount(sessionId);
            summary.avgAttention   = db.eegCaptureDao().getAvgAttention(sessionId);
            summary.avgMeditation  = db.eegCaptureDao().getAvgMeditation(sessionId);
            summary.avgTheta       = db.eegCaptureDao().getAvgTheta(sessionId);
            summary.avgLowAlpha    = db.eegCaptureDao().getAvgLowAlpha(sessionId);
            summary.avgHighAlpha   = db.eegCaptureDao().getAvgHighAlpha(sessionId);
            summary.avgLowBeta     = db.eegCaptureDao().getAvgLowBeta(sessionId);
            summary.avgHighBeta    = db.eegCaptureDao().getAvgHighBeta(sessionId);
            summary.avgLowGamma    = db.eegCaptureDao().getAvgLowGamma(sessionId);
            summary.avgHighGamma   = db.eegCaptureDao().getAvgHighGamma(sessionId);
            mainHandler.post(() -> callback.onResult(summary));
        });
    }

    // ─────────────────────────────────────────────────────────────────────────
    // 狀態查詢
    // ─────────────────────────────────────────────────────────────────────────

    /** 取得當前進行中的場次 ID（無場次回傳 -1） */
    public long getCurrentSessionId() { return currentSessionId; }

    /** 取得當前場次已擷取的秒數 */
    public int getCaptureSeqNum() { return captureSeqNum; }

    /** 是否有進行中的場次 */
    public boolean isSessionActive() { return currentSessionId >= 0; }

    // ─────────────────────────────────────────────────────────────────────────
    // 內部資料類別與介面
    // ─────────────────────────────────────────────────────────────────────────

    /** 非同步回呼介面（結果在主執行緒回傳） */
    public interface Callback<T> {
        void onResult(T result);
    }

    /** 場次統計摘要 */
    public static class SessionSummary {
        public long   sessionId;
        public int    totalCaptures;
        public int    goodSignalCount;
        public double avgAttention;
        public double avgMeditation;
        public double avgTheta;
        public double avgLowAlpha;
        public double avgHighAlpha;
        public double avgLowBeta;
        public double avgHighBeta;
        public double avgLowGamma;
        public double avgHighGamma;

        /** 有效擷取率（goodSignal 百分比） */
        public double getSignalQualityRate() {
            if (totalCaptures == 0) return 0;
            return (double) goodSignalCount / totalCaptures * 100.0;
        }

        /** 是否達到成功門檻（≥ 150 筆有效資料） */
        public boolean isSuccess() {
            return totalCaptures >= 150;
        }
    }
}
