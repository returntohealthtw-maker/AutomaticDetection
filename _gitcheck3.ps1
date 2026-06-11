$o = "d:\Write program\AutomaticDetection\_gitcheck3_result.txt"
Set-Location "d:\Write program\AutomaticDetection"
$all = git ls-files
"TOTAL_TRACKED: $($all.Count)" | Set-Content $o
$reportApp = $all | Where-Object { $_ -match "report-app" }
"MATCH report-app: $($reportApp.Count)" | Add-Content $o
($reportApp | Select-Object -First 15) | Add-Content $o
$staticApp = $all | Where-Object { $_ -match "static-app" }
"MATCH static-app: $($staticApp.Count)" | Add-Content $o
($staticApp | Select-Object -First 10) | Add-Content $o
"=== HEAD commit for report-app index.html (by substring via log --all) ===" | Add-Content $o
(git log --oneline -5) 2>&1 | Add-Content $o
"DONE" | Add-Content $o
