import subprocess, re

commits = [
    ("a367986", "後端系統/static-app/report-app/assets/index-YiNJp2m1.js"),
    ("a4be3de", "後端系統/static-app/report-app/assets/index-BRhOh-TR.js"),
]

for commit, path in commits:
    try:
        out = subprocess.check_output(
            ["git", "show", f"{commit}:{path}"],
            cwd="D:/Write program/AutomaticDetection",
            timeout=30
        ).decode("utf-8", errors="replace")
        # Try different patterns
        patterns = [
            r'y=x\?(\d+)',
            r'minLen.*?(\d+)',
            r'length.*>=.*?(\d+)',
            r'G\.length',
            r'字數',
            r'1400|1500|9999|0:m|0,m',
        ]
        for p in patterns:
            m = re.search(p, out)
            if m:
                start = max(0, m.start()-30)
                end = min(len(out), m.end()+80)
                print(f"{commit[:7]} | pattern '{p}' -> ...{out[start:end]}...")
                break
        else:
            print(f"{commit[:7]} | NO matching pattern found")
    except Exception as e:
        print(f"{commit[:7]} | error: {e}")
