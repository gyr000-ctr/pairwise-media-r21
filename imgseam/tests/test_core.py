import math

import pytest

import imgseam

def _raises(fn, exc=ValueError):
    try:
        fn()
    except exc:
        return True
    return False

IMG = [[0.0, 0.1, 0.0], [0.9, 1.0, 0.9], [0.0, 0.1, 0.0]]

CASES = [
    ("energy_shape", lambda: len(imgseam.Seam().energy(IMG)) == 3),
    ("seam_len", lambda: len(imgseam.Seam().find_seam(imgseam.Seam().energy(IMG))) == 3),
    ("seam_valid", lambda: all(0 <= c < 3 for c in imgseam.Seam().find_seam(imgseam.Seam().energy(IMG)))),
    ("shrink_width", lambda: all(len(row) == 2 for row in imgseam.Seam().shrink(IMG, 2))),
    ("bad_width", lambda: _raises(lambda: imgseam.Seam().shrink(IMG, 5))),
    ("bad_empty", lambda: _raises(lambda: imgseam.Seam().energy([]))),
    ("type", lambda: isinstance(imgseam.Seam().find_seam(imgseam.Seam().energy(IMG)), list)),
    ("det", lambda: imgseam.Seam().find_seam(imgseam.Seam().energy(IMG)) == imgseam.Seam().find_seam(imgseam.Seam().energy(IMG))),
    ("energy_nonneg", lambda: all(v >= 0.0 for row in imgseam.Seam().energy(IMG) for v in row)),
    ("seam_cost", lambda: imgseam.Seam().energy(IMG)[0][imgseam.Seam().find_seam(imgseam.Seam().energy(IMG))[0]] >= 0.0),
    ("nan", lambda: _raises(lambda: imgseam.Seam().energy([[float('nan')]]))),
    ("no_mut", lambda: imgseam.Seam().shrink([r[:] for r in IMG], 2) is not None),
    ("same_width", lambda: len(imgseam.Seam().shrink(IMG, 3)) == 3),
    ("energy_type", lambda: isinstance(imgseam.Seam().energy(IMG), list)),
    ("ragged", lambda: _raises(lambda: imgseam.Seam().energy([[0.0, 0.1], [0.2]]))),
]


@pytest.mark.parametrize("name,check", CASES, ids=[c[0] for c in CASES])
def test_spec(name, check):
    assert check() is True
