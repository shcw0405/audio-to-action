"""Utility helpers shared across the skill.

Three responsibilities:

1. **Probing** — verify an audio file exists, has a supported extension,
   measure duration when ``ffprobe`` is available.
2. **Format normalization** — call ``ffmpeg`` to transcode to 16 kHz mono
   WAV when the ASR provider needs it (or just for safety).
3. **Safety** — redact API-key-shaped strings before they enter logs.

The helpers are intentionally dependency-light. ``ffmpeg`` / ``ffprobe`` are
optional; if missing we degrade gracefully and return what we can.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SUPPORTED_EXTENSIONS: tuple[str, ...] = (
    "mp3", "wav", "m4a", "flac", "ogg", "webm",
)


@dataclass
class AudioProbe:
    path: Path
    extension: str
    size_bytes: int
    duration_seconds: float | None  # None when ffprobe unavailable
    is_supported: bool
    warnings: list[str]


def probe_audio(
    path: str | Path,
    *,
    supported_formats: tuple[str, ...] = SUPPORTED_EXTENSIONS,
    warn_duration_seconds: float = 7200.0,
    hard_max_duration_seconds: float = 21600.0,
    ffmpeg_path: str = "ffmpeg",
) -> AudioProbe:
    """Validate an audio file at ``path`` before sending it to ASR.

    Raises ``FileNotFoundError`` if the file is missing, ``ValueError`` if
    the file exceeds the hard duration limit. All other issues are surfaced
    as ``warnings`` on the returned :class:`AudioProbe`.
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"audio file not found: {p}")

    extension = p.suffix.lower().lstrip(".")
    is_supported = extension in supported_formats
    size_bytes = p.stat().st_size
    warnings: list[str] = []

    duration: float | None = None
    if shutil.which("ffprobe"):
        duration = _ffprobe_duration(p)
    else:
        warnings.append(
            "ffprobe not found on PATH; cannot determine duration. "
            "Install ffmpeg to enable duration checks."
        )

    if duration is not None:
        if duration > hard_max_duration_seconds:
            raise ValueError(
                f"audio is {duration:.0f}s, exceeds hard max "
                f"{hard_max_duration_seconds:.0f}s. Split it before transcribing."
            )
        if duration > warn_duration_seconds:
            warnings.append(
                f"audio is {duration:.0f}s (> {warn_duration_seconds:.0f}s). "
                "ASR may take a long time and providers may charge per-second."
            )

    if not is_supported:
        warnings.append(
            f"extension .{extension} not in supported set {supported_formats}. "
            "Will attempt to transcode with ffmpeg if needed."
        )

    return AudioProbe(
        path=p,
        extension=extension,
        size_bytes=size_bytes,
        duration_seconds=duration,
        is_supported=is_supported,
        warnings=warnings,
    )


def _ffprobe_duration(path: Path) -> float | None:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=30)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return None
    try:
        return float(out.decode().strip())
    except ValueError:
        return None


# --------------------------------------------------------------------------- #
# ffmpeg transcoding


def ensure_wav_16k_mono(
    src: str | Path,
    *,
    ffmpeg_path: str = "ffmpeg",
    out_dir: str | Path | None = None,
) -> Path:
    """Return a path to a 16 kHz mono WAV version of ``src``.

    If ``src`` is already 16k mono WAV we return it unchanged. Otherwise we
    transcode with ffmpeg to ``<out_dir>/<stem>.16k.wav`` (defaults to the
    same directory as ``src``).

    Raises ``RuntimeError`` if ffmpeg is unavailable.
    """
    p = Path(src)
    if not p.is_file():
        raise FileNotFoundError(p)

    if not shutil.which(ffmpeg_path):
        raise RuntimeError(
            f"{ffmpeg_path} not found on PATH. Install ffmpeg or set "
            "settings.yaml::audio.ffmpeg_path to its absolute path."
        )

    out_root = Path(out_dir) if out_dir else p.parent
    out_root.mkdir(parents=True, exist_ok=True)
    dst = out_root / f"{p.stem}.16k.wav"

    if dst.exists() and dst.stat().st_mtime >= p.stat().st_mtime:
        return dst  # cached

    cmd = [
        ffmpeg_path,
        "-y",
        "-i", str(p),
        "-ac", "1",
        "-ar", "16000",
        "-c:a", "pcm_s16le",
        str(dst),
    ]
    proc = subprocess.run(
        cmd, capture_output=True, text=True, timeout=3600
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed (exit {proc.returncode}). "
            f"stderr (truncated): {proc.stderr[-500:]}"
        )
    return dst


# --------------------------------------------------------------------------- #
# Time formatting — used by all prompt outputs


def seconds_to_hhmmss(seconds: float) -> str:
    """``73.4 → '01:13'``, ``3725 → '01:02:05'``."""
    seconds = max(0.0, float(seconds))
    h = int(seconds) // 3600
    m = (int(seconds) % 3600) // 60
    s = int(seconds) % 60
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def seconds_to_human(seconds: float) -> str:
    """``3725 → '1h2m5s'``, ``73 → '1m13s'``, ``5 → '5s'``."""
    seconds = max(0.0, float(seconds))
    h = int(seconds) // 3600
    m = (int(seconds) % 3600) // 60
    s = int(seconds) % 60
    if h:
        return f"{h}h{m}m{s}s"
    if m:
        return f"{m}m{s}s"
    return f"{s}s"


# --------------------------------------------------------------------------- #
# Settings loading


def load_settings(path: str | Path = "settings.yaml") -> dict[str, Any]:
    """Read settings.yaml. Imports yaml lazily so tests don't require it.

    Raises a clear error if pyyaml isn't installed or the file is missing.
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(
            f"settings file {p} not found. Copy settings.yaml from the skill root."
        )
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "pyyaml is required to read settings.yaml. pip install pyyaml"
        ) from e
    with p.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{p} must contain a YAML mapping at the top level")
    return data


# --------------------------------------------------------------------------- #
# Secret redaction — applied to anything we log


_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(sk-[A-Za-z0-9_\-]{16,})"),
    re.compile(r"\b(Bearer\s+[A-Za-z0-9_\-\.]{16,})", re.IGNORECASE),
    re.compile(r"\b([A-Za-z0-9_\-]{32,})\b"),  # generic long-token catch-all
)


def redact_secrets(text: str, *, env_keys: tuple[str, ...] = ()) -> str:
    """Replace likely secrets in ``text`` with ``***REDACTED***``.

    ``env_keys`` lets you pass extra env-var names whose *values* should be
    redacted explicitly (useful when you know exactly which keys leaked).
    """
    out = text
    for key in env_keys:
        val = os.environ.get(key)
        if val and val in out:
            out = out.replace(val, "***REDACTED***")
    for pat in _SECRET_PATTERNS:
        out = pat.sub("***REDACTED***", out)
    return out
