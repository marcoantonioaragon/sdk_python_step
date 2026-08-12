import sys
import os
import pytest

# Ensure project root is on sys.path so local package can be imported during tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sdk_python_step.variation_assigner import VariationAssigner


def test_init_with_dict_and_list():
    vdict = {"a": 0.5, "b": 0.5}
    va = VariationAssigner("e", 1.0, vdict)
    assert set(va.variations.keys()) == {"a", "b"}

    val = VariationAssigner("e", 1.0, ["a", "b"])  # list -> balanced
    assert set(val.variations.keys()) == {"a", "b"}
    assert abs(sum(val.variations.values()) - 1.0) < 1e-8


def test_invalid_alloc_sum():
    with pytest.raises(ValueError):
        VariationAssign = VariationAssigner("e", 1.0, {"a": 0.6, "b": 0.3})


def test_invalid_traffic_allocation():
    with pytest.raises(ValueError):
        VariationAssigner("e", -0.1, {"a": 1.0})
    with pytest.raises(ValueError):
        VariationAssigner("e", 1.1, {"a": 1.0})


def test_all_out_when_traffic_zero():
    va = VariationAssigner("e", 0.0, {"a": 0.5, "b": 0.5})
    for u in ["u1", "u2", "u3"]:
        assert va.assign_variation(u) == 'out of the experiment'


def test_select_variation_boundaries():
    va = VariationAssigner("exp", 0.5, {"c": 0.5, "t": 0.5})

    # random_val equal to traffic_alocation => out
    assert va._VariationAssigner__select_variation(0.5) == 'out of the experiment'

    # random_val slightly less than traffic_alocation maps to normalized near 1.0
    # which should land in second bucket
    assert va._VariationAssigner__select_variation(0.49) in {"c", "t"}

    # verify normalized mapping: pick normalized 0.25 -> first bucket
    # compute random_val = normalized * traffic_alocation
    rv = 0.25 * va.traffic_alocation
    assert va._VariationAssigner__select_variation(rv) == 'c'

    rv2 = 0.75 * va.traffic_alocation
    assert va._VariationAssigner__select_variation(rv2) == 't'


def test_assign_variation_type_error():
    va = VariationAssigner("e", 1.0, {"a": 1.0})
    with pytest.raises(ValueError):
        va.assign_variation(123)  # non-string
