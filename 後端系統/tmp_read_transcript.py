import json, sys

path = r"C:\Users\wayne\.cursor\projects\d-Write-program-AutomaticDetection\agent-transcripts\8d734878-e01e-4a26-8466-fb25f635a266\8d734878-e01e-4a26-8466-fb25f635a266.jsonl"

with open(path, encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")

# Read lines around 4800-4890 to see recent conversation
for i in range(max(0, len(lines)-90), len(lines)):
    line = lines[i]
    try:
        obj = json.loads(line)
        role = obj.get('role', '?')
        content = obj.get('content', '')
        text = ''
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            parts = []
            for c in content:
                if isinstance(c, dict) and c.get('type') == 'text':
                    parts.append(c.get('text', ''))
            text = ' '.join(parts)
        if text.strip() and len(text.strip()) > 10:
            print(f"\nL{i}[{role}]: {text[:500]}")
    except Exception as e:
        pass
