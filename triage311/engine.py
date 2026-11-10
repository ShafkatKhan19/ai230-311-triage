"""311 triage engine: every lookup and count goes through our HashTable,
and the queue of open complaints is our IndexedMinHeap."""

from .hashtable import HashTable
from .indexed_heap import IndexedMinHeap

# Urgency weight per complaint type (higher = more urgent). Anything not listed gets 1.
_WEIGHTS = [
    ("Gas Leak", 10), ("Elevator", 8), ("HEAT/HOT WATER", 8), ("Water System", 7),
    ("Traffic Signal Condition", 7), ("Street Condition", 5), ("Sewer", 5),
    ("Electric", 6), ("PLUMBING", 5), ("Blocked Driveway", 3), ("Illegal Parking", 2),
    ("Noise - Residential", 2), ("Noise - Street/Sidewalk", 2), ("Noise - Commercial", 2),
    ("Noise - Vehicle", 2), ("UNSANITARY CONDITION", 4), ("Dirty Condition", 2),
    ("Abandoned Vehicle", 1), ("Graffiti", 1),
]
TYPE_WEIGHT = HashTable()
for _t, _w in _WEIGHTS:
    TYPE_WEIGHT[_t] = _w

ESCALATION_STEP = 3


class TriageEngine:
    def __init__(self):
        self.records = HashTable()   # complaint key -> record
        self.counts = HashTable()    # (zip, complaint type) -> count
        self.queue = IndexedMinHeap()  # open complaints, most urgent first
        self.weight = HashTable()    # complaint key -> current urgency weight

    # ------------------------------------------------------------------ priority
    def _priority(self, key):
        rec = self.records[key]
        # Min-heap: most urgent = largest weight, then oldest, then lowest key.
        return (-self.weight[key], rec["created"], key)

    # ------------------------------------------------------------------ ingest
    def add(self, rec):
        key = rec["key"]
        self.records[key] = rec
        self.weight[key] = TYPE_WEIGHT.get(rec["type"], 1)
        ck = (rec["zip"], rec["type"])
        self.counts[ck] = self.counts.get(ck, 0) + 1

    def replay(self, until):
        """Rebuild the open queue as of time `until`: a complaint is open if it was
        created at or before `until` and not closed by then. Events are applied in time
        order, so this is the same sequence of pushes/removes a live system would see."""
        self.queue = IndexedMinHeap()
        events = []
        for key, rec in self.records.items():
            if rec["created"] <= until:
                events.append((rec["created"], 0, key))
                if rec["closed"] is not None and rec["created"] <= rec["closed"] <= until:
                    events.append((rec["closed"], 1, key))
        events.sort()
        pushes = removes = 0
        for _, kind, key in events:
            if kind == 0:
                self.queue.push(key, self._priority(key))
                pushes += 1
            elif key in self.queue:
                self.queue.remove(key)
                removes += 1
        return pushes, removes

    # ------------------------------------------------------------------ operations
    def next(self, k=10):
        return [(key, self.records[key]) for key, _ in self.queue.smallest(k)]

    def lookup(self, key):
        return self.records.get(key)

    def escalate(self, key, step=ESCALATION_STEP):
        if key not in self.queue:
            raise KeyError(f"{key} is not an open complaint")
        self.weight[key] = self.weight[key] + step
        self.queue.update(key, self._priority(key))

    def close(self, key):
        self.queue.remove(key)

    def count(self, zip_code, complaint_type):
        return self.counts.get((zip_code, complaint_type), 0)
