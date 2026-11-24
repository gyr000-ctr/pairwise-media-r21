"""imgseam 核心 API（初始未实现）。"""


class Seam:
    def energy(self, image):
        """能量图"""
        raise NotImplementedError

    def find_seam(self, energy):
        """最小缝"""
        raise NotImplementedError

    def shrink(self, image, w):
        """裁到目标宽"""
        raise NotImplementedError
