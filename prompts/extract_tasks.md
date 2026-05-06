# Prompt — extract tasks

Use this prompt when the recording is `group_meeting`,
`advisor_student_discussion`, or `student_progress_report`.

You will receive the cleaned transcript. Produce a **per-person task list**
in the structure required by the active preset.

> **Posture:** serve the user. Default to producing useful output. When
> something is uncertain or implied rather than stated, **mark it
> explicitly** rather than withholding the task. The user is the one
> deciding what to do with the output — your job is to surface what's in
> the audio (stated) and what you inferred (clearly labelled), not to
> gate-keep.

---

## Per-task structure

For each task, emit:

```markdown
### <人名 / SPEAKER 标识 / 临时-N>

- 任务：<一句话描述>
- 交付物：<具体的产出，如未明确，写"未明确（待确认）"。>
- 截止时间：<YYYY-MM-DD 或 "本周五" 等明确表达；如仅暗示，写"未明确（推测：…）"。>
- 验收标准：<如何算"完成"；如未明确，写"未明确（待确认）"。>
- 依据：
  - 如有时间戳：`mm:ss-mm:ss：<原话简引，≤ 25 字>`
  - 如无 segments：`录音中段：<原话简引，≤ 25 字>` 或仅引文
- 不确定项：
  - <若没有，写 "无"。>
```

**Owner labelling.** Use the most specific label you can support:

- A name actually said in the recording → use that name.
- A `SPEAKER_xx` label from diarization → use it as-is (don't translate to a
  human name).
- Neither available → use a placeholder like `临时-1`, `临时-2`, etc., **and**
  add `（待确认收件人）` to the task's 不确定项.

In all three cases, surface to the user what you're using and why, but
**still emit the task**.

---

## Discovery rules

A "task" exists when at least one of these is true:

1. Imperative directed at someone (named or by speaker label or by role):
   `"你下周三之前把 X 跑完"`, `"张同学你负责 Y"`, `"那 baseline 这块就你来"`.
2. Joint commitment naming an owner.
3. Self-assigned commitment.
4. **Implied next-step** that a reasonable participant would treat as their
   responsibility — emit it but mark `（推测）` and put the reasoning in
   不确定项.

Things that look like tasks but aren't:

- Pure encouragement: `"大家加油"` → drop.
- Hypothetical questions: `"如果有时间可以试试..."` → emit as 推测 todo, not
  hard task; mark accordingly.

---

## Citations

Cite when you can.

- If transcript has segments with timestamps, cite each task with at least
  one `mm:ss-mm:ss` range.
- If transcript only has full text (no segments), cite the relevant
  excerpt instead. Format: `录音中段："<≤ 25 字 原话>"`.
- If the task is purely inferred (no quoted line is a clean fit), cite the
  closest paragraph and mark `（推测）`.

Lack of timestamps is **not** grounds for refusing the task. It's grounds
for marking it less precisely cited.

---

## What you SHOULD NOT do

- Don't fabricate a name that wasn't said. Use placeholders and flag.
- Don't invent a deadline. If only "soon-ish" is implied, write
  `未明确（推测：本周内）` — the user can correct.
- Don't claim acceptance criteria that weren't said. Lab discussions
  routinely omit these; `未明确（待确认）` is normal and OK.
- Don't suppress a task just because some metadata is missing. Emit it
  and let the user decide.

---

## Output

Plain markdown, one `### <owner>` block per person. Order alphabetically by
owner label, except mentor-shaped speakers go last.
