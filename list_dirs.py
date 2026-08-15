import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
root = 'D:/Write program/AutomaticDetection'
for item in os.listdir(root):
    print(item)
    if os.path.isdir(os.path.join(root, item)):
        try:
            for sub in os.listdir(os.path.join(root, item)):
                print(f'  {sub}')
        except:
            pass
