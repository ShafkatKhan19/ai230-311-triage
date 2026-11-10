"""Indexed binary min-heap written from scratch.

Each item is a hashable key with a comparable priority. A position map
(our own HashTable) records where every key sits in the heap array, which
gives O(log n) update() and remove() - operations Python's heapq lacks.
"""

from .hashtable import HashTable


class IndexedMinHeap:
    def __init__(self):
        self._heap = []          # list of [priority, key]
        self._pos = HashTable()  # key -> index in self._heap

    def __len__(self):
        return len(self._heap)

    def __contains__(self, key):
        return key in self._pos

    def priority(self, key):
        return self._heap[self._pos[key]][0]

    # ------------------------------------------------------------------ core moves
    def _swap(self, i, j):
        h = self._heap
        h[i], h[j] = h[j], h[i]
        self._pos[h[i][1]] = i
        self._pos[h[j][1]] = j

    def _sift_up(self, i):
        h = self._heap
        while i > 0:
            parent = (i - 1) // 2
            if h[i][0] < h[parent][0]:
                self._swap(i, parent)
                i = parent
            else:
                return

    def _sift_down(self, i):
        h = self._heap
        n = len(h)
        while True:
            left = 2 * i + 1
            right = left + 1
            smallest = i
            if left < n and h[left][0] < h[smallest][0]:
                smallest = left
            if right < n and h[right][0] < h[smallest][0]:
                smallest = right
            if smallest == i:
                return
            self._swap(i, smallest)
            i = smallest

    # ------------------------------------------------------------------ public API
    def push(self, key, priority):
        if key in self._pos:
            raise KeyError(f"{key!r} already in heap; use update()")
        self._heap.append([priority, key])
        i = len(self._heap) - 1
        self._pos[key] = i
        self._sift_up(i)

    def peek(self):
        if not self._heap:
            raise IndexError("peek from empty heap")
        priority, key = self._heap[0]
        return key, priority

    def pop(self):
        if not self._heap:
            raise IndexError("pop from empty heap")
        priority, key = self._heap[0]
        self._remove_at(0)
        return key, priority

    def update(self, key, new_priority):
        """Change a key's priority (increase or decrease) in O(log n)."""
        i = self._pos[key]
        old = self._heap[i][0]
        self._heap[i][0] = new_priority
        if new_priority < old:
            self._sift_up(i)
        else:
            self._sift_down(i)

    def remove(self, key):
        """Delete an arbitrary key in O(log n). Returns its priority."""
        i = self._pos[key]
        priority = self._heap[i][0]
        self._remove_at(i)
        return priority

    def _remove_at(self, i):
        h = self._heap
        last = len(h) - 1
        if i != last:
            self._swap(i, last)
        _, key = h.pop()
        del self._pos[key]
        if i < len(h):
            self._sift_down(i)
            self._sift_up(i)

    def smallest(self, k):
        """Return the k smallest (key, priority) pairs without modifying the heap.

        Uses a second small heap over indices, so it costs O(k log k).
        """
        out = []
        if not self._heap:
            return out
        frontier = IndexedMinHeap()
        frontier.push(0, self._heap[0][0])
        while frontier and len(out) < k:
            i, pr = frontier.pop()
            out.append((self._heap[i][1], pr))
            for c in (2 * i + 1, 2 * i + 2):
                if c < len(self._heap):
                    frontier.push(c, self._heap[c][0])
        return out

    def check_invariants(self):
        h = self._heap
        for i in range(1, len(h)):
            assert not (h[i][0] < h[(i - 1) // 2][0])
        assert len(self._pos) == len(h)
        for i, (_, key) in enumerate(h):
            assert self._pos[key] == i
