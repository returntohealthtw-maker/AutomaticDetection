import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
content = open(r'D:\Write program\AutomaticDetection\後端系統\static-app\app_prototype.html', encoding='utf-8').read()
idx = content.find('function switchAdminTab')
# find end of function
end = content.find('\nfunction ', idx + 50)
print(content[idx:end][:3000])
