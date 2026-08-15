import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from app.services.algorithms import build_mbti_payload, compute_mbti_layers_from_captures, compute_averages, BandAverages

caps = [
    {'low_alpha': 45, 'theta': 55, 'high_gamma': 30, 'focus': 40, 'high_beta': 50, 'low_beta': 45, 'low_gamma': 35, 'high_alpha': 40, 'good_signal': 0, 'attention': 55, 'meditation': 45, 'delta': 60},
    {'low_alpha': 47, 'theta': 58, 'high_gamma': 28, 'focus': 42, 'high_beta': 52, 'low_beta': 43, 'low_gamma': 37, 'high_alpha': 38, 'good_signal': 0, 'attention': 57, 'meditation': 43, 'delta': 58},
    {'low_alpha': 43, 'theta': 52, 'high_gamma': 35, 'focus': 38, 'high_beta': 48, 'low_beta': 48, 'low_gamma': 33, 'high_alpha': 42, 'good_signal': 0, 'attention': 53, 'meditation': 47, 'delta': 62},
    {'low_alpha': 46, 'theta': 56, 'high_gamma': 32, 'focus': 41, 'high_beta': 51, 'low_beta': 44, 'low_gamma': 36, 'high_alpha': 39, 'good_signal': 0, 'attention': 56, 'meditation': 44, 'delta': 60},
]

try:
    layers = compute_mbti_layers_from_captures(caps)
    print("Layers:")
    for k, v in layers.items():
        t = v.get('type','?')
        s = v.get('secondary','?')
        print(f"  {k}: {t} (sec={s})")

    avg = compute_averages(caps)
    payload = build_mbti_payload(avg, caps)
    print("\nPrimary:", payload['mbti_primary'])
    print("Secondaries:", payload['mbti_secondaries'])
    print("Profiles:", payload['mbti_profiles'])
except Exception as e:
    import traceback
    traceback.print_exc()
