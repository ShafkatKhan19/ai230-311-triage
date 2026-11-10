"""Turn results/*.csv into the figures for the report (results/*.png)."""

import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

os.makedirs("results", exist_ok=True)


def load(path):
    with open(path) as f:
        return list(csv.DictReader(f))


# 1. Lookup cost vs load factor
rows = load("results/hashtable_loadfactor.csv")
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
for impl, style in (("robin_hood", "o-"), ("linear", "s-"), ("dict", "^--")):
    r = [x for x in rows if x["impl"] == impl]
    lf = [float(x["load_factor"]) for x in r]
    axes[0].plot(lf, [float(x["miss_ns"]) for x in r], style, label=impl)
    if impl != "dict":
        axes[1].plot(lf, [int(x["max_probe"]) for x in r], style, label=impl)
axes[0].set(title="Unsuccessful lookup vs load factor", xlabel="load factor", ylabel="ns per lookup", yscale="log")
axes[1].set(title="Longest probe sequence", xlabel="load factor", ylabel="slots probed")
for a in axes:
    a.legend()
    a.grid(alpha=0.3)
fig.tight_layout()
fig.savefig("results/hashtable_loadfactor.png", dpi=150)

# 2. Heap replay: speed and memory
rows = load("results/heap_replay.csv")
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
for impl, style in (("indexed_heap", "o-"), ("heapq_lazy", "s-")):
    r = [x for x in rows if x["impl"] == impl]
    esc = [float(x["escalations_per_complaint"]) for x in r]
    axes[0].plot(esc, [float(x["events_per_sec"]) for x in r], style, label=impl)
    axes[1].plot(esc, [int(x["peak_array_len"]) for x in r], style, label=impl)
axes[0].set(title="Replay throughput", xlabel="escalations per complaint", ylabel="events / second")
axes[1].set(title="Peak heap array size", xlabel="escalations per complaint", ylabel="entries")
for a in axes:
    a.legend()
    a.grid(alpha=0.3)
fig.tight_layout()
fig.savefig("results/heap_replay.png", dpi=150)
print("wrote results/hashtable_loadfactor.png and results/heap_replay.png")
