# Runs every benchmark on the real data and regenerates the plots.
#   powershell -ExecutionPolicy Bypass -File bench\run_all.ps1
Set-Location (Split-Path $PSScriptRoot -Parent)
$py = ".\.venv\Scripts\python.exe"
$data = "data\311_2025q3.csv"
New-Item -ItemType Directory -Force results | Out-Null
& $py -u bench\probe_quality.py $data *> results\probe_quality.log
& $py -u bench\bench_hashtable.py $data --cap-exp 19 *> results\bench_hashtable.log
& $py -u bench\bench_heap.py $data --limit 1000000 *> results\bench_heap.log
& $py bench\plots.py *> results\plots.log
"ALL DONE" | Out-File results\done.txt
