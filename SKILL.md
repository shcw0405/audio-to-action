---
name: audio-to-action
description: |
  Use this skill whenever the user uploads, references, or asks about an audio
  file (.mp3, .wav, .m4a, .flac, .ogg, .webm) in a research-lab / office
  context — group meetings, advisor-student discussions, casual lab chat,
  voice memos, student progress reports. The skill does not stop at
  transcription: it understands the recording, classifies the content type,
  and emits structured, reviewable output (summaries, per-person tasks,
  todos, message drafts). Trigger phrases include "transcribe this",
  "what did we say in the meeting", "组会录音", "整理这段录音",
  "把这段会议变成任务".
---

# audio-to-action

A fixed-workflow skill for turning office / lab recordings into reviewable,
structured output. **It is not a generic ASR wrapper.** It treats audio as the
beginning of a workflow whose end is a set of structured artifacts — summaries,
per-person tasks, message drafts, todos — that a human can review and act on.

---

## 1. When to trigger

Trigger when **any** of the following is true:

1. The user references an audio file by path, attachment, or URL whose
   extension is one of: `.mp3 .wav .m4a .flac .ogg .webm`.
2. The user explicitly asks to transcribe / summarize / extract tasks from a
   recording.
3. The user pastes a chunk of obviously-transcribed text and asks for the same
   downstream processing (skip steps 1–4 below; jump straight to step 5).

Do **not** trigger for:

- Music files the user only wants converted, tagged, or played.
- Audio the user is asking about purely as a file-format question
  ("how do I convert wav to mp3?").

---

## 2. Full processing flow

```
Audio file
  ↓ (1) sanity-check file (exists, format, size, duration)
  ↓ (2) ffmpeg-normalize if needed
  ↓ (3) ASR via configured provider
  ↓ (4) normalize to unified transcript schema
  ↓ (5) clean transcript (filler removal, punctuation, paragraphing)
  ↓ (6) classify content type
  ↓ (7) branch on content type:
        ├── known preset  →  apply preset, produce structured output
        └── unknown / ambiguous  →  ask the user how to proceed
  ↓ (8) emit reviewable artifacts (no auto-send, ever)
```

### Step 1 — Sanity check

Use `tools/utils.py::probe_audio` to confirm:

- File exists and is readable.
- Extension is in the supported set.
- Size and duration are reasonable (warn the user if duration > 2 hours).

If the format is unsupported but ffmpeg is installed, transparently transcode
to 16kHz mono WAV before passing to ASR.

### Step 2 — ASR

Call the ASR provider configured in `settings.yaml`. The skill ships with an
**OpenAI-compatible** adapter; other providers (faster-whisper local,
Deepgram, Azure, etc.) are added by implementing the `ASRProvider` protocol
in `tools/asr_client.py`. Configuration is **never hardcoded** — always read
from `settings.yaml` (or its env-var overrides).

### Step 3 — Normalize

Whatever the provider returns, normalize through
`tools/transcript_normalizer.py::normalize` so the rest of the skill operates
on a **single transcript schema** (see §4).

### Step 4 — Clean

Apply `prompts/clean_transcript.md`: remove filler, repair punctuation, group
into paragraphs. **Do not** invent content. Keep timestamps anchored to the
nearest original segment.

### Step 5 — Classify

Apply `prompts/classify_audio_content.md`. Possible labels:

| Label | Meaning |
| --- | --- |
| `group_meeting` | Multi-person meeting with task assignment. |
| `advisor_student_discussion` | 1:1 advisor + student. |
| `casual_discussion` | Ad-hoc chat, ideas not yet tasks. |
| `voice_memo` | Single-speaker memo / note-to-self. |
| `student_progress_report` | Student reporting status. |
| `unknown` | Cannot decide confidently. |

The classifier must also output a **confidence** in `[0, 1]`. Confidence below
**0.6** is treated as `unknown` regardless of the chosen label.

### Step 6 — Branch

- Confidence ≥ 0.6 and label is one of the five known presets → apply that
  preset directly (see §6).
- Otherwise → run `prompts/ask_followup.md` and present the user with options
  A–F. **Do not** silently default to the meeting preset. Ad-hoc chats are
  not group meetings.

### Step 7 — Emit

All output is markdown, reviewable, and clearly separates:

- **Stated** — exact words / timestamps from the recording.
- **Inferred** — model interpretation, marked with `（推测）` /
  `(inferred)`.
- **Unconfirmed** — items that need user confirmation, marked with
  `（待确认）` / `(needs confirmation)`.

---

## 3. Required artifacts

Every successful run produces, at minimum:

1. `transcript.json` — the unified-schema transcript.
2. `transcript.cleaned.md` — human-readable cleaned text.
3. A preset-specific markdown report (see §6).
4. **If any messages-to-people are drafted:** a "待审查消息清单 / Drafts for
   Review" section. Drafts are **never** sent automatically. Sending must go
   through a separate, explicitly-approved tool that this skill does not
   provide in MVP.

---

## 4. Unified transcript schema

```json
{
  "source_file": "meeting.mp3",
  "language": "zh",
  "duration": 3600.0,
  "text": "完整转写文本",
  "segments": [
    {
      "id": 1,
      "start": 12.3,
      "end": 18.6,
      "speaker": "SPEAKER_01",
      "text": "这周你先把 baseline 跑完。",
      "confidence": 0.92
    }
  ],
  "metadata": {
    "asr_provider": "openai_compatible",
    "asr_model": "faster-whisper-large-v3",
    "diarization": false
  }
}
```

Rules:

- `speaker` is `null` or `"UNKNOWN"` when unknown. **Never invent a name.**
- `confidence` may be omitted if the provider does not return it.
- `segments` is allowed to be empty if the provider only returned full text.

---

## 5. Asking the user when unsure

When classification confidence < 0.6, or content does not fit a known preset,
emit the menu from `prompts/ask_followup.md`:

```
我已完成转写。这段录音看起来更像 <best-guess>，置信度较低。

你希望我怎么处理？

A. 只整理全文转写
B. 总结核心观点
C. 提取待办事项
D. 按参与人拆分任务
E. 生成可发送给他人的消息草稿
F. 自定义处理方式（请告诉我具体目标）
```

**Do not** force a meeting preset onto an ambiguous recording. If the user
picks D or E but speakers cannot be reliably identified, ask the user to
provide a speaker map (`SPEAKER_01 → 张同学`) before proceeding.

---

## 6. Presets

### Preset 1 — `group_meeting`

```markdown
# 组会处理结果

## 一、会议摘要
## 二、本周核心内容
## 三、按人拆分的任务

### <学生标识>
- 任务：
- 交付物：
- 截止时间：
- 验收标准：
- 依据：（时间戳 + 引文）
- 不确定项：

## 四、待审查消息清单
## 五、待确认问题
```

### Preset 2 — `advisor_student_discussion`

```markdown
# 导师-学生讨论整理

## 一、讨论摘要
## 二、学生当前进展
## 三、导师建议
## 四、下一步任务
## 五、待确认问题
## 六、可发送消息草稿
```

### Preset 3 — `casual_discussion`

```markdown
# 临时讨论整理

## 一、讨论背景
## 二、核心观点
## 三、达成共识
## 四、未解决问题
## 五、下一步行动
```

### Preset 4 — `voice_memo`

```markdown
# 语音备忘录整理

## 一、清理后的笔记
## 二、核心想法
## 三、可执行 Todo
## 四、后续可展开方向
```

### Preset 5 — `student_progress_report`

```markdown
# 学生进展汇报整理

## 一、已完成工作
## 二、当前问题
## 三、需要导师反馈的点
## 四、建议下一步
```

---

## 7. Message drafts must be reviewable

When the skill drafts a message to a specific person (preset 1 §四, preset 2
§六), the output **must** include, for each draft:

```markdown
### N. 发给 <学生标识>

**消息草稿：**

<草稿正文>

**依据：**
- 录音 mm:ss-mm:ss：<原话引文>
- 录音 mm:ss-mm:ss：<原话引文>

**不确定项：**
- <未明确截止时间 / 任务边界 / 验收标准 等>
```

Hard rules:

- Never send. Only draft.
- Never address the recipient by a name that was not stated in the recording
  or supplied by the user.
- If a draft cites a deadline, the deadline must have a citation. If
  inferred, mark it `（推测，待确认）`.
- Full transcripts are **not** included in drafts. Only the relevant excerpt
  cited as 依据.

---

## 8. Safety rules (non-negotiable)

1. **Do not invent speaker identities.** `SPEAKER_01` stays `SPEAKER_01`
   until the user maps it.
2. **Do not invent students, deadlines, or task ownership.** If a piece of
   information is implied but not stated, mark it `（推测）`.
3. **Do not auto-send anything.** The skill produces drafts; sending is a
   separate, explicit, user-approved action outside this skill.
4. **Do not leak full transcripts** into person-specific drafts. Only cite the
   relevant excerpts.
5. **Do not retain audio or transcripts beyond the run** unless the user asked
   you to save them. If you do save, save next to the source file or under
   `./out/` and tell the user the path.
6. **API keys** come from environment variables named in `settings.yaml`
   (`api_key_env: ASR_API_KEY`). Never hardcode. Never echo the key back.
7. When unsure, **ask** (see §5). Silent defaults are worse than a question.

---

## 9. Layout

```
audio-to-action/
├── SKILL.md                         ← you are here
├── README.md                        ← setup, extension, FAQ
├── settings.yaml                    ← ASR + behaviour config
├── prompts/
│   ├── classify_audio_content.md
│   ├── clean_transcript.md
│   ├── summarize_meeting.md
│   ├── extract_tasks.md
│   ├── build_student_messages.md
│   └── ask_followup.md
├── tools/
│   ├── asr_client.py                ← provider protocol + OpenAI-compatible
│   ├── diarization_client.py        ← stub interface for future pyannote/etc.
│   ├── transcript_normalizer.py
│   ├── schema.py
│   └── utils.py
├── examples/
│   ├── group_meeting_input_transcript.md
│   ├── group_meeting_output.md
│   ├── casual_discussion_output.md
│   └── voice_memo_output.md
└── tests/
    ├── test_transcript_schema.py
    ├── test_content_classification.py
    └── test_task_extraction.py
```
