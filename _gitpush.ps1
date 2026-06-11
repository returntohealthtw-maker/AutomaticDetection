$o = "d:\Write program\AutomaticDetection\_gitpush_result.txt"
$repo = "d:\Write program\AutomaticDetection"
Set-Location $repo
# 一併把 report-app 內的刪除（舊 hash 資產）也納入，確保 repo 乾淨
$appDir = Join-Path $repo "後端系統\static-app\report-app"
Set-Location $appDir
(git add -A .) 2>&1 | Out-Null
Set-Location $repo
"=== commit ===" | Set-Content $o
(git commit -m "fix(report-app): add Imagen quota circuit-breaker to avoid headless timeout on 429") 2>&1 | Add-Content $o
"=== push ===" | Add-Content $o
(git push origin master) 2>&1 | Add-Content $o
"DONE" | Add-Content $o
