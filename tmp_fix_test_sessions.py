import sys, requests, urllib3
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=8)
token = r.json().get('token','')
h = {'Authorization': 'Bearer '+token}

# 把所有測試 session 的 subject_name 改掉，讓他們不再出現在真實受測者名下
test_sessions = {
    129: '測試_鄭靜怡',   # 這是我雙DB驗證時的測試資料，非真實腦波
    134: '測試_雙DB',
    133: '測試_ms',
    131: '測試_format',
    130: '測試_ping',
    128: '測試_07',
    127: '測試_upload',
}

import psycopg2
# 嘗試用 update-summary 之類的 API 或直接用 raw SQL
# 先嘗試看看有沒有 admin 更新 session 的端點
# 若無，直接用 check_db 的方式建立腳本

# 實際上需要 DB 連線 - 透過後端 API 間接修改
# 沒有 API 可以更新 session 的 subject_name，需要直接用 psycopg2

print("測試 sessions 需要透過 DB 直接更新 subject_name")
print("修改方法：使用後端 admin 端點或 DB migration")

# 先看看後端有沒有 admin session update 端點
test_ep = requests.get(BASE+'/eeg/sessions/129/stats', headers=h, verify=False, timeout=8).json()
print(f"Session #129: {test_ep.get('subject_name')} created_at={test_ep.get('created_at')}")
