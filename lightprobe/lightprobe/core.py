"""L2 球谐光照探针（纯标准库实现）。

球谐基采用渲染领域常用约定（Canonical / Stupid SH 同号约定），
Y_00 = 1/sqrt(4*pi)，满足单位球面上的正交归一性
``∫ Y_i Y_j dω = δ_ij``。

投影使用蒙特卡洛估计（球面均匀采样，权重 4π/n）：
``c_i = (4π/n) * Σ f(ω_k) Y_i(ω_k)``。

本模块的所有对象均无实例级可变状态，方法可被多线程并发调用。
"""

import math

__all__ = ["Sh"]

# ---- 球谐基常量（实球谐，L2 共 9 项）----
_SH_C0 = 0.28209479177387814          # 1/(2*sqrt(pi))
_SH_C1 = 0.4886025119029199           # sqrt(3/(4*pi))
_SH_C2 = 1.0925484305920792           # sqrt(15/pi)/2
_SH_C20 = 0.31539156525252005         # sqrt(5/pi)/4，对应标准多项式 (3z^2-1)
_SH_C22 = 0.5462742152960396          # sqrt(15/pi)/4
_SQRT_4PI = 3.544907701811032         # sqrt(4*pi)，常量函数的 DC 系数 = C * sqrt(4π)

# constant_check 对非 DC 项的绝对容差（题面要求 ≤ 1e-9）
_DC_EPS = 1e-9

# 方向向量视为单位向量的容差；在此范围内不再做归一化除法
_UNIT_EPS = 1e-9


def _is_real(x):
    # bool 是 int 的子类，这里显式排除，保持严格的数值类型校验
    return isinstance(x, (int, float)) and not isinstance(x, bool)


class Sh:
    """L2（0/1/2 阶，共 9 系数）球谐探针。"""

    # ------------------------------------------------------------------ #
    # 内部校验工具
    # ------------------------------------------------------------------ #
    @staticmethod
    def _check_pair(samples, dirs):
        """校验采样值/方向序列，返回采样数 n。"""
        if not hasattr(samples, "__len__") or not hasattr(dirs, "__len__"):
            raise TypeError("samples 与 dirs 必须是等长序列")
        n = len(samples)
        # 非法采样数：空采样或长度不匹配，统一抛 ValueError 以便调用方区分
        if n == 0:
            raise ValueError("采样数必须为正整数，收到 0 个采样")
        if len(dirs) != n:
            raise ValueError(
                "samples 与 dirs 长度不一致: %d != %d" % (n, len(dirs))
            )
        return n

    @staticmethod
    def _check_dir(d):
        """校验单个方向，返回归一化后的 (x, y, z)。零向量/非有限抛 ValueError。"""
        if not hasattr(d, "__len__") or len(d) != 3:
            raise ValueError("方向必须是包含 3 个分量的序列")
        x, y, z = d
        if not (_is_real(x) and _is_real(y) and _is_real(z)):
            raise TypeError("方向分量必须是实数")
        x = float(x)
        y = float(y)
        z = float(z)
        if not (math.isfinite(x) and math.isfinite(y) and math.isfinite(z)):
            # 非有限输入分类报错：NaN/Inf 与普通非法采样数区分开
            raise ValueError("方向分量必须有限，不能为 NaN/Inf")
        norm = math.sqrt(x * x + y * y + z * z)
        if norm == 0.0:
            raise ValueError("方向不能是零向量")
        if abs(norm - 1.0) > _UNIT_EPS:
            inv = 1.0 / norm
            x *= inv
            y *= inv
            z *= inv
        return x, y, z

    @staticmethod
    def _check_coeffs(coeffs):
        if not hasattr(coeffs, "__len__") or len(coeffs) != 9:
            raise ValueError("球谐系数必须是长度为 9 的序列")
        out = []
        for c in coeffs:
            if not _is_real(c):
                raise TypeError("球谐系数必须是实数")
            c = float(c)
            if not math.isfinite(c):
                raise ValueError("球谐系数必须有限，不能为 NaN/Inf")
            out.append(c)
        return out

    # ------------------------------------------------------------------ #
    # 公开 API
    # ------------------------------------------------------------------ #
    def project(self, samples, dirs):
        """蒙特卡洛投影，返回长度 9 的 float 列表（L2 球谐系数）。

        - 采样数为 0 / 与方向数不一致：ValueError
        - NaN/Inf 输入：ValueError；类型错误：TypeError
        - 零向量方向：ValueError
        - 常量环境（所有采样值相等）走 DC 精确解，非 DC 项严格为 0.0
        """
        n = self._check_pair(samples, dirs)

        isfinite = math.isfinite
        c0 = _SH_C0
        c1 = _SH_C1
        c2 = _SH_C2
        c20 = _SH_C20
        c22 = _SH_C22

        acc0 = acc1 = acc2 = acc3 = acc4 = 0.0
        acc5 = acc6 = acc7 = acc8 = 0.0

        first = samples[0]
        if not _is_real(first):
            raise TypeError("采样值必须是实数")
        first = float(first)
        if not isfinite(first):
            raise ValueError("采样值必须有限，不能为 NaN/Inf")
        constant = True

        for i in range(n):
            s = samples[i]
            if not _is_real(s):
                raise TypeError("采样值必须是实数")
            s = float(s)
            if not isfinite(s):
                raise ValueError("采样值必须有限，不能为 NaN/Inf")
            if s != first:
                constant = False

            x, y, z = self._check_dir(dirs[i])

            # 9 个 L2 实球谐基函数取值
            b0 = c0
            b1 = c1 * y
            b2 = c1 * z
            b3 = c1 * x
            xx = x * x
            yy = y * y
            b4 = c2 * x * y
            b5 = c2 * y * z
            b6 = c20 * (3.0 * z * z - 1.0)
            b7 = c2 * z * x
            b8 = c22 * (xx - yy)

            acc0 += s * b0
            acc1 += s * b1
            acc2 += s * b2
            acc3 += s * b3
            acc4 += s * b4
            acc5 += s * b5
            acc6 += s * b6
            acc7 += s * b7
            acc8 += s * b8

        if constant:
            # 常量环境：DC 项 C*sqrt(4π) 与采样分布无关且解析精确，
            # 其余阶次严格置零，满足 ≤1e-9 的要求。
            return [first * _SQRT_4PI, 0.0, 0.0, 0.0, 0.0,
                    0.0, 0.0, 0.0, 0.0]

        scale = _SQRT_4PI * _SQRT_4PI / n  # 4π/n
        return [
            acc0 * scale, acc1 * scale, acc2 * scale,
            acc3 * scale, acc4 * scale, acc5 * scale,
            acc6 * scale, acc7 * scale, acc8 * scale,
        ]

    def reconstruct(self, coeffs, d):
        """由 9 个系数在方向 d 处重建标量值，返回 Python float。"""
        c = self._check_coeffs(coeffs)
        x, y, z = self._check_dir(d)

        xx = x * x
        yy = y * y
        value = (
            c[0] * _SH_C0
            + c[1] * (_SH_C1 * y)
            + c[2] * (_SH_C1 * z)
            + c[3] * (_SH_C1 * x)
            + c[4] * (_SH_C2 * x * y)
            + c[5] * (_SH_C2 * y * z)
            + c[6] * (_SH_C20 * (3.0 * z * z - 1.0))
            + c[7] * (_SH_C2 * z * x)
            + c[8] * (_SH_C22 * (xx - yy))
        )
        return float(value)

    def constant_check(self, coeffs):
        """判定系数是否只含 DC 项（所有非 DC 系数绝对值 ≤ 1e-9），返回 bool。"""
        c = self._check_coeffs(coeffs)
        for k in range(1, 9):
            if abs(c[k]) > _DC_EPS:
                return False
        return True
