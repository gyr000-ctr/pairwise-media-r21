"""pathrecord 核心 API：输入录制与确定性回放。

约束实现要点：
- 回放与原始输入逐帧一致（原样保存，零误差，远优于 1e-12）；
- 时间戳要求单调不减：乱序数据在 playback()/compress() 时抛出
  可区分的 NonMonotonicError（append 本身不拒绝，便于先录后验）；
- 变速回放步数不变：playback(speed) 校验速度合法，但帧序列不变；
- compress() 为游程编码（RLE），不修改原录制，decompress() 可无损还原；
- 所有公开方法持锁，并发安全；10 万帧录制/回放远低于 300 ms。
"""

from __future__ import annotations

import math
import threading

__all__ = [
    "Record",
    "RecordError",
    "NonFiniteValueError",
    "InvalidTimestampError",
    "InvalidStateError",
    "InvalidSpeedError",
    "NonMonotonicError",
]

_NUMBER = (int, float)


class RecordError(ValueError):
    """pathrecord 所有校验错误的基类（ValueError 的子类，可按类别区分）。"""


class NonFiniteValueError(RecordError):
    """输入包含 NaN 或 ±inf（非有限输入）。"""


class InvalidTimestampError(RecordError):
    """时间戳非法（类型错误或小于 0）。"""


class InvalidStateError(RecordError):
    """状态非法（不是数值元组）。"""


class InvalidSpeedError(RecordError):
    """回放速度非法（类型错误或 <= 0）。"""


class NonMonotonicError(RecordError):
    """时间戳乱序（非单调不减）。"""


def _is_num(x):
    return isinstance(x, _NUMBER) and not isinstance(x, bool)


class Record:
    """输入帧录制器：append 录制，playback 确定性回放，compress 无损压缩。"""

    def __init__(self):
        self._lock = threading.Lock()
        self._frames = []          # list[(t: float, state: tuple[float, ...])]
        self._monotonic = True     # 已录制时间戳是否单调不减

    # ---------------- 校验 ----------------

    @staticmethod
    def _check_t(t):
        if not _is_num(t):
            raise InvalidTimestampError(
                "timestamp must be a real number, got %r" % (t,))
        if not math.isfinite(t):
            raise NonFiniteValueError(
                "timestamp must be finite (no NaN/inf), got %r" % (t,))
        if t < 0:
            raise InvalidTimestampError(
                "timestamp must be >= 0, got %r" % (t,))

    @staticmethod
    def _check_state(state):
        if not isinstance(state, tuple):
            raise InvalidStateError(
                "state must be a tuple of finite numbers, got %r" % (state,))
        for v in state:
            if not _is_num(v):
                raise InvalidStateError(
                    "state components must be real numbers, got %r" % (v,))
            if not math.isfinite(v):
                raise NonFiniteValueError(
                    "state components must be finite (no NaN/inf), got %r" % (v,))

    # ---------------- 录制 ----------------

    def append(self, t, state):
        """录制一帧。t 须为 >= 0 的有限实数，state 须为有限实数元组。"""
        self._check_t(t)
        self._check_state(state)
        t = float(t)
        state = tuple(float(v) for v in state)
        with self._lock:
            if self._frames and t < self._frames[-1][0]:
                self._monotonic = False
            self._frames.append((t, state))

    # ---------------- 回放 ----------------

    def playback(self, speed=1.0):
        """确定性回放：返回状态列表（与录制逐帧一致）。

        speed 必须为有限正数；变速只影响播放节奏，步数（帧数）不变。
        若录制的时间戳乱序，抛出 NonMonotonicError。
        """
        if not _is_num(speed):
            raise InvalidSpeedError(
                "speed must be a real number, got %r" % (speed,))
        if not math.isfinite(speed):
            raise NonFiniteValueError(
                "speed must be finite (no NaN/inf), got %r" % (speed,))
        if speed <= 0:
            raise InvalidSpeedError("speed must be > 0, got %r" % (speed,))
        with self._lock:
            if not self._monotonic:
                raise NonMonotonicError(
                    "timestamps are not non-decreasing; recording is ambiguous")
            return [state for _, state in self._frames]

    # ---------------- 压缩 ----------------

    def compress(self):
        """游程编码压缩，返回 list[(t, state, count)]，不修改原录制。"""
        with self._lock:
            if not self._monotonic:
                raise NonMonotonicError(
                    "timestamps are not non-decreasing; recording is ambiguous")
            frames = list(self._frames)
        out = []
        for t, state in frames:
            if out and out[-1][0] == t and out[-1][1] == state:
                prev = out[-1]
                out[-1] = (prev[0], prev[1], prev[2] + 1)
            else:
                out.append((t, state, 1))
        return out

    @classmethod
    def decompress(cls, compressed):
        """将 compress() 的产物无损还原为一个新的 Record。"""
        record = cls()
        frames = []
        for entry in compressed:
            try:
                t, state, count = entry
            except (TypeError, ValueError):
                raise InvalidStateError(
                    "compressed entries must be (t, state, count), got %r"
                    % (entry,)) from None
            cls._check_t(t)
            cls._check_state(state)
            if not _is_num(count) or count < 1:
                raise InvalidStateError(
                    "run count must be a positive integer, got %r" % (count,))
            t = float(t)
            state = tuple(float(v) for v in state)
            if frames and t < frames[-1][0]:
                record._monotonic = False
            frames.extend([(t, state)] * int(count))
        record._frames = frames
        return record

    # ---------------- 辅助 ----------------

    def frames(self):
        """返回完整帧序列 list[(t, state)] 的拷贝。"""
        with self._lock:
            return list(self._frames)

    def __len__(self):
        with self._lock:
            return len(self._frames)
