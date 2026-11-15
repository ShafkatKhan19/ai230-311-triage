# Runs every benchmark on the real data and regenerates the plots.
#   powershell -ExecutionPolicy Bypass -File bench\run_all.ps1
# Logs are written as UTF-8 so they read correctly on GitHub.
Set-Location (Split-Path $PSScriptRoot -Parent)
$py = ".\.venv\Scripts\python.exe"
$data = "data\311_2025q3.csv"
New-Item -ItemType Directory -Force results | Out-Null
& $py -u bench\probe_quality.py $data 2>&1 | Out-File -Encoding utf8 results\probe_quality.log
& $py -u bench\bench_hashtable.py $data --cap-exp 19 2>&1 | Out-File -Encoding utf8 results\bench_hashtable.log
& $py -u bench\bench_heap.py $data --limit 1000000 2>&1 | Out-File -Encoding utf8 results\bench_heap.log
& $py -u bench\scaling.py $data 2>&1 | Out-File -Encoding utf8 results\scaling.log
& $py bench\plots.py 2>&1 | Out-File -Encoding utf8 results\plots.log
"ALL DONE" | Out-File -Encoding utf8 results\done.txt
