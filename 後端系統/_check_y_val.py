import subprocess, re, sys

commits = [
    ("a367986", "後端系統/static-app/report-app/assets/index-YiNJp2m1.js"),
    ("a4be3de", "後端系統/static-app/report-app/assets/index-BRhOh-TR.js"),
    ("f553610", "後端系統/static-app/report-app/assets/index-C7o2fWH6.js"),
    ("f10afe1", "後端系統/static-app/report-app/assets/index-CqHWGLJp.js"),
]

for commit, path in commits:
    try:
        out = subprocess.check_output(
            ["git", "show", f"{commit}:{path}"],
            cwd="D:/Write program/AutomaticDetection",
            timeout=20
        ).decode("utf-8", errors="replace")
        # Find y=x? pattern
        m = re.search(r'y=x\?(\d+):m\?(\d+):(\d+)', out)
        if m:
            print(f"{commit[:7]} | y=x?{m.group(1)}:m?{m.group(2)}:{m.group(3)}")
        else:
            print(f"{commit[:7]} | pattern not found")
    except Exception as e:
        print(f"{commit[:7]} | error: {e}")
