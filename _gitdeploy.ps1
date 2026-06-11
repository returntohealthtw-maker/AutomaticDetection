$o = "d:\Write program\AutomaticDetection\_gitdeploy_result.txt"
$repo = "d:\Write program\AutomaticDetection"
$appDir = Join-Path $repo "後端系統\static-app\report-app"
"=== staging report-app from inside dir ===" | Set-Content $o
Set-Location $appDir
(git add -A .) 2>&1 | Add-Content $o
Set-Location $repo
"=== staged changes under report-app ===" | Add-Content $o
(git -c core.quotepath=false diff --cached --stat) 2>&1 | Add-Content $o
"DONE_STAGE" | Add-Content $o
