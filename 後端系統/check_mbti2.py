import sys, math
sys.path.insert(0, '.')
from app.services.algorithms import _norm100_to_raw, BandAverages, compute_mbti
from app.algorithms.bagua import Bagua
from app.algorithms.data_stats import DATA_STATS
from scipy.stats import norm

def show(label, lo_alpha, theta, hi_alpha=56, lo_beta=95, hi_beta=100, lo_gamma=50, hi_gamma=50, att=87, med=60):
    avg = BandAverages(28, theta, lo_alpha, hi_alpha, lo_beta, hi_beta, lo_gamma, hi_gamma, att, med, 180)
    result = compute_mbti(avg)
    raw_la = _norm100_to_raw(lo_alpha)
    raw_th = _norm100_to_raw(theta)
    p_la = norm.cdf(math.log10(max(raw_la,0.1)), DATA_STATS['lowAlpha']['mean'], DATA_STATS['lowAlpha']['std'])
    p_th = norm.cdf(math.log10(max(raw_th,0.1)), DATA_STATS['lowAlpha']['mean'], DATA_STATS['lowAlpha']['std'])
    bagua = Bagua.calcBagua(None, raw_la)
    print(f"{label}")
    print(f"  lo_alpha={lo_alpha} -> raw={raw_la:.0f}, p={p_la:.3f} -> bagua={bagua.id}({bagua.name})")
    print(f"  theta={theta} -> raw={raw_th:.0f}, p={p_th:.3f} -> high={p_th>0.5}")
    print(f"  => MBTI: {result['mbti_type']}")
    print()

# Bagua thresholds
print("=== Bagua zones (normalized lo_alpha) ===")
for pct, name in [(0.0,'qian<'), (0.125,'dui<'), (0.25,'zhen<'), (0.375,'xun<'), (0.5,'kan<'), (0.625,'gen<'), (0.75,'kun<')]:
    z = norm.ppf(max(pct, 0.0001))
    log10r = z * DATA_STATS['lowAlpha']['std'] + DATA_STATS['lowAlpha']['mean']
    norm_val = log10r / 0.06
    print(f"  {name:6s}: norm_lo_alpha >= {norm_val:.1f}% (z={z:.3f})")
print()

# Key test scenarios
show("A: normalized lo_alpha=49, theta=66 (seed-42 test)", 49, 66)
show("B: normalized lo_alpha=70, theta=85", 70, 85)
show("C: normalized lo_alpha=71, theta=85", 71, 85)
show("D: normalized lo_alpha=72, theta=85", 72, 85)
show("E: lo_alpha=100 (capped raw), theta=100", 100, 100)

# What the local DB values (raw) would produce IF they were stored as normalized
print("=== Local DB raw values treated as-if normalized (bug scenario) ===")
raw_samples_la = [16423, 5505, 91278, 2321, 30847, 56842, 25604, 9496, 14713]
raw_samples_th = [228295, 90476, 332170, 21178, 183950, 1070147, 474161, 27967, 6596]

# If headless renderer caps at 100 => lo_alpha=min(100,val)=100 for most
capped_la = [min(100, x) for x in raw_samples_la]
capped_th = [min(100, x) for x in raw_samples_th]
avg_la = round(sum(capped_la) / len(capped_la))
avg_th = round(sum(capped_th) / len(capped_th))
print(f"After cap at 100: avg_lo_alpha={avg_la}, avg_theta={avg_th}")
show("  capped raw values", avg_la, avg_th)

# What if DB correctly stores bandTo100 values (new production behavior)
import math
def b100(raw):
    if raw <= 0: return 0
    return max(0, min(100, math.log10(raw+1)/6*100))

norm_samples_la = [b100(x) for x in raw_samples_la]
norm_samples_th = [b100(x) for x in raw_samples_th]
avg_norm_la = round(sum(norm_samples_la)/len(norm_samples_la), 1)
avg_norm_th = round(sum(norm_samples_th)/len(norm_samples_th), 1)
print(f"After bandTo100: avg_lo_alpha={avg_norm_la:.1f}, avg_theta={avg_norm_th:.1f}")
show(f"  bandTo100 of local DB values (lo={avg_norm_la:.0f}, th={avg_norm_th:.0f})", round(avg_norm_la), round(avg_norm_th))
