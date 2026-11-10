import heapq

import pytest
from hypothesis import given, settings, strategies as st

from triage311.indexed_heap import IndexedMinHeap


def test_push_pop_order():
    h = IndexedMinHeap()
    for k, p in [("a", 5), ("b", 1), ("c", 3), ("d", 4), ("e", 2)]:
        h.push(k, p)
    assert [h.pop()[0] for _ in range(5)] == ["b", "e", "c", "d", "a"]
    with pytest.raises(IndexError):
        h.pop()


def test_update_both_directions_and_remove():
    h = IndexedMinHeap()
    for i in range(10):
        h.push(i, i)
    h.update(9, -1)   # decrease-key: 9 jumps to the top
    h.update(0, 100)  # increase-key: 0 sinks to the bottom
    h.check_invariants()
    assert h.peek() == (9, -1)
    assert h.remove(5) == 5 and 5 not in h
    h.check_invariants()
    order = [h.pop()[0] for _ in range(len(h))]
    assert order == [9, 1, 2, 3, 4, 6, 7, 8, 0]


def test_duplicate_push_rejected():
    h = IndexedMinHeap()
    h.push("x", 1)
    with pytest.raises(KeyError):
        h.push("x", 2)


def test_smallest_k_does_not_modify():
    h = IndexedMinHeap()
    for i in [7, 3, 9, 1, 5, 8]:
        h.push(f"k{i}", i)
    assert [p for _, p in h.smallest(3)] == [1, 3, 5]
    assert len(h) == 6
    h.check_invariants()


# ---------------------------------------------------------------- property test
ops = st.lists(
    st.tuples(st.sampled_from(["push", "pop", "update", "remove"]),
              st.integers(0, 40), st.integers(-1000, 1000)),
    max_size=300,
)


@settings(max_examples=300, deadline=None)
@given(ops=ops)
def test_matches_reference(ops):
    """Compare against a plain dict + heapq.nsmallest reference model."""
    h, ref = IndexedMinHeap(), {}
    for op, k, p in ops:
        if op == "push" and k not in ref:
            h.push(k, (p, k))
            ref[k] = (p, k)
        elif op == "update" and k in ref:
            h.update(k, (p, k))
            ref[k] = (p, k)
        elif op == "remove" and k in ref:
            assert h.remove(k) == ref.pop(k)
        elif op == "pop" and ref:
            key, pr = h.pop()
            expected = heapq.nsmallest(1, ref.values())[0]
            assert pr == expected
            del ref[key]
        assert len(h) == len(ref)
    h.check_invariants()
