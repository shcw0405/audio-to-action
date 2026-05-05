"""ASR adapter / provider layer.

The skill never talks to a specific ASR vendor directly. It talks to an
``ASRProvider`` instance whose ``transcribe`` method returns a *raw* dict in
whatever shape that vendor uses; the ``transcript_normalizer`` then turns
that dict into the unified :class:`tools.schema.Transcript`.

Why a registry pattern? So that swapping ``asr.provider`` in
``settings.yaml`` is enough to change behaviour — no code edits in the rest
of the skill.

Built-in providers
------------------
- ``openai_compatible`` — fully implemented. Works with OpenAI itself,
  faster-whisper-server, vLLM, or any endpoint that mirrors
  ``POST /v1/audio/transcriptions``.
- ``faster_whisper_local`` — interface stub. Implement
  :class:`_FasterWhisperLocal.transcribe` to enable.
- ``custom_http`` — interface stub. Implement
  :class:`_CustomHTTP.transcribe` to enable.

Adding a provider is a 3-step process — see README §6.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, Protocol

try:  # requests is the only network dep, keep import optional for tests
    import requests  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover
    requests = None  # type: ignore[assignment]


class ASRProvider(Protocol):
    """Minimal interface every adapter must satisfy.

    Adapters return *raw* provider output. Normalization happens elsewhere
    (``transcript_normalizer.normalize``) so each adapter stays small and
    testable.
    """

    name: str

    def transcribe(
        self,
        audio_path: str | Path,
        *,
        language: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Transcribe ``audio_path`` and return the provider's raw response."""
        ...


# --------------------------------------------------------------------------- #
# Provider registry — populated by @register_provider

_REGISTRY: dict[str, type] = {}


def register_provider(name: str) -> Callable[[type], type]:
    """Class decorator that puts a provider class into the registry.

    Used like::

        @register_provider("deepgram")
        class Deepgram(ASRProvider): ...
    """

    def deco(cls: type) -> type:
        if not hasattr(cls, "transcribe"):
            raise TypeError(f"{cls.__name__} must define a transcribe(...) method")
        _REGISTRY[name] = cls
        cls.name = name  # type: ignore[attr-defined]
        return cls

    return deco


def get_provider(name: str, config: dict[str, Any]) -> ASRProvider:
    """Look up a provider by name and instantiate with its config block."""
    if name not in _REGISTRY:
        raise KeyError(
            f"unknown ASR provider {name!r}. "
            f"Registered: {sorted(_REGISTRY)}. "
            f"Add one with @register_provider in tools/asr_client.py."
        )
    cls = _REGISTRY[name]
    return cls(config)  # type: ignore[call-arg]


def list_providers() -> list[str]:
    return sorted(_REGISTRY)


# --------------------------------------------------------------------------- #
# Built-in: OpenAI-compatible /audio/transcriptions endpoint


@register_provider("openai_compatible")
class _OpenAICompatible:
    """OpenAI-style ``/v1/audio/transcriptions`` adapter.

    Works against OpenAI's hosted API and any local server that imitates the
    same wire format (faster-whisper-server, vLLM, LM Studio, ...).

    Config block (from ``settings.yaml::asr.openai_compatible``)::

        base_url: http://127.0.0.1:8000/v1
        api_key_env: ASR_API_KEY
        model: faster-whisper-large-v3
        language: zh
        response_format: verbose_json
        timestamp_granularities: [segment]
        temperature: 0.0
        timeout_seconds: 600
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.base_url = str(config.get("base_url", "")).rstrip("/")
        if not self.base_url:
            raise ValueError("openai_compatible.base_url is required")
        env_name = config.get("api_key_env", "ASR_API_KEY")
        self.api_key = os.environ.get(env_name)
        # Local servers often don't require auth; tolerate missing key.
        self.model = config.get("model", "whisper-1")
        self.default_language = config.get("language")
        self.response_format = config.get("response_format", "verbose_json")
        self.timestamp_granularities = config.get(
            "timestamp_granularities", ["segment"]
        )
        self.temperature = float(config.get("temperature", 0.0))
        self.timeout = float(config.get("timeout_seconds", 600))

    # ------------------------------------------------------------------ #

    def transcribe(
        self,
        audio_path: str | Path,
        *,
        language: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if requests is None:
            raise RuntimeError(
                "the `requests` package is required for openai_compatible ASR. "
                "pip install requests"
            )

        path = Path(audio_path)
        if not path.is_file():
            raise FileNotFoundError(path)

        url = f"{self.base_url}/audio/transcriptions"
        headers: dict[str, str] = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        data: dict[str, Any] = {
            "model": self.model,
            "response_format": self.response_format,
            "temperature": self.temperature,
        }
        lang = language or self.default_language
        if lang:
            data["language"] = lang
        # OpenAI requires a list of granularities; older servers may not
        # support it — we still send to keep the contract stable.
        if self.timestamp_granularities:
            data["timestamp_granularities[]"] = self.timestamp_granularities

        with path.open("rb") as fh:
            files = {"file": (path.name, fh, _guess_mime(path))}
            response = requests.post(
                url,
                headers=headers,
                data=data,
                files=files,
                timeout=self.timeout,
            )

        if response.status_code >= 400:
            # Don't echo the API key. Body may contain useful provider error.
            raise RuntimeError(
                f"ASR provider returned {response.status_code}: "
                f"{response.text[:500]}"
            )

        return response.json()


def _guess_mime(path: Path) -> str:
    ext = path.suffix.lower().lstrip(".")
    return {
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "m4a": "audio/mp4",
        "flac": "audio/flac",
        "ogg": "audio/ogg",
        "webm": "audio/webm",
    }.get(ext, "application/octet-stream")


# --------------------------------------------------------------------------- #
# Stubs — interface exists so callers don't need to special-case "not yet
# implemented" providers. Each raises NotImplementedError with a clear next-
# step pointer.


@register_provider("faster_whisper_local")
class _FasterWhisperLocal:
    """Local faster-whisper. Interface only — implement to enable."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    def transcribe(
        self, audio_path: str | Path, *, language: str | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        raise NotImplementedError(
            "faster_whisper_local is a stub. To enable:\n"
            "  pip install faster-whisper\n"
            "  then implement _FasterWhisperLocal.transcribe in "
            "tools/asr_client.py."
        )


@register_provider("custom_http")
class _CustomHTTP:
    """Custom HTTP endpoint. Interface only — implement to enable."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    def transcribe(
        self, audio_path: str | Path, *, language: str | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        raise NotImplementedError(
            "custom_http is a stub. Implement _CustomHTTP.transcribe to "
            "POST your audio to settings.yaml::asr.custom_http.url and "
            "return the raw JSON."
        )


# --------------------------------------------------------------------------- #
# Convenience: load settings.yaml and instantiate the active provider


def from_settings(settings: dict[str, Any]) -> ASRProvider:
    """Read the ``asr`` section of a parsed settings dict and return a provider.

    Example::

        import yaml
        from tools.asr_client import from_settings
        with open("settings.yaml") as f:
            settings = yaml.safe_load(f)
        asr = from_settings(settings)
        raw = asr.transcribe("meeting.mp3")
    """
    asr_section = settings.get("asr", {})
    name = asr_section.get("provider")
    if not name:
        raise KeyError("settings.yaml::asr.provider is required")
    config = asr_section.get(name, {})
    return get_provider(name, config)
