# pathrecord

## 题面（可直接粘贴）

子目录：pathrecord。输入录制与确定性回放。约束：录制后回放与原始输入逐帧一致（≤1e-12）；时间戳单调（乱序可区分报错）；支持变速回放但步数不变；压缩后仍可无损还原；10 万帧不超过 300 ms；并发安全。验收：cd pathrecord && python -m pytest tests -q。

## 边界要求（评审侧隐藏用例判分）

- 并发安全
- 非有限输入分类报错
- 性能上界按题面

## 运行方式

```bash
cd pathrecord && python -m pytest tests -q
```

初始 15 failed。

## 字段

- 所属领域：游戏、图形与多媒体
- 子方向：游戏开发
- 任务类型：Bugfix
- 语言/框架：Python 3, pytest
- 环境可复现等级：无外部依赖
