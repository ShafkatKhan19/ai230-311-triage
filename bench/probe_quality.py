"""How well does each mix step spread the real 311 keys?

Fills a fixed-size table to each load factor and compares the measured average
probe distance with the textbook prediction for linear probing with uniform
hashing: (1/2) * (1/(1 - a) - 1) extra probes per successful search.
Robin Hood and plain linear probing have the same average, so only one is built.

    python bench/probe_quality.py data/311_2025q3.csv
Writes results/probe_quality.csv.
"""

import argparse
import csv
import os
import statistics
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from triage311.data import read_311  # noqa: E402
from triage311.hashtable import HashTable  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--cap-exp", type=int, default=19)
    args = ap.parse_args()
    os.makedirs("results", exist_ok=True)

    keys = list(dict.fromkeys(r["key"] for r in read_311(args.csv)))
    cap = 2 ** args.cap_exp
    rows = []
    for lf in (0.5, 0.6, 0.7, 0.8, 0.9):
        n = int(cap * lf)
        theory = 0.5 * (1 / (1 - lf) - 1)
        for mix in ("splitmix", "fibonacci"):
            t = HashTable(cap, max_load=0.99, mix=mix)
            for k in keys[:n]:
                t[k] = k
            pl = sorted(t.probe_lengths())
            avg = statistics.mean(pl)
            rows.append([lf, mix, n, round(theory, 3), round(avg, 3), round(avg / theory, 2), pl[-1]])
            print(f"lf={lf} {mix:9} theory {theory:5.2f}  measured {avg:5.2f}  "
                  f"ratio {avg / theory:4.2f}  max {pl[-1]}")
    with open("results/probe_quality.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["load_factor", "mix", "n", "theory_avg_probe", "measured_avg_probe", "ratio", "max_probe"])
        w.writerows(rows)


if __name__ == "__main__":
    main()
