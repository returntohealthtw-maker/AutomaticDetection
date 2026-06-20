"""
Fix: rename our injected 'a6' function to '_chk5da' to avoid conflict
with the existing 'a6' variable (SVG arc data) already in the bundle.
"""
import pathlib, re

p = pathlib.Path(__file__).parent / "static-app/report-app/assets/index-CqHWGLJp.js"
t = p.read_text(encoding="utf-8")

# Verify the conflict: our function a6 vs existing a6 object
our_fn = "function a6(a){return!!a&&"
if our_fn not in t:
    print("ERROR: our function a6 not found!")
else:
    print(f"Found our function a6 at pos={t.find(our_fn)}")

existing_a6 = "a6={arc:"
if existing_a6 not in t:
    print("WARNING: existing a6 arc not found (may have different encoding)")
else:
    print(f"Found existing a6 arc at pos={t.find(existing_a6)}")

# Check that _chk5da is not already in the bundle
new_name = "_chk5da"
if new_name in t:
    print(f"ERROR: {new_name} already exists in bundle!")
else:
    print(f"Safe to use name: {new_name}")

# Rename: function a6(...) -> function _chk5da(...)
# And all call sites: a6(G) -> _chk5da(G)
patches = [
    # Rename function declaration
    ("function a6(a){return!!a&&", f"function {new_name}(a){{return!!a&&"),
    # Rename call sites in retry loop: (!x||a6(G))
    ("(!x||a6(G))", f"(!x||{new_name}(G))"),
    # Rename call site in post-retry check: if(x&&G&&!a6(G))
    ("if(x&&G&&!a6(G))", f"if(x&&G&&!{new_name}(G))"),
]

for old, new in patches:
    if old not in t:
        print(f"MISSING patch target: {old[:60]}")
    else:
        count = t.count(old)
        t = t.replace(old, new)
        print(f"OK: replaced {count}x '{old[:50]}' -> '{new[:50]}'")

p.write_text(t, encoding="utf-8")
print("\nDone. Verifying no 'function a6' remains:")
if "function a6(" in t:
    print("  ERROR: still has function a6!")
else:
    print("  OK: no 'function a6' declaration")
print(f"  New function name '{new_name}' count: {t.count(new_name)}")
