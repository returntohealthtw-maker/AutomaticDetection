package com.sh.simpleeeg;

import androidx.room.Dao;
import androidx.room.Insert;
import androidx.room.Query;

import java.util.List;

/**
 * 腦波擷取資料表存取介面（DAO）
 */
@Dao
public interface EegCaptureDao {

    /** 新增一筆腦波擷取記錄，回傳自動產生的 capture_id */
    @Insert
    long insert(EegCaptureEntity capture);

    /** 取得指定場次的所有擷取資料，依序號排列 */
    @Query("SELECT * FROM eeg_captures WHERE session_id = :sessionId ORDER BY seq_num ASC")
    List<EegCaptureEntity> getBySessionId(long sessionId);

    /** 取得指定場次的基線期資料（is_baseline=1，前 30 秒） */
    @Query("SELECT * FROM eeg_captures WHERE session_id = :sessionId AND is_baseline = 1 ORDER BY seq_num ASC")
    List<EegCaptureEntity> getBaseline(long sessionId);

    /** 取得指定場次的正式檢測資料（is_baseline=0） */
    @Query("SELECT * FROM eeg_captures WHERE session_id = :sessionId AND is_baseline = 0 ORDER BY seq_num ASC")
    List<EegCaptureEntity> getDetectionData(long sessionId);

    /** 統計指定場次的擷取總筆數 */
    @Query("SELECT COUNT(*) FROM eeg_captures WHERE session_id = :sessionId")
    int getCountBySessionId(long sessionId);

    /** 統計訊號良好的筆數（good_signal = 0） */
    @Query("SELECT COUNT(*) FROM eeg_captures WHERE session_id = :sessionId AND good_signal = 0")
    int getGoodSignalCount(long sessionId);

    /** 取得專注力平均值 */
    @Query("SELECT AVG(attention) FROM eeg_captures WHERE session_id = :sessionId AND is_baseline = 0")
    double getAvgAttention(long sessionId);

    /** 取得放鬆度平均值 */
    @Query("SELECT AVG(meditation) FROM eeg_captures WHERE session_id = :sessionId AND is_baseline = 0")
    double getAvgMeditation(long sessionId);

    /** 取得 Theta 波平均值 */
    @Query("SELECT AVG(theta) FROM eeg_captures WHERE session_id = :sessionId AND is_baseline = 0")
    double getAvgTheta(long sessionId);

    /** 取得 Low Alpha 波平均值 */
    @Query("SELECT AVG(low_alpha) FROM eeg_captures WHERE session_id = :sessionId AND is_baseline = 0")
    double getAvgLowAlpha(long sessionId);

    /** 取得 High Alpha 波平均值 */
    @Query("SELECT AVG(high_alpha) FROM eeg_captures WHERE session_id = :sessionId AND is_baseline = 0")
    double getAvgHighAlpha(long sessionId);

    /** 取得 Low Beta 波平均值 */
    @Query("SELECT AVG(low_beta) FROM eeg_captures WHERE session_id = :sessionId AND is_baseline = 0")
    double getAvgLowBeta(long sessionId);

    /** 取得 High Beta 波平均值 */
    @Query("SELECT AVG(high_beta) FROM eeg_captures WHERE session_id = :sessionId AND is_baseline = 0")
    double getAvgHighBeta(long sessionId);

    /** 取得 Low Gamma 波平均值 */
    @Query("SELECT AVG(low_gamma) FROM eeg_captures WHERE session_id = :sessionId AND is_baseline = 0")
    double getAvgLowGamma(long sessionId);

    /** 取得 High Gamma 波平均值 */
    @Query("SELECT AVG(high_gamma) FROM eeg_captures WHERE session_id = :sessionId AND is_baseline = 0")
    double getAvgHighGamma(long sessionId);

    /** 刪除指定場次的所有擷取資料 */
    @Query("DELETE FROM eeg_captures WHERE session_id = :sessionId")
    void deleteBySessionId(long sessionId);
}
