"""Tests for tools/schema.py and tools/transcript_normalizer.py.

These tests do **not** hit any network. They lock in the unified-schema
contract: any provider's raw output, after going through ``normalize``,
must come out as a valid :class:`Transcript`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Make `tools` importable when running pytest from the skill root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.schema import (  # noqa: E402
    ALLOWED_LABELS,
    Classification,
    Segment,
    Transcript,
    iter_segments_in_window,
)
from tools.transcript_normalizer import normalize  # noqa: E402


# --------------------------------------------------------------------------- #
# Segment


class TestSegment:
    def test_minimal_segment(self) -> None:
        s = Segment(id=1, start=0.0, end=1.5, text="hello")
        assert s.speaker is None
        assert s.confidence is None

    def test_speaker_empty_string_normalized_to_none(self) -> None:
        s = Segment(id=1, start=0.0, end=1.0, text="x", speaker="")
        assert s.speaker is None

    def test_negative_start_rejected(self) -> None:
        with pytest.raises(ValueError):
            Segment(id=1, start=-0.1, end=1.0, text="x")

    def test_end_before_start_rejected(self) -> None:
        with pytest.raises(ValueError):
            Segment(id=1, start=2.0, end=1.0, text="x")

    def test_confidence_out_of_range(self) -> None:
        with pytest.raises(ValueError):
            Segment(id=1, start=0.0, end=1.0, text="x", confidence=1.5)

    def test_to_dict_drops_none_fields(self) -> None:
        s = Segment(id=1, start=0.0, end=1.0, text="x")
        d = s.to_dict()
        assert "confidence" not in d
        assert "speaker" not in d


# --------------------------------------------------------------------------- #
# Transcript


class TestTranscript:
    def test_text_filled_from_segments_when_missing(self) -> None:
        segs = [
            Segment(id=1, start=0.0, end=1.0, text="hello"),
            Segment(id=2, start=1.0, end=2.0, text="world"),
        ]
        t = Transcript(
            source_file="x.mp3",
            language="en",
            duration=2.0,
            text="",
            segments=segs,
        )
        assert t.text == "hello world"

    def test_round_trip_to_dict(self) -> None:
        segs = [
            Segment(
                id=1, start=0.0, end=1.0, text="嗨", speaker="SPEAKER_01",
                confidence=0.9,
            ),
        ]
        original = Transcript(
            source_file="x.mp3", language="zh", duration=1.0,
            text="嗨", segments=segs,
        )
        recovered = Transcript.from_dict(json.loads(json.dumps(original.to_dict())))
        assert recovered.to_dict() == original.to_dict()

    def test_speakers_excludes_unknown(self) -> None:
        segs = [
            Segment(id=1, start=0.0, end=1.0, text="a", speaker="SPEAKER_01"),
            Segment(id=2, start=1.0, end=2.0, text="b", speaker="UNKNOWN"),
            Segment(id=3, start=2.0, end=3.0, text="c", speaker=None),
            Segment(id=4, start=3.0, end=4.0, text="d", speaker="SPEAKER_02"),
            Segment(id=5, start=4.0, end=5.0, text="e", speaker="SPEAKER_01"),
        ]
        t = Transcript(
            source_file="x.mp3", language=None, duration=5.0,
            text="", segments=segs,
        )
        assert t.speakers == ["SPEAKER_01", "SPEAKER_02"]


# --------------------------------------------------------------------------- #
# Classification


class TestClassification:
    def test_rejects_unknown_label(self) -> None:
        with pytest.raises(ValueError):
            Classification(label="meeting", confidence=0.9)

    def test_all_allowed_labels_construct(self) -> None:
        for lbl in ALLOWED_LABELS:
            c = Classification(label=lbl, confidence=0.7)
            assert c.label == lbl

    def test_is_ambiguous_below_threshold(self) -> None:
        c = Classification(label="group_meeting", confidence=0.5)
        assert c.is_ambiguous(0.6) is True

    def test_unknown_is_always_ambiguous(self) -> None:
        c = Classification(label="unknown", confidence=0.99)
        assert c.is_ambiguous(0.6) is True


# --------------------------------------------------------------------------- #
# iter_segments_in_window


def test_window_extraction_includes_overlap_only() -> None:
    segs = [
        Segment(id=1, start=0.0, end=2.0, text="a"),
        Segment(id=2, start=1.5, end=3.0, text="b"),
        Segment(id=3, start=4.0, end=5.0, text="c"),
        Segment(id=4, start=4.9, end=6.0, text="d"),
    ]
    got = iter_segments_in_window(segs, start=2.5, end=5.0)
    assert [s.id for s in got] == [2, 3, 4]


# --------------------------------------------------------------------------- #
# Normalizer — openai_compatible


class TestNormalizeOpenAICompatible:
    def _raw(self) -> dict:
        # Shape returned by Whisper / faster-whisper-server with
        # response_format=verbose_json.
        return {
            "language": "zh",
            "duration": 12.5,
            "text": "你好。世界。",
            "segments": [
                {
                    "id": 0, "start": 0.0, "end": 5.0,
                    "text": " 你好。",
                    "avg_logprob": -0.1,
                    "no_speech_prob": 0.01,
                },
                {
                    "id": 1, "start": 5.0, "end": 12.5,
                    "text": " 世界。",
                    "avg_logprob": -0.4,
                    "no_speech_prob": 0.02,
                },
            ],
        }

    def test_basic_normalization(self) -> None:
        t = normalize(
            self._raw(),
            source_file="hi.mp3",
            provider="openai_compatible",
            model="faster-whisper-large-v3",
        )
        assert t.source_file == "hi.mp3"
        assert t.language == "zh"
        assert t.duration == pytest.approx(12.5)
        assert len(t.segments) == 2
        assert t.segments[0].text == "你好。"
        assert t.metadata.asr_provider == "openai_compatible"
        assert t.metadata.asr_model == "faster-whisper-large-v3"
        assert t.metadata.diarization is False

    def test_logprob_to_confidence_in_range(self) -> None:
        t = normalize(
            self._raw(),
            source_file="hi.mp3",
            provider="openai_compatible",
            model="m",
        )
        for s in t.segments:
            assert s.confidence is not None
            assert 0.0 <= s.confidence <= 1.0

    def test_diarization_merge(self) -> None:
        t = normalize(
            self._raw(),
            source_file="hi.mp3",
            provider="openai_compatible",
            model="m",
            diarization_turns=[
                {"start": 0.0, "end": 4.5, "speaker": "SPEAKER_01"},
                {"start": 4.5, "end": 12.5, "speaker": "SPEAKER_02"},
            ],
        )
        assert t.segments[0].speaker == "SPEAKER_01"
        assert t.segments[1].speaker == "SPEAKER_02"
        assert t.metadata.diarization is True

    def test_no_segments_falls_back_to_text(self) -> None:
        raw = {"text": "全文", "duration": 1.0}
        t = normalize(
            raw, source_file="x.mp3", provider="openai_compatible", model="m"
        )
        assert t.text == "全文"
        assert t.segments == []


# --------------------------------------------------------------------------- #
# Normalizer — generic fallback


def test_generic_fallback_handles_chunks_key() -> None:
    raw = {
        "language": "en",
        "chunks": [
            {"timestamp": [0.0, 1.0], "text": "hi", "confidence": 0.8},
            {"timestamp": [1.0, 2.0], "text": "there"},
        ],
    }
    t = normalize(raw, source_file="x.mp3", provider="some_other", model="?")
    assert len(t.segments) == 2
    assert t.segments[0].confidence == pytest.approx(0.8)
    assert t.segments[1].confidence is None
    assert t.duration == pytest.approx(2.0)
