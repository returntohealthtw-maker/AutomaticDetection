package com.sh.simpleeeg;

import androidx.room.ColumnInfo;
import androidx.room.Entity;
import androidx.room.ForeignKey;
import androidx.room.Index;
import androidx.room.PrimaryKey;

/**
 * 腦波原始擷取資料表
 * 每秒儲存一筆，每場次最多 180 筆（3 分鐘 × 60 秒）
 */
@Entity(
    tableName = "eeg_captures",
    foreignKeys = @ForeignKey(
        entity    = SessionEntity.class,
        parentColumns = "session_id",
        childColumns  = "session_id",
        onDelete  = ForeignKey.CASCADE   // 刪除場次時同步刪除擷取資料
    ),
    indices = { @Index("session_id") }
)
public class EegCaptureEntity {

    @PrimaryKey(autoGenerate = true)
    @ColumnInfo(name = "capture_id")
    public long captureId;

    /** 所屬場次 ID（外鍵） */
    @ColumnInfo(name = "session_id")
    public long sessionId;

    /** 場次內序號，從 1 開始（第 1 秒 = 1，第 180 秒 = 180） */
    @ColumnInfo(name = "seq_num")
    public int seqNum;

    /** 是否為基線期（前 30 秒）：1 = 基線，0 = 正式檢測 */
    @ColumnInfo(name = "is_baseline")
    public int isBaseline;

    /** 擷取時間戳（Unix ms） */
    @ColumnInfo(name = "captured_at")
    public long capturedAt;

    /**
     * 訊號品質
     * 0 = 良好 (Good)
     * 1~50 = 微弱 (Weak)
     * 200 = 無訊號 (No signal)
     */
    @ColumnInfo(name = "good_signal")
    public int goodSignal;

    /** 專注力分數（0–100，eSense 演算法） */
    @ColumnInfo(name = "attention")
    public int attention;

    /** 放鬆度/冥想分數（0–100，eSense 演算法） */
    @ColumnInfo(name = "meditation")
    public int meditation;

    // ─── 腦波頻帶功率（原始整數，TGAM 晶片輸出） ───────────────────

    /** Delta 波（0.5–4 Hz）原始功率 */
    @ColumnInfo(name = "delta")
    public int delta;

    /** Theta 波（4–8 Hz）/ 直覺波 原始功率 */
    @ColumnInfo(name = "theta")
    public int theta;

    /** Low Alpha 波（8–10 Hz）/ 安定波 原始功率 */
    @ColumnInfo(name = "low_alpha")
    public int lowAlpha;

    /** High Alpha 波（10–13 Hz）/ 氣血波 原始功率 */
    @ColumnInfo(name = "high_alpha")
    public int highAlpha;

    /** Low Beta 波（13–20 Hz）/ 邏輯波 原始功率 */
    @ColumnInfo(name = "low_beta")
    public int lowBeta;

    /** High Beta 波（20–30 Hz）/ 執行波 原始功率 */
    @ColumnInfo(name = "high_beta")
    public int highBeta;

    /** Low Gamma 波（30–35 Hz）/ 慈悲波 原始功率 */
    @ColumnInfo(name = "low_gamma")
    public int lowGamma;

    /** High Gamma 波（35–100 Hz）/ 觀察波 原始功率 */
    @ColumnInfo(name = "high_gamma")
    public int highGamma;

    /** 回饋值（保留原始程式的 iFeedback 欄位） */
    @ColumnInfo(name = "feedback")
    public int feedback;
}
