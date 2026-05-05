"""Unified transcript schema for audio-to-action.

Every ASR provider, no matter what it returns natively, is normalized to the
dataclasses defined here before any downstream prompt or tool sees the data.

Design rules
------------
- ``Segment.speaker`` is ``None`` when unknown. ``"UNKNOWN"`` is also tolerated
  for compatibility with diarization tools that emit a placeholder string.
  **Never invent a name in code; let the human / LLM map labels later.**
- ``Segment.confidence`` is optional. Missing means "provider didn't tell us".
- ``Transcript.text`` is the canonical full text. If it is missing on input,
  ``normalize`` will reconstruct it by joining segments.
- The dataclasses are JSON-stable: ``to_dict``/``from_dict`` round-trip.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Iterable

ALLOWED_LABELS: tuple[str, ...] = (
    "group_meeting",
    "advisor_student_discussion",
    "casual_discussion",
    "voice_memo",
    "student_progress_report",
    "unknown",
)


@dataclass
class Segment:
    """One ASR segment with timing, optional speaker, optional confidence."""

    id: int
    start: float  # seconds from start of recording
    end: float  # seconds from start of recording
    text: str
    speaker: str | None = None  # None or "UNKNOWN" when unknown — never fabricated
    confidence: float | None = None

    def __post_init__(self) -> None:
        if self.start < 0 or self.end < 0:
            raise ValueError(f"segment {self.id}: timestamps must be ≥ 0")
        if self.end < self.start:
            raise ValueError(
                f"segment {self.id}: end ({self.end}) < start ({self.start})"
            )
        if self.confidence is not None and not (0.0 <= self.confidence <= 1.0):
            raise ValueError(
                f"segment {self.id}: confidence must be in [0, 1], got {self.confidence}"
            )
        # Normalize speaker placeholder.
        if self.speaker == "":
            self.speaker = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # Drop None confidence to keep JSON compact.
        if d["confidence"] is None:
            d.pop("confidence")
        if d["speaker"] is None:
            d.pop("speaker")
        return d


@dataclass
class TranscriptMetadata:
    """Provenance metadata. Cheap to extend; no behaviour depends on it."""

    asr_provider: str = "unknown"
    asr_model: str = "unknown"
    diarization: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "asr_provider": self.asr_provider,
            "asr_model": self.asr_model,
            "diarization": self.diarization,
        }
        if self.extra:
            out.update(self.extra)
        return out


@dataclass
class Transcript:
    source_file: str
    language: str | None
    duration: float
    text: str
    segments: list[Segment] = field(default_factory=list)
    metadata: TranscriptMetadata = field(default_factory=TranscriptMetadata)

    def __post_init__(self) -> None:
        if self.duration < 0:
            raise ValueError("duration must be ≥ 0")
        # If text was not provided but we have segments, build text from them.
        if not self.text and self.segments:
            self.text = " ".join(s.text.strip() for s in self.segments if s.text).strip()

    # --------------------------------------------------------------------- #
    # serialization

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_file": self.source_file,
            "language": self.language,
            "duration": self.duration,
            "text": self.text,
            "segments": [s.to_dict() for s in self.segments],
            "metadata": self.metadata.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Transcript":
        segments = [
            Segment(
                id=s["id"],
                start=float(s["start"]),
                end=float(s["end"]),
                text=s["text"],
                speaker=s.get("speaker"),
                confidence=s.get("confidence"),
            )
            for s in d.get("segments", [])
        ]
        meta_dict = dict(d.get("metadata") or {})
        known = {"asr_provider", "asr_model", "diarization"}
        metadata = TranscriptMetadata(
            asr_provider=meta_dict.pop("asr_provider", "unknown"),
            asr_model=meta_dict.pop("asr_model", "unknown"),
            diarization=bool(meta_dict.pop("diarization", False)),
            extra=meta_dict,
        )
        return cls(
            source_file=d["source_file"],
            language=d.get("language"),
            duration=float(d.get("duration", 0.0)),
            text=d.get("text", ""),
            segments=segments,
            metadata=metadata,
        )

    # --------------------------------------------------------------------- #
    # convenience

    @property
    def speakers(self) -> list[str]:
        """Distinct speaker labels in transcript order, excluding None/UNKNOWN."""
        seen: list[str] = []
        for s in self.segments:
            if s.speaker and s.speaker != "UNKNOWN" and s.speaker not in seen:
                seen.append(s.speaker)
        return seen

    def has_diarization(self) -> bool:
        return any(s.speaker and s.speaker != "UNKNOWN" for s in self.segments)


# ------------------------------------------------------------------------- #
# Classification result — the output of prompts/classify_audio_content.md


@dataclass
class Classification:
    label: str
    confidence: float
    rationale: str = ""
    alternative_label: str | None = None
    alternative_confidence: float | None = None

    def __post_init__(self) -> None:
        if self.label not in ALLOWED_LABELS:
            raise ValueError(
                f"label {self.label!r} not in allowed set {ALLOWED_LABELS}"
            )
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be in [0, 1], got {self.confidence}")
        if self.alternative_label is not None and self.alternative_label not in ALLOWED_LABELS:
            raise ValueError(
                f"alternative_label {self.alternative_label!r} not in allowed set"
            )

    def is_ambiguous(self, threshold: float = 0.6) -> bool:
        """Below the threshold we should ask the user instead of acting."""
        return self.confidence < threshold or self.label == "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "alternative_label": self.alternative_label,
            "alternative_confidence": self.alternative_confidence,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Classification":
        return cls(
            label=d["label"],
            confidence=float(d["confidence"]),
            rationale=d.get("rationale", ""),
            alternative_label=d.get("alternative_label"),
            alternative_confidence=(
                float(d["alternative_confidence"])
                if d.get("alternative_confidence") is not None
                else None
            ),
        )


def iter_segments_in_window(
    segments: Iterable[Segment], start: float, end: float
) -> list[Segment]:
    """Helper — return the segments that overlap [start, end).

    Used by prompts that need to cite specific sections by timestamp.
    """
    out: list[Segment] = []
    for s in segments:
        if s.end <= start or s.start >= end:
            continue
        out.append(s)
    return out
