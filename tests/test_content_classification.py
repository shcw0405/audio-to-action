"""Tests for the content-classification contract.

We do not call any LLM here. Instead we lock in:

- The Classification dataclass round-trips.
- ``is_ambiguous`` correctly fires when:
    * confidence < threshold
    * label == "unknown" (regardless of confidence)
- The set of allowed labels matches the SKILL.md contract.

When you add a new content-type label, also add it to
``settings.yaml::classification.labels`` and update the asserted set in
``test_allowed_labels_match_settings``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.schema import ALLOWED_LABELS, Classification  # noqa: E402


EXPECTED_LABELS = {
    "group_meeting",
    "advisor_student_discussion",
    "casual_discussion",
    "voice_memo",
    "student_progress_report",
    "unknown",
}


def test_allowed_labels_match_skill_md_contract() -> None:
    assert set(ALLOWED_LABELS) == EXPECTED_LABELS


def test_allowed_labels_match_settings_yaml() -> None:
    """If settings.yaml is present and parseable, its labels must agree."""
    settings_path = Path(__file__).resolve().parent.parent / "settings.yaml"
    if not settings_path.exists():
        pytest.skip("settings.yaml not present")
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        pytest.skip("pyyaml not installed")
    data = yaml.safe_load(settings_path.read_text(encoding="utf-8")) or {}
    declared = set(data.get("classification", {}).get("labels", []) or [])
    assert declared == EXPECTED_LABELS, (
        f"settings.yaml::classification.labels {declared} does not match "
        f"schema.ALLOWED_LABELS {EXPECTED_LABELS}"
    )


# --------------------------------------------------------------------------- #


class TestAmbiguityRules:
    def test_high_confidence_known_label_is_not_ambiguous(self) -> None:
        c = Classification(label="group_meeting", confidence=0.85)
        assert c.is_ambiguous(0.6) is False

    def test_low_confidence_is_ambiguous(self) -> None:
        c = Classification(label="group_meeting", confidence=0.55)
        assert c.is_ambiguous(0.6) is True

    def test_unknown_is_ambiguous_even_at_high_confidence(self) -> None:
        c = Classification(label="unknown", confidence=0.99)
        assert c.is_ambiguous(0.6) is True

    @pytest.mark.parametrize("threshold", [0.3, 0.5, 0.6, 0.8, 0.95])
    def test_threshold_is_inclusive_lower_exclusive_upper(
        self, threshold: float
    ) -> None:
        # exact threshold: not ambiguous
        c = Classification(label="voice_memo", confidence=threshold)
        assert c.is_ambiguous(threshold) is False
        # just below: ambiguous
        if threshold > 0.0:
            c2 = Classification(label="voice_memo", confidence=threshold - 0.01)
            assert c2.is_ambiguous(threshold) is True


# --------------------------------------------------------------------------- #


class TestRoundTrip:
    def test_to_from_dict(self) -> None:
        c = Classification(
            label="advisor_student_discussion",
            confidence=0.81,
            rationale="两位发言者，导师与学生的不对称对话。",
            alternative_label="group_meeting",
            alternative_confidence=0.42,
        )
        recovered = Classification.from_dict(
            json.loads(json.dumps(c.to_dict()))
        )
        assert recovered.to_dict() == c.to_dict()

    def test_from_dict_minimal(self) -> None:
        c = Classification.from_dict(
            {"label": "voice_memo", "confidence": 0.7}
        )
        assert c.rationale == ""
        assert c.alternative_label is None


# --------------------------------------------------------------------------- #
# A small sanity check on the *shape* the classifier prompt is expected to
# return — kept here so prompt drift doesn't silently break ingestion.


SAMPLE_CLASSIFIER_OUTPUTS = [
    {
        "label": "group_meeting",
        "confidence": 0.83,
        "rationale": "三位发言者；多次任务分派。",
        "alternative_label": "advisor_student_discussion",
        "alternative_confidence": 0.41,
    },
    {
        "label": "voice_memo",
        "confidence": 0.92,
        "rationale": "single speaker, self-addressed.",
    },
    {
        "label": "unknown",
        "confidence": 0.25,
        "rationale": "transcript too short",
    },
]


@pytest.mark.parametrize("payload", SAMPLE_CLASSIFIER_OUTPUTS)
def test_sample_classifier_outputs_parse(payload: dict) -> None:
    c = Classification.from_dict(payload)
    assert c.label == payload["label"]
    assert 0.0 <= c.confidence <= 1.0
