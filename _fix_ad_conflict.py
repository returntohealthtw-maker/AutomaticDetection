import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
js_path = r'D:\Write program\AutomaticDetection\後端系統\static-app\child-report-app\assets\index-sYBW65kC.js'
with open(js_path, encoding='utf-8', errors='replace') as f:
    content = f.read()

# 修正 1：const Ad=[...] -> const _xAdCh=[...]
old1 = 'const Ad=[{title:"\u8166\u6ce2\u6578\u64da\u4e0b\u7684\u771f\u5be6\u81ea\u6211"'
new1 = 'const _xAdCh=[{title:"\u8166\u6ce2\u6578\u64da\u4e0b\u7684\u771f\u5be6\u81ea\u6211"'
c1 = content.count(old1)
print(f'const Ad 宣告: {c1} 處')

# 修正 2：return Ad; -> return _xAdCh;
old2 = 'return Ad;if(a.institution'
new2 = 'return _xAdCh;if(a.institution'
c2 = content.count(old2)
print(f'return Ad: {c2} 處')

if c1 != 1 or c2 != 1:
    print('ERROR: 匹配數量不對，停止')
    exit(1)

content2 = content.replace(old1, new1, 1).replace(old2, new2, 1)
with open(js_path, 'w', encoding='utf-8', errors='replace') as f:
    f.write(content2)
print('完成：const Ad -> const _xAdCh，return Ad -> return _xAdCh')

# 驗證
with open(js_path, encoding='utf-8', errors='replace') as f:
    v = f.read()
import re
decls = re.findall(r'\bconst _xAdCh\b', v)
rets = re.findall(r'return _xAdCh\b', v)
print(f'驗證 _xAdCh 宣告: {len(decls)} 處，return: {len(rets)} 處')
# 確認 const Ad 只剩 lib 的那個
orig = re.findall(r'\bconst Ad\b', v)
print(f'驗證剩餘 const Ad: {len(orig)} 處（應為0，lib 的用逗號分隔不是獨立 const）')
