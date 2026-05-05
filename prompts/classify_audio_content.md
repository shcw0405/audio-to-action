# Prompt — classify audio content

You are reading a cleaned transcript of a recording made in a research-lab /
office context. Your job is to classify it into **exactly one** of the
following labels and return a confidence score.

---

## Labels

| Label | Recognize when... |
| --- | --- |
| `group_meeting` | More than two distinct speakers, agenda-driven, contains explicit task assignment ("X 你负责...", "下周交..."), often references project names or weekly cadence. |
| `advisor_student_discussion` | Two speakers; one clearly mentor-shaped (gives directions, asks probing questions, references prior work history), one clearly student-shaped (reports progress, receives instruction). May contain task assignment but the structure is 1:1. |
| `casual_discussion` | Free-form, idea-stage. Discusses possibilities, hypotheticals, "what if we tried...". Few or no concrete tasks. May still be multi-speaker. |
| `voice_memo` | Single speaker for ≥ 90% of duration. Self-addressed: "记一下", "提醒自己", "想到一个 idea"... |
| `student_progress_report` | Predominantly one speaker reporting status: "这周我做了...", "遇到的问题是...", "下周打算..." Very low instruction density; reads like a report being delivered. |
| `unknown` | None of the above fits with confidence ≥ 0.6. |

---

## Decision rules

1. Speaker count:
   - 1 speaker → `voice_memo` *or* `student_progress_report`. Disambiguate
     by whether the speaker addresses an audience ("各位老师...") or
     themselves ("提醒一下我自己...").
   - 2 speakers → `advisor_student_discussion` *or* `casual_discussion`.
     Disambiguate by instructional asymmetry.
   - 3+ speakers → `group_meeting` *or* `casual_discussion`. Disambiguate
     by task-assignment density.

2. **Task assignment density** dominates: if there are ≥ 2 explicit
   "you do X by Y" instructions, lean toward `group_meeting` /
   `advisor_student_discussion` even if the conversation is otherwise loose.

3. **Do not** use speaker *names* to decide. Names may be missing or
   anonymized. Decide on shape, not identity.

4. If two labels both score ≥ 0.6, return the higher-scoring one and lower
   the confidence by 0.1 to reflect ambiguity.

---

## Output format

Return strict JSON, no prose:

```json
{
  "label": "group_meeting",
  "confidence": 0.83,
  "rationale": "三位发言者；张同学和李同学被多次点名；‘下周三前提交’等明确任务；议题集中在 baseline 实验。",
  "alternative_label": "advisor_student_discussion",
  "alternative_confidence": 0.41
}
```

`rationale` is one or two sentences in the user's likely language (Chinese
if transcript is Chinese), citing concrete features. Do **not** quote whole
paragraphs.

---

## Hard rules

- Never invent speaker names. Use `SPEAKER_01` etc. as given.
- If the transcript is empty or < 30 seconds of speech, return label
  `unknown` with confidence ≤ 0.3 and rationale `"transcript too short"`.
- Confidence is in `[0, 1]`. If you would say "I'm not sure", that maps to
  ≤ 0.6, regardless of the chosen label.
