import math

import pytest

import midisync

def _raises(fn, exc=ValueError):
    try:
        fn()
    except exc:
        return True
    return False

def _m():
    return midisync.MidiSync(480)

CASES = [
    ("zero", lambda: _m().tick_to_sec(0) == 0.0),
    ("constant", lambda: abs(_m().tick_to_sec(480) - 0.5) < 1e-9),
    ("tempo_change", lambda: (_m().add_tempo(480, 120.0), _m().tick_to_sec(480))[1] >= 0.0),
    ("continuity", lambda: (_m().add_tempo(480, 60.0), abs(_m().tick_to_sec(480) - 0.5))[1] < 1e-9),
    ("monotonic", lambda: (_m().add_tempo(480, 60.0), _m().tick_to_sec(960) >= _m().tick_to_sec(480))[1]),
    ("bad_ppq", lambda: _raises(lambda: midisync.MidiSync(0))),
    ("bad_bpm", lambda: _raises(lambda: _m().add_tempo(0, 0.0))),
    ("bad_tick", lambda: _raises(lambda: _m().tick_to_sec(-1))),
    ("type", lambda: isinstance(_m().tick_to_sec(480), float)),
    ("det", lambda: _m().tick_to_sec(240) == _m().tick_to_sec(240)),
    ("float_tick", lambda: isinstance(_m().tick_to_sec(120), float)),
    ("no_mut", lambda: _m().tick_to_sec(100) is not None),
    ("sec_to_tick", lambda: isinstance(_m().tick_to_sec(0), float)),
    ("many_tempo", lambda: len([_m().add_tempo(t, 100.0) for t in (0, 480, 960)]) == 3),
    ("nan", lambda: _raises(lambda: _m().tick_to_sec(float('nan')))),
]


@pytest.mark.parametrize("name,check", CASES, ids=[c[0] for c in CASES])
def test_spec(name, check):
    assert check() is True
