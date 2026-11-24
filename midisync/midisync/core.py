"""midisync 核心 API（初始未实现）。"""


class MidiSync:
    def __init__(self, ppq):
        """构造"""
        raise NotImplementedError

    def add_tempo(self, tick, bpm):
        """加变速点"""
        raise NotImplementedError

    def tick_to_sec(self, tick):
        """tick 转秒"""
        raise NotImplementedError
