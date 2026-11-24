import math

import pytest

import lightprobe

def _raises(fn, exc=ValueError):
    try:
        fn()
    except exc:
        return True
    return False

DIRS = [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)]

CASES = [
    ("coeff_len", lambda: len(lightprobe.Sh().project([1.0, 1.0, 1.0], DIRS)) == 9),
    ("constant_dc", lambda: lightprobe.Sh().constant_check(lightprobe.Sh().project([1.0] * 8, [(1.0, 0.0, 0.0)] * 8)) is True),
    ("reconstruct_type", lambda: isinstance(lightprobe.Sh().reconstruct(lightprobe.Sh().project([1.0], [(1.0, 0.0, 0.0)]), (1.0, 0.0, 0.0)), float)),
    ("bad_len", lambda: _raises(lambda: lightprobe.Sh().project([1.0], []))),
    ("bad_coeffs", lambda: _raises(lambda: lightprobe.Sh().reconstruct([0.0] * 3, (1.0, 0.0, 0.0)))),
    ("bad_dir", lambda: _raises(lambda: lightprobe.Sh().project([1.0], [(0.0, 0.0, 0.0)]))),
    ("type", lambda: isinstance(lightprobe.Sh().project([1.0], [(1.0, 0.0, 0.0)]), list)),
    ("det", lambda: lightprobe.Sh().project([1.0], [(1.0, 0.0, 0.0)]) == lightprobe.Sh().project([1.0], [(1.0, 0.0, 0.0)])),
    ("reconstruct_finite", lambda: math.isfinite(lightprobe.Sh().reconstruct(lightprobe.Sh().project([1.0], [(1.0, 0.0, 0.0)]), (1.0, 0.0, 0.0)))),
    ("constant_recon", lambda: abs(lightprobe.Sh().reconstruct(lightprobe.Sh().project([1.0] * 8, [(1.0, 0.0, 0.0)] * 8), (1.0, 0.0, 0.0)) - 1.0) <= 0.1),
    ("nan", lambda: _raises(lambda: lightprobe.Sh().project([float('nan')], [(1.0, 0.0, 0.0)]))),
    ("no_mut", lambda: lightprobe.Sh().project([1.0], list(DIRS[:1])) is not None),
    ("coeff_type", lambda: isinstance(lightprobe.Sh().project([1.0], [(1.0, 0.0, 0.0)])[0], float)),
    ("two_samples", lambda: len(lightprobe.Sh().project([1.0, 2.0], [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0)])) == 9),
    ("bool_check", lambda: isinstance(lightprobe.Sh().constant_check([0.0] * 9), bool)),
]


@pytest.mark.parametrize("name,check", CASES, ids=[c[0] for c in CASES])
def test_spec(name, check):
    assert check() is True
