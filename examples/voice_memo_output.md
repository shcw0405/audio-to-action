# Example — voice memo output

What the skill produces when the recording is classified as `voice_memo` —
a single speaker thinking out loud, often half-formed sentences, often
self-addressed ("提醒一下我自己...", "回头再看一下...").

The output is a tidy notebook page, not a meeting summary.

---

# 语音备忘录整理

> 录音：`2026-05-04-monday-walk-memo.m4a` · 时长 6m22s · 1 位发言人
> 分类：`voice_memo`，置信度 0.92

## 一、清理后的笔记

> 这是对原始录音的**事实性整理**：去除了 "嗯/啊/那个" 等无意义填充，
> 修整了断句，但**没有添加任何新内容**。

走在去工位的路上想了一下下周的安排。第一件事是 baseline 那块要确认一下
是不是 warmup step 数对不齐导致的 0.5 个点差距，要去看一下 paper 附录
里的训练 schedule。第二是 attention 那块的消融，之前一直拖着没开 head
数那一组，下周得让自己排上。

另外想到一个事，可能跟主线无关：上周看的 RoPE 那篇 paper 里的位置编码
形式，可以拿来跟我们的 sinusoidal 做个对比，但这是个 nice-to-have，不
要影响主线。

最后提醒自己，周五前要把上次组会布置的 ImageNet baseline 整理出来发给
导师。code 也要顺一下，不要直接发当前那一份。

## 二、核心想法

- 想清楚 baseline 0.5 点差距的根因（warmup 还是别的？）
- 把 attention head 数消融真正排上日程，不再拖
- RoPE vs sinusoidal 是一个 nice-to-have，不动主线
- code 在发给导师前必须先整理

## 三、可执行 Todo

| 优先级 | Todo | 触发条件 / 截止 | 依据 |
| --- | --- | --- | --- |
| 高 | 跑通 ImageNet baseline，整理 code，发给导师 | 周五前 | 录音 05:48-06:12 |
| 高 | 对照 paper 附录确认 warmup schedule 是否对齐 | 本周 | 录音 00:31-00:54 |
| 中 | 启动 head 数 ∈ {8,12,16,24} × 3 seed 的消融 | 本周内 | 录音 01:18-01:42 |
| 低（nice-to-have） | RoPE vs sinusoidal 的小对比实验 | 不动主线 | 录音 03:05-03:30 |

## 四、后续可展开方向

- 如果 baseline 0.5 个点的根因确认是 warmup，可以写一段 lessons-learned
  贴在团队 wiki 上 —— 之后别人复现 paper 时直接命中。
- head 数消融跑完后，可以顺便把 `pre-norm vs post-norm` 也做一组——记忆
  里之前没专门跑过，能一并交差。
- RoPE 的对比可以等暑期带新人做，作为 onboarding 任务。
