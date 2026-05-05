# Prompt — clean transcript

You will receive the raw output of an ASR system (segments with timestamps,
possibly with speaker labels, possibly with ASR artifacts). Produce a
**cleaned** version that is faithful to the original.

---

## What "clean" means

Do:

- Remove disfluencies that carry no meaning: `嗯`, `呃`, `啊`, `就是说`,
  `然后那个`, `you know`, `like`, `um`, `uh` — when they are filler.
  Keep them when they are content (e.g. quoting someone else).
- Repair obvious mis-segmentations and missing punctuation.
- Group adjacent segments by the same speaker into paragraphs.
- Normalize whitespace.
- Convert numbers and units consistently (`两千零二十六年` → `2026 年`)
  *only* when the meaning is unambiguous.

Do **not**:

- Rewrite for style.
- Translate.
- Summarize.
- Add information that is not in the source.
- Change the meaning, even subtly. If you are tempted to "fix" something,
  leave it.
- Invent or assign speaker names. `SPEAKER_01` stays `SPEAKER_01` unless
  the user has provided a speaker map.
- Drop timestamps. Each paragraph must keep at least the start timestamp of
  its first source segment.

---

## Output format

Markdown, one paragraph per speaker turn:

```
**[SPEAKER_01 | 00:12]** 这周我们先看一下 baseline 的实验结果，张同学你先讲一下进展。

**[SPEAKER_02 | 00:21]** 好的，目前 baseline 模型已经在三个数据集上跑通……
```

Format rules:

- Timestamps in `mm:ss` (or `hh:mm:ss` for recordings > 1 h).
- One blank line between turns.
- If the segmenter clearly mis-attributed a sentence to the wrong speaker,
  do not silently re-attribute. Instead, leave it as-is and flag at the end:

  ```
  ## Suspected attribution issues
  - 03:14 — sentence "下周三前发我" attributed to SPEAKER_02; tone and
    content look like SPEAKER_01.
  ```

---

## Hard rules

- **Never invent speakers.** If diarization didn't run, use `UNKNOWN` for
  every turn.
- **Never invent words.** Better to leave `[inaudible]` than guess.
- If a segment is < 0.5 s and contains only filler, you may drop it — but
  log it under `## Dropped` at the end.
- Output must be reconstructible into the original meaning. A reviewer
  reading this should be able to tell exactly what was said.
