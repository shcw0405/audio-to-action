# Example — casual discussion output

What the skill produces when the recording is classified as
`casual_discussion` (an ad-hoc lab chat, no clear task assignment yet).

Notice: **no per-person tasks, no message drafts.** Casual chats are not
meetings; the skill must not pretend they are. The most valuable artifact
here is a clear summary of where the discussion landed and what remains
open.

---

# 临时讨论整理

> 录音：`2026-05-04-coffee-chat.mp3` · 时长 14m08s · 2 位发言人
> 分类：`casual_discussion`，置信度 0.71
> 说话人映射：未提供

## 一、讨论背景

两人在临时讨论一个新的 idea：能否用更轻量的 attention 替换当前 baseline
里的标准 attention，目的是降低长序列下的显存。讨论是开放式的，没有形
成本周要做的具体任务。

## 二、核心观点

- 现在 baseline 在 4k token 长度下显存吃紧，是一个"被忽略的瓶颈"
  （依据：02:31）。
- linear attention 的近似精度在他们这个数据集上历史结果不算稳定，需要
  实验才能下结论（依据：05:14）。
- 如果做，建议先在小模型 + 短序列上 sanity check，再放大；不要直接
  上 baseline（依据：08:42）。
- 也提到 sliding-window attention 可能是更便宜的替代方案，但目前没人
  对其在 lab 数据上的表现有把握（依据：10:05）。

## 三、达成共识

- 这件事**值得**做一个小实验探一下，但**不是本周**的事；等 baseline 那
  条线稳定再说（依据：12:31）。
- 共同认为 sliding-window 是更值得先试的版本，比 linear attention 风
  险低（依据：12:55）。

## 四、未解决问题

- 在哪个数据集上做这个 sanity check？两人没有明确决定。
- 谁来主导？讨论中没有指定 owner。
- 与现有 baseline 实验的优先级关系如何？只说了"等 baseline 稳定"，但没
  有给出明确的触发条件。

## 五、下一步行动（建议，待确认）

> 这部分是**模型基于讨论内容的整理（推测）**，不是会议中明确交代的任务。
> 是否纳入待办，请你确认。

- （推测）等 baseline 在 ImageNet 上的精度稳定后，启动一个 1-2 周的
  sliding-window attention 探索。
- （推测）先选一个小模型 + 长序列 toy 任务做 sanity check，再决定要不
  要放到 baseline 上。
- （推测）记一个 idea card，避免被遗忘；不进本周 todo。
