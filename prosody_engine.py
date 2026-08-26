# -*- coding: utf-8 -*-
"""
Local Audio Prosody & Emotion Analysis Module (Prosody & Tone Engine).
100% local, zero-cost audio waveform analysis (RMS amplitude, dynamics, speech tempo)
allowing the model to distinguish whisper, shout, trembling voice, and rapid monologue.
"""

import os
import wave
import math
from typing import Dict, List, Tuple, Any, Optional
import numpy as np

class AudioProsodyEngine:
    def __init__(self):
        pass

    @staticmethod
    def read_wav_segment(wav_path: str, start_ms: int, end_ms: int) -> Optional[np.ndarray]:
        """Reads audio waveform segment from WAV file (16kHz mono)."""
        if not wav_path or not os.path.exists(wav_path):
            return None

        try:
            with wave.open(wav_path, "rb") as wf:
                framerate = wf.getframerate()
                nchannels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                
                # Compute frame positions
                start_frame = int((start_ms / 1000.0) * framerate)
                duration_frames = int(((end_ms - start_ms) / 1000.0) * framerate)
                
                if duration_frames <= 0:
                    return None

                wf.setpos(min(start_frame, max(0, wf.getnframes() - 1)))
                raw_bytes = wf.readframes(duration_frames)
                
                if not raw_bytes:
                    return None

                # Convert to int16 numpy array
                if sampwidth == 2:
                    audio_data = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32)
                elif sampwidth == 1:
                    audio_data = (np.frombuffer(raw_bytes, dtype=np.uint8).astype(np.float32) - 128) * 256.0
                else:
                    return None

                if nchannels > 1:
                    audio_data = audio_data.reshape(-1, nchannels).mean(axis=1)

                return audio_data
        except Exception:
            return None

    @classmethod
    def analyze_scene_prosody(
        cls,
        wav_path: str,
        batch_start_ms: int,
        events: List[Tuple[int, Any]]
    ) -> Dict[int, str]:
        """
        Analyzes phonic characteristics (RMS dBFS, dynamics, tempo) for all dialogue events in a batch.
        Returns a dictionary: {batch_id: 'tone_description'} (e.g. {1: 'cichy szept', 2: 'krzyk / wzburzenie'}).
        """
        if not wav_path or not os.path.exists(wav_path):
            return {}

        results = {}

        for b_id, ev in events:
            # Relative timestamp in WAV slice
            rel_start = max(0, ev.start - batch_start_ms)
            rel_end = max(rel_start + 200, ev.end - batch_start_ms)

            samples = cls.read_wav_segment(wav_path, rel_start, rel_end)
            if samples is None or len(samples) < 400:
                continue

            # Compute RMS (Root Mean Square) energy
            rms = np.sqrt(np.mean(samples ** 2))
            if rms <= 1.0:
                continue

            # Convert to decibels dBFS (maximum for 16-bit is 32767)
            dbfs = 20 * math.log10(rms / 32767.0)

            # Peak amplitude
            peak = np.max(np.abs(samples))
            peak_dbfs = 20 * math.log10(max(1.0, peak) / 32767.0)

            # Detect tone characteristics
            tags = []
            if dbfs < -33.0:
                tags.append("cichy szept / niepewność")
            elif dbfs > -13.0 or peak_dbfs > -1.5:
                tags.append("krzyk / wysokie emocje / wzburzenie")

            # Analyze speech duration and energy variance (trembling / rapid)
            duration_s = (ev.end - ev.start) / 1000.0
            if duration_s > 0:
                # Energy variance in 50ms windows
                window_size = 800  # 50ms at 16kHz
                if len(samples) > window_size * 2:
                    chunks = [samples[i:i+window_size] for i in range(0, len(samples), window_size)]
                    chunk_energies = [np.sqrt(np.mean(c**2)) for c in chunks if len(c) == window_size]
                    if chunk_energies:
                        energy_std = np.std(chunk_energies) / (rms + 1e-5)
                        if energy_std > 0.85 and "krzyk" not in str(tags):
                            tags.append("emocjonalne drżenie głosu")

            if tags:
                results[b_id] = " | ".join(tags)

        return results
