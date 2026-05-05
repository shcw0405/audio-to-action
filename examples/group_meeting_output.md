# Example — group meeting output

This is what the skill produces after running `extract_tasks.md`,
`summarize_meeting.md`, and `build_student_messages.md` on the cleaned
transcript in `group_meeting_input_transcript.md`.

It is the canonical shape of a `group_meeting` preset run.

---

# 组会处理结果

> 录音：`2026-05-04-group-meeting.mp3` · 时长 38m12s · 3 位发言人
> 分类：`group_meeting`，置信度 0.87
> 说话人映射：未提供（请见 §五 待确认问题）

## 一、会议摘要

本次组会是一次例行的进展同步。SPEAKER_01（导师角色）听取了 SPEAKER_02 和
SPEAKER_03 两位同学这周的工作，并布置了下周的两件具体任务：ImageNet 上
baseline 的对齐、attention head 数的消融实验。数据清洗工作本周暂缓。

## 二、本周核心内容

- baseline 在 CIFAR-10 上已经复现到 92.3，离 paper 差 0.5 个点，怀疑是
  warmup 不对齐（依据：00:21、00:48）。
- attention 的初步消融显示 pre-norm 比 post-norm 稳定；head 数从 8 增到
  16 反而 val loss 上升，待进一步消融（依据：01:14、01:48）。
- 数据清洗本周不推进，等 baseline 稳定后再回来（依据：02:31）。
- 评测集按 paper 的划分走，确保可比（依据：02:48、02:58）。

## 三、按人拆分的任务

### SPEAKER_02

- 任务：在 ImageNet 上跑通 baseline，对齐 paper 的精度（至少先得到一个能
  对上的数）。
- 交付物：实验数（精度）+ 整理后的 code。
- 截止时间：下周三之前（依据：00:48）。
- 验收标准：未明确（仅说"发我一份"）。
- 依据：
  - 录音 00:48-01:05：下周三之前 ImageNet baseline，code 整理。
  - 录音 03:08-03:18：下周三前发我 ImageNet baseline。
- 不确定项：
  - 验收标准是否需要附实验报告 / 配置文件？（待确认）

### SPEAKER_03

- 任务：跑 attention head 数消融，head ∈ {8, 12, 16, 24}，每组 3 个
  seed，batch size 固定。
- 交付物：消融实验结果，下周组会上汇报。
- 截止时间：下周组会前（具体日期未明，**推测**为下周一同一时间）。
- 验收标准：未明确。
- 依据：
  - 录音 01:48-02:12：head 维度 8/12/16/24，三个 seed，下周组会讲。
  - 录音 01:48-02:12：batch size 固定，别让两个变量一起动。
- 不确定项：
  - 是否需要把 LayerNorm 位置（pre/post-norm）也作为对比维度纳入？
    （未明确）
  - 下周组会的具体日期需要导师确认。

## 四、待审查消息清单

> ⚠️ 以下是消息**草稿**，未经发送。`SPEAKER_02 / SPEAKER_03` 的真实身份
> 尚未映射，发送前请补全收件人姓名。

### 1. 发给 SPEAKER_02

**消息草稿：**

同学你好，本周请把 ImageNet 上的 baseline 跑通，先得到一个能对上 paper
的精度即可，并把 code 整理一份发给导师。截止时间是下周三之前。验收标
准未明确，建议你确认是否需要附实验报告。

**依据：**
- 录音 00:48-01:05：下周三之前 ImageNet baseline，code 整理。
- 录音 03:08-03:18：下周三前发我 ImageNet baseline。

**不确定项：**
- 收件人真实身份未确认（SPEAKER_02 → ?）
- 是否需要附实验报告 / 配置文件？

### 2. 发给 SPEAKER_03

**消息草稿：**

同学你好，下周组会请汇报 attention head 数的消融实验：head 数取
8 / 12 / 16 / 24 四组，每组跑 3 个 seed，batch size 在四组之间固定。
LayerNorm 位置（pre/post-norm）这一组观察也建议一并整理。

**依据：**
- 录音 01:48-02:12：head 维度 8/12/16/24，三个 seed。
- 录音 01:48-02:12：batch size 固定，别让两个变量一起动。

**不确定项：**
- 收件人真实身份未确认（SPEAKER_03 → ?）
- 是否需要把 pre/post-norm 也作为对比维度（建议但未明确要求）。
- 下周组会具体日期。

## 五、待确认问题

1. SPEAKER_01 / SPEAKER_02 / SPEAKER_03 是否对应你认识的人？方便的话补
   一份映射，我会重发上面的草稿。
2. 验收标准（任务怎么算"完成"）几乎所有任务都未明确。是否需要在发送前
   统一补一段验收说明？
3. 数据清洗任务本周暂缓，下周是否需要我自动跟进？
