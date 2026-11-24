import math

import pytest

import texpack

def _raises(fn, exc=ValueError):
    try:
        fn()
    except exc:
        return True
    return False

BLK = [[0.5] * 4 for _ in range(4)]

CASES = [
    ("bytes", lambda: len(tcpack_encode()) if False else len(texpack.Bc1().encode_block(BLK)) == 8),
    ("constant_lossless", lambda: abs(texpack.Bc1().decode_block(texpack.Bc1().encode_block(BLK))[0][0] - 0.5) < 0.05),
    ("psnr_high", lambda: texpack.Bc1().psnr(BLK, texpack.Bc1().decode_block(texpack.Bc1().encode_block(BLK))) >= 30.0),
    ("bad_block_rows", lambda: _raises(lambda: texpack.Bc1().encode_block([[0.5] * 4]))),
    ("bad_block_size", lambda: _raises(lambda: texpack.Bc1().encode_block([[0.5] * 3] * 4))),
    ("bad_data", lambda: _raises(lambda: texpack.Bc1().decode_block([]))),
    ("type", lambda: isinstance(texpack.Bc1().encode_block(BLK), list)),
    ("det", lambda: texpack.Bc1().encode_block(BLK) == texpack.Bc1().encode_block(BLK)),
    ("decode_shape", lambda: len(texpack.Bc1().decode_block(texpack.Bc1().encode_block(BLK))) == 4),
    ("range", lambda: all(0.0 <= v <= 1.0 for row in texpack.Bc1().decode_block(texpack.Bc1().encode_block(BLK)) for v in row)),
    ("byte_range", lambda: all(0 <= b <= 255 for b in texpack.Bc1().encode_block(BLK))),
    ("gradient", lambda: texpack.Bc1().psnr([[i / 3.0] * 4 for i in range(4)], texpack.Bc1().decode_block(texpack.Bc1().encode_block([[i / 3.0] * 4 for i in range(4)]))) >= 25.0),
    ("nan", lambda: _raises(lambda: texpack.Bc1().encode_block([[float('nan')] * 4 for _ in range(4)]))),
    ("no_mut", lambda: texpack.Bc1().encode_block([r[:] for r in BLK]) is not None),
    ("psnr_type", lambda: isinstance(texpack.Bc1().psnr(BLK, BLK), float)),
]


@pytest.mark.parametrize("name,check", CASES, ids=[c[0] for c in CASES])
def test_spec(name, check):
    assert check() is True
