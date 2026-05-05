"""Tests for the task-extraction *contract*.

The extractor is implemented as an LLM prompt (``prompts/extract_tasks.md``)
so we cannot unit-test the model itself. What we *can* and *should* test
are the data structures the extractor emits into and the invariants it
must respect:

- Each emitted task carries at least one timestamped citation.
- A task without an owner is forbidden — it must be surfaced as a
  待确认 question instead.
- ``iter_segments_in_window`` correctly slices a transcript by timestamp,
  which is what the extractor uses to verify its own citations.

We model the contract with a tiny ``Task`` dataclass local to this test
file. If the runtime grows a real ``Task`` type later, replace this with
an import.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.schema import Segment, Transcript, iter_segments_in_window  # noqa: E402


# --------------------------------------------------------------------------- #
# Local Task contract — what extract_tasks.md is supposed to produce.


@dataclass
class Citation:
    start: float
    end: float
    excerpt: str  # ≤ 25 chars


@dataclass
class Task:
    owner: str               # speaker label or mapped name; never blank
    description: str
    deliverable: str | None = None
    deadline: str | None = None
    acceptance: str | None = None
    citations: list[Citation] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.owner:
            raise ValueError(
                "task without an owner is forbidden — surface as 待确认 instead"
            )
        if not self.citations:
            raise ValueError(
                f"task for {self.owner!r} has no citations — drop or surface as 待确认"
            )


# --------------------------------------------------------------------------- #


def _make_transcript() -> Transcript:
    """A small synthetic transcript modelled on examples/group_meeting_*."""
    segs = [
        Segment(id=1, start=0.0, end=8.0, text="开始组会，先讲进展。", speaker="SPEAKER_01"),
        Segment(id=2, start=8.0, end=21.0, text="baseline 复现到 92.3。", speaker="SPEAKER_02"),
        Segment(id=3, start=48.0, end=65.0,
                text="下周三之前 ImageNet baseline，code 整理。", speaker="SPEAKER_01"),
        Segment(id=4, start=65.0, end=80.0,
                text="下周三前没问题。", speaker="SPEAKER_02"),
        Segment(id=5, start=108.0, end=132.0,
                text="head 8/12/16/24，三个 seed，下周组会讲。", speaker="SPEAKER_01"),
        Segment(id=6, start=132.0, end=140.0,
                text="行，下周组会讲。", speaker="SPEAKER_03"),
        Segment(id=7, start=158.0, end=170.0,
                text="数据清洗这块先放一下。", speaker="SPEAKER_01"),
    ]
    return Transcript(
        source_file="meeting.mp3",
        language="zh",
        duration=170.0,
        text=" ".join(s.text for s in segs),
        segments=segs,
    )


# --------------------------------------------------------------------------- #
# Contract tests on Task


class TestTaskContract:
    def test_owner_required(self) -> None:
        with pytest.raises(ValueError):
            Task(
                owner="",
                description="Do something",
                citations=[Citation(0, 1, "x")],
            )

    def test_at_least_one_citation_required(self) -> None:
        with pytest.raises(ValueError):
            Task(owner="SPEAKER_02", description="Run baseline")

    def test_minimal_valid_task(self) -> None:
        t = Task(
            owner="SPEAKER_02",
            description="Run ImageNet baseline",
            deadline="下周三前",
            citations=[Citation(48.0, 65.0, "下周三之前 ImageNet baseline")],
        )
        assert t.deliverable is None
        assert t.acceptance is None
        assert t.uncertainties == []


# --------------------------------------------------------------------------- #
# Contract tests on citation slicing


class TestCitationSlicing:
    def test_citation_window_returns_overlapping_segments(self) -> None:
        t = _make_transcript()
        # The "下周三之前" task should cite 48s-65s.
        cited = iter_segments_in_window(t.segments, start=48.0, end=65.0)
        assert [s.id for s in cited] == [3]

    def test_citation_window_with_overlap_at_edges(self) -> None:
        t = _make_transcript()
        cited = iter_segments_in_window(t.segments, start=60.0, end=110.0)
        # seg 3 (48-65) overlaps; seg 4 (65-80) overlaps; seg 5 starts at 108
        assert [s.id for s in cited] == [3, 4, 5]

    def test_empty_window_returns_empty(self) -> None:
        t = _make_transcript()
        assert iter_segments_in_window(t.segments, 200.0, 300.0) == []


# --------------------------------------------------------------------------- #
# Sanity check on a full mock extractor output


def test_full_extractor_output_round_trips() -> None:
    """Models the per-person task list a faithful extractor would emit."""
    tasks = [
        Task(
            owner="SPEAKER_02",
            description="跑通 ImageNet 上的 baseline，对齐 paper 精度",
            deliverable="精度数 + 整理后 code",
            deadline="下周三前",
            acceptance=None,                # "未明确" → modeled as None
            citations=[
                Citation(48.0, 65.0, "下周三之前 ImageNet baseline"),
            ],
            uncertainties=[
                "验收标准未明确，是否需附实验报告？",
            ],
        ),
        Task(
            owner="SPEAKER_03",
            description="head 数消融 8/12/16/24，每组 3 seed",
            deliverable="实验结果，下周组会汇报",
            deadline="下周组会前（推测）",
            acceptance=None,
            citations=[
                Citation(108.0, 132.0, "head 8/12/16/24"),
            ],
            uncertainties=[
                "下周组会的具体日期未明",
            ],
        ),
    ]
    # No exceptions raised → the contract holds.
    assert all(t.citations for t in tasks)
    assert all(t.owner for t in tasks)

    # Owners list does not invent names — only speaker labels are present.
    owners = {t.owner for t in tasks}
    assert owners == {"SPEAKER_02", "SPEAKER_03"}


def test_directive_without_owner_must_not_become_task() -> None:
    """Models the rule: '"who is doing X?" -> 待确认 instead of guessing.'"""
    # A directive like "数据清洗先放一下" has no owner; the extractor MUST
    # NOT emit it as a Task. We assert that constructing a Task without an
    # owner is impossible (the contract enforces it).
    with pytest.raises(ValueError):
        Task(
            owner="",
            description="数据清洗暂缓",
            citations=[Citation(158.0, 170.0, "数据清洗先放一下")],
        )
