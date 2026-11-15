# Live demo script (about 5 minutes)

## Before class

1. Open VS Code in `N:\projects\triage311`, open a terminal, make the font large.
2. Open `triage311/hashtable.py` and `triage311/indexed_heap.py` in tabs.
3. Start the demo 1 minute early. Loading takes about 40 seconds:

```powershell
.venv\Scripts\python.exe -m triage311.cli data\311_2025q3.csv --at "2025-08-15 18:00"
```

Backup if the big file is slow or missing (loads in 3 seconds):

```powershell
.venv\Scripts\python.exe scripts\make_sample.py data\sample.csv 60000
.venv\Scripts\python.exe -m triage311.cli data\sample.csv --at "2025-07-05 18:00"
```

## The run

| Step | Type this | What to say |
|---|---|---|
| 1 | (startup lines) | "922,606 real NYC 311 complaints from Q3 2025 are now in my hash table. It replayed 463k openings and 402k closures in time order, so the heap holds the 61,078 complaints open on Aug 15 at 6 pm." |
| 2 | In a second terminal: `.venv\Scripts\python.exe -m pytest -q` | "51 tests. The property tests run random operation sequences against dict and heapq, and a mutation check confirms the tests fail when I break the code." |
| 3 | `next 10` | "The 10 most urgent open complaints. Weight first, then oldest. This does not pop anything: it walks the heap from the root with a small second heap, O(k log k)." |
| 4 | `escalate <ID of #10>` | "This complaint escalates. Its weight goes from 8 to 11." |
| 5 | `next 3` | "It is now #1. That was one update: the position map found its index in O(1), then sift-up in O(log n). heapq cannot do this." |
| 6 | `close <same ID>` then `next 3` | "Closed. It is removed from the middle of the heap in O(log n), and the queue is back to how it was." |
| 7 | `lookup <same ID>` | "The record is still in the hash table, marked closed. About 0.02 ms." |
| 8 | `lookup 999` | "A missing key. Robin Hood stops as soon as it meets an entry closer to home than the search." |
| 9 | `count 11201 Noise - Residential` | "Counts use a tuple key, (ZIP, type), in the same hash table. 1,178 for Downtown Brooklyn." |
| 10 | `stats` | "Average probe distance about 0.4 at load 0.44. The formula for linear probing predicts 0.39." |
| 11 | open `results/probe_quality.png`, `results/heap_replay.png` and `results/scaling.png` | "Two findings: my first mix step was 2x worse than theory on real keys, splitmix64 fixed it. And heapq is faster, but its array grows to 52x the size of mine under updates." |

## Questions to expect

**Why Robin Hood instead of plain linear probing?**
Same average probe length, much smaller worst case. At load 0.9: longest probe 41 vs 833, and failed lookups are 5x faster. A failed lookup can stop early, because if the key were present it would have displaced any entry that is closer to its home slot.

**Why does a lookup stop early? Show the line.**
`_find_slot` in `hashtable.py`: `if self._robin_hood and dist[i] < d: return -1`. `d` is how far the search has travelled, `dist[i]` is how far the resident is from its home. Insert never leaves a "richer" entry in front of a "poorer" one, so the key cannot be further on.

**How do you delete without tombstones?**
Backward shift: after removing an entry, move each following entry back one slot until an empty slot or an entry with distance 0. Every moved entry gets one step closer to home, so the invariant holds.

**Why the mix step?**
In Python `hash(n) == n` for ints, and 311 keys are increasing integers. Masked directly, they fill long runs of neighbouring slots. splitmix64 makes the low bits look random. With it, measured probe lengths match the formula ½(1/(1−α) − 1) within 1%.

**How is `update` O(log n)?**
The position map (my own HashTable) stores key → index in the heap array, and every swap updates it. So finding the entry is O(1), and then it sifts up or down at most log n levels.

**Why is dict 27x faster if both are O(1)?**
Constant factors. dict is C: a lookup is a few machine instructions. Mine runs Python bytecode for every probe step. The shape of the curves is the same; the constant is not.

**Why is heapq faster than your heap?**
It is C, and it does no position-map writes. Every swap in mine does two hash table writes of about 1 µs each. The trade is memory and features: mine stays at about 87k entries, lazy deletion reaches 4.5 million at 4 escalations per complaint.

**Why resize at 0.85?**
Probe lengths are still short there with Robin Hood (about 3 on average), but deletes get expensive past 0.8–0.9 because whole clusters shift.

**Why a heap and not a balanced tree?**
The system needs min, update and delete, never ordered range queries. A heap does those with a flat array and far less code.

**How do you know it is really O(1) and O(log n)?**
`bench/scaling.py`. At a fixed load of 0.7 the probe count stays at about 1.17 from 2,867 keys to 734,003 keys. Heap pops take log2(n) minus about 1.7 swaps at every size, counted, not timed. Pushes average about one swap, because most new entries stop near the bottom.

**Then why does lookup time still rise with n?**
Same number of probes, but each one is slower: the arrays of a million-slot table are about 32 MB, bigger than the 12 MB L3 cache, and probes land at random addresses. I did not measure cache misses, so that is the likely cause, not a proven one.

**How do you know your tests are any good?**
`scripts/mutation_check.py` breaks 16 lines one at a time. The first run missed one: `remove()` without the sift-up. I added a seven-entry heap test that forces that case; now all 16 are caught.

**What did AI write?**
It helped draft code, tests and the report. I reviewed and ran everything, and the disclosure is in the report and commit messages. (Be ready to walk through any function line by line.)
