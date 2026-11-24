# texpack

## 题面（可直接粘贴）

子目录：texpack。BC1 块压缩编码。约束：每 4x4 块输出 8 字节；解码后与原始块 PSNR ≥30 dB；端点选择用最小二乘而非取极值（与暴力端点搜索差 ≤1 dB）；恒定块无损；10 万块不超过 800 ms；非法块尺寸可区分报错；并发安全。验收：cd texpack && python -m pytest tests -q。

## 边界要求（评审侧隐藏用例判分）

- 并发安全
- 非有限输入分类报错
- 性能上界按题面

## 运行方式

```bash
cd texpack && python -m pytest tests -q
```

初始 15 failed。

## 字段

- 所属领域：游戏、图形与多媒体
- 子方向：图形渲染
- 任务类型：Bugfix
- 语言/框架：Python 3, pytest
- 环境可复现等级：无外部依赖
