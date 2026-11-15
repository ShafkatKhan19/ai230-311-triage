"""Edge cases for IndexedMinHeap beyond the basic suite."""
import random

import pytest
from hypothesis import given, settings, strategies as st

from triage311.indexed_heap import IndexedMinHeap


def test_empty_heap_errors():
    h = IndexedMinHeap()
    with pytest.raises(IndexError):
        h.peek()
    with pytest.raises(KeyError):
        h.update("missing", 1)
    with pytest.raises(KeyError):
        h.remove("missing")
    assert h.smallest(5) == [] and len(h) == 0


def test_single_item_and_remove_last_position():
    h = IndexedMinHeap()
    h.push("only", 3)
    assert h.peek() == ("only", 3) and h.priority("only") == 3
    assert h.remove("only") == 3 and len(h) == 0
    for i in range(7):
        h.push(i, i)
    h.remove(6)                      # the entry in the last array slot
    h.check_invariants()
    assert 6 not in h and len(h) == 6


def test_heapsort_matches_sorted():
    rng = random.Random(3)
    values = [rng.randint(-10_000, 10_000) for _ in range(5_000)]
    h = IndexedMinHeap()
    for i, v in enumerate(values):
        h.push(i, v)
    assert [h.pop()[1] for _ in range(len(values))] == sorted(values)


def test_equal_priorities_all_come_out():
    h = IndexedMinHeap()
    for k in "abcdef":
        h.push(k, 1)
    assert sorted(h.pop()[0] for _ in range(6)) == list("abcdef")


def test_update_to_same_priority_is_a_no_op():
    h = IndexedMinHeap()
    for i in range(20):
        h.push(i, i)
    h.update(10, 10)
    h.check_invariants()
    assert h.priority(10) == 10


def test_smallest_k_larger_than_heap_and_zero():
    h = IndexedMinHeap()
    for i in [4, 2, 6]:
        h.push(i, i)
    assert h.smallest(0) == []
    assert h.smallest(99) == [(2, 2), (4, 4), (6, 6)]


@settings(max_examples=200, deadline=None)
@given(prios=st.lists(st.integers(-100, 100), max_size=120), k=st.integers(0, 130))
def test_smallest_k_equals_sorted_prefix(prios, k):
    h = IndexedMinHeap()
    for i, p in enumerate(prios):
        h.push(i, (p, i))            # unique priorities so the order is fully determined
    expected = sorted((p, i) for i, p in enumerate(prios))[:k]
    assert [pr for _, pr in h.smallest(k)] == expected
    assert len(h) == len(prios)
    h.check_invariants()


def test_remove_can_require_sift_up():
    """Found by scripts/mutation_check.py: the random tests rarely hit this case.

    Removing 11 moves the last entry (4) into a different subtree, under parent 10,
    so the replacement has to move up, not down.
    """
    h = IndexedMinHeap()
    for p in [1, 10, 2, 11, 12, 3, 4]:     # this push order needs no swaps: array == list
        h.push(p, p)
    h.remove(11)
    h.check_invariants()
    assert [h.pop()[0] for _ in range(6)] == [1, 2, 3, 4, 10, 12]
