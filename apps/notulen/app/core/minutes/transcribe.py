"""CPU whisper transcription (local fallback).

The dashboard runs whisper-medium on CPU when no GPU worker is available
(KUBECONFIG_DATA unset, K8s down, dev box). Speaker diarization is
GPU-only; this fallback returns transcripts without speaker labels.

Twin declaration: the GPU path in
``apps/notulen/entrypoints/worker.py`` carries its own
transcription (whisper-large-v3 + pyannote) by design — the worker image
is a self-contained distribution unit with no package imports, so the
block-formatting grammar is deliberately duplicated there (module-standard
§2.2 twin rule).

FAILURE POLICY: Tier-1 — model/transcription errors propagate;
``process_job`` marks the job ``failed``. faster_whisper imports lazily so
the dashboard boots without it loaded.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger("notulen")

# Silence longer than this starts a new transcript block.
PAUSE_THRESHOLD_SEC = 2.0


def _format_ts(seconds: float) -> str:
    """Format seconds as [MM:SS]."""
    minutes, secs = divmod(int(seconds), 60)
    return f"[{minutes:02d}:{secs:02d}]"


def transcribe_cpu(wav_path: Path) -> tuple[str, float]:
    """Transcribe a WAV file with whisper (CPU).

    Returns (transcript_text, duration_seconds).
    """
    import gc  # noqa: PLC0415
    from faster_whisper import WhisperModel  # noqa: PLC0415 — heavy, GPU-image dep

    logger.info("Loading whisper medium model (int8, CPU)...")
    model = WhisperModel("medium", compute_type="int8", device="cpu")
    logger.info("Whisper model loaded.")

    try:
        segments, info = model.transcribe(
            str(wav_path),
            language=os.environ.get("MINUTES_LANGUAGE", "nl"),
            beam_size=5,
            vad_filter=True, word_timestamps=True,
        )

        blocks: list[str] = []
        current_block: list[str] = []
        block_start: float = 0.0
        prev_end: float = 0.0

        for segment in segments:
            # New block on pause
            if current_block and segment.start - prev_end > PAUSE_THRESHOLD_SEC:
                blocks.append(f"{_format_ts(block_start)} {' '.join(current_block)}")
                current_block = []
                block_start = segment.start

            if not current_block:
                block_start = segment.start

            current_block.append(segment.text.strip())
            prev_end = segment.end

        if current_block:
            blocks.append(f"{_format_ts(block_start)} {' '.join(current_block)}")

        transcript = "\n\n".join(blocks)
        return transcript, info.duration
    finally:
        del model
        gc.collect()
        logger.info("Whisper model unloaded.")
