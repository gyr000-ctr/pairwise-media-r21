"""pathrecord 核心 API（初始未实现）。"""


class Record:
    def __init__(self):
        """构造"""
        raise NotImplementedError

    def append(self, t, state):
        """录制"""
        raise NotImplementedError

    def playback(self, speed=1.0):
        """回放"""
        raise NotImplementedError

    def compress(self):
        """压缩"""
        raise NotImplementedError
