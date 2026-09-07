import sys, requests, warnings
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

BASE = 'https://backend-production-2da61.up.railway.app'
s = requests.Session()
s.verify = False

# 確認版本
r = s.get(f'{BASE}/api/v1/app/version')
print(f"版本: {r.json().get('html_version')}")

# 查 OpenAPI schema 確認 EegStatsOut 有新欄位
r2 = s.get(f'{BASE}/openapi.json')
schema = r2.json()
components = schema.get('components', {}).get('schemas', {})
eeg_out = components.get('EegStatsOut', {})
props = eeg_out.get('properties', {})
print("\n=== EegStatsOut 欄位 ===")
for k, v in props.items():
    print(f"  {k}: {v.get('type') or v.get('anyOf','')}")

print()
if 'qeeg_band_scores' in props:
    print("✅ qeeg_band_scores 欄位存在")
else:
    print("❌ qeeg_band_scores 欄位不存在")
if 'qeeg_signal_grade' in props:
    print("✅ qeeg_signal_grade 欄位存在")
else:
    print("❌ qeeg_signal_grade 欄位不存在")
