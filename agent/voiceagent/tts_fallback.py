"""
High-fidelity local audio synthesis fallback for Windows.
Converts text to smooth, natural speech using Microsoft Zira Desktop (SAPI5)
resampled to native 48,000 Hz WebRTC studio rate with drift-free wall-clock pacing.
"""

from __future__ import annotations

import asyncio
import audioop
import logging
import os
import tempfile
import time
import wave
from typing import List, Tuple

import pyttsx3
from livekit import rtc

log = logging.getLogger("voiceagent.fallback")

# Standard WebRTC / Opus parameters
TARGET_SAMPLE_RATE = 48000
TARGET_CHANNELS = 1
FRAME_DURATION_S = 0.02  # 20ms per frame
SAMPLES_PER_FRAME = int(TARGET_SAMPLE_RATE * FRAME_DURATION_S)  # 960 samples
BYTES_PER_SAMPLE = 2  # 16-bit PCM
BYTES_PER_FRAME = SAMPLES_PER_FRAME * TARGET_CHANNELS * BYTES_PER_SAMPLE  # 1920 bytes


def synthesize_speech_frames(text: str) -> Tuple[List[rtc.AudioFrame], int, int]:
    """Convert text to smooth 48kHz 20ms rtc.AudioFrame instances using Microsoft Zira."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        tmp_path = tf.name

    try:
        engine = pyttsx3.init()
        # Select Microsoft Zira (smooth, natural female voice) over harsh David
        for v in engine.getProperty("voices"):
            if "zira" in v.name.lower():
                engine.setProperty("voice", v.id)
                break

        # Natural, calm speaking rate and full volume
        engine.setProperty("rate", 155)
        engine.setProperty("volume", 1.0)
        engine.save_to_file(text, tmp_path)
        engine.runAndWait()

        # Read original WAV audio
        with wave.open(tmp_path, "rb") as w:
            orig_rate = w.getframerate()
            orig_channels = w.getnchannels()
            raw_pcm = w.readframes(w.getnframes())

        # If stereo, convert to mono
        if orig_channels == 2:
            raw_pcm = audioop.tomono(raw_pcm, 2, 0.5, 0.5)

        # Resample from original (usually 22050Hz) to native WebRTC 48000Hz
        if orig_rate != TARGET_SAMPLE_RATE:
            resampled_pcm, _ = audioop.ratecv(
                raw_pcm,
                2,  # 16-bit
                1,  # mono
                orig_rate,
                TARGET_SAMPLE_RATE,
                None,
            )
        else:
            resampled_pcm = raw_pcm

        # Chunk into exact 20ms (960 samples = 1920 bytes) AudioFrames
        frames: List[rtc.AudioFrame] = []
        offset = 0
        total_len = len(resampled_pcm)

        while offset < total_len:
            chunk = resampled_pcm[offset : offset + BYTES_PER_FRAME]
            offset += BYTES_PER_FRAME

            # Pad final frame with silence if needed so Opus doesn't glitch
            if len(chunk) < BYTES_PER_FRAME:
                chunk = chunk + b"\x00" * (BYTES_PER_FRAME - len(chunk))

            frames.append(
                rtc.AudioFrame(
                    data=chunk,
                    sample_rate=TARGET_SAMPLE_RATE,
                    num_channels=TARGET_CHANNELS,
                    samples_per_channel=SAMPLES_PER_FRAME,
                )
            )

        log.info(
            "Synthesized %d smooth 48kHz audio frames for text: '%s'",
            len(frames),
            text[:40],
        )
        return frames, TARGET_SAMPLE_RATE, TARGET_CHANNELS
    except Exception as e:
        log.error("Failed to synthesize smooth speech via pyttsx3: %s", e)
        return [], TARGET_SAMPLE_RATE, TARGET_CHANNELS
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


async def play_audio_frames(
    frames: List[rtc.AudioFrame],
    source: rtc.AudioSource,
    is_cancelled_fnc=None,
) -> None:
    """Stream audio frames into a LiveKit AudioSource using drift-free wall-clock pacing.

    Eliminates Windows timer jitter (where sleep(0.02) overshoots to 31ms),
    maintaining a constant 50fps stream into WebRTC with zero buffer underruns.
    """
    if not frames:
        return

    # Pre-fill a small 4-frame jitter buffer (80ms) for ultra-smooth playback
    lead_count = min(4, len(frames))
    for i in range(lead_count):
        if is_cancelled_fnc and is_cancelled_fnc():
            return
        await source.capture_frame(frames[i])

    # Wall-clock pacing for the remaining frames
    start_time = time.perf_counter()
    for idx, frame in enumerate(frames[lead_count:], start=lead_count):
        if is_cancelled_fnc and is_cancelled_fnc():
            log.info("Audio playback interrupted by user or supervisor")
            break

        await source.capture_frame(frame)

        # Expected target timestamp
        target_time = start_time + (idx - lead_count + 1) * FRAME_DURATION_S
        time_to_wait = target_time - time.perf_counter()

        if time_to_wait > 0.003:
            await asyncio.sleep(time_to_wait)
