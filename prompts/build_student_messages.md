# Prompt — build per-student message drafts

Use this prompt when the active preset includes a "待审查消息清单" section
(presets `group_meeting` and `advisor_student_discussion`), **or** when the
user explicitly asks for message drafts in the A–F follow-up menu.

You receive (a) the cleaned transcript and, when available, (b) the
per-person task list produced by `extract_tasks.md`. Output one message
draft per recipient.

> **Posture:** serve the user. Produce a useful draft they can review and
> send. The user is the human-in-the-loop, not you. Your job is to be
> faithful to the recording, mark inferences, and surface choices the
> user might want to make — not to refuse the work because some metadata
> is missing.

---

## Per-message structure

```markdown
### N. 发给 <收件人>

**消息草稿：**

<草稿正文 — 中文，2–6 句话。>

**依据：**
- 如有时间戳：`录音 mm:ss-mm:ss：<≤ 25 字 原话简引>`
- 如无 segments：`录音中段：<≤ 25 字 原话简引>`

**不确定项：**
- <若没有，写 "无"。否则列出收件人姓名、截止时间、验收标准等任何你拿不准的字段。>
```

---

## Recipient labelling

Pick the most specific label you can support:

| Available | Label to use |
| --- | --- |
| Name said in recording | The name |
| SPEAKER_xx from diarization | `SPEAKER_xx`, with note "请确认对应的真实身份" in 不确定项 |
| Neither | `临时-1` / `临时-2` / 等，with note in 不确定项 |

Always emit the draft. Never refuse on the grounds that the recipient's
real name isn't known.

---

## What goes in the draft body

A good draft is short and reflects only what was said (or what you've
clearly marked as inferred). Include:

1. **Greeting** in the form used in the recording if known
   (`张同学`, `李博士`...). If unknown, use `<收件人>` and flag in 不确定项.
2. **The task** — one or two sentences.
3. **Deadline** — if stated, include verbatim; if inferred, append
   `（推测时间，请确认）`.
4. **Acceptance / deliverable** — only if stated, otherwise omit (the
   draft can read "如有疑问随时找我"; user can edit).
5. **Closing** — brief invitation for the recipient to follow up.

A good draft does **not** include:

- The full transcript (unless the user explicitly asks for it).
- Tasks for other people (cross-contamination is the most common
  review-failure mode — keep each person's draft focused on them).
- Coaching context (e.g. "导师觉得你状态不好") — that's a 1:1
  conversation, not a task message.

---

## Citations

Cite the lines you used. Format:

- With timestamps: `录音 mm:ss-mm:ss：<excerpt>`
- Without timestamps: `录音中段：<excerpt>`

Excerpts ≤ 25 characters.

---

## Sending

**The skill itself does not send messages.** The user reviews the draft
and clicks an explicit "发送" affordance to actually send. Until the user
clicks, nothing leaves the local machine.

This is the one hard rule that stays: **outbound communication requires
an explicit user click**, after the draft is shown. Auto-send (model
sends in one shot, user can't intercept) is forbidden.

If you generate a draft that you think the user should pause on (e.g.
the deadline is implied not stated, or you used a placeholder name),
write a one-line note above the draft starting with `⚠️` so the user
notices before clicking 发送.

---

## Worked example

Transcript fragment:

> [12:31] 张同学，你这周把 baseline 在 ImageNet 上的精度跑出来。
> [12:45] 周五前发给我，code 也整理一下。

Draft:

```markdown
### 1. 发给 张同学

**消息草稿：**

张同学你好，本周请把 baseline 在 ImageNet 上的精度结果跑出来，并整理对应的代码，
周五前发给导师。如有疑问随时找我。

**依据：**
- 录音 12:31-12:38：baseline 在 ImageNet 上的精度
- 录音 12:45-12:52：周五前发给我，code 整理

**不确定项：**
- 验收标准未明确（仅说"发给我"），是否需要附实验报告？
```

If diarization wasn't run and the recording only has `SPEAKER_02`:

```markdown
### 1. 发给 SPEAKER_02

**消息草稿：**

同学你好，本周请把 baseline...

**不确定项：**
- 收件人真实身份未确认（SPEAKER_02 → ?）— 发送前请映射到具体姓名
- 验收标准未明确（仅说"发给我"），是否需要附实验报告？
```

Both forms are acceptable output. The user reviews, edits, and clicks 发送.
