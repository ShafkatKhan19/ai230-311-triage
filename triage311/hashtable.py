"""Open-addressing hash table written from scratch (no dict / set used for storage).

Two probing modes share one implementation:
  * robin_hood=True  (default) - Robin Hood linear probing with backward-shift deletion
  * robin_hood=False           - plain linear probing with Knuth's deletion (Algorithm R)

Keys are hashed with Python's hash() followed by a Fibonacci-hashing mix step
(mix=False turns it off, to measure what happens without it).

Both modes keep deletion tombstone-free, so lookups never walk over dead slots.
The table capacity is always a power of two so the home slot is `hash & mask`.
"""

_EMPTY = object()  # sentinel for an unused slot
_MASK64 = (1 << 64) - 1
_GOLDEN = 0x9E3779B97F4A7C15  # 2^64 / golden ratio (Fibonacci hashing)


def _mix(h):
    """Scramble Python's hash before masking.

    hash(int) is the identity, and 311 complaint keys are near-sequential
    integers, so without mixing they fill one long contiguous run of slots.
    Multiplying by the golden-ratio constant and folding the high bits down
    spreads them evenly across the table.
    """
    h = (h * _GOLDEN) & _MASK64
    return h ^ (h >> 32)


class HashTable:
    def __init__(self, capacity=16, max_load=0.85, robin_hood=True, mix=True):
        if not 0.1 <= max_load < 1.0:
            raise ValueError("max_load must be in [0.1, 1.0)")
        cap = 8
        while cap < capacity:
            cap *= 2
        self._max_load = max_load
        self._robin_hood = robin_hood
        self._hash = (lambda k: _mix(hash(k))) if mix else hash
        self._init_slots(cap)
        self._size = 0
        self.resizes = 0  # exposed for benchmarks

    # ------------------------------------------------------------------ internals
    def _init_slots(self, cap):
        self._cap = cap
        self._mask = cap - 1
        self._keys = [_EMPTY] * cap
        self._vals = [None] * cap
        self._hashes = [0] * cap
        self._dist = [0] * cap  # probe distance from home slot

    def _home(self, h):
        return h & self._mask

    def _find_slot(self, key, h):
        """Return the slot index holding `key`, or -1 if absent."""
        keys, hashes, dist, mask = self._keys, self._hashes, self._dist, self._mask
        i = h & mask
        d = 0
        while True:
            k = keys[i]
            if k is _EMPTY:
                return -1
            # Robin Hood early exit: if the resident is closer to home than we
            # would be, our key would have displaced it, so the key is absent.
            if self._robin_hood and dist[i] < d:
                return -1
            if hashes[i] == h and (k is key or k == key):
                return i
            i = (i + 1) & mask
            d += 1

    def _resize(self, new_cap):
        old_keys, old_vals, old_hashes = self._keys, self._vals, self._hashes
        self._init_slots(new_cap)
        self._size = 0
        self.resizes += 1
        for k, v, h in zip(old_keys, old_vals, old_hashes):
            if k is not _EMPTY:
                self._insert_new(k, v, h)

    def _insert_new(self, key, val, h):
        """Insert a key known not to be present. Caller handles resizing."""
        keys, vals, hashes, dist, mask = self._keys, self._vals, self._hashes, self._dist, self._mask
        i = h & mask
        d = 0
        while True:
            if keys[i] is _EMPTY:
                keys[i], vals[i], hashes[i], dist[i] = key, val, h, d
                self._size += 1
                return
            if self._robin_hood and dist[i] < d:
                # Steal the slot from the "richer" resident and keep inserting it.
                keys[i], key = key, keys[i]
                vals[i], val = val, vals[i]
                hashes[i], h = h, hashes[i]
                dist[i], d = d, dist[i]
            i = (i + 1) & mask
            d += 1

    # ------------------------------------------------------------------ public API
    def __len__(self):
        return self._size

    def __contains__(self, key):
        return self._find_slot(key, self._hash(key)) >= 0

    def __getitem__(self, key):
        i = self._find_slot(key, self._hash(key))
        if i < 0:
            raise KeyError(key)
        return self._vals[i]

    def get(self, key, default=None):
        i = self._find_slot(key, self._hash(key))
        return default if i < 0 else self._vals[i]

    def __setitem__(self, key, val):
        h = self._hash(key)
        i = self._find_slot(key, h)
        if i >= 0:
            self._vals[i] = val
            return
        if (self._size + 1) > self._cap * self._max_load:
            self._resize(self._cap * 2)
        self._insert_new(key, val, h)

    def __delitem__(self, key):
        i = self._find_slot(key, self._hash(key))
        if i < 0:
            raise KeyError(key)
        if self._robin_hood:
            self._backward_shift(i)
        else:
            self._knuth_delete(i)
        self._size -= 1

    def pop(self, key, *default):
        i = self._find_slot(key, self._hash(key))
        if i < 0:
            if default:
                return default[0]
            raise KeyError(key)
        val = self._vals[i]
        del self[key]
        return val

    def _clear_slot(self, i):
        self._keys[i] = _EMPTY
        self._vals[i] = None
        self._dist[i] = 0

    def _move(self, src, dst):
        self._keys[dst] = self._keys[src]
        self._vals[dst] = self._vals[src]
        self._hashes[dst] = self._hashes[src]

    def _backward_shift(self, i):
        """Robin Hood deletion: pull the following run back by one slot."""
        mask = self._mask
        j = (i + 1) & mask
        while self._keys[j] is not _EMPTY and self._dist[j] > 0:
            self._move(j, i)
            self._dist[i] = self._dist[j] - 1
            i = j
            j = (j + 1) & mask
        self._clear_slot(i)

    def _knuth_delete(self, i):
        """Plain linear probing deletion (Knuth Vol.3, Algorithm R)."""
        mask = self._mask
        self._clear_slot(i)
        j = i
        while True:
            j = (j + 1) & mask
            if self._keys[j] is _EMPTY:
                return
            home = self._hashes[j] & mask
            # Move entry j into hole i unless its home lies cyclically in (i, j].
            if (i < j and (home <= i or home > j)) or (i > j and (home <= i and home > j)):
                self._move(j, i)
                self._dist[i] = (i - home) & mask
                self._clear_slot(j)
                i = j

    def keys(self):
        for k in self._keys:
            if k is not _EMPTY:
                yield k

    def items(self):
        for k, v in zip(self._keys, self._vals):
            if k is not _EMPTY:
                yield k, v

    __iter__ = keys

    # ------------------------------------------------------------------ diagnostics
    @property
    def capacity(self):
        return self._cap

    @property
    def load_factor(self):
        return self._size / self._cap

    def probe_lengths(self):
        """Probe distance of every stored key (0 = sits in its home slot)."""
        return [d for k, d in zip(self._keys, self._dist) if k is not _EMPTY]

    def check_invariants(self):
        """Used by tests: every key is findable and stored distances are correct."""
        count = 0
        for i, k in enumerate(self._keys):
            if k is _EMPTY:
                continue
            count += 1
            assert self._dist[i] == (i - (self._hashes[i] & self._mask)) & self._mask
            assert self._find_slot(k, self._hashes[i]) == i
        assert count == self._size
