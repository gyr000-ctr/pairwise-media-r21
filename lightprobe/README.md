# lightprobe

## 题面（可直接粘贴）

子目录：lightprobe。球谐光照探针（L2）。约束：9 个系数投影与蒙特卡洛积分差 ≤5%；重建与原始函数误差 ≤10%；常量环境只填充 DC 项（其余 ≤1e-9）；非法采样数可区分报错；1 万采样不超过 500 ms；并发安全。验收：cd lightprobe && python -m pytest tests -q。

## 边界要求（评审侧隐藏用例判分）

- 并发安全
- 非有限输入分类报错
- 性能上界按题面

## 运行方式

```bash
cd lightprobe && python -m pytest tests -q
```

初始 15 failed。

## 字段

- 所属领域：游戏、图形与多媒体
- 子方向：图形渲染
- 任务类型：Bugfix
- 语言/框架：Python 3, pytest
- 环境可复现等级：无外部依赖
