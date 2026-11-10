"""Priority queue benchmark on a replay of the 311 timeline.

Our IndexedMinHeap (true update/remove) vs heapq with lazy deletion
(the standard workaround: push a new entry on every change, skip stale ones on pop).

Workload, in time order: every complaint is opened, receives `esc` escalations
on average, and is closed when its Closed Date arrives. Every 100 events a
dispatcher pops the most urgent complaint (as a crew taking the next job).

    python bench/bench_heap.py data/311_2025.csv
Writes results/heap_replay.csv.
"""

import argparse
import csv
import heapq
import os
import random
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from triage311.data import read_311  # noqa: E402
from triage311.engine import TYPE_WEIGHT  # noqa: E402
from triage311.indexed_heap import IndexedMinHeap  # noqa: E402


class LazyHeapq:
    """heapq + dict of live priorities. update/remove are O(log n) pushes or O(1)
    marks, but stale entries stay in the array until they reach the top."""

    def __init__(self):
        self.h = []
        self.live = {}
        self.peak = 0
        self.stale_popped = 0

    def push(self, key, pr):
        self.live[key] = pr
        heapq.heappush(self.h, (pr, key))
        if len(self.h) > self.peak:
            self.peak = len(self.h)

    update = push

    def remove(self, key):
        del self.live[key]

    def __contains__(self, key):
        return key in self.live

    def __len__(self):
        return len(self.live)

    def pop(self):
        while self.h:
            pr, key = heapq.heappop(self.h)
            if self.live.get(key) == pr:
                del self.live[key]
                return key, pr
            self.stale_popped += 1
        raise IndexError("pop from empty heap")


class Indexed:
    def __init__(self):
        self.q = IndexedMinHeap()
        self.peak = 0
        self.stale_popped = 0

    def push(self, key, pr):
        self.q.push(key, pr)
        if len(self.q) > self.peak:
            self.peak = len(self.q)

    def update(self, key, pr):
        self.q.update(key, pr)

    def remove(self, key):
        self.q.remove(key)

    def __contains__(self, key):
        return key in self.q

    def __len__(self):
        return len(self.q)

    def pop(self):
        return self.q.pop()


def build_events(records, esc, rng):
    events = []
    for r in records:
        events.append((r["created"], 0, r["key"]))
        n_esc = int(esc) + (1 if rng.random() < esc - int(esc) else 0)
        end = r["closed"] if r["closed"] and r["closed"] > r["created"] else None
        for _ in range(n_esc):
            if end:
                t = r["created"] + (end - r["created"]) * rng.random()
            else:
                t = r["created"]
            events.append((t, 1, r["key"]))
        if end:
            events.append((end, 2, r["key"]))
    events.sort()
    return events


def run(impl, events, base_weight, created):
    weight = {}
    pops = 0
    t0 = time.perf_counter()
    for i, (_, kind, key) in enumerate(events):
        if kind == 0:
            weight[key] = base_weight[key]
            impl.push(key, (-weight[key], created[key], key))
        elif key in impl:
            if kind == 1:
                weight[key] += 3
                impl.update(key, (-weight[key], created[key], key))
            else:
                impl.remove(key)
        if i % 100 == 99 and len(impl):
            impl.pop()
            pops += 1
    return time.perf_counter() - t0, pops


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--limit", type=int, default=500_000)
    args = ap.parse_args()
    os.makedirs("results", exist_ok=True)

    records = list(read_311(args.csv, args.limit))
    base_weight = {r["key"]: TYPE_WEIGHT.get(r["type"], 1) for r in records}
    created = {r["key"]: r["created"] for r in records}
    print(f"{len(records):,} complaints")

    rows = []
    for esc in (0, 0.5, 1, 2, 4):
        events = build_events(records, esc, random.Random(1))
        for name, cls in (("indexed_heap", Indexed), ("heapq_lazy", LazyHeapq)):
            impl = cls()
            secs, pops = run(impl, events, base_weight, created)
            rows.append([esc, name, len(events), secs, len(events) / secs, impl.peak, impl.stale_popped, pops])
            print(f"esc={esc:<3} {name:13} {secs:6.2f}s  {len(events)/secs:9,.0f} ev/s  "
                  f"peak array {impl.peak:9,}  stale popped {impl.stale_popped:,}")
    with open("results/heap_replay.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["escalations_per_complaint", "impl", "events", "seconds", "events_per_sec",
                    "peak_array_len", "stale_popped", "dispatches"])
        w.writerows(rows)


if __name__ == "__main__":
    main()
