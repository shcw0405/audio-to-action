# Prompt — summarize meeting

Use this prompt only when the recording has been classified as
`group_meeting` or `advisor_student_discussion` with confidence ≥ 0.6.

You will receive the cleaned transcript. Produce the meeting summary section
of the preset report.

---

## Output structure

```markdown
## 一、会议摘要

<2–4 句话，覆盖：会议是关于什么；做出了哪些决定；分派了哪些主要任务。>

## 二、本周核心内容

- <要点 1>（依据：mm:ss）
- <要点 2>（依据：mm:ss）
- <要点 3>（依据：mm:ss）
```

Each bullet in **本周核心内容** must cite at least one timestamp from the
transcript. If you cannot cite, do not include the bullet.

---

## Style rules

- Write in the user's transcript language (Chinese if the transcript is
  Chinese).
- Prefer **stated facts** over interpretation. If you must interpret, mark
  it `（推测）`.
- Do not list every minor exchange. The summary is the 4–6 things a person
  who missed the meeting actually needs to know.
- Do not name people who were not named in the transcript. `SPEAKER_01`
  stays `SPEAKER_01` unless the user has supplied a map.

---

## Hard rules

- Never include full quotes longer than ~25 characters. Cite by timestamp,
  paraphrase the substance.
- Never include the entire transcript, even folded.
- If the meeting reaches no decisions, say so explicitly:
  `本次会议未形成明确结论，详见 §四 待审查消息清单。`
