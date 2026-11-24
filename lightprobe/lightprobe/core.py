"""lightprobe 核心 API（初始未实现）。"""


class Sh:
    def project(self, samples, dirs):
        """投影系数"""
        raise NotImplementedError

    def reconstruct(self, coeffs, d):
        """重建"""
        raise NotImplementedError

    def constant_check(self, coeffs):
        """DC 判定"""
        raise NotImplementedError
