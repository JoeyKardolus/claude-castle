"""GPU worker for the notulen pipeline.

Runs as a per-job K8s Job (created by ``gpu_jobs.create_notulen_job``,
the optional GPU tier). Reads job config from env vars,
downloads audio from S3, runs pyannote diarization + whisper-large-v3
transcription on GPU, generates notulen markdown via Claude API, and
writes results back to PostgreSQL.

Twin declaration (module-standard §2.2): this file is a self-contained
distribution unit — the worker image copies ONLY this file plus the
template (infra/docker/notulen-worker/Dockerfile), so it
deliberately duplicates, with no import path back to the dashboard:
    - the transcript block grammar of ``app/core/minutes/transcribe.py``
      (plus speaker labels, which are GPU-only),
    - the prompt of ``app/core/minutes/notulen_writer.py``,
    - the column allowlist of ``app/shared/update_job.py``.
Keep them in sync by hand; the duplication is the design, not drift.

FAILURE POLICY:
    - Job-row writes (status, transcript, markdown) are Tier-1: failures
      propagate, the worker exits 1, K8s records the Job failed, and the
      dashboard's startup recovery sweeps the orphaned row. Until
      2026-06-12 these writes were swallowed with a log line, which could
      silently lose a finished transcription.
    - The ai-calls bookkeeping INSERT is Tier-2 best-effort: cost
      accounting must never fail a finished notulen (documented swallow).
    - ``complete`` is NOT set here: the worker has no commit credential, so
      it parks the markdown as ``committing`` and the dashboard's
      git_writer_loop commits it.

Env vars (all required unless noted):
    JOB_ID             UUID of the notulen_jobs row
    AUDIO_KEY          S3 key of the uploaded audio (e.g. notulen/audio/<id>.wav)
    TITLE              Meeting subject
    MEETING_DATE       YYYY-MM-DD
    ATTENDEES          Comma-separated attendee list (may be empty)
    AGENDA             Optional agenda text (may be empty)

    DB_URL             PostgreSQL connection string
    ANTHROPIC_API_KEY  Claude API key
    S3_BUCKET          Bucket holding the uploaded audio (default: castle)
    S3_ENDPOINT        Optional custom S3 endpoint URL (unset = AWS)
    S3_REGION          Default: us-east-1
    S3_ACCESS_KEY      Optional; falls back to boto3's default credential
    S3_SECRET_KEY        chain (AWS_ACCESS_KEY_ID / instance role / ...)
    MINUTES_LANGUAGE   ISO 639-1 language for transcription + minutes
                       (optional, default: nl)

Config is read at module scope as deliberate fail-fast (the sanctioned
one-shot-Job exception in module-standard §6.1): a missing env var must
kill the pod at import, before any GPU time is spent.
"""
from __future__ import annotations

import gc
import logging
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("notulen_worker")


# ── Config (module-scope fail-fast, see docstring) ──────────────────────────

JOB_ID = os.environ["JOB_ID"]
AUDIO_KEY = os.environ["AUDIO_KEY"]
TITLE = os.environ["TITLE"]
MEETING_DATE = os.environ["MEETING_DATE"]
ATTENDEES = [name.strip() for name in os.environ.get("ATTENDEES", "").split(",") if name.strip()]
AGENDA = os.environ.get("AGENDA", "")

DB_URL = os.environ["DB_URL"]
S3_BUCKET = os.environ.get("S3_BUCKET", "castle")
S3_REGION = os.environ.get("S3_REGION", "us-east-1")
MINUTES_LANGUAGE = os.environ.get("MINUTES_LANGUAGE", "nl")

# Silence longer than this starts a new transcript block (twin of
# app/core/minutes/transcribe.py).
PAUSE_THRESHOLD_SEC = 2.0


# ── Database helpers ────────────────────────────────────────────────────────

def _db_conn():
    import psycopg2
    return psycopg2.connect(DB_URL)


# Only these columns may be updated by _update_job. Interpolating a dict
# key straight into the UPDATE statement is a classic SQL-injection
# footgun even when all call sites look safe. Allowlist at the DB boundary
# so an attacker-influenced key can never reach raw SQL. Twin of
# app/shared/update_job.py.
_UPDATABLE_JOB_COLUMNS = frozenset({
    "status", "error",
    "transcript_text", "duration_secs",
    "output_markdown", "completed_at",
    "s3_audio_key",
})


def _update_job(**fields) -> None:
    """Tier-1 job-row write: raises on unknown columns or DB failure."""
    if not fields:
        return
    bad = set(fields) - _UPDATABLE_JOB_COLUMNS
    if bad:
        raise ValueError(f"Refusing to update notulen_jobs: unknown columns {sorted(bad)}")
    conn = _db_conn()
    try:
        # Column names are safe (allowlisted above); values go through
        # psycopg2 parameter substitution.
        sets = ", ".join(f'"{column}" = %s' for column in fields)
        vals = list(fields.values())
        vals.append(JOB_ID)
        with conn.cursor() as cur:
            cur.execute(f"UPDATE notulen_jobs SET {sets} WHERE id = %s", vals)
        conn.commit()
    finally:
        conn.close()


def _log_ai_call(input_tokens: int, output_tokens: int, cost: float, duration_ms: int, success: bool, error: str = "") -> None:
    try:
        conn = _db_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO notulen_ai_calls (run_id, purpose, model, input_tokens, output_tokens, "
                    "cost_estimate, duration_ms, success, error) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (JOB_ID, "generate_notulen", "claude-sonnet-4-6",
                     input_tokens, output_tokens, cost, duration_ms, success, error or None),
                )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        # Documented Tier-2 swallow: cost bookkeeping must never fail a
        # finished notulen (see module FAILURE POLICY).
        log.exception("Failed to record ai-call bookkeeping for job %s", JOB_ID)


# ── S3 helpers ──────────────────────────────────────────────────────────────

def _s3_client():
    import boto3
    from botocore.config import Config
    kwargs = {}
    if os.environ.get("S3_ENDPOINT"):
        kwargs["endpoint_url"] = os.environ["S3_ENDPOINT"]
    if os.environ.get("S3_ACCESS_KEY"):
        kwargs["aws_access_key_id"] = os.environ["S3_ACCESS_KEY"]
        kwargs["aws_secret_access_key"] = os.environ["S3_SECRET_KEY"]
    return boto3.client(
        "s3",
        region_name=S3_REGION,
        config=Config(signature_version="s3v4", retries={"max_attempts": 3, "mode": "adaptive"}),
        **kwargs,
    )


def _download_audio(local_path: Path) -> None:
    log.info("Downloading %s from S3...", AUDIO_KEY)
    _s3_client().download_file(S3_BUCKET, AUDIO_KEY, str(local_path))


# ── Audio transcode ─────────────────────────────────────────────────────────

def _transcode_to_wav(src: Path, dst: Path) -> None:
    """Transcode any audio format to 16kHz mono WAV for whisper/pyannote."""
    result = subprocess.run(
        ["ffmpeg", "-i", str(src), "-ar", "16000", "-ac", "1",
         "-f", "wav", str(dst), "-y", "-loglevel", "error"],
        capture_output=True, text=True, timeout=600,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr}")


# ── Diarization ─────────────────────────────────────────────────────────────

def _diarize(wav_path: Path) -> list[tuple[float, float, str]]:
    """Run pyannote speaker diarization on GPU. Returns [(start, end, speaker), ...]."""
    from pyannote.audio import Pipeline
    import torch

    log.info("Loading pyannote pipeline on GPU...")
    hf_token = os.environ.get("HF_TOKEN") or None
    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        use_auth_token=hf_token,
    )
    # Pyannote 3.x silently returns None when the HF token is invalid or the
    # gated model terms haven't been accepted, so `.to()` blows up with the
    # cryptic "'NoneType' has no attribute 'to'". Fail loud with the actual
    # cause — past us learned this the hard way on 2026-05-13.
    if pipeline is None:
        raise RuntimeError(
            "pyannote Pipeline.from_pretrained returned None. "
            "Cause is almost always one of: (1) HF_TOKEN missing/invalid, "
            "(2) gated-model terms not accepted at "
            "huggingface.co/pyannote/{speaker-diarization-3.1, segmentation-3.0}, "
            "(3) network block. Regenerate token + re-accept terms."
        )
    pipeline.to(torch.device("cuda"))

    log.info("Running diarization...")
    started = time.time()
    output = pipeline(str(wav_path))
    diarization = getattr(output, "speaker_diarization", output)

    turns = [
        (turn.start, turn.end, speaker)
        for turn, _track, speaker in diarization.itertracks(yield_label=True)
    ]
    n_speakers = len(set(speaker for _start, _end, speaker in turns))
    log.info("Diarization done in %.1fs: %d turns, %d speakers",
             time.time() - started, len(turns), n_speakers)

    del pipeline, output, diarization
    gc.collect()
    torch.cuda.empty_cache()
    return turns


# ── Transcription ───────────────────────────────────────────────────────────

def _format_ts(seconds: float) -> str:
    minutes, secs = divmod(int(seconds), 60)
    return f"[{minutes:02d}:{secs:02d}]"


def _find_speaker(timestamp: float, turns: list[tuple[float, float, str]]) -> str:
    for start, end, speaker in turns:
        if start <= timestamp <= end:
            return speaker
    return ""


def _merge_into_blocks(segments, speaker_turns: list[tuple[float, float, str]]) -> list[str]:
    """Merge whisper segments into ``[MM:SS] [SPEAKER] text`` blocks.

    A new block starts on a pause > PAUSE_THRESHOLD_SEC or a speaker
    change (the speaker-label half is GPU-only; the pause grammar is the
    declared twin of ``app/core/minutes/transcribe.py``).
    """
    blocks: list[str] = []
    current_block: list[str] = []
    current_speaker: str = ""
    block_start: float = 0.0
    prev_end: float = 0.0

    for segment in segments:
        seg_mid = (segment.start + segment.end) / 2
        speaker = _find_speaker(seg_mid, speaker_turns) if speaker_turns else ""
        speaker_changed = bool(speaker and current_speaker and speaker != current_speaker)

        if current_block and (segment.start - prev_end > PAUSE_THRESHOLD_SEC or speaker_changed):
            prefix = _format_ts(block_start) + (f" [{current_speaker}]" if current_speaker else "")
            blocks.append(f"{prefix} {' '.join(current_block)}")
            current_block = []
            block_start = segment.start

        if not current_block:
            block_start = segment.start
            current_speaker = speaker
        if speaker:
            current_speaker = speaker

        current_block.append(segment.text.strip())
        prev_end = segment.end

    if current_block:
        prefix = _format_ts(block_start) + (f" [{current_speaker}]" if current_speaker else "")
        blocks.append(f"{prefix} {' '.join(current_block)}")

    return blocks


def _transcribe(wav_path: Path, speaker_turns: list[tuple[float, float, str]]) -> tuple[str, float]:
    """Run whisper-large-v3 on GPU; returns (block-merged transcript, duration)."""
    from faster_whisper import WhisperModel

    log.info("Loading whisper large-v3 on GPU (float16)...")
    model = WhisperModel("large-v3", compute_type="float16", device="cuda")

    log.info("Transcribing...")
    started = time.time()
    segments, info = model.transcribe(
        str(wav_path), language=MINUTES_LANGUAGE, beam_size=5,
        vad_filter=True, word_timestamps=True,
    )

    blocks = _merge_into_blocks(segments, speaker_turns)
    transcript = "\n\n".join(blocks)
    log.info("Transcription done in %.1fs: %d blocks, duration=%.1fs",
             time.time() - started, len(blocks), info.duration)
    return transcript, info.duration


# ── Notulen generation ──────────────────────────────────────────────────────

def _load_template() -> str:
    for candidate in (Path(os.environ.get("NOTULEN_TEMPLATE", "/app/notulen_template.md")),):
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")
    return ""


def _generate_notulen(transcript: str) -> str:
    import anthropic

    template = _load_template()
    agenda_block = f"\nAGENDA (vooraf opgegeven door de gebruiker):\n{AGENDA.strip()}\n" if AGENDA.strip() else ""

    system_prompt = f"""Je bent een professionele notulist.

Maak notulen van de vergadering op basis van het transcript. Het transcript bevat
timestamps [MM:SS] en spreker-labels [SPEAKER_00], [SPEAKER_01] etc. per blok.
Verschillende labels = verschillende personen.

AANWEZIGEN: {", ".join(ATTENDEES)}
Koppel de spreker-labels aan de aanwezigen op basis van context.

TEMPLATE:
{template}
{agenda_block}
INVULREGELS:
- Onderwerp: "{TITLE}", Datum: {MEETING_DATE}, Aanwezig: {", ".join(ATTENDEES)}
- Notulist: "Automatisch (Whisper + Claude)"
- Schrijf de notulen in de taal met taalcode "{MINUTES_LANGUAGE}" ("nl" = Nederlands)
- "Besproken": subsectie per onderwerp met 2-5 bullets, noem sprekers waar mogelijk
- "Besluiten": alleen expliciete besluiten, of "Geen expliciete besluiten genomen."
- "Actiepunten": tabel, elke concrete taak apart, deadline alleen als expliciet genoemd
- Sla small talk over
- Geef ALLEEN het ingevulde template terug"""

    client = anthropic.Anthropic()
    started = time.time()
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4000,
            temperature=0,
            system=system_prompt,
            messages=[{"role": "user", "content": f"TRANSCRIPT:\n\n{transcript}"}],
        )
    except Exception as exc:
        _log_ai_call(0, 0, 0.0, int((time.time() - started) * 1000), False, str(exc)[:500])
        raise

    elapsed_ms = int((time.time() - started) * 1000)
    content = ""
    if response.content:
        first = response.content[0]
        content = getattr(first, "text", "") or ""
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    cost = (input_tokens / 1_000_000) * 3.0 + (output_tokens / 1_000_000) * 15.0
    _log_ai_call(input_tokens, output_tokens, round(cost, 6), elapsed_ms, True)
    log.info("Notulen generated in %.1fs (%d in / %d out tokens, $%.4f)",
             elapsed_ms / 1000, input_tokens, output_tokens, cost)
    return content


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> int:
    log.info("Notulen worker starting: job=%s audio=%s", JOB_ID, AUDIO_KEY)
    log.info("Title=%r date=%s attendees=%s", TITLE, MEETING_DATE, ATTENDEES)

    try:
        _update_job(status="transcribing")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            raw_path = tmp / "audio.raw"
            wav_path = tmp / "audio.wav"

            _download_audio(raw_path)
            _transcode_to_wav(raw_path, wav_path)
            raw_path.unlink(missing_ok=True)

            speaker_turns = _diarize(wav_path)
            transcript, duration = _transcribe(wav_path, speaker_turns)

        if not transcript.strip():
            raise RuntimeError("Transcription produced no text")

        _update_job(
            status="structuring",
            transcript_text=transcript,
            duration_secs=int(duration),
        )

        notulen_md = _generate_notulen(transcript)

        # `committing`, not `complete`: the markdown is in Postgres but not yet
        # in git. The dashboard's git_writer_loop commits it and flips the row
        # to `complete` (ADR-0020). completed_at marks markdown-ready time.
        _update_job(
            status="committing",
            output_markdown=notulen_md,
            completed_at=datetime.now(timezone.utc),
        )

        log.info("Job %s transcribed, handed to git_writer_loop for commit", JOB_ID)
        return 0
    except Exception as exc:
        log.exception("Worker failed")
        try:
            _update_job(status="failed", error=str(exc)[:2000])
        except Exception:
            # Documented swallow: the failure-mark itself failed (DB down).
            # Exit 1 below is the loud signal; the dashboard's startup
            # recovery sweeps the orphaned row once the K8s Job is gone.
            log.exception("Could not mark job %s failed", JOB_ID)
        return 1


if __name__ == "__main__":
    sys.exit(main())
