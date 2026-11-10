"""Hash table benchmarks: our HashTable (Robin Hood and plain linear) vs Python dict.

    python bench/bench_hashtable.py data/311_2025.csv          # real data
    python bench/bench_hashtable.py data/sample.csv --limit 200000

Writes results/hashtable_loadfactor.csv and results/hashtable_full.csv.
"""

import argparse
import csv
import os
import random
import statistics
import sys
import time
import tracemalloc

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from triage311.data import read_311  # noqa: E402
from triage311.hashtable import HashTable  # noqa: E402

REPEATS = 3


def timed(fn):
    best = float("inf")
    for _ in range(REPEATS):
        t0 = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - t0)
    return best


def run_ops(make, keys, missing, deletes):
    """Time insert / hit / miss / delete for a table factory. Returns seconds per op."""
    def ins():
        t = make()
        for k in keys:
            t[k] = k
        return t

    t_ins = timed(ins)
    table = ins()
    t_hit = timed(lambda: [table[k] for k in keys])
    t_miss = timed(lambda: [k in table for k in missing])

    def dele():
        t = ins()
        t0 = time.perf_counter()
        for k in deletes:
            del t[k]
        return time.perf_counter() - t0
    t_del = min(dele() for _ in range(REPEATS))
    n = len(keys)
    return table, t_ins / n, t_hit / n, t_miss / len(missing), t_del / len(deletes)


def memory_of(make, keys):
    tracemalloc.start()
    t = make()
    for k in keys:
        t[k] = k
    size, _ = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    del t
    return size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--cap-exp", type=int, default=18, help="table size 2^k for the load-factor sweep")
    args = ap.parse_args()
    os.makedirs("results", exist_ok=True)
    rng = random.Random(0)

    keys = [r["key"] for r in read_311(args.csv, args.limit)]
    keys = list(dict.fromkeys(keys))  # dedupe, keep order
    print(f"{len(keys):,} unique complaint keys")
    missing_all = [k + 10**12 if isinstance(k, int) else k + "_x" for k in keys]

    # ---- 1. load-factor sweep at a fixed capacity (no resizing during the run)
    cap = 2 ** args.cap_exp
    rows = []
    for lf in (0.5, 0.6, 0.7, 0.8, 0.9):
        n = int(cap * lf)
        if n > len(keys):
            print(f"skip lf={lf}: need {n} keys")
            continue
        sub = keys[:n]
        missing = missing_all[:20000]
        deletes = rng.sample(sub, min(20000, n))
        for name, make in [
            ("robin_hood", lambda: HashTable(cap, max_load=0.99, robin_hood=True)),
            ("linear", lambda: HashTable(cap, max_load=0.99, robin_hood=False)),
            ("dict", dict),
        ]:
            table, ti, th, tm, td = run_ops(make, sub, missing, deletes)
            if name == "dict":
                avg_p = max_p = p99 = ""
            else:
                pl = sorted(table.probe_lengths())
                avg_p, max_p, p99 = round(statistics.mean(pl), 3), pl[-1], pl[int(0.99 * len(pl))]
            rows.append([lf, name, n, ti * 1e9, th * 1e9, tm * 1e9, td * 1e9, avg_p, p99, max_p])
            print(f"lf={lf} {name:10} insert {ti*1e9:7.0f}ns  hit {th*1e9:6.0f}ns  "
                  f"miss {tm*1e9:6.0f}ns  del {td*1e9:6.0f}ns  avg probe {avg_p}  max {max_p}")
    with open("results/hashtable_loadfactor.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["load_factor", "impl", "n", "insert_ns", "hit_ns", "miss_ns", "delete_ns",
                    "avg_probe", "p99_probe", "max_probe"])
        w.writerows(rows)

    # ---- 2. full dataset with normal resizing, plus memory
    rows = []
    deletes = rng.sample(keys, min(50000, len(keys)))
    for name, make in [("robin_hood", lambda: HashTable()), ("linear", lambda: HashTable(robin_hood=False)),
                       ("dict", dict)]:
        _, ti, th, tm, td = run_ops(make, keys, missing_all[:50000], deletes)
        mem = memory_of(make, keys)
        rows.append([name, len(keys), ti * 1e9, th * 1e9, tm * 1e9, td * 1e9, mem / len(keys)])
        print(f"full {name:10} insert {ti*1e9:7.0f}ns  hit {th*1e9:6.0f}ns  miss {tm*1e9:6.0f}ns  "
              f"del {td*1e9:6.0f}ns  mem {mem/len(keys):6.1f} B/key")
    # ---- 3. why the mix step exists: sequential keys without mixing (small size, it gets slow)
    small = keys[:12000]
    miss = missing_all[:2000]
    for name, make in [("linear_mixed", lambda: HashTable(2**14, max_load=0.99, robin_hood=False)),
                       ("linear_unmixed", lambda: HashTable(2**14, max_load=0.99, robin_hood=False, mix=False)),
                       ("robin_hood_unmixed", lambda: HashTable(2**14, max_load=0.99, mix=False))]:
        _, ti, th, tm, td = run_ops(make, small, miss, small[:2000])
        rows.append([name, len(small), ti * 1e9, th * 1e9, tm * 1e9, td * 1e9, ""])
        print(f"no-mix test {name:18} insert {ti*1e9:7.0f}ns  hit {th*1e9:6.0f}ns  miss {tm*1e9:9.0f}ns")

    with open("results/hashtable_full.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["impl", "n", "insert_ns", "hit_ns", "miss_ns", "delete_ns", "bytes_per_key"])
        w.writerows(rows)


if __name__ == "__main__":
    main()
