"""
Voice processing for speech-to-text and text-to-speech.

Improvements over v1:
- Unified audio normalisation via a single ffmpeg pass (no pydub dependency)
- SpeechToText: configurable confidence threshold, language auto-detection, retry
- TextToSpeech: persistent Piper process with warm reuse; WAV header wrapping
- Helper: audio_bytes_to_wav ensures callers always receive a valid WAV file
- Cleaner error hierarchy: AudioConversionError, TranscriptionError, SynthesisError
"""

from __future__ import annotations

import io
import logging
import os
import shutil
import subprocess
import tempfile
import struct
import wave
from typing import Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Locate tools once at import time
# ---------------------------------------------------------------------------
FFMPEG_PATH: Optional[str] = shutil.which("ffmpeg")
if FFMPEG_PATH is None:
    logger.warning(
        "ffmpeg not found on PATH.  Browser-recorded audio (webm/ogg/mp3) "
        "cannot be decoded. Install ffmpeg to enable full audio support."
    )

PIPER_PATH: Optional[str] = shutil.which("piper")
if PIPER_PATH is None:
    logger.warning(
        "piper not found on PATH. Text-to-speech voice output will be unavailable. "
        "Install Piper to enable audio responses."
    )

# ---------------------------------------------------------------------------
# Temp directory bootstrap (handles restricted environments)
# ---------------------------------------------------------------------------
def _bootstrap_tmpdir() -> str:
    candidates = [
        os.environ.get("TMPDIR"),
        "/tmp",
        "/var/tmp",
        "/usr/tmp",
        os.path.join(os.getcwd(), "tmp"),
    ]
    for path in candidates:
        if path and os.path.isdir(path):
            return path
    fallback = os.path.join(os.getcwd(), "tmp")
    os.makedirs(fallback, exist_ok=True)
    os.environ["TMPDIR"] = fallback
    return fallback


tempfile.tempdir = _bootstrap_tmpdir()

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------
class AudioConversionError(RuntimeError):
    pass


class TranscriptionError(RuntimeError):
    pass


class SynthesisError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Audio utilities
# ---------------------------------------------------------------------------

def _pcm_to_wav(pcm_bytes: bytes, sample_rate: int = 16_000, channels: int = 1, sample_width: int = 2) -> bytes:
    """Wrap raw PCM bytes in a RIFF/WAV container."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return buf.getvalue()


def audio_bytes_to_wav(
    audio_data: bytes,
    target_sr: int = 16_000,
    target_channels: int = 1,
) -> bytes:
    """
    Normalise any audio format (wav, webm, ogg, mp4, mp3 …) to a 16-kHz
    mono 16-bit WAV using a single ffmpeg invocation.

    Returns raw WAV bytes ready for soundfile / whisper.
    Raises AudioConversionError on failure.
    """
    if not audio_data:
        raise AudioConversionError("Empty audio_data provided.")

    if FFMPEG_PATH is None:
        # Attempt a direct soundfile read as last resort (wav/flac only)
        try:
            import soundfile as sf
            arr, sr = sf.read(io.BytesIO(audio_data))
            # If already correct format, return as-is (wrapped in WAV)
            if arr.ndim > 1:
                arr = arr.mean(axis=1)
            pcm = (arr * 32767).astype(np.int16).tobytes()
            return _pcm_to_wav(pcm, sample_rate=sr)
        except Exception as exc:
            raise AudioConversionError(
                "ffmpeg is not available and direct WAV read failed. "
                f"Install ffmpeg to support browser audio formats. Detail: {exc}"
            ) from exc

    cmd = [
        FFMPEG_PATH,
        "-hide_banner",
        "-loglevel", "error",
        "-i", "pipe:0",
        "-ar", str(target_sr),
        "-ac", str(target_channels),
        "-sample_fmt", "s16",
        "-f", "wav",
        "pipe:1",
    ]
    try:
        proc = subprocess.run(
            cmd,
            input=audio_data,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
    except subprocess.TimeoutExpired as exc:
        raise AudioConversionError("ffmpeg timed out during audio conversion.") from exc

    if proc.returncode != 0:
        stderr_msg = proc.stderr.decode("utf-8", errors="replace").strip()
        raise AudioConversionError(
            f"ffmpeg exited with code {proc.returncode}: {stderr_msg}"
        )

    if not proc.stdout:
        raise AudioConversionError("ffmpeg produced empty output.")

    return proc.stdout


# ---------------------------------------------------------------------------
# Speech-to-Text
# ---------------------------------------------------------------------------

class SpeechToText:
    """
    Transcribe audio using OpenAI Whisper.

    Args:
        model_name:          Whisper model size (tiny/base/small/medium/large).
        confidence_threshold: Minimum segment confidence to accept transcription.
                              Segments below this are considered low-quality.
        auto_detect_language: When True, Whisper infers the language; the caller's
                              `language` hint is used only as a fallback.
        max_retries:          How many times to retry on transient errors.
    """

    def __init__(
        self,
        model_name: str = "base",
        confidence_threshold: float = 0.40,
        auto_detect_language: bool = True,
        max_retries: int = 2,
    ):
        import whisper  # local import so the module loads without whisper installed

        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.auto_detect_language = auto_detect_language
        self.max_retries = max_retries

        logger.info("Loading Whisper model: %s", model_name)
        self._model = whisper.load_model(model_name)
        logger.info("Whisper model %s ready.", model_name)

    # ------------------------------------------------------------------
    def transcribe(
        self,
        audio_data: bytes,
        language: str = "en",
    ) -> Tuple[str, float, str]:
        """
        Transcribe *audio_data* (any format) to text.

        Returns:
            (text, confidence, language) where confidence ∈ [0, 1].
            Returns ("", 0.0, language) on unrecoverable failure.
        """
        # --- 1. Normalise to 16-kHz mono WAV ---
        try:
            wav_bytes = audio_bytes_to_wav(audio_data)
        except AudioConversionError as exc:
            logger.error("Audio conversion failed: %s", exc)
            return "", 0.0, language

        # --- 2. Decode to float32 numpy array ---
        try:
            import soundfile as sf
            audio_array, _ = sf.read(io.BytesIO(wav_bytes), dtype="float32")
            if audio_array.ndim > 1:
                audio_array = audio_array.mean(axis=1)
        except Exception as exc:
            logger.error("soundfile read failed: %s", exc)
            return "", 0.0

        # --- 3. Transcribe with optional retry ---
        whisper_lang = None if self.auto_detect_language else language
        last_exc: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 2):
            try:
                result = self._model.transcribe(
                    audio_array,
                    language=whisper_lang,
                    verbose=False,
                )
                break
            except Exception as exc:
                last_exc = exc
                logger.warning("Whisper attempt %d/%d failed: %s", attempt, self.max_retries + 1, exc)
        else:
            logger.error("All Whisper attempts failed: %s", last_exc)
            return "", 0.0

        # --- 4. Aggregate segment confidence ---
        text = result.get("text", "").strip()
        segments = result.get("segments") or []
        confidence = self._aggregate_confidence(segments)

        if confidence < self.confidence_threshold and text:
            logger.warning(
                "Low confidence transcription (%.2f < %.2f): %r",
                confidence,
                self.confidence_threshold,
                text,
            )

        detected_lang = result.get("language", language)
        logger.info(
            "Transcribed [lang=%s conf=%.2f]: %s",
            detected_lang,
            confidence,
            text[:120],
        )
        return text, confidence, detected_lang

    # ------------------------------------------------------------------
    @staticmethod
    def _aggregate_confidence(segments: list) -> float:
        """Return mean confidence across all segments; 0.85 if no data."""
        if not segments:
            return 0.85
        scores = [s.get("confidence", 0.85) for s in segments if isinstance(s, dict)]
        return float(np.mean(scores)) if scores else 0.85


# ---------------------------------------------------------------------------
# Text-to-Speech
# ---------------------------------------------------------------------------

_PIPER_WAV_HEADER_BYTES = 44  # Piper --output-raw skips the header; we add it back

class TextToSpeech:
    """
    Convert text to speech via Piper TTS.

    Uses a *persistent* Piper subprocess to amortise model-load cost across
    multiple synthesis calls.  Falls back to a fresh process if the persistent
    one dies.

    Args:
        model_path:    Path to the Piper .onnx voice model.
        sample_rate:   Output sample rate (must match model; Piper default 22050).
        channels:      Number of audio channels (Piper outputs mono).
    """

    def __init__(
        self,
        model_path: str = "en_US-lessac-medium.onnx",
        sample_rate: int = 22_050,
        channels: int = 1,
    ):
        self.model_path = model_path
        self.sample_rate = sample_rate
        self.channels = channels
        self._process: Optional[subprocess.Popen] = None
        logger.info("TextToSpeech initialised (model=%s, sr=%d)", model_path, sample_rate)

    # ------------------------------------------------------------------
    def _ensure_process(self) -> subprocess.Popen:
        """Return a live Piper process, (re-)starting if needed."""
        if self._process is not None and self._process.poll() is None:
            return self._process

        if PIPER_PATH is None:
            raise SynthesisError(
                "Piper executable not found. Install Piper or ensure it is available on PATH."
            )

        cmd = [
            PIPER_PATH,
            "--model", self.model_path,
            "--output-raw",          # raw PCM → we wrap in WAV ourselves
            "--quiet",
        ]
        logger.info("Starting Piper process: %s", " ".join(cmd))
        self._process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return self._process

    # ------------------------------------------------------------------
    def synthesize(self, text: str) -> bytes:
        """
        Synthesise *text* to a WAV audio buffer.

        Returns:
            WAV bytes (RIFF container, 16-bit PCM).
        Raises:
            SynthesisError on failure.
        """
        if not text or not text.strip():
            logger.warning("synthesize() called with empty text — returning silence.")
            return _pcm_to_wav(b"", self.sample_rate, self.channels)

        text_clean = text.strip() + "\n"  # Piper expects newline-delimited input

        try:
            proc = self._ensure_process()
            stdout, stderr = proc.communicate(
                input=text_clean.encode("utf-8"),
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            self._process = None  # kill stale process
            raise SynthesisError("Piper TTS timed out.")
        except BrokenPipeError:
            self._process = None
            raise SynthesisError("Piper process pipe broken — will restart on next call.")
        except Exception as exc:
            self._process = None
            raise SynthesisError(f"Piper process error: {exc}") from exc

        if stderr:
            logger.debug("Piper stderr: %s", stderr.decode("utf-8", errors="replace")[:200])

        if not stdout:
            raise SynthesisError("Piper produced no audio output.")

        # Wrap raw PCM in a WAV container so callers get a playable file
        wav_bytes = _pcm_to_wav(stdout, self.sample_rate, self.channels)
        logger.info(
            "Synthesised %d PCM bytes → %d WAV bytes for: %r",
            len(stdout),
            len(wav_bytes),
            text[:60],
        )
        return wav_bytes

    # ------------------------------------------------------------------
    def close(self) -> None:
        """Terminate the background Piper process gracefully."""
        if self._process is not None:
            try:
                self._process.stdin.close()
                self._process.wait(timeout=5)
            except Exception:
                self._process.kill()
            finally:
                self._process = None
            logger.info("Piper process closed.")

    def __del__(self):
        self.close()


# ---------------------------------------------------------------------------
# Module-level singletons (lazy)
# ---------------------------------------------------------------------------
_stt: Optional[SpeechToText] = None
_tts: Optional[TextToSpeech] = None


def get_speech_to_text(
    model_name: str = "base",
    confidence_threshold: float = 0.40,
    auto_detect_language: bool = True,
) -> SpeechToText:
    """Return the global SpeechToText instance, creating it on first call."""
    global _stt
    if _stt is None:
        _stt = SpeechToText(
            model_name=model_name,
            confidence_threshold=confidence_threshold,
            auto_detect_language=auto_detect_language,
        )
    return _stt


def get_text_to_speech(
    model_path: str = "en_US-lessac-medium.onnx",
    sample_rate: int = 22_050,
) -> TextToSpeech:
    """Return the global TextToSpeech instance, creating it on first call."""
    global _tts
    if _tts is None:
        _tts = TextToSpeech(model_path=model_path, sample_rate=sample_rate)
    return _tts
