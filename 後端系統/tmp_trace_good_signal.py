"""
追蹤 session 89 的 good_signal 如何傳入 qEEG pipeline，
找出為何 usable_epochs = 0 的根本原因。
"""
import sys, requests, json, warnings
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

BASE = 'https://backend-production-2da61.up.railway.app'
s = requests.Session()
s.verify = False
r = s.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'})
token = r.json().get('access_token','')
s.headers['Authorization'] = f'Bearer {token}'

# 取出全部 captures（含 good_signal）
r2 = s.get(f'{BASE}/api/v1/sessions/89/captures', params={'limit': 200})
data = r2.json()
caps = data.get('captures', data if isinstance(data, list) else [])
print(f"captures 數量: {len(caps)}")

good_vals = [c.get('good_signal', 'N/A') for c in caps[:20]]
print(f"前20筆 good_signal: {good_vals}")

unique_gs = set(c.get('good_signal') for c in caps)
print(f"good_signal 唯一值: {unique_gs}")

# 模擬 _captures_to_per_sec 邏輯
good_signal_list = [int(c.get('good_signal', 0) or 0) for c in caps]
print(f"\ngood_signal_list（模擬 _captures_to_per_sec）唯一值: {set(good_signal_list)}")

# 模擬 assess_signal_quality 邏輯
good_arr = good_signal_list or []
n = len(caps)
usable = sum(1 for gs in good_arr if (gs or 0) < 50)
ratio = usable / n if n > 0 else 0.0
print(f"\nassess_signal_quality 模擬：")
print(f"  n_samples = {n}")
print(f"  good_arr 長度 = {len(good_arr)}")
print(f"  usable = {usable}")
print(f"  ratio = {ratio:.3f}")
if ratio >= 0.90:
    grade = "A"
elif ratio >= 0.75:
    grade = "B"
elif ratio >= 0.60:
    grade = "C"
else:
    grade = "D"
print(f"  grade = {grade}")

print("\n結論：")
if len(good_arr) == 0:
    print("  ❌ good_arr 為空，原因：good_signal_list 為空 → usable=0 → grade=D")
elif usable == 0:
    print("  ❌ usable=0，原因：所有 good_signal >= 50")
    print(f"  最小值: {min(good_arr)}, 最大值: {max(good_arr)}")
else:
    print(f"  ✅ 正確應為 grade={grade}，若伺服器顯示 D 代表部署時程式碼版本不同")
