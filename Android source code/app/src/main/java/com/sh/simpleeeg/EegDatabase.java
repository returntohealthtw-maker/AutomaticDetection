package com.sh.simpleeeg;

import android.content.Context;

import androidx.room.Database;
import androidx.room.Room;
import androidx.room.RoomDatabase;

/**
 * Room 資料庫主類別（單例）
 *
 * 資料庫檔案儲存於：
 *   /data/data/com.sh.simpleeeg/databases/eeg_database.db
 *
 * 若日後需要更改資料表結構（新增欄位等），須遞增 version 並提供 Migration。
 */
@Database(
    entities  = { SessionEntity.class, EegCaptureEntity.class },
    version   = 2,
    exportSchema = false
)
public abstract class EegDatabase extends RoomDatabase {

    private static final String DB_NAME = "eeg_database.db";

    // ─── Double-checked locking singleton ────────────────────────────────────
    private static volatile EegDatabase INSTANCE;

    public static EegDatabase getInstance(Context context) {
        if (INSTANCE == null) {
            synchronized (EegDatabase.class) {
                if (INSTANCE == null) {
                    INSTANCE = Room.databaseBuilder(
                            context.getApplicationContext(),
                            EegDatabase.class,
                            DB_NAME
                    )
                    // schema 升版時自動重建資料表（測試期可用；正式上線改用 Migration）
                    .fallbackToDestructiveMigration()
                    .build();
                }
            }
        }
        return INSTANCE;
    }
    // ─────────────────────────────────────────────────────────────────────────

    /** 場次 DAO */
    public abstract SessionDao sessionDao();

    /** 腦波擷取 DAO */
    public abstract EegCaptureDao eegCaptureDao();
}
