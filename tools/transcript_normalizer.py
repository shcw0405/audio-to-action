"""Normalize ASR / diarization outputs into :class:`tools.schema.Transcript`.

Why this layer exists: providers disagree on field names, timestamp units,
segment shape, and whether they include speaker labels. The rest of the
skill — prompts, classification, preset rendering — needs a single,
predictable shape.

Provider-specific normalizers live here as small functions named
``_normalize_<provider>``. To add a new provider, write one of those and
register it in :func:`_NORMALIZERS`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .schema import Segment, Transcript, TranscriptMetadata


def normalize(
    raw: dict[str, Any],
    *,
    source_file: str | Path,
    provider: str,
    model: str = "unknown",
    diarization_turns: list[dict[str, Any]] | None = None,
) -> Transcript:
    """Convert a provider's raw output into a :class:`Transcript`.

    Parameters
    ----------
    raw
        The dict returned by ``ASRProvider.transcribe``.
    source_file
        Path to the original audio file (kept for provenance / display).
    provider
        Name as registered with ``@register_provider``. Drives which
        normalizer function is used.
    model
        Recorded in metadata. No behaviour depends on it.
    diarization_turns
        Optional list of ``{start, end, speaker}`` dicts from
        ``Diarizer.diarize``. When given, segment speakers are reassigned
        by timestamp overlap with these turns.
    """
    norm = _NORMALIZERS.get(provider, _normalize_generic)
    transcript = norm(
        raw,
        source_file=str(source_file),
        provider=provider,
        model=model,
    )
    if diarization_turns:
        _merge_diarization(transcript, diarization_turns)
    return transcript


# --------------------------------------------------------------------------- #
# OpenAI-compatible /audio/transcriptions verbose_json
#
# Shape (truncated):
# {
#   "language": "zh",
#   "duration": 3600.0,
#   "text": "...",
#   "segments": [
#     {"id": 0, "start": 0.0, "end": 3.4, "text": "...",
#      "avg_logprob": -0.31, "no_speech_prob": 0.02, ...},
#     ...
#   ]
# }


def _normalize_openai_compatible(
    raw: dict[str, Any],
    *,
    source_file: str,
    provider: str,
    model: str,
) -> Transcript:
    raw_segments = raw.get("segments") or []
    segments: list[Segment] = []
    for i, s in enumerate(raw_segments):
        confidence = _logprob_to_confidence(s.get("avg_logprob"))
        segments.append(
            Segment(
                id=int(s.get("id", i)),
                start=float(s.get("start", 0.0)),
                end=float(s.get("end", 0.0)),
                text=str(s.get("text", "")).strip(),
                speaker=s.get("speaker"),  # usually absent here
                confidence=confidence,
            )
        )

    text = (raw.get("text") or "").strip()
    if not text and segments:
        text = " ".join(s.text for s in segments if s.text).strip()

    duration = float(raw.get("duration") or _last_end(segments))

    return Transcript(
        source_file=source_file,
        language=raw.get("language"),
        duration=duration,
        text=text,
        segments=segments,
        metadata=TranscriptMetadata(
            asr_provider=provider,
            asr_model=model,
            diarization=False,
        ),
    )


# --------------------------------------------------------------------------- #
# Generic fallback — best-effort for unknown providers.
#
# Looks for keys: text, segments|chunks|results, language, duration.


def _normalize_generic(
    raw: dict[str, Any],
    *,
    source_file: str,
    provider: str,
    model: str,
) -> Transcript:
    seg_list = (
        raw.get("segments")
        or raw.get("chunks")
        or raw.get("results")
        or []
    )
    segments: list[Segment] = []
    for i, s in enumerate(seg_list):
        # Many providers wrap timestamps under "timestamp": [start, end].
        start, end = _extract_times(s)
        text = (
            s.get("text")
            or s.get("transcript")
            or s.get("content")
            or ""
        )
        confidence = s.get("confidence")
        if confidence is None:
            confidence = _logprob_to_confidence(s.get("avg_logprob"))
        segments.append(
            Segment(
                id=int(s.get("id", i)),
                start=float(start),
                end=float(end),
                text=str(text).strip(),
                speaker=s.get("speaker"),
                confidence=confidence,
            )
        )

    text = (
        raw.get("text")
        or raw.get("transcript")
        or " ".join(s.text for s in segments)
    ).strip()

    duration = float(raw.get("duration") or _last_end(segments))

    return Transcript(
        source_file=source_file,
        language=raw.get("language"),
        duration=duration,
        text=text,
        segments=segments,
        metadata=TranscriptMetadata(
            asr_provider=provider,
            asr_model=model,
            diarization=False,
        ),
    )


# --------------------------------------------------------------------------- #
# Diarization merge


def _merge_diarization(
    transcript: Transcript,
    turns: list[dict[str, Any]],
) -> None:
    """Assign each segment's speaker to the diarization turn it overlaps most.

    Modifies ``transcript`` in place. Sets ``metadata.diarization = True`` if
    at least one segment got a speaker.
    """
    if not turns:
        return
    parsed_turns = [
        (float(t["start"]), float(t["end"]), str(t["speaker"]))
        for t in turns
    ]
    assigned_any = False
    for seg in transcript.segments:
        best_overlap = 0.0
        best_speaker: str | None = None
        for start, end, spk in parsed_turns:
            overlap = max(0.0, min(seg.end, end) - max(seg.start, start))
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = spk
        if best_speaker and best_overlap > 0:
            seg.speaker = best_speaker
            assigned_any = True
    if assigned_any:
        transcript.metadata.diarization = True


# --------------------------------------------------------------------------- #
# Helpers


def _logprob_to_confidence(logprob: Any) -> float | None:
    """Convert Whisper-style avg_logprob (in dB-ish range) to a [0, 1] proxy.

    This is a heuristic. Real confidence requires per-token logprobs and
    proper calibration. The number is OK for sorting / flagging but should
    not be presented to users as a calibrated probability.
    """
    if logprob is None:
        return None
    try:
        lp = float(logprob)
    except (TypeError, ValueError):
        return None
    # Clamp to a typical Whisper range and normalize.
    # avg_logprob ≈ 0 → very confident; ≈ -1 → poor.
    lp = max(-1.0, min(0.0, lp))
    return round(1.0 + lp, 3)  # -1 → 0.0; 0 → 1.0


def _last_end(segments: list[Segment]) -> float:
    return max((s.end for s in segments), default=0.0)


def _extract_times(s: dict[str, Any]) -> tuple[float, float]:
    """Best-effort timestamp extraction from a chunk in a foreign schema."""
    if "start" in s and "end" in s:
        return float(s["start"]), float(s["end"])
    ts = s.get("timestamp") or s.get("times")
    if isinstance(ts, (list, tuple)) and len(ts) >= 2:
        return float(ts[0]), float(ts[1])
    return 0.0, 0.0


# --------------------------------------------------------------------------- #
# Registry — extend by adding entries here.


_NORMALIZERS: dict[str, Callable[..., Transcript]] = {
    "openai_compatible": _normalize_openai_compatible,
    # add: "deepgram": _normalize_deepgram,
    # add: "azure": _normalize_azure, ...
}
