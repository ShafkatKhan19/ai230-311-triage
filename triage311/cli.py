"""Interactive demo.

    python -m triage311.cli data/311_2025.csv --at "2025-07-04 18:00"

Commands:  next [k] | lookup ID | escalate ID | close ID | count ZIP TYPE... | stats | help | quit
"""

import argparse
import time
from datetime import datetime

from .data import read_311
from .engine import TriageEngine


def fmt(rec):
    return (f"{rec['key']:>10}  {rec['created']:%m-%d %H:%M}  {rec['zip'] or '-----':5}  "
            f"{rec['type'][:28]:28}  {rec['descriptor'][:30]}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="311 Triage Engine demo")
    ap.add_argument("csv")
    ap.add_argument("--at", help='replay time, e.g. "2025-07-04 18:00" (default: latest created date)')
    ap.add_argument("--limit", type=int, help="only load the first N rows")
    args = ap.parse_args(argv)

    eng = TriageEngine()
    t0 = time.perf_counter()
    latest = None
    for rec in read_311(args.csv, args.limit):
        eng.add(rec)
        if latest is None or rec["created"] > latest:
            latest = rec["created"]
    print(f"Loaded {len(eng.records):,} complaints in {time.perf_counter() - t0:.1f}s "
          f"(hash table capacity {eng.records.capacity:,}, load {eng.records.load_factor:.2f})")

    if latest is None:
        raise SystemExit(f"No complaints could be read from {args.csv}")
    try:
        at = datetime.strptime(args.at, "%Y-%m-%d %H:%M") if args.at else latest
    except ValueError:
        raise SystemExit('--at must look like "2025-08-15 18:00"')
    t0 = time.perf_counter()
    pushes, removes = eng.replay(at)
    print(f"Replayed to {at:%Y-%m-%d %H:%M}: {pushes:,} opened, {removes:,} closed, "
          f"{len(eng.queue):,} still open ({time.perf_counter() - t0:.1f}s)\n")

    while True:
        try:
            line = input("triage> ").strip()
        except EOFError:
            break
        if not line:
            continue
        cmd, *rest = line.split()
        if cmd in ("lookup", "escalate", "close", "count") and not rest:
            print(f"usage: {cmd} needs an argument (type help)")
            continue
        try:
            t0 = time.perf_counter()
            if cmd in ("quit", "exit", "q"):
                break
            elif cmd == "next":
                k = int(rest[0]) if rest else 10
                for i, (key, rec) in enumerate(eng.next(k), 1):
                    print(f"{i:>3}. [w={eng.weight[key]:>2}] {fmt(rec)}")
            elif cmd == "lookup":
                rec = eng.lookup(_key(rest[0]))
                print(fmt(rec) + ("   OPEN" if rec and rec["key"] in eng.queue else "   closed")
                      if rec else "not found")
            elif cmd == "escalate":
                key = _key(rest[0])
                eng.escalate(key)
                print(f"escalated {key} to weight {eng.weight[key]}")
            elif cmd == "close":
                eng.close(_key(rest[0]))
                print("closed")
            elif cmd == "count":
                print(eng.count(rest[0], " ".join(rest[1:])))
            elif cmd == "stats":
                pl = eng.records.probe_lengths()
                print(f"open: {len(eng.queue):,}  records: {len(eng.records):,}  "
                      f"avg probe: {sum(pl) / len(pl):.2f}  max probe: {max(pl)}")
            else:
                print(__doc__)
                continue
            print(f"  ({(time.perf_counter() - t0) * 1e3:.3f} ms)")
        except (KeyError, IndexError, ValueError) as e:
            print(f"error: {e}")


def _key(s):
    return int(s) if s.isdigit() else s


if __name__ == "__main__":
    main()
