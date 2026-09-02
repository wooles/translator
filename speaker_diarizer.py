# -*- coding: utf-8 -*-
"""
Local Voice Pitch Classification & Speaker Diarization Module.
100% local, pitch-tracking module based on autocorrelation (F0 Fundamental Frequency)
to identify speaker gender register (low male vs high female voice) in off-screen dialogue scenes.
"""

import os
import wave
from typing import Dict, List, Tuple, Any, Optional
import numpy as np

class SpeakerVoiceClassifier:
    def __init__(self):
        pass

    @staticmethod
    def estimate_pitch_f0(samples: np.ndarray, sample_rate: int = 16000) -> Optional[float]:
        """
        Estimates fundamental voice frequency (F0) using autocorrelation method.
        Human speech range: 75 Hz (deep male) to 450 Hz (high female/child).
        """
        if samples is None or len(samples) < sample_rate * 0.3:
            return None

        # Normalize and remove DC offset
        samples = samples - np.mean(samples)
        if np.max(np.abs(samples)) < 50.0:
            return None

        # Search range for pitch period at 16kHz
        # Min F0 = 75 Hz -> Max Lag = 16000 / 75 = 213 samples
        # Max F0 = 400 Hz -> Min Lag = 16000 / 400 = 40 samples
        min_lag = int(sample_rate / 400)  # ~40
        max_lag = int(sample_rate / 75)   # ~213

        # Window analysis of 60ms with 50% overlap
        window_size = int(sample_rate * 0.06)  # 960 samples
        hop_size = int(sample_rate * 0.03)     # 480 samples

        f0_estimates = []

        for start in range(0, len(samples) - window_size, hop_size):
            frame = samples[start:start + window_size]
            energy = np.sum(frame ** 2)
            if energy < 1e5:  # Skip silence
                continue

            # Window autocorrelation
            corr = np.correlate(frame, frame, mode="full")
            corr = corr[len(frame) - 1:]

            if len(corr) <= max_lag:
                continue

            # Search peak in speech lag range
            search_region = corr[min_lag:max_lag]
            if len(search_region) == 0:
                continue

            peak_idx = np.argmax(search_region) + min_lag
            peak_val = corr[peak_idx]

            # Voiced periodicity threshold
            if corr[0] > 0 and (peak_val / corr[0]) > 0.35:
                f0 = sample_rate / peak_idx
                if 75.0 <= f0 <= 450.0:
                    f0_estimates.append(f0)
                    if len(f0_estimates) >= 12:
                        break

        if not f0_estimates or len(f0_estimates) < 3:
            return None

        # Median of detected pitch points
        return float(np.median(f0_estimates))

    @classmethod
    def classify_scene_speakers(
        cls,
        wav_path: str,
        batch_start_ms: int,
        events: List[Tuple[int, Any]]
    ) -> Dict[int, str]:
        """
        Classifies voice pitch and register for all dialogue events in a batch.
        Returns a dictionary: {batch_id: 'Głos: żeński/wysoki' | 'Głos: męski/niski'}.
        """
        if not wav_path or not os.path.exists(wav_path):
            return {}

        results = {}

        try:
            with wave.open(wav_path, "rb") as wf:
                framerate = wf.getframerate()
                nchannels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                total_frames = wf.getnframes()
                
                raw_bytes = wf.readframes(total_frames)
                if not raw_bytes:
                    return {}

                if sampwidth == 2:
                    full_audio = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32)
                elif sampwidth == 1:
                    full_audio = (np.frombuffer(raw_bytes, dtype=np.uint8).astype(np.float32) - 128) * 256.0
                else:
                    return {}

                if nchannels > 1:
                    full_audio = full_audio.reshape(-1, nchannels).mean(axis=1)

            for b_id, ev in events:
                rel_start = max(0, ev.start - batch_start_ms)
                rel_end = max(rel_start + 200, ev.end - batch_start_ms)

                start_idx = int((rel_start / 1000.0) * framerate)
                end_idx = int((rel_end / 1000.0) * framerate)

                if end_idx <= start_idx or start_idx >= len(full_audio):
                    continue

                chunk = full_audio[start_idx:min(end_idx, len(full_audio))]
                f0 = cls.estimate_pitch_f0(chunk, sample_rate=framerate)

                if f0 is not None:
                    if f0 <= 155.0:
                        results[b_id] = f"męski / niski (~{int(f0)}Hz)"
                    elif f0 <= 190.0:
                        results[b_id] = f"męski tenor / alt żeński (~{int(f0)}Hz)"
                    else:
                        results[b_id] = f"wysoki / dziecięcy / żeński (~{int(f0)}Hz)"

        except Exception:
            pass

        return results
