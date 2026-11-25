"""midisync：MIDI tempo map 的 tick <-> 秒换算。

时间轴模型
----------
MIDI 文件给出的是以 tick 为单位的拍点位置，以及若干条 tempo（BPM）事件。
拍长（每拍 tick 数）由文件头部的 PPQ 决定，且整首歌保持不变；tempo 事件
则在某个 tick 处切换速度。因此：

* 在相邻两个变速点之间速度恒定，tick 与秒是线性关系；
* tick -> 秒 必须按 tempo 分段积分，而不是"全曲用同一个 BPM"；
* 在变速点处函数连续：变速只影响它之后的时间，已经过去的时间不变。

本模块在一个排序的事件表上维护每段的"前缀秒数"，查询时用二分查找定位
所在段再做一次线性外推，复杂度 O(log n)，且不受 tick 绝对值影响。
"""

from __future__ import annotations

import bisect
import math
import numbers
import threading

__all__ = [
    "MidiSync",
    "MidiSyncError",
    "InvalidPpqError",
    "InvalidBpmError",
    "InvalidTickError",
    "InvalidTimeError",
    "DEFAULT_BPM",
]

#: 未显式设置 tempo 时采用的默认速度（与常见 MIDI 约定一致）。
DEFAULT_BPM = 120.0

_SECONDS_PER_MINUTE = 60.0


# ---------------------------------------------------------------------------
# 异常
# ---------------------------------------------------------------------------

class MidiSyncError(ValueError):
    """midisync 参数错误的基类。

    继承 :class:`ValueError`，因此按值错误捕获的代码仍然可用；同时每种
    非法输入都有独立的子类，便于调用方区分是 PPQ、BPM 还是 tick/时间出错。
    """


class InvalidPpqError(MidiSyncError):
    """构造参数 ppq 非法（非实数、非有限或不为正）。"""


class InvalidBpmError(MidiSyncError):
    """BPM 非法（非实数、非有限或不为正）。"""


class InvalidTickError(MidiSyncError):
    """tick 非法（非实数、非有限或为负）。"""


class InvalidTimeError(MidiSyncError):
    """秒值非法（非实数、非有限或为负）。"""


# ---------------------------------------------------------------------------
# 参数校验
# ---------------------------------------------------------------------------

def _as_finite_real(value, error, name, *, positive=False, non_negative=False):
    """把 *value* 归一化为有限 float，否则抛出 *error*。

    拒绝 bool（它是 int 的子类，但不是有意义的时值）以及所有非实数类型，
    并统一处理 NaN / ±inf（NaN 的比较恒为 False，单独用 isfinite 拦截）。
    """
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise error(f"{name} 必须是实数，收到 {type(value).__name__}: {value!r}")
    try:
        result = float(value)
    except (OverflowError, ValueError, TypeError):
        raise error(f"{name} 无法表示为有限浮点数: {value!r}") from None
    if not math.isfinite(result):
        raise error(f"{name} 必须是有限值，收到 {value!r}")
    if positive and result <= 0.0:
        raise error(f"{name} 必须大于 0，收到 {value!r}")
    if non_negative and result < 0.0:
        raise error(f"{name} 必须大于等于 0，收到 {value!r}")
    return result


# ---------------------------------------------------------------------------
# 主体
# ---------------------------------------------------------------------------

class MidiSync:
    """MIDI tempo map 时间轴换算器。

    典型用法::

        m = MidiSync(480)          # 每拍 480 tick
        m.add_tempo(0, 120.0)      # 0 号 tick 处 120 BPM
        m.add_tempo(480, 60.0)     # 第 1 拍后降速到 60 BPM
        m.tick_to_sec(960)         # -> 1.5

    读取路径（``tick_to_sec`` / ``sec_to_tick``）不加锁：它们只读取一个
    不可变快照引用；``add_tempo`` 在锁内构建好全新快照后一次性发布。
    因此并发读、以及"读的同时写入"都不会观察到半成品状态，也没有数据竞争。
    """

    __slots__ = ("_ppq", "_lock", "_events", "_cache")

    def __init__(self, ppq):
        """构造。

        :param ppq: 每拍 tick 数（PPQ / PPQN），必须为有限正实数。
        :raises InvalidPpqError: ppq 非法。
        """
        ppq_value = _as_finite_real(ppq, InvalidPpqError, "ppq", positive=True)
        self._ppq = ppq_value
        self._lock = threading.Lock()
        # 事件表：(tick, bpm)，按 tick 升序；tick 0 处一定有事件。
        self._events = [(0.0, DEFAULT_BPM)]
        # 不可变快照：(ticks, secs, secs_per_tick)。
        self._cache = self._build_cache()

    # -- 内部：由事件表构建只读快照 -------------------------------------

    def _build_cache(self):
        """根据当前事件表构建 (ticks, secs, deltas) 不可变快照。

        ``secs[i]`` 是从 0 号 tick 到事件 ``i`` 的累计秒数（分段积分）；
        ``deltas[i]`` 是第 ``i`` 段的每 tick 秒数。因为
        ``secs[i] = secs[i-1] + (ticks[i]-ticks[i-1]) * deltas[i-1]``，
        在事件 tick 处左右极限是同一个浮点数，变速点严格连续。
        """
        ppq = self._ppq
        events = self._events
        ticks = []
        deltas = []
        for tick, bpm in events:
            ticks.append(tick)
            # 每 tick 秒数 = (60 / bpm) / ppq，先除 BPM 再除 PPQ 以减小误差。
            deltas.append((_SECONDS_PER_MINUTE / bpm) / ppq)

        secs = [0.0]
        elapsed = 0.0
        for i in range(1, len(ticks)):
            elapsed += (ticks[i] - ticks[i - 1]) * deltas[i - 1]
            secs.append(elapsed)

        return (tuple(ticks), tuple(secs), tuple(deltas))

    # -- 写路径 ---------------------------------------------------------

    def add_tempo(self, tick, bpm):
        """在 *tick* 处设置新的速度 *bpm*。

        * 同一 tick 重复设置时覆盖旧值（保持函数单值）；
        * tick 之前的时间不受影响，变速点处保持连续；
        * 允许乱序添加，内部始终按 tick 排序。

        :raises InvalidTickError: tick 非有限实数或为负。
        :raises InvalidBpmError: bpm 非有限实数或不为正。
        """
        tick_value = _as_finite_real(
            tick, InvalidTickError, "tick", non_negative=True
        )
        bpm_value = _as_finite_real(bpm, InvalidBpmError, "bpm", positive=True)

        with self._lock:
            events = self._events
            # (tick,) 与 (tick, bpm) 比较时，前缀相等则较短的元组更小，
            # 因此 bisect_left 恰好返回第一个 tick >= tick_value 的位置。
            index = bisect.bisect_left(events, (tick_value,))
            if index < len(events) and events[index][0] == tick_value:
                events[index] = (tick_value, bpm_value)
            else:
                events.insert(index, (tick_value, bpm_value))
            # 先完整构建新快照，再一次性发布，读取方永远只看到完整快照。
            self._cache = self._build_cache()

    # -- 读路径 ---------------------------------------------------------

    def tick_to_sec(self, tick):
        """把 MIDI tick 换算为从 0 tick 起算的秒数（float）。

        采用分段积分 + 二分定位，结果与"逐 tick 累加"的偏差在 1e-9 秒内。

        :raises InvalidTickError: tick 非有限实数或为负。
        """
        ticks, secs, deltas = self._cache
        if isinstance(tick, bool) or not isinstance(tick, numbers.Real):
            raise InvalidTickError(
                f"tick 必须是实数，收到 {type(tick).__name__}: {tick!r}"
            )
        try:
            value = float(tick)
        except (OverflowError, ValueError, TypeError):
            raise InvalidTickError(
                f"tick 无法表示为有限浮点数: {tick!r}"
            ) from None
        if not math.isfinite(value):
            raise InvalidTickError(f"tick 必须是有限值，收到 {tick!r}")
        if value < 0.0:
            raise InvalidTickError(f"tick 必须大于等于 0，收到 {tick!r}")

        index = bisect.bisect_right(ticks, value) - 1
        return secs[index] + (value - ticks[index]) * deltas[index]

    def sec_to_tick(self, sec):
        """把秒数反算为 tick（float），是 :meth:`tick_to_sec` 的逆运算。

        :raises InvalidTimeError: sec 非有限实数或为负。
        """
        ticks, secs, deltas = self._cache
        if isinstance(sec, bool) or not isinstance(sec, numbers.Real):
            raise InvalidTimeError(
                f"sec 必须是实数，收到 {type(sec).__name__}: {sec!r}"
            )
        try:
            value = float(sec)
        except (OverflowError, ValueError, TypeError):
            raise InvalidTimeError(
                f"sec 无法表示为有限浮点数: {sec!r}"
            ) from None
        if not math.isfinite(value):
            raise InvalidTimeError(f"sec 必须是有限值，收到 {sec!r}")
        if value < 0.0:
            raise InvalidTimeError(f"sec 必须大于等于 0，收到 {sec!r}")

        index = bisect.bisect_right(secs, value) - 1
        if index < 0:
            index = 0
        last = len(ticks) - 1
        if index > last:
            index = last
        return ticks[index] + (value - secs[index]) / deltas[index]
