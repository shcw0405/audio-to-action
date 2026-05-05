# Prompt — build per-student message drafts

Use this prompt when the active preset includes a "待审查消息清单" section
(presets `group_meeting` and `advisor_student_discussion`).

You receive (a) the cleaned transcript and (b) the per-person task list
produced by `extract_tasks.md`. Output one message draft per person.

---

## Per-message structure

```markdown
### N. 发给 <学生标识>

**消息草稿：**

<草稿正文 — 中文，2-6 句话。>

**依据：**
- 录音 mm:ss-mm:ss：<原话简引，≤ 25 字>
- 录音 mm:ss-mm:ss：<原话简引，≤ 25 字>

**不确定项：**
- <若没有，写 "无"。>
```

---

## What goes in the draft body

A good draft is short, reviewable, and reflects only what was said. Include:

1. **Greeting** using the same form of address used in the recording
   (`张同学`, `李博士`...). If no name is known, use `<同学>` and flag it
   under `不确定项`.
2. **The task** — one or two sentences.
3. **Deadline** — only if a deadline was stated. If inferred, append
   `（推测时间，请确认）`.
4. **Acceptance / deliverable** — only if stated.
5. **Closing** — a brief offer for the student to follow up
   ("有问题随时找我").

A good draft does **not** include:

- The entire transcript.
- Quotes longer than ~25 characters.
- Tasks for other people.
- Side discussion that wasn't directed at this person.
- Mentor-private context (e.g. "导师说你最近状态不好" — that's a coaching
  conversation, not a task message).

---

## Worked example

If the transcript contains:

> [12:31] 导师：张同学，你这周把 baseline 在 ImageNet 上的精度跑出来。
> [12:45] 导师：周五前发给我，code 也整理一下。

The draft for `SPEAKER_02 / 张同学` is:

```markdown
### 1. 发给 张同学

**消息草稿：**

张同学你好，本周请把 baseline 在 ImageNet 上的精度结果跑出来，并整理对应的代码，
周五前发给导师。有问题随时找我。

**依据：**
- 录音 12:31-12:38：baseline 在 ImageNet 上的精度
- 录音 12:45-12:52：周五前发给我，code 整理

**不确定项：**
- 验收标准未明确（仅说"发给我"），是否需要附实验报告？
```

---

## Hard rules

1. **Never auto-send.** This skill produces drafts only.
2. **Never address by a name not stated in the recording or supplied by
   the user.** When unsure, use the speaker label (`SPEAKER_02`) and flag
   `（待确认收件人）`.
3. **Never include the full transcript** in the draft body or its
   evidence. Cite timestamps + ≤ 25-char excerpts only.
4. **Never include other students' tasks** in a given person's draft.
   Cross-contamination is the most common review failure.
5. If you have no citation for a sentence in the draft body, you cannot
   write that sentence. Cut it.
6. If `不确定项` would have ≥ 3 entries, prefer to **skip the draft
   entirely** and surface the questions under `## 待确认问题` instead. A
   draft is supposed to be ready-for-review, not a riddle.
