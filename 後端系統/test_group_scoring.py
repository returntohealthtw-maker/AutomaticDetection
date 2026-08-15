"""Quick test for the new group-scoring MBTI algorithm."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))
sys.path.insert(0, os.path.dirname(__file__))

from app.services.algorithms import (
    compute_mbti_group_scoring,
    build_mbti_payload,
    compute_averages,
    _calc_mind_color,
    _calc_personality_from_bagua_color,
    PERSONALITY_GROUPS,
    _MC_ORANGE, _MC_GREEN, _MC_BLUE, _MC_YELLOW,
)

def make_capture(la, th, ha=30, hb=25, lb=20, lg=15, hg=10):
    return {
        "low_alpha": la, "theta": th,
        "high_alpha": ha, "high_beta": hb, "low_beta": lb,
        "low_gamma": lg, "high_gamma": hg,
        "good_signal": 0,
    }

# ── Test 1: MindColor calculation ──────────────────────────────
print("=== Test 1: MindColor ===")
color_names = {0: "ORANGE", 1: "GREEN", 2: "BLUE", 3: "YELLOW"}
# All equal bands → should be some color
c = _calc_mind_color(30, 30, 25, 20, 15, 10)
print(f"  Equal bands → {color_names[c]}")

# Very high gamma → BLUE
c = _calc_mind_color(10, 10, 5, 5, 80, 80)
print(f"  High gamma  → {color_names[c]}  (expect BLUE)")

# Very low gamma → YELLOW or GREEN
c = _calc_mind_color(50, 50, 30, 30, 2, 2)
print(f"  Low gamma   → {color_names[c]}  (expect YELLOW or GREEN)")

# ── Test 2: Personality from bagua + color ──────────────────────
print("\n=== Test 2: calcPersonality ===")
# Bagua 0 (乾), GREEN → ENTJ
t = _calc_personality_from_bagua_color(0, False, _MC_GREEN, 50, 30)
print(f"  QIAN + GREEN → {t}  (expect ENTJ)")
t = _calc_personality_from_bagua_color(0, False, _MC_BLUE, 50, 30)
print(f"  QIAN + BLUE  → {t}  (expect ESTJ)")
# Bagua 2 (LI active), BLUE → ENFJ
t = _calc_personality_from_bagua_color(2, True, _MC_BLUE, 40, 50)
print(f"  LI  + BLUE   → {t}  (expect ENFJ)")
# Bagua 4 (坎), GREEN → INTP
t = _calc_personality_from_bagua_color(4, False, _MC_GREEN, 40, 60)
print(f"  KAN + GREEN  → {t}  (expect INTP)")

# ── Test 3: Group scoring with consistent data ──────────────────
print("\n=== Test 3: Group scoring (consistent ISTJ data) ===")
captures = [make_capture(la=35, th=45) for _ in range(30)]
profiles = compute_mbti_group_scoring(captures)
print(f"  Profiles: {profiles[:6]}")

# ── Test 4: Group scoring with real-ish data ───────────────────
print("\n=== Test 4: Group scoring (varied data) ===")
import random
random.seed(42)
captures2 = []
for _ in range(60):
    la = random.uniform(20, 80)
    th = random.uniform(15, 70)
    ha = random.uniform(10, 50)
    hb = random.uniform(10, 40)
    lb = random.uniform(8, 35)
    lg = random.uniform(5, 30)
    hg = random.uniform(5, 25)
    captures2.append(make_capture(la, th, ha, hb, lb, lg, hg))

profiles2 = compute_mbti_group_scoring(captures2)
print(f"  Profiles: {profiles2[:6]}")

# ── Test 5: build_mbti_payload ────────────────────────────────
print("\n=== Test 5: build_mbti_payload ===")
avg = compute_averages(captures2)
payload = build_mbti_payload(avg, captures2)
print(f"  Primary:     {payload['mbti_primary']}")
print(f"  Secondaries: {[s['mbti'] for s in payload['mbti_secondaries']]}")
print(f"  Profiles[0:5]: {[(p['type'], p['pct']) for p in payload['mbti_profiles'][:5]]}")

# ── Test 6: PERSONALITY_GROUPS coverage ───────────────────────
print("\n=== Test 6: PERSONALITY_GROUPS ===")
all_in_groups = set(t for grp in PERSONALITY_GROUPS for t in grp)
all_16 = {"INTJ","INTP","ENTJ","ENTP","INFJ","INFP","ENFJ","ENFP",
          "ISTJ","ISFJ","ESTJ","ESFJ","ISTP","ISFP","ESTP","ESFP"}
missing = all_16 - all_in_groups
extra   = all_in_groups - all_16
print(f"  Missing: {missing or 'None'}")
print(f"  Extra:   {extra   or 'None'}")
print(f"  OK: {not missing and not extra}")
