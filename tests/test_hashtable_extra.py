"""Edge cases and statistical checks for HashTable beyond the basic suite."""
import random

import pytest
from hypothesis import given, settings, strategies as st

from triage311.hashtable import HashTable

MODES = [True, False]


def test_bad_arguments_rejected():
    with pytest.raises(ValueError):
        HashTable(max_load=1.0)
    with pytest.raises(ValueError):
        HashTable(mix="md5")
    with pytest.raises(TypeError):
        HashTable()[[1, 2]] = "lists are unhashable"


@pytest.mark.parametrize("rh", MODES)
def test_none_values_and_falsy_keys(rh):
    t = HashTable(robin_hood=rh)
    t[0] = None
    t[""] = 0
    t[None] = "none key"
    assert 0 in t and t[0] is None            # stored None is not "missing"
    assert t.get(0, "default") is None
    assert t[""] == 0 and t[None] == "none key"
    assert t.pop(0) is None and 0 not in t
    with pytest.raises(KeyError):
        t.pop(0)


@pytest.mark.parametrize("rh", MODES)
def test_equal_keys_of_different_types_share_a_slot(rh):
    # Same rule as dict: 1 == 1.0 == True and they hash the same.
    t = HashTable(robin_hood=rh)
    t[1] = "int"
    t[1.0] = "float"
    t[True] = "bool"
    assert len(t) == 1 and t[1] == "bool"


@pytest.mark.parametrize("rh", MODES)
def test_iteration_and_repr(rh):
    t = HashTable(robin_hood=rh)
    for i in range(50):
        t[f"k{i}"] = i
    assert sorted(t) == sorted(f"k{i}" for i in range(50))
    assert sorted(t.values()) == list(range(50))
    assert dict(t.items()) == {f"k{i}": i for i in range(50)}
    assert "50 items" in repr(t)


@pytest.mark.parametrize("rh", MODES)
def test_fill_empty_refill(rh):
    """Delete everything, then reuse the table: no slot may be left unusable."""
    t = HashTable(capacity=8, robin_hood=rh)
    for round_ in range(3):
        for i in range(500):
            t[(round_, i)] = i
        for i in range(500):
            del t[(round_, i)]
        assert len(t) == 0
        t.check_invariants()
    assert list(t.keys()) == []


@pytest.mark.parametrize("rh", MODES)
def test_negative_and_huge_int_keys(rh):
    keys = [-1, -2, -(2**63), 2**64 + 5, 2**200, 0]
    t = HashTable(robin_hood=rh)
    for k in keys:
        t[k] = str(k)
    t.check_invariants()
    assert all(t[k] == str(k) for k in keys)


@pytest.mark.parametrize("mix", ["splitmix", "fibonacci"])
def test_probe_length_matches_theory_on_random_keys(mix):
    """With uniform hashing, linear probing has 1/2 * (1/(1-a) - 1) extra probes on average."""
    rng = random.Random(42)
    cap, load = 2**15, 0.7
    t = HashTable(cap, max_load=0.99, mix=mix)
    for _ in range(int(cap * load)):
        t[rng.getrandbits(60)] = 1
    pl = t.probe_lengths()
    theory = 0.5 * (1 / (1 - load) - 1)
    assert abs(sum(pl) / len(pl) - theory) / theory < 0.10


def test_robin_hood_and_linear_have_same_mean_probe_but_rh_smaller_max():
    rng = random.Random(1)
    keys = [rng.getrandbits(60) for _ in range(int(2**14 * 0.9))]
    rh, lin = HashTable(2**14, max_load=0.99), HashTable(2**14, max_load=0.99, robin_hood=False)
    for k in keys:
        rh[k] = lin[k] = 1
    a, b = rh.probe_lengths(), lin.probe_lengths()
    assert sum(a) == sum(b)          # Robin Hood only redistributes the total displacement
    assert max(a) < max(b)


# ---------------------------------------------------------------- property test, mixed key types
mixed_keys = st.one_of(
    st.integers(), st.text(max_size=6), st.tuples(st.integers(0, 9), st.text(max_size=3)),
    st.floats(allow_nan=False), st.booleans(), st.none(),
)


@pytest.mark.parametrize("rh", MODES)
@settings(max_examples=150, deadline=None)
@given(ops=st.lists(st.tuples(st.sampled_from(["set", "del", "pop"]), mixed_keys, st.integers()), max_size=200))
def test_matches_dict_with_mixed_key_types(rh, ops):
    ours, ref = HashTable(capacity=8, robin_hood=rh), {}
    for op, k, v in ops:
        if op == "set":
            ours[k] = v
            ref[k] = v
        elif op == "del" and k in ref:
            del ours[k]
            del ref[k]
        elif op == "pop":
            assert ours.pop(k, "absent") == ref.pop(k, "absent")
        assert len(ours) == len(ref) and (k in ours) == (k in ref)
    ours.check_invariants()
    assert len(list(ours.items())) == len(ref)
    for k, v in ref.items():
        assert ours[k] == v
