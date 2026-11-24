# midisync

## 题面（可直接粘贴）

子目录：midisync。MIDI 时间轴换算（tempo map）。约束：tick→秒必须按 tempo 分段积分（与逐 tick 累加差 ≤1e-9）；变速点处连续；BPM 变化不影响已过去时间；非法 BPM/tick 可区分报错；10 万次换算不超过 200 ms；并发安全。验收：cd midisync && python -m pytest tests -q。

## 边界要求（评审侧隐藏用例判分）

- 并发安全
- 非有限输入分类报错
- 性能上界按题面

## 运行方式

```bash
cd midisync && python -m pytest tests -q
```

初始 15 failed。

## 字段

- 所属领域：游戏、图形与多媒体
- 子方向：音视频处理
- 任务类型：Bugfix
- 语言/框架：Python 3, pytest
- 环境可复现等级：无外部依赖
