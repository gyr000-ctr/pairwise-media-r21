"""texpack 核心 API（初始未实现）。"""


class Bc1:
    def encode_block(self, block):
        """编码 4x4 块"""
        raise NotImplementedError

    def decode_block(self, data):
        """解码"""
        raise NotImplementedError

    def psnr(self, a, b):
        """PSNR"""
        raise NotImplementedError
