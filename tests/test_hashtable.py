import pytest
from hypothesis import given, settings, strategies as st

from triage311.hashtable import HashTable

MODES = [True, False]  # robin_hood on / off


@pytest.mark.parametrize("rh", MODES)
def test_basic_set_get_delete(rh):
    t = HashTable(robin_hood=rh)
    t["a"] = 1
    t["b"] = 2
    t["a"] = 3  # overwrite
    assert t["a"] == 3 and t["b"] == 2 and len(t) == 2
    del t["a"]
    assert "a" not in t and len(t) == 1
    with pytest.raises(KeyError):
        t["a"]
    with pytest.raises(KeyError):
        del t["missing"]
    assert t.get("missing", 42) == 42
    assert t.pop("b") == 2 and len(t) == 0
    assert t.pop("b", None) is None


@pytest.mark.parametrize("rh", MODES)
def test_resize_keeps_everything(rh):
    t = HashTable(capacity=8, robin_hood=rh)
    for i in range(10_000):
        t[i] = i * i
    assert len(t) == 10_000 and t.resizes > 0
    assert t.load_factor <= 0.85
    for i in range(10_000):
        assert t[i] == i * i
    t.check_invariants()


class Collide:
    """Keys that all hash to the same value - worst case for probing."""
    def __init__(self, v):
        self.v = v
    def __hash__(self):
        return 7
    def __eq__(self, other):
        return isinstance(other, Collide) and self.v == other.v


@pytest.mark.parametrize("rh", MODES)
def test_all_keys_collide(rh):
    t = HashTable(robin_hood=rh)
    keys = [Collide(i) for i in range(200)]
    for k in keys:
        t[k] = k.v
    for k in keys[::2]:
        del t[k]
    t.check_invariants()
    for k in keys:
        assert t.get(k) == (None if k.v % 2 == 0 else k.v)


@pytest.mark.parametrize("rh", MODES)
def test_wraparound_deletion(rh):
    # Small fixed table so clusters wrap past the end of the array.
    t = HashTable(capacity=8, max_load=0.85, robin_hood=rh, mix=None)  # raw hash so homes are known
    for k in [6, 7, 14, 15, 22]:  # homes 6,7,6,7,6 -> cluster wraps to slots 0..
        t[k] = k
    for k in [6, 14, 7]:
        del t[k]
        t.check_invariants()
    assert sorted(t.keys()) == [15, 22]


# ---------------------------------------------------------------- property test
ops = st.lists(
    st.tuples(st.sampled_from(["set", "del", "get"]),
              st.integers(-50, 50), st.integers()),
    max_size=400,
)


@pytest.mark.parametrize("rh", MODES)
@pytest.mark.parametrize("mix", ["splitmix", "fibonacci", None])
@settings(max_examples=200, deadline=None)
@given(ops=ops)
def test_matches_dict(rh, mix, ops):
    """Random operation sequences must behave exactly like Python's dict."""
    ours, ref = HashTable(capacity=8, robin_hood=rh, mix=mix), {}
    for op, k, v in ops:
        if op == "set":
            ours[k] = v
            ref[k] = v
        elif op == "del":
            if k in ref:
                del ours[k]
                del ref[k]
            else:
                with pytest.raises(KeyError):
                    del ours[k]
        else:
            assert ours.get(k) == ref.get(k)
        assert len(ours) == len(ref)
    ours.check_invariants()
    assert sorted(ours.items()) == sorted(ref.items())
