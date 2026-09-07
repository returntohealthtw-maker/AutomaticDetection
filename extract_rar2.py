import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Try extracting with unrar
try:
    import unrar.rarfile as urf
    rar_path = 'D:/Write program/AutomaticDetection/相關資料/演算法/BrainDNA.rar'
    dst = 'D:/Write program/AutomaticDetection/相關資料/_extracted/BrainDNA'
    os.makedirs(dst, exist_ok=True)
    with urf.RarFile(rar_path) as rf:
        rf.extractall(dst)
    print('Extracted with unrar.rarfile')
except Exception as e:
    print(f'unrar.rarfile failed: {e}')
    # Try patool
    try:
        import patoollib
        patoollib.extract_archive(rar_path, outdir=dst)
        print('Extracted with patool')
    except Exception as e2:
        print(f'patool failed: {e2}')
        # Try with subprocess calling unrar.exe or WinRAR
        import subprocess
        for exe in ['unrar', r'C:\Program Files\WinRAR\unrar.exe', r'C:\Program Files\WinRAR\WinRAR.exe']:
            try:
                r = subprocess.run([exe, 'x', '-y', rar_path, dst], capture_output=True, timeout=60)
                if r.returncode == 0:
                    print(f'Extracted with {exe}')
                    break
            except Exception as e3:
                print(f'{exe}: {e3}')
