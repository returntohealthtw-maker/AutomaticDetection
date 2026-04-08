package com.sh.simpleeeg;

import androidx.room.Dao;
import androidx.room.Insert;
import androidx.room.Query;
import androidx.room.Update;

import java.util.List;

/**
 * 場次資料表存取介面（DAO）
 */
@Dao
public interface SessionDao {

    /** 新增一筆場次，回傳自動產生的 session_id */
    @Insert
    long insert(SessionEntity session);

    /** 更新場次資料（用於補充欄位） */
    @Update
    void update(SessionEntity session);

    /** 完成場次：記錄結束時間、擷取筆數、設為成功（status=1） */
    @Query("UPDATE sessions SET end_time = :endTime, total_captures = :totalCaptures, " +
           "status = 1 WHERE session_id = :sessionId")
    void completeSession(long sessionId, long endTime, int totalCaptures);

    /** 標記場次失敗（status=2） */
    @Query("UPDATE sessions SET end_time = :endTime, total_captures = :totalCaptures, " +
           "status = 2, failure_reason = :reason WHERE session_id = :sessionId")
    void failSession(long sessionId, long endTime, int totalCaptures, String reason);

    /** 取得所有場次，依開始時間降冪（最新在最前） */
    @Query("SELECT * FROM sessions ORDER BY start_time DESC")
    List<SessionEntity> getAll();

    /** 以 session_id 取得單筆場次 */
    @Query("SELECT * FROM sessions WHERE session_id = :sessionId")
    SessionEntity getById(long sessionId);

    /** 取得最近 N 筆場次 */
    @Query("SELECT * FROM sessions ORDER BY start_time DESC LIMIT :limit")
    List<SessionEntity> getRecent(int limit);

    /** 統計場次總數 */
    @Query("SELECT COUNT(*) FROM sessions")
    int getCount();

    /** 刪除指定場次（會連帶刪除 eeg_captures，因為設有 CASCADE） */
    @Query("DELETE FROM sessions WHERE session_id = :sessionId")
    void deleteById(long sessionId);
}
