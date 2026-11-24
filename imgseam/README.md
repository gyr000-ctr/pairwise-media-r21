# imgseam

## 题面（可直接粘贴）

子目录：imgseam。接缝裁剪（seam carving）。约束：能量图为梯度幅值；最小缝与动态规划暴力解一致（≤1e-9）；删除后每行恰少一列；能量单调下降；非法目标宽度可区分报错；100 万像素不超过 800 ms；并发安全。验收：cd imgseam && python -m pytest tests -q。

## 边界要求（评审侧隐藏用例判分）

- 并发安全
- 非有限输入分类报错
- 性能上界按题面

## 运行方式

```bash
cd imgseam && python -m pytest tests -q
```

初始 15 failed。

## 字段

- 所属领域：游戏、图形与多媒体
- 子方向：图像处理
- 任务类型：Bugfix
- 语言/框架：Python 3, pytest
- 环境可复现等级：无外部依赖
