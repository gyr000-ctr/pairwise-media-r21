"""imgseam 核心 API：接缝裁剪（seam carving）。

约定：
- 能量图：梯度幅值 sqrt(gx^2 + gy^2)。中心差分，边界钳制（edge replicate），
  即边界处用单侧差分，角点两个方向均为单侧。
- 最小缝：动态规划，8 连通（相邻行缝列号至多相差 1），平局取最左列；
  与逐格枚举所有前驱的暴力 DP 使用相同浮点加法顺序，代价差为 0。
- 裁剪：在初始能量图上找最小缝，图像与能量图同步删除该缝，
  重复到目标宽度。能量图总量每一步严格下降被删缝代价（可证明单调），
  且每行每次恰好删除一列。整个过程不修改输入。

Seam 为无状态对象，方法内部仅使用局部变量，多线程共享同一实例并发安全。
提供 numpy 向量化快路径与等价的纯 Python 回退，两路运算顺序、平局规则一致，
返回结果位相同。
"""

import math

try:
    import numpy as _np
except ImportError:  # pragma: no cover - 纯 Python 回退路径
    _np = None

__all__ = ["Seam"]


# --------------------------------------------------------------------------
# 输入校验
# --------------------------------------------------------------------------

def _check_grid(grid, name):
    """校验二维数值网格，返回 (行数, 列数)。

    结构非法（非 list、空、行长短不一、含空行）-> ValueError；
    含 NaN/Inf -> ValueError；元素不是数值 -> TypeError。
    """
    if not isinstance(grid, list):
        raise TypeError("%s 必须是二维列表" % name)
    h = len(grid)
    if h == 0:
        raise ValueError("%s 不能为空" % name)
    first = grid[0]
    if not isinstance(first, list) or len(first) == 0:
        raise ValueError("%s 必须是非空的二维列表" % name)
    w = len(first)
    for row in grid:
        if not isinstance(row, list) or len(row) != w:
            raise ValueError("%s 必须是矩形二维列表（存在空行或长短不一的行）" % name)
        for v in row:
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise TypeError("%s 含有非数值元素" % name)
            if not math.isfinite(v):
                raise ValueError("%s 含有非有限值（NaN/Inf）" % name)
    return h, w


# --------------------------------------------------------------------------
# 纯 Python 实现（numpy 不可用时的回退，同时是正确性基准）
# --------------------------------------------------------------------------

def _energy_py(image):
    h = len(image)
    w = len(image[0])
    out = [[0.0] * w for _ in range(h)]
    last_i = h - 1
    last_j = w - 1
    for i in range(h):
        row = image[i]
        up = image[i - 1 if i > 0 else 0]
        down = image[i + 1 if i < last_i else last_i]
        orow = out[i]
        for j in range(w):
            jl = j - 1 if j > 0 else 0
            jr = j + 1 if j < last_j else last_j
            gx = row[jr] - row[jl]
            gy = down[j] - up[j]
            orow[j] = math.sqrt(gx * gx + gy * gy)
    return out


def _find_seam_py(energy):
    """动态规划最小缝，返回每行列号组成的 list（长度 = 行数）。"""
    h = len(energy)
    w = len(energy[0])
    prev = [float(v) for v in energy[0]]
    back = [[0] * w for _ in range(h)]
    for i in range(1, h):
        erow = energy[i]
        brow = back[i]
        cur = [0.0] * w

        # 左边界 j=0：前驱仅 0、1
        c0 = prev[0]
        if w > 1 and prev[1] < c0:
            base, brow[0] = prev[1], 1
        else:
            base, brow[0] = c0, 0
        cur[0] = base + erow[0]

        # 中间列：前驱 j-1 / j / j+1，严格小于 => 平局保留最左
        for j in range(1, w - 1):
            a = prev[j - 1]
            b = prev[j]
            c = prev[j + 1]
            if a <= b:
                if a <= c:
                    m, k = a, j - 1
                else:
                    m, k = c, j + 1
            elif b <= c:
                m, k = b, j
            else:
                m, k = c, j + 1
            brow[j] = k
            cur[j] = m + erow[j]

        # 右边界 j=w-1：前驱仅 w-2、w-1
        if w > 1:
            j = w - 1
            a, b = prev[j - 1], prev[j]
            if a <= b:
                base, k = a, j - 1
            else:
                base, k = b, j
            brow[j] = k
            cur[j] = base + erow[j]

        prev = cur

    best = 0
    bestv = prev[0]
    for j in range(1, w):
        if prev[j] < bestv:
            bestv, best = prev[j], j

    seam = [0] * h
    seam[h - 1] = best
    for i in range(h - 1, 0, -1):
        best = back[i][best]
        seam[i - 1] = best
    return seam


def _remove_seam_py(grid, seam):
    return [row[:c] + row[c + 1:] for row, c in zip(grid, seam)]


def _shrink_py(image, w):
    """carve-map 语义：图像与初始能量图同步删缝。"""
    cur = [row[:] for row in image]
    emap = _energy_py(cur)
    while len(cur[0]) > w:
        seam = _find_seam_py(emap)
        cur = _remove_seam_py(cur, seam)
        emap = _remove_seam_py(emap, seam)
    return cur


# --------------------------------------------------------------------------
# numpy 快路径（运算顺序、平局规则与纯 Python 路径逐格一致）
# --------------------------------------------------------------------------

def _energy_np(a):
    """a: float64 ndarray (h, w)，返回同形状梯度幅值 ndarray。"""
    padded = _np.pad(a, 1, mode="edge")
    gx = padded[1:-1, 2:] - padded[1:-1, :-2]
    gy = padded[2:, 1:-1] - padded[:-2, 1:-1]
    return _np.sqrt(gx * gx + gy * gy)


def _find_seam_np(e):
    """e: 能量 ndarray，返回 python list（每行列号），最左平局。

    每行仅做向量化比较（无 stack/argmin），平局规则与 _find_seam_py 一致：
    L<=C 且 L<=R 取左；否则 R<C 取右；其余取中。
    """
    h, w = e.shape
    if w == 1:
        return [0] * h
    prev = e[0].copy()
    back = _np.empty((h, w), dtype=_np.intp)
    cols = _np.arange(w)
    left = _np.empty(w)
    right = _np.empty(w)
    inf = _np.inf
    for i in range(1, h):
        left[0] = inf
        left[1:] = prev[:-1]          # 前驱 j-1
        right[-1] = inf
        right[:-1] = prev[1:]         # 前驱 j+1
        val = _np.minimum(_np.minimum(left, prev), right)
        idx = _np.ones(w, dtype=_np.intp)
        idx[right < prev] = 2
        idx[(left <= prev) & (left <= right)] = 0
        back[i] = cols + idx - 1
        prev = val + e[i]
    best = int(_np.argmin(prev))
    seam = [0] * h
    seam[h - 1] = best
    for i in range(h - 1, 0, -1):
        best = int(back[i, best])
        seam[i - 1] = best
    return seam


def _shrink_np(image, w):
    """carve-map 语义：图像与初始能量图同步删缝。"""
    cur = _np.asarray(image, dtype=_np.float64)  # 构造拷贝，不触及输入
    emap = _energy_np(cur)
    h = cur.shape[0]
    rows = _np.arange(h)
    while cur.shape[1] > w:
        seam = _find_seam_np(emap)
        mask = _np.ones(cur.shape, dtype=bool)
        mask[rows, seam] = False
        cur = cur[mask].reshape(h, -1)
        emap = emap[mask].reshape(h, -1)
    return cur.tolist()


# --------------------------------------------------------------------------
# 公开 API
# --------------------------------------------------------------------------

class Seam:
    """无状态接缝裁剪器；同一实例可被多线程并发调用。"""

    def energy(self, image):
        """计算梯度幅值能量图，返回与输入同形状的 list[list[float]]。"""
        _check_grid(image, "image")
        if _np is not None:
            return _energy_np(_np.asarray(image, dtype=_np.float64)).tolist()
        return _energy_py(image)

    def find_seam(self, energy):
        """返回最小缝（每行一列的 list）；平局取最左，与暴力 DP 一致。"""
        _check_grid(energy, "energy")
        if _np is not None:
            return _find_seam_np(_np.asarray(energy, dtype=_np.float64))
        return _find_seam_py(energy)

    def shrink(self, image, w):
        """把图像裁剪到目标宽度 w，返回新图像（不修改输入）。

        0 <= w <= 当前宽度，否则 ValueError；w 非 int 时 TypeError。
        """
        _check_grid(image, "image")
        if isinstance(w, bool) or not isinstance(w, int):
            raise TypeError("目标宽度必须是 int，收到 %r" % type(w).__name__)
        width = len(image[0])
        if w < 0 or w > width:
            raise ValueError("非法目标宽度 %d：需满足 0 <= w <= %d" % (w, width))
        if w == width:
            return [row[:] for row in image]
        if _np is not None:
            return _shrink_np(image, w)
        return _shrink_py(image, w)
