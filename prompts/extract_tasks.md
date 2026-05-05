# Prompt — extract tasks

Use this prompt when the recording is `group_meeting`,
`advisor_student_discussion`, or `student_progress_report`.

You will receive the cleaned transcript. Produce a **per-person task list**
in the structure required by the active preset.

---

## Per-task structure

For each task, emit:

```markdown
### <学生标识>

- 任务：<一句话描述>
- 交付物：<具体的产出，例如 "实验报告 + 代码 PR"。如未明确，写 "未明确（待确认）"。>
- 截止时间：<YYYY-MM-DD 或 "本周五" 等明确表达；如仅暗示，写 "未明确（推测：…）"。>
- 验收标准：<如何算"完成"；如未明确，写 "未明确（待确认）"。>
- 依据：
  - mm:ss-mm:ss：<原话简引，≤ 25 字>
  - mm:ss-mm:ss：<原话简引，≤ 25 字>
- 不确定项：
  - <若没有，写 "无"。>
```

`<学生标识>` is the speaker label — `SPEAKER_02` if no name was stated,
`张同学` only if a name was actually used in the transcript or the user has
provided a speaker map.

---

## Discovery rules

A "task" exists when at least one of these is true:

1. Imperative directed at a specific speaker:
   `"你下周三之前把 X 跑完"`, `"张同学你负责 Y"`.
2. Joint commitment that names an owner:
   `"那 baseline 这块就李同学来吧"` — agreed to without objection.
3. Self-assigned commitment:
   `"我这周把数据清洗做完"` from a non-mentor speaker.

Things that look like tasks but are **not**:

- Hypotheticals: `"如果有时间可以试试..."` → not a task. Goes in
  `casual_discussion` preset's "未解决问题" or "下一步行动" instead.
- Generic encouragement: `"大家加油"` → drop.
- Mentor stating a goal without an owner: → flag in `不确定项`, not a
  task.

---

## Hard rules

- **Owners are stated, not inferred.** If a directive is given but no owner
  is named, surface it under `不确定项` with `（待确认任务归属）`.
- **Deadlines are stated, not inferred.** If only a "soon-ish" deadline is
  implied, write `未明确（推测：本周内）` — never write a concrete date you
  cannot cite.
- **Acceptance criteria** are usually missing in lab discussions. That is
  fine — say `未明确（待确认）`. Do not invent.
- Each task **must** cite at least one timestamp range. No citation → do
  not emit the task; instead surface under `## 待确认问题` at the report
  level.
- When the same task is mentioned several times, cite all occurrences in
  `依据` (helpful for review).

---

## Output

Plain markdown, one `### <学生标识>` block per person. Do not wrap in
extra prose. Order alphabetically by speaker label, except mentor-shaped
speakers go last (they typically don't get tasks; if they do, list them at
the end).
