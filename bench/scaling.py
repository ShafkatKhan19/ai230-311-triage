"""Growth with n: does the cost per operation follow the predicted complexity?

1. Hash table at a fixed load factor of 0.7, capacity 2^12 .. 2^20.
   Theory: probes per lookup depend only on the load factor, so they stay flat as n grows.
2. Indexed heap with n = 2^12 .. 2^19 and the full file: push every complaint, then pop every one.
   Swaps are counted, so that part of the result does not depend on the machine.
   Theory: at most floor(log2 n) swaps per pop; pushes are O(log n) worst case.
3. The reason the mix step exists: sequential integer keys with and without mixing.

    python bench/scaling.py data/311_2025q3.csv
Writes results/scaling_hash.csv, results/scaling_heap.csv, results/unmixed_sequential.csv
and results/scaling.png.
"""

import argparse
import csv
import math
import os
import random
import statistics
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from triage311.data import read_311  # noqa: E402
from triage311.engine import TYPE_WEIGHT  # noqa: E402
from triage311.hashtable import HashTable  # noqa: E402
from triage311.indexed_heap import IndexedMinHeap  # noqa: E402

REPEATS = 3
LOAD = 0.7
SAMPLE = 20_000


def best_ns(fn, n_ops):
    best = float("inf")
    for _ in range(REPEATS):
        t0 = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - t0)
    return best / n_ops * 1e9


class CountingHeap(IndexedMinHeap):
    """Same heap, but counts swaps. Used only for the operation counts, never for timing."""

    swaps = 0

    def _swap(self, i, j):
        self.swaps += 1
        super()._swap(i, j)


def hash_scaling(keys, rng):
    rows = []
    for exp in range(12, 21):
        cap = 2 ** exp
        n = int(cap * LOAD)
        if n > len(keys):
            break
        table = HashTable(cap, max_load=0.99)
        for k in keys[:n]:
            table[k] = k
        hits = rng.sample(keys[:n], min(SAMPLE, n))
        misses = [k + 10**12 for k in hits]
        hit_ns = best_ns(lambda: [table[k] for k in hits], len(hits))
        miss_ns = best_ns(lambda: [k in table for k in misses], len(misses))
        ref = dict.fromkeys(keys[:n])
        dict_ns = best_ns(lambda: [ref[k] for k in hits], len(hits))
        avg_probe = statistics.mean(table.probe_lengths())
        rows.append([n, cap, round(avg_probe, 3), round(hit_ns, 1), round(miss_ns, 1), round(dict_ns, 1)])
        print(f"hash n={n:>8,} avg probe {avg_probe:5.3f}  hit {hit_ns:6.0f}ns  miss {miss_ns:6.0f}ns  dict {dict_ns:4.0f}ns")
    return rows


def heap_scaling(records):
    rows = []
    sizes = [2 ** e for e in range(12, 20) if 2 ** e <= len(records)]
    if len(records) not in sizes:
        sizes.append(len(records))
    for n in sizes:
        items = [(r["key"], (-TYPE_WEIGHT.get(r["type"], 1), r["created"], r["key"])) for r in records[:n]]
        # pass 1: count swaps
        h = CountingHeap()
        for key, pr in items:
            h.push(key, pr)
        push_swaps = h.swaps
        h.swaps = 0
        while h:
            h.pop()
        pop_swaps = h.swaps
        # pass 2: time the plain heap (single run; a full push-and-pop pass is long)
        h = IndexedMinHeap()
        t0 = time.perf_counter()
        for key, pr in items:
            h.push(key, pr)
        t1 = time.perf_counter()
        while h:
            h.pop()
        t2 = time.perf_counter()
        rows.append([n, round(math.log2(n), 2), round(push_swaps / n, 3), round(pop_swaps / n, 3),
                     round((t1 - t0) / n * 1e9), round((t2 - t1) / n * 1e9)])
        print(f"heap n={n:>8,} log2 n {math.log2(n):5.2f}  swaps/push {push_swaps / n:5.2f}  "
              f"swaps/pop {pop_swaps / n:5.2f}  push {(t1 - t0) / n * 1e9:6.0f}ns  pop {(t2 - t1) / n * 1e9:6.0f}ns")
    return rows


def unmixed_sequential():
    """12,000 consecutive integers in a 16,384-slot table, plain linear probing."""
    keys = list(range(65_000_000, 65_012_000))
    misses = [k + 10**12 for k in keys[:2000]]
    rows = []
    for name, kwargs in (("linear, splitmix", dict(robin_hood=False)),
                         ("linear, no mix", dict(robin_hood=False, mix=None)),
                         ("robin hood, no mix", dict(mix=None))):
        t = HashTable(2 ** 14, max_load=0.99, **kwargs)
        for k in keys:
            t[k] = k
        miss_ns = best_ns(lambda: [k in t for k in misses], len(misses))
        rows.append([name, len(keys), round(miss_ns), max(t.probe_lengths())])
        print(f"sequential keys, {name:18} miss {miss_ns:10.0f}ns  max probe {max(t.probe_lengths())}")
    return rows


def write(path, header, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def plot(hash_rows, heap_rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    n = [r[0] for r in hash_rows]
    axes[0].plot(n, [r[2] for r in hash_rows], "o-", label="measured")
    axes[0].axhline(0.5 * (1 / (1 - LOAD) - 1), color="k", ls="--", label="theory (depends on load only)")
    axes[0].set(title=f"Hash table: probes per lookup at load {LOAD}", xlabel="n (keys)", ylabel="extra probes",
                xscale="log", ylim=(0, 2))
    axes[1].plot(n, [r[3] for r in hash_rows], "o-", label="HashTable hit")
    axes[1].plot(n, [r[4] for r in hash_rows], "s-", label="HashTable miss")
    axes[1].plot(n, [r[5] for r in hash_rows], "^--", label="dict hit")
    axes[1].set(title=f"Hash table: time per lookup at load {LOAD}", xlabel="n (keys)", ylabel="ns per lookup",
                xscale="log", yscale="log")
    hn = [r[0] for r in heap_rows]
    axes[2].plot(hn, [r[1] for r in heap_rows], "k--", label="log2 n (upper bound)")
    axes[2].plot(hn, [r[3] for r in heap_rows], "o-", label="swaps per pop")
    axes[2].plot(hn, [r[2] for r in heap_rows], "s-", label="swaps per push")
    axes[2].set(title="Indexed heap: swaps per operation", xlabel="n (complaints)", ylabel="swaps", xscale="log")
    for a in axes:
        a.legend()
        a.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig("results/scaling.png", dpi=150)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    args = ap.parse_args()
    os.makedirs("results", exist_ok=True)

    seen = HashTable()
    records = []
    for r in read_311(args.csv):
        if r["key"] not in seen:
            seen[r["key"]] = True
            records.append(r)
    keys = [r["key"] for r in records]
    print(f"{len(records):,} complaints")

    hash_rows = hash_scaling(keys, random.Random(0))
    write("results/scaling_hash.csv", ["n", "capacity", "avg_probe", "hit_ns", "miss_ns", "dict_hit_ns"], hash_rows)
    heap_rows = heap_scaling(records)
    write("results/scaling_heap.csv", ["n", "log2_n", "swaps_per_push", "swaps_per_pop", "push_ns", "pop_ns"],
          heap_rows)
    write("results/unmixed_sequential.csv", ["table", "n", "miss_ns", "max_probe"], unmixed_sequential())
    plot(hash_rows, heap_rows)
    print("wrote results/scaling_*.csv, results/unmixed_sequential.csv, results/scaling.png")


if __name__ == "__main__":
    main()
