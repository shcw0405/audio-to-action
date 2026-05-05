"""Diarization adapter (stub).

MVP ships with an interface and a no-op ``"none"`` provider only. The
intent: keep the call site stable so plugging pyannote / WhisperX /
Deepgram diarization in later does not require touching the rest of the
pipeline.

A diarizer takes a path to audio and returns a list of speaker turns:

    [{"start": 0.0, "end": 4.7, "speaker": "SPEAKER_01"}, ...]

The ``transcript_normalizer`` then merges these turns onto the ASR
segments by timestamp overlap.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Protocol


class Diarizer(Protocol):
    name: str

    def diarize(
        self, audio_path: str | Path, **kwargs: Any
    ) -> list[dict[str, Any]]:
        """Return a list of ``{start, end, speaker}`` dicts."""
        ...


_REGISTRY: dict[str, type] = {}


def register_diarizer(name: str) -> Callable[[type], type]:
    def deco(cls: type) -> type:
        if not hasattr(cls, "diarize"):
            raise TypeError(f"{cls.__name__} must define a diarize(...) method")
        _REGISTRY[name] = cls
        cls.name = name  # type: ignore[attr-defined]
        return cls

    return deco


def get_diarizer(name: str, config: dict[str, Any]) -> Diarizer:
    if name not in _REGISTRY:
        raise KeyError(
            f"unknown diarizer {name!r}. Registered: {sorted(_REGISTRY)}."
        )
    return _REGISTRY[name](config)  # type: ignore[call-arg]


# --------------------------------------------------------------------------- #
# Built-in: no-op


@register_diarizer("none")
class _NoDiarizer:
    """Returns no turns. Use when diarization is disabled or unavailable."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}

    def diarize(
        self, audio_path: str | Path, **kwargs: Any
    ) -> list[dict[str, Any]]:
        return []


# --------------------------------------------------------------------------- #
# Stubs — registered but raise on use. Implement to enable.


@register_diarizer("pyannote")
class _PyannoteDiarizer:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    def diarize(
        self, audio_path: str | Path, **kwargs: Any
    ) -> list[dict[str, Any]]:
        raise NotImplementedError(
            "pyannote diarization is a stub. To enable:\n"
            "  pip install pyannote.audio\n"
            "  set HF_TOKEN, accept the model license,\n"
            "  then implement _PyannoteDiarizer.diarize."
        )


@register_diarizer("whisperx")
class _WhisperXDiarizer:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    def diarize(
        self, audio_path: str | Path, **kwargs: Any
    ) -> list[dict[str, Any]]:
        raise NotImplementedError(
            "whisperx diarization is a stub. Implement "
            "_WhisperXDiarizer.diarize to enable."
        )


def from_settings(settings: dict[str, Any]) -> Diarizer:
    section = settings.get("diarization", {})
    if not section.get("enable", False):
        return _NoDiarizer({})
    name = section.get("provider", "none")
    config = section.get(name, {}) if name != "none" else {}
    return get_diarizer(name, config)
