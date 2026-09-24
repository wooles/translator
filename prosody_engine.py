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
    def detect_intra_line_pause(cls, samples: np.ndarray, min_pause_ms: int = 600) -> Optional[int]:
        """
        Detects significant suspense/breath pauses (silence gap >= min_pause_ms)
        within an ongoing spoken dialogue line. Returns pause duration in ms or None.
        """
        if samples is None or len(samples) < 16000 * 1.5:  # Requires at least 1.5s duration
            return None

        window_size = 800  # 50ms at 16kHz
        if len(samples) < window_size * 4:
            return None

        chunks = [samples[i:i+window_size] for i in range(0, len(samples), window_size)]
        chunk_energies = [np.sqrt(np.mean(c**2)) for c in chunks if len(c) == window_size]
        if not chunk_energies:
            return None

        max_energy = max(chunk_energies)
        if max_energy < 5.0:
            return None

        # Silence threshold: 12% of peak energy or background floor
        silence_threshold = max(2.0, max_energy * 0.12)
        is_silence = [e < silence_threshold for e in chunk_energies]

        # Ignore initial 200ms and final 200ms
        trim_start = 4
        trim_end = len(is_silence) - 4
        if trim_end <= trim_start:
            return None

        middle_silence = is_silence[trim_start:trim_end]
        
        # Count longest consecutive silence block in the middle
        max_consecutive = 0
        current_consecutive = 0
        for s in middle_silence:
            if s:
                current_consecutive += 1
                if current_consecutive > max_consecutive:
                    max_consecutive = current_consecutive
            else:
                current_consecutive = 0

        pause_ms = max_consecutive * 50
        if pause_ms >= min_pause_ms:
            return pause_ms

        return None

    @classmethod
    def analyze_scene_prosody(
        cls,
        wav_path: str,
        batch_start_ms: int,
        events: List[Tuple[int, Any]]
    ) -> Dict[int, str]:
        """
        Analyzes phonic characteristics (RMS dBFS, dynamics, tempo, emotion, breath pauses)
        for all dialogue events in a batch.
        Returns a dictionary: {batch_id: 'tone_description'}
        """
        if not wav_path or not os.path.exists(wav_path):
            return {}

        results = {}
        prev_dbfs: Optional[float] = None

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

            # Detect tone characteristics and emotional expression
            tags = []
            if dbfs < -34.0:
                tags.append("cichy szept / monolog wewnętrzny")
            elif dbfs > -12.0 or peak_dbfs > -1.0:
                tags.append("krzyk bojowy / silne wzburzenie emocjonalne")

            # Filar CLXXVIII: Detect sudden affective collapse / shock shift (drop >= 12 dBFS or shout -> whisper)
            if prev_dbfs is not None and cls.detect_affective_shock_shift(prev_dbfs, dbfs):
                tags.append("pęknięcie afektywne / nagły szok lub zamilknięcie (Ac=SHOCK_DROP)")

            # Analyze speech duration and energy variance (trembling / rapid / calm sarcasm)
            duration_s = (ev.end - ev.start) / 1000.0
            if duration_s > 0:
                window_size = 800  # 50ms at 16kHz
                if len(samples) > window_size * 2:
                    chunks = [samples[i:i+window_size] for i in range(0, len(samples), window_size)]
                    chunk_energies = [np.sqrt(np.mean(c**2)) for c in chunks if len(c) == window_size]
                    if chunk_energies:
                        energy_std = np.std(chunk_energies) / (rms + 1e-5)
                        if energy_std > 0.90 and "krzyk" not in str(tags):
                            tags.append("emocjonalne drżenie głosu / płacz")
                        elif energy_std < 0.28 and -28.0 <= dbfs <= -18.0:
                            tags.append("chłodny sarkazm / opanowany dystans")

            # Detect intra-line dramatic breath pause (suspense)
            pause_ms = cls.detect_intra_line_pause(samples, min_pause_ms=650)
            if pause_ms:
                tags.append(f"dramatyczna pauza oddechowa seiyuu (~{pause_ms}ms)")

            # Calculate Mouth-Pacing syllable budget for concise lip synchrony
            syllable_limit = cls.calculate_syllable_budget(duration_s, dbfs)
            if duration_s <= 0.7:
                tags.append(f"Mouth-Pacing: max {syllable_limit} sylaby (mowa seiyuu trwa tylko {duration_s:.1f}s - KONDENSUJ!)")
            elif duration_s <= 1.2:
                tags.append(f"Mouth-Pacing: max {syllable_limit} sylab ({duration_s:.1f}s)")

            if tags:
                results[b_id] = " | ".join(tags)

            prev_dbfs = dbfs

        return results

    @classmethod
    def detect_affective_shock_shift(cls, prev_dbfs: float, curr_dbfs: float) -> bool:
        """
        Detects sudden affective collapse / shock shift (Filar CLXXVIII).
        Triggers when acoustic energy plunges by >= 12 dBFS between consecutive turns
        or transitions from a shout/high-energy state (>-18 dBFS) directly into near-whisper (<-30 dBFS).
        """
        if prev_dbfs - curr_dbfs >= 12.0:
            return True
        if prev_dbfs > -18.0 and curr_dbfs < -30.0:
            return True
        return False

    @classmethod
    def calculate_syllable_budget(cls, duration_s: float, dbfs: float = -20.0) -> int:
        """
        Calculates recommended maximum Polish syllable budget based on seiyuu speech duration (Mouth-Pacing).
        Enforces concise dubbing/subtitling synchrony, preventing cognitive overload when character lips close early.
        """
        if duration_s <= 0.4:
            return 2
        elif duration_s <= 0.7:
            return 3
        elif duration_s <= 1.0:
            return 5
        elif duration_s <= 1.5:
            return 8
        elif duration_s <= 2.0:
            return 11
        else:
            return int(duration_s * 5.5)

    @classmethod
    def detect_emotional_breakdown(
        cls,
        prosody_tag: str = "",
        whisper_text: str = "",
        energy_std: Optional[float] = None
    ) -> Optional[str]:
        """
        Detects affective breakdowns (crying, sobbing, terror, panic) from phonic cues and Whisper markers.
        Establishes Dynamic Affective Primacy over static character personas from Series Bible.
        """
        prosody_lower = (prosody_tag or "").lower()
        whisper_lower = (whisper_text or "").lower()

        has_fonic_tremble = "płacz" in prosody_lower or "drżenie głosu" in prosody_lower or (energy_std is not None and energy_std > 0.90)
        has_whisper_panic = any(k in whisper_lower for k in [
            "sonna", "そんな", "tasukete", "助けて", "iya", "嫌", "h-hi", "ひっ", "kowai", "怖い", "u...", "うっ", "nande", "何で"
        ]) or any(whisper_lower.startswith(w) for w in ["h-", "k-", "s-", "n-", "d-", "m-"])

        if has_fonic_tremble or (has_whisper_panic and ("krzyk" in prosody_lower or "szept" in prosody_lower or has_fonic_tremble or len(whisper_lower.split()) <= 4)):
            return (
                "[🚨 PRYMAT AFEKTU / ZAŁAMANIE EMOCJONALNE: Fizjologia głosu seiyū i markery audio wskazują na panikę/płacz! "
                "UCHYLA SIĘ statyczny profil chłodu z Series Bible! Wymóg: histeryczna składnia, urwane słowa, pełna ekspresja rozpaczy]"
            )
        return None

