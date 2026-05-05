# Prompt — ask the user how to proceed

Use this prompt when **any** of the following is true:

- Classification confidence < 0.6.
- The label is `unknown`.
- The label is one of the known presets, but the transcript is missing
  information critical to running it (e.g. `group_meeting` preset asked for,
  but no diarization and no speaker map provided).

---

## What to output

A short message to the user that contains:

1. One sentence stating the best guess and its confidence.
2. A bulleted menu of A–F options. **Do not** pre-select.
3. (Optional) one or two short clarifying questions the user can answer
   alongside their choice.

---

## Template

```markdown
我已完成转写（约 <duration_human> ，<segments_count> 段）。
这段录音看起来更像 <best_guess_label_human>，置信度 <confidence>。

你希望我怎么处理？

A. 只整理全文转写
B. 总结核心观点
C. 提取待办事项
D. 按参与人拆分任务
E. 生成可发送给他人的消息草稿（**会先给你审查，不会自动发送**）
F. 自定义处理方式（请告诉我具体目标）

附加问题（可选回答）：
- 录音中的 SPEAKER_01 / SPEAKER_02 是否对应你认识的人？方便的话告诉我对应关系。
- 这段录音是否有保密要求？我可以避免把全文写入任何对外消息草稿。
```

---

## `<best_guess_label_human>` mapping

| internal label | human-friendly form |
| --- | --- |
| `group_meeting` | 一次组会 |
| `advisor_student_discussion` | 导师和学生的单独讨论 |
| `casual_discussion` | 一次临时讨论 / 聊天 |
| `voice_memo` | 一段语音备忘录 |
| `student_progress_report` | 一次进度汇报 |
| `unknown` | 不太能确定的录音类型 |

---

## Hard rules

- **Do not silently fall back** to the meeting preset because it's the
  most "useful" one. Ad-hoc chats are not meetings; treating them as such
  is the headline failure mode of this skill.
- **Do not list option E without the parenthetical reminder** that drafts
  are review-only.
- If diarization didn't run and the user picks D or E, ask for a speaker
  map *before* generating per-person output.
- Keep the message under ~ 12 lines. The point is to get a quick answer,
  not to lecture.
