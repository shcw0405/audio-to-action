"""End-to-end harness — call the audio-to-action skill from Python.

Not part of the Skill itself. Useful when you want to batch-process audio
without going through Claude Code, or when you're debugging a new ASR
provider end-to-end.

Usage
-----

    # default settings.yaml at repo root
    python scripts/run_pipeline.py path/to/recording.m4a

    # custom config + custom output dir
    python scripts/run_pipeline.py recording.wav \\
        --settings my-settings.yaml \\
        --out-dir ./results

What it does
------------
1. ``probe_audio`` — verifies file, ext, duration (degrades gracefully
   without ffprobe).
2. ``asr.transcribe`` — sends the file to whatever provider is active in
   ``settings.yaml::asr.provider``.
3. ``normalize`` — coerces the provider response into the unified
   :class:`tools.schema.Transcript` shape.
4. Writes ``asr_raw.json``, ``transcript.json`` to the output directory.

Note this script does **not** drive the LLM stages (clean/classify/preset).
Those are the skill's job inside Claude Code, not the runtime's.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Allow running from anywhere — resolve project root from this file's location.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from tools.utils import load_settings, probe_audio, redact_secrets  # noqa: E402
from tools.asr_client import from_settings as asr_from_settings  # noqa: E402
from tools.transcript_normalizer import normalize  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run audio-to-action end-to-end (ASR + normalize)."
    )
    parser.add_argument(
        "audio",
        type=Path,
        help="Path to an audio file (.mp3 .wav .m4a .flac .ogg .webm).",
    )
    parser.add_argument(
        "--settings",
        type=Path,
        default=_REPO_ROOT / "settings.yaml",
        help="Path to settings.yaml (default: project root).",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Where to write artifacts. Default: <audio_dir>/out/",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    audio_path: Path = args.audio.resolve()
    out_dir: Path = (args.out_dir or audio_path.parent / "out").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    settings = load_settings(args.settings)
    audio_cfg = settings.get("audio", {})

    print(f"[probe]    {audio_path}")
    p = probe_audio(
        audio_path,
        warn_duration_seconds=float(audio_cfg.get("warn_duration_seconds", 7200)),
        hard_max_duration_seconds=float(audio_cfg.get("hard_max_duration_seconds", 21600)),
    )
    print(
        f"[probe]    ext={p.extension} size={p.size_bytes/1024/1024:.1f}MB "
        f"duration={p.duration_seconds}"
    )
    for w in p.warnings:
        print(f"[probe]    warn: {w}")

    asr = asr_from_settings(settings)
    provider_name = settings["asr"]["provider"]
    asr_cfg = settings["asr"][provider_name]
    print(
        f"[asr]      provider={provider_name} "
        f"base_url={asr_cfg.get('base_url')} model={asr_cfg.get('model')} "
        f"language={asr_cfg.get('language')}"
    )

    t0 = time.time()
    print("[asr]      sending file ...")
    raw = asr.transcribe(audio_path)
    elapsed = time.time() - t0
    print(f"[asr]      done in {elapsed:.1f}s")

    raw_path = out_dir / "asr_raw.json"
    raw_path.write_text(
        redact_secrets(json.dumps(raw, ensure_ascii=False, indent=2)),
        encoding="utf-8",
    )
    print(f"[asr]      raw response saved → {raw_path}")

    transcript = normalize(
        raw,
        source_file=str(audio_path),
        provider=provider_name,
        model=asr_cfg.get("model", "?"),
    )

    transcript_path = out_dir / "transcript.json"
    transcript_path.write_text(
        json.dumps(transcript.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        f"[normalize] segments={len(transcript.segments)} "
        f"language={transcript.language} duration={transcript.duration:.1f}s "
        f"diarization={transcript.has_diarization()}"
    )
    print(f"[normalize] saved      → {transcript_path}")
    print(f"[normalize] text bytes = {len(transcript.text)}")
    head = transcript.text[:200].replace("\n", " ")
    print(f"[normalize] text head  = {head}...")


if __name__ == "__main__":
    main()
