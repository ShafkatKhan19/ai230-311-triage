# 311 Triage Engine — AI 230 Project 2: Data Structures in Practice

A hash table and an indexed priority queue built from scratch, applied to NYC 311 service requests.
The engine stores every complaint, answers lookups and per-ZIP counts, and keeps all open
complaints ordered by urgency. When a complaint escalates or closes, it is updated or removed in O(log n).

## What's built (no library data structures)

| File | What it is |
|---|---|
| `triage311/hashtable.py` | Open-addressing hash table. Robin Hood probing with backward-shift deletion (default), or plain linear probing with Knuth deletion. splitmix64 mix step (Fibonacci and no-mix kept as options for comparison). Power-of-two capacity, resize at load 0.85. |
| `triage311/indexed_heap.py` | Binary min-heap plus a position map (our own `HashTable`), giving `push`, `pop`, `peek`, `update`, `remove` and `smallest(k)`. |
| `triage311/engine.py` | Triage engine: records, (ZIP, type) counts, urgency weights, open-complaint queue, timeline replay. |
| `triage311/data.py` | Loader for both 311 CSV formats (website export and SODA API). |
| `triage311/cli.py` | Live demo. |
| `tests/` | pytest unit tests plus hypothesis property tests that check against `dict` and `heapq`. |
| `bench/` | Benchmarks vs built-ins, probe-length check vs theory, plots. `bench/run_all.ps1` runs everything. |
| `results/` | Raw CSVs, logs and plots from the real-data run. |
| `report/` | Written report (docx and pdf). |

## Setup

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest -q
```

## Get the data (NYC Open Data, dataset erm2-nwe9)

Pull one quarter (about 800k–900k rows) through the API:

```bash
mkdir -p data
curl -G "https://data.cityofnewyork.us/resource/erm2-nwe9.csv" \
  --data-urlencode "\$select=unique_key,created_date,closed_date,complaint_type,descriptor,incident_zip,borough,status" \
  --data-urlencode "\$where=created_date between '2025-07-01T00:00:00' and '2025-09-30T23:59:59'" \
  --data-urlencode "\$limit=2000000" -o data/311_2025q3.csv
```

The website export from https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2010-to-Present/erm2-nwe9 also works.
`scripts/make_sample.py` makes a synthetic file in the same format, for development only.

## Run

```bash
python -m triage311.cli data/311_2025q3.csv --at "2025-08-15 18:00"
#   next 10 | lookup <id> | escalate <id> | close <id> | count 11201 HEAT/HOT WATER | stats | quit

powershell -ExecutionPolicy Bypass -File bench\run_all.ps1   # all benchmarks + plots, about 25 min
```

## Key results (922,606 real complaints, Q3 2025)

- With the splitmix64 mix, average probe length matches the linear-probing theory within 1% at load 0.5-0.9. The first Fibonacci mix was 1.6-2x above it.
- At load 0.9, Robin Hood misses are 5x faster than plain linear probing, and the worst case is 41 vs 833 slots.
- dict is about 27x faster on lookups (C vs Python); both are O(1).
- heapq with lazy deletion is 3.3-9.6x faster, but its array grows to 52x the size of the indexed heap at 4 escalations per complaint.

Full analysis: `report/AI230_Project2_Report_Shafkat.pdf`.

## AI use disclosure
Parts of this code were drafted with an AI assistant (Claude) and then reviewed, tested and modified by me.
I can explain every function. See the report for details.
