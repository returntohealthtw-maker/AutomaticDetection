$o = "d:\Write program\AutomaticDetection\_gitcheck_result.txt"
Set-Location "d:\Write program\AutomaticDetection"
"=== status report-app ===" | Set-Content $o
(git -c core.quotepath=false status --short -- "後端系統/static-app/report-app") 2>&1 | Add-Content $o
"=== status geminiService ===" | Add-Content $o
(git -c core.quotepath=false status --short -- "_reports_review/adult/services/geminiService.ts") 2>&1 | Add-Content $o
"=== ls-files report-app index.html ===" | Add-Content $o
(git ls-files -- "後端系統/static-app/report-app/index.html") 2>&1 | Add-Content $o
"=== ls-files geminiService ===" | Add-Content $o
(git ls-files -- "_reports_review/adult/services/geminiService.ts") 2>&1 | Add-Content $o
"=== check ignore geminiService ===" | Add-Content $o
(git check-ignore -v "_reports_review/adult/services/geminiService.ts") 2>&1 | Add-Content $o
"DONE" | Add-Content $o
