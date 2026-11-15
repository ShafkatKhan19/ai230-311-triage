"""Mutation check: break one line at a time and confirm the test suite notices.

A passing test suite only matters if it fails when the code is wrong. Each entry
below replaces one line of the implementation with a plausible bug, runs pytest,
and restores the file. A mutant that survives points at a missing test.

    python scripts/mutation_check.py
"""
import subprocess
import sys

MUTANTS = [
    ('triage311/hashtable.py',
     'if self._robin_hood and dist[i] < d:\n                return -1',
     'if self._robin_hood and dist[i] <= d:\n                return -1',
     'RH early exit off by one'),
    ('triage311/hashtable.py',
     'self._dist[i] = self._dist[j] - 1',
     'self._dist[i] = self._dist[j]',
     'backward shift keeps old distance'),
    ('triage311/hashtable.py',
     'while self._keys[j] is not _EMPTY and self._dist[j] > 0:',
     'while self._keys[j] is not _EMPTY:',
     'backward shift ignores home entries'),
    ('triage311/hashtable.py',
     '(i > j and (home <= i and home > j))',
     '(i > j and (home <= i or home > j))',
     'Knuth wraparound branch wrong'),
    ('triage311/hashtable.py',
     '(i < j and (home <= i or home > j))',
     '(i < j and (home < i or home > j))',
     'Knuth boundary home==i'),
    ('triage311/hashtable.py',
     'if (self._size + 1) > self._cap * self._max_load:',
     'if (self._size + 1) > self._cap * 2:',
     'never resizes'),
    ('triage311/hashtable.py',
     'dist[i], d = d, dist[i]',
     'dist[i] = d',
     'RH swap forgets carried distance'),
    ('triage311/hashtable.py',
     'if hashes[i] == h and (k is key or k == key):',
     'if hashes[i] == h:',
     'hash equality treated as key equality'),
    ('triage311/indexed_heap.py',
     '            self._sift_down(i)\n            self._sift_up(i)',
     '            self._sift_down(i)',
     'remove never sifts up'),
    ('triage311/indexed_heap.py',
     '        self._pos[h[j][1]] = j\n',
     '',
     'swap updates one map entry only'),
    ('triage311/indexed_heap.py',
     '        if new_priority < old:\n            self._sift_up(i)\n        else:\n            self._sift_down(i)',
     '        self._sift_up(i)',
     'update never sifts down'),
    ('triage311/indexed_heap.py',
     'if right < n and h[right][0] < h[smallest][0]:',
     'if right < n and h[right][0] < h[i][0]:',
     'sift down picks wrong child'),
    ('triage311/indexed_heap.py',
     'for c in (2 * i + 1, 2 * i + 2):',
     'for c in (2 * i + 1,):',
     'smallest(k) skips right children'),
    ('triage311/engine.py',
     '            return False\n',
     '            pass\n',
     'duplicate rows counted twice'),
    ('triage311/engine.py',
     'return (-self.weight[key], rec["created"], key)',
     'return (self.weight[key], rec["created"], key)',
     'priority sign flipped'),
    ('triage311/engine.py',
     'rec["created"] <= rec["closed"] <= until',
     'rec["created"] <= rec["closed"]',
     'replay ignores the cut-off for closures'),
]


def main():
    caught = 0
    for path, old, new, name in MUTANTS:
        source = open(path).read()
        assert source.count(old) == 1, f"mutant out of date: {name}"
        open(path, "w").write(source.replace(old, new))
        try:
            run = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider"],
                                 capture_output=True, text=True, timeout=180)
            detected = run.returncode != 0
        except subprocess.TimeoutExpired:   # e.g. an infinite probe loop
            detected = True
        finally:
            open(path, "w").write(source)
        caught += detected
        print(("caught   " if detected else "SURVIVED ") + name)
    print(f"{caught} / {len(MUTANTS)} mutants caught")
    return 0 if caught == len(MUTANTS) else 1


if __name__ == "__main__":
    sys.exit(main())
