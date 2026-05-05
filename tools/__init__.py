"""audio-to-action runtime tools.

The ``tools`` package contains the Python building blocks the skill calls
into during a run:

- :mod:`schema`               — unified ``Transcript`` / ``Classification`` types
- :mod:`asr_client`           — provider-agnostic ASR adapter layer
- :mod:`diarization_client`   — pluggable diarization (stubs in MVP)
- :mod:`transcript_normalizer`— any-provider raw output → unified schema
- :mod:`utils`                — ffmpeg, file probing, redaction, time formatting

These modules are intentionally framework-free so they can be imported by
both the skill runtime and the test suite.
"""

from .schema import (
    ALLOWED_LABELS,
    Classification,
    Segment,
    Transcript,
    TranscriptMetadata,
    iter_segments_in_window,
)
from .asr_client import (
    ASRProvider,
    from_settings as asr_from_settings,
    get_provider,
    list_providers,
    register_provider,
)
from .diarization_client import (
    Diarizer,
    from_settings as diarizer_from_settings,
    get_diarizer,
    register_diarizer,
)
from .transcript_normalizer import normalize
from .utils import (
    AudioProbe,
    SUPPORTED_EXTENSIONS,
    ensure_wav_16k_mono,
    load_settings,
    probe_audio,
    redact_secrets,
    seconds_to_hhmmss,
    seconds_to_human,
)

__all__ = [
    "ALLOWED_LABELS",
    "ASRProvider",
    "AudioProbe",
    "Classification",
    "Diarizer",
    "SUPPORTED_EXTENSIONS",
    "Segment",
    "Transcript",
    "TranscriptMetadata",
    "asr_from_settings",
    "diarizer_from_settings",
    "ensure_wav_16k_mono",
    "get_diarizer",
    "get_provider",
    "iter_segments_in_window",
    "list_providers",
    "load_settings",
    "normalize",
    "probe_audio",
    "redact_secrets",
    "register_diarizer",
    "register_provider",
    "seconds_to_hhmmss",
    "seconds_to_human",
]
