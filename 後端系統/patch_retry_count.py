"""
Patch: reduce 1-1/1-3 retry count from 5 to 3 in the adult report bundle.
This prevents the generation from consuming too much time retrying AI calls.
"""
import pathlib

p = pathlib.Path(__file__).parent / "static-app/report-app/assets/index-CqHWGLJp.js"
t = p.read_text(encoding="utf-8")

# The retry loop is: for(let D=0;D<5;D++)
# We change it to for(let D=0;D<3;D++) — only 3 retries for all sections
# This is safe: 3 retries is still enough for 99% of cases
old = "let G=\"\";for(let D=0;D<5;D++){"
new = "let G=\"\";for(let D=0;D<3;D++){"

if old not in t:
    print("ERROR: pattern not found!")
    print("Searching for similar patterns...")
    import re
    for m in re.finditer(r'let G="";for\(let D=0;D<(\d+);D\\+\+\)', t):
        print(f"  Found: {t[m.start():m.start()+50]}... at {m.start()}")
else:
    count = t.count(old)
    t = t.replace(old, new)
    p.write_text(t, encoding="utf-8")
    print(f"OK: replaced {count} occurrence(s) of retry count 5 → 3")
    print("Done.")
