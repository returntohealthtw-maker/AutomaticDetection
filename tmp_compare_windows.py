"""比較 Session #60 的 BrainDNA 結果：最佳30秒 vs 全部資料"""
import json, urllib3, requests
urllib3.disable_warnings()

BASE = "https://backend-production-2da61.up.railway.app"

r = requests.post(f"{BASE}/api/v1/auth/login",
                  json={"phone":"0900000000","password":"admin123"},
                  verify=False, timeout=15)
token = r.json().get("token", r.json().get("access_token",""))
hdrs = {"Authorization": f"Bearer {token}"}

data = requests.get(f"{BASE}/api/admin/compare-windows/60",
                    headers=hdrs, verify=False, timeout=30).json()

if "error" in data:
    print("錯誤:", data); exit()

w30   = data["window_30s"]   or {}
wfull = data["window_full"]  or {}
diff  = data["diff"]         or {}

print(f"Session #60  總樣本數: {data['total_samples']} 秒")
print(f"最佳視窗起始: 第 {data['best_window_start']} 秒，長度: {data['best_window_length']} 秒")
print()

BAND_LABELS = {
    "delta":      "Delta      深度休息",
    "theta":      "Theta      直覺能力",
    "low_alpha":  "Low α      內在安定",
    "high_alpha": "High α     氣血飽滿",
    "low_beta":   "Low β      邏輯分析",
    "high_beta":  "High β     高度專注",
    "low_gamma":  "Low γ      慈悲柔軟",
    "high_gamma": "High γ     觀察環境",
}

print(f"{'頻段':<28} {'最佳30秒':>8} {'全部資料':>8} {'差異':>8}")
print("-" * 58)
for k, label in BAND_LABELS.items():
    v30   = w30.get(k,  "—")
    vfull = wfull.get(k,"—")
    d     = diff.get(k, "")
    sign  = ("+" if isinstance(d,int) and d>0 else "") if d!="" else ""
    print(f"{label:<28} {str(v30):>8} {str(vfull):>8}   {sign}{d}")
