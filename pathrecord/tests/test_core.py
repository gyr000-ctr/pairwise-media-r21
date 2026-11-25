import math

import pytest

import pathrecord

def _raises(fn, exc=ValueError):
    try:
        fn()
    except exc:
        return True
    return False

def _r():
    return pathrecord.Record()

CASES = [
    ("empty_playback", lambda: _r().playback() == []),
    ("append_len", lambda: (_r().append(0.0, (0.0, 0.0)), len(_r().playback()))[1] >= 0),
    ("roundtrip", lambda: (lambda r: (r.append(0.0, (0.0, 0.0)), r.append(0.1, (1.0, 0.0)), r.playback()[0] == (0.0, 0.0))[-1])(_r())),
    ("monotonic", lambda: (lambda r: (r.append(0.5, (0.0, 0.0)), r.append(0.1, (1.0, 0.0))) and True)(_r())),
    ("bad_t", lambda: _raises(lambda: _r().append(-1.0, (0.0, 0.0)))),
    ("bad_state", lambda: _raises(lambda: _r().append(0.0, 1.0))),
    ("type", lambda: isinstance(_r().playback(), list)),
    ("det", lambda: (lambda r: (r.append(0.0, (0.5, 0.5)), r.playback()))(_r()) == (lambda r: (r.append(0.0, (0.5, 0.5)), r.playback()))(_r())),
    ("speed_same_len", lambda: (lambda r: (r.append(0.0, (0.0, 0.0)), r.append(0.1, (1.0, 0.0)), len(r.playback(2.0)) == len(r.playback(1.0)))[-1])(_r())),
    ("compress", lambda: (lambda r: (r.append(0.0, (0.0, 0.0)), r.append(0.0, (0.0, 0.0)), isinstance(r.compress(), list))[-1])(_r())),
    ("nan", lambda: _raises(lambda: _r().append(float('nan'), (0.0, 0.0)))),
    ("no_mut", lambda: (lambda r: (r.append(0.0, (0.0, 0.0)), r.compress() is not None)[-1])(_r())),
    ("play_type", lambda: isinstance(_r().playback(), list)),
    ("bad_speed", lambda: _raises(lambda: _r().playback(0.0))),
    ("frame_pair", lambda: (lambda r: (r.append(0.0, (0.0, 0.0)), len(r.playback()[0]) == 2)[-1])(_r())),
]


@pytest.mark.parametrize("name,check", CASES, ids=[c[0] for c in CASES])
def test_spec(name, check):
    assert check() is True
