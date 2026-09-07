"""
Debug script: compute MBTI for given normalized brainwave values
Usage: python check_mbti_debug.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.services.algorithms import compute_mbti, BandAverages, _norm100_to_raw
from app.algorithms.bagua import Bagua
from app.algorithms.data_stats import DATA_STATS
import math
from scipy.stats import norm

def mbti_from_normalized(lo_alpha, theta, hi_alpha=50, lo_beta=50, hi_beta=50, lo_gamma=50, hi_gamma=50, att=50, med=50):
    avg = BandAverages(
        delta=28, theta=theta,
        low_alpha=lo_alpha, high_alpha=hi_alpha,
        low_beta=lo_beta, high_beta=hi_beta,
        low_gamma=lo_gamma, high_gamma=hi_gamma,
        attention=att, meditation=med,
        sample_count=180
    )
    result = compute_mbti(avg)
    
    raw_la = _norm100_to_raw(lo_alpha)
    raw_th = _norm100_to_raw(theta)
    la_p = norm.cdf(math.log10(max(raw_la, 0.1)), DATA_STATS["lowAlpha"]["mean"], DATA_STATS["lowAlpha"]["std"])
    th_p = norm.cdf(math.log10(max(raw_th, 0.1)), DATA_STATS["lowAlpha"]["mean"], DATA_STATS["lowAlpha"]["std"])
    bagua = Bagua.calcBagua(None, raw_la)
    
    print(f"  lowAlpha={lo_alpha} → raw={raw_la:.0f}, log10={math.log10(max(raw_la,0.1)):.3f}, pct={la_p:.3f} → bagua={bagua.id}({bagua.name})")
    print(f"  theta={theta}    → raw={raw_th:.0f}, log10={math.log10(max(raw_th,0.1)):.3f}, pct={th_p:.3f} → high={th_p>0.5}")
    print(f"  → MBTI: {result['mbti_type']}")
    print()
    return result

print("=== MBTI 診斷工具 ===")
print()

# Test cases
test_cases = [
    ("test data (lowAlpha=49, theta=66)", 49, 66),
    ("typical user (both at mean ~68, 79)", 68, 79),
    ("high lowAlpha = 71, theta=80", 71, 80),
    ("high lowAlpha = 72, theta=70", 72, 70),
    ("lowAlpha=56, theta=66", 56, 66),
    ("lowAlpha=45, theta=50", 45, 50),
    ("lowAlpha=60, theta=66", 60, 66),
    ("lowAlpha=65, theta=66", 65, 66),
    ("lowAlpha=70, theta=66", 70, 66),
    ("lowAlpha=75, theta=66", 75, 66),
    ("lowAlpha=80, theta=66", 80, 66),
]

print("Bagua thresholds for normalized lowAlpha:")
for pct, name in [(0.125,"qian"), (0.25,"dui"), (0.375,"zhen"), (0.5,"xun"), (0.625,"kan"), (0.75,"gen"), (1.0,"kun")]:
    z = norm.ppf(pct)
    log10_raw = z * DATA_STATS["lowAlpha"]["std"] + DATA_STATS["lowAlpha"]["mean"]
    normalized = log10_raw / 0.06
    print(f"  {name} starts at normalized lowAlpha >= {normalized:.1f} (pct>={pct})")

print()
print("=== Test cases ===")
for label, la, th in test_cases:
    print(f"--- {label} ---")
    mbti_from_normalized(la, th)

# Try to read from local DB
try:
    import sqlite3
    db_path = os.path.join(os.path.dirname(__file__), "eeg_dev.db")
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        print(f"\nLocal DB tables: {tables}")
        
        if "eeg_captures" in tables:
            cur.execute("PRAGMA table_info(eeg_captures)")
            cols = [r[1] for r in cur.fetchall()]
            print(f"EegCaptures cols: {cols}")
            
            cur.execute("SELECT session_id, low_alpha, high_alpha, theta FROM eeg_captures ORDER BY id DESC LIMIT 10")
            rows = cur.fetchall()
            print("\nRecent captures (session_id, lo_alpha, hi_alpha, theta):")
            for r in rows:
                print(f"  {r}")
        conn.close()
except Exception as e:
    print(f"Local DB not accessible: {e}")
