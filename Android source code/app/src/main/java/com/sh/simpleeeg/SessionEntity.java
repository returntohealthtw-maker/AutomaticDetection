package com.sh.simpleeeg;

import androidx.room.ColumnInfo;
import androidx.room.Entity;
import androidx.room.PrimaryKey;

/**
 * 檢測場次資料表
 * 每次啟動腦波檢測即建立一筆場次記錄
 */
@Entity(tableName = "sessions")
public class SessionEntity {

    @PrimaryKey(autoGenerate = true)
    @ColumnInfo(name = "session_id")
    public long sessionId;

    /** 執行檢測的顧問姓名 */
    @ColumnInfo(name = "consultant_name")
    public String consultantName;

    /** 受測者姓名 */
    @ColumnInfo(name = "subject_name")
    public String subjectName;

    /** 受測者生日（格式：yyyy-MM-dd） */
    @ColumnInfo(name = "subject_birthday")
    public String subjectBirthday;

    /** 受測者性別（M/F） */
    @ColumnInfo(name = "subject_gender")
    public String subjectGender;

    /** 受測者年齡 */
    @ColumnInfo(name = "subject_age")
    public int subjectAge;

    /** 報告類型（adult/child） */
    @ColumnInfo(name = "report_type")
    public String reportType;

    /** 檢測開始時間（Unix ms） */
    @ColumnInfo(name = "start_time")
    public long startTime;

    /** 檢測結束時間（Unix ms，0 = 尚未結束） */
    @ColumnInfo(name = "end_time")
    public long endTime;

    /** 實際擷取筆數（每秒一筆） */
    @ColumnInfo(name = "total_captures")
    public int totalCaptures;

    /**
     * 場次狀態
     * 0 = 進行中 (in_progress)
     * 1 = 成功完成 (completed，≥150 有效筆)
     * 2 = 失敗/中斷 (failed)
     */
    @ColumnInfo(name = "status")
    public int status;

    /** 失敗原因（如 "bluetooth_disconnected"），成功時為 null */
    @ColumnInfo(name = "failure_reason")
    public String failureReason;

    /** 建立時間（Unix ms） */
    @ColumnInfo(name = "created_at")
    public long createdAt;
}
