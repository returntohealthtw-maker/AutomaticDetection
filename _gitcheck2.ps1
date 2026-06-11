$o = "d:\Write program\AutomaticDetection\_gitcheck2_result.txt"
Set-Location "d:\Write program\AutomaticDetection"
"=== tracked files under static-app (count) ===" | Set-Content $o
$tracked = git ls-files -- "後端系統/static-app"
"TRACKED_COUNT: $($tracked.Count)" | Add-Content $o
($tracked | Select-Object -First 30) | Add-Content $o
"=== check-ignore report-app ===" | Add-Content $o
(git check-ignore -v "後端系統/static-app/report-app/index.html") 2>&1 | Add-Content $o
"=== check-ignore child-report-app ===" | Add-Content $o
(git check-ignore -v "後端系統/static-app/child-report-app/index.html") 2>&1 | Add-Content $o
"=== git log for report-app (last 3) ===" | Add-Content $o
(git log --oneline -3 -- "後端系統/static-app/report-app") 2>&1 | Add-Content $o
"=== .gitignore lines mentioning static or report ===" | Add-Content $o
(Select-String -Path ".gitignore" -Pattern "static|report|dist|_reports" | ForEach-Object { "$($_.LineNumber): $($_.Line)" }) | Add-Content $o
"DONE" | Add-Content $o
