# -*- coding: utf-8 -*-
"""
Shot-Cut Subtitle Snapping Module (Shot-Cut Snapper / Netflix AVT Standard).
Detects camera shot transitions using fast native FFmpeg scene filtering
and aligns subtitle timing boundaries (start/end) to shot cuts, eliminating
visual subtitle shot-bleed flicker across scene transitions.
"""

import os
import re
import subprocess
from typing import List, Tuple, Optional, Any
import logging

logger = logging.getLogger("scene_snapper")


class SceneShotSnapper:
    @staticmethod
    def detect_scene_cuts_ffmpeg(
        video_path: str,
        threshold: float = 0.38,
        max_duration_sec: Optional[float] = None
    ) -> List[int]:
        """
        Detects timestamps of shot transitions in video (in milliseconds)
        using native FFmpeg filter 'select=gt(scene,0.38)'.
        Executes at several hundred fps without full video rendering.
        """
        if not video_path or not os.path.exists(video_path):
            return []

        cuts_ms: List[int] = []
        
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i", video_path,
            "-filter:v", f"select='gt(scene,{threshold})',showinfo",
            "-f", "null",
            "-"
        ]
        if max_duration_sec:
            cmd.insert(4, "-t")
            cmd.insert(5, str(max_duration_sec))

        try:
            # Execute process and capture stderr containing showinfo timestamps
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=120
            )
            
            # FFmpeg showinfo pattern: pts_time:12.345
            for line in result.stderr.splitlines():
                if "pts_time:" in line:
                    match = re.search(r"pts_time:([0-9\.]+)", line)
                    if match:
                        sec = float(match.group(1))
                        cuts_ms.append(int(sec * 1000))

        except Exception as e:
            logger.warning(f"Could not extract scene cuts via FFmpeg: {e}")

        return sorted(list(set(cuts_ms)))

    @classmethod
    def snap_subtitles_to_cuts(
        cls,
        events: List[Any],
        scene_cuts_ms: List[int],
        snap_window_ms: int = 250,
        min_duration_ms: int = 700
    ) -> Tuple[List[Any], int]:
        """
        Snaps start and end times of each subtitle event to the nearest shot transition
        if distance is within snap_window_ms (default ~250ms / 6 frames).
        
        Returns: (modified_events, snapped_count)
        """
        if not events or not scene_cuts_ms:
            return events, 0

        snapped_count = 0

        for ev in events:
            if not hasattr(ev, "start") or not hasattr(ev, "end"):
                continue

            orig_start = ev.start
            orig_end = ev.end

            # 1. Snap start timestamp
            for cut in scene_cuts_ms:
                if abs(ev.start - cut) <= snap_window_ms:
                    # Ensure subtitle duration does not drop below minimum
                    if (ev.end - cut) >= min_duration_ms:
                        ev.start = cut
                        snapped_count += 1
                        break

            # 2. Snap end timestamp (Netflix AVT Standard: 2 frames before cut to prevent ghost flashes)
            for cut in scene_cuts_ms:
                if abs(ev.end - cut) <= snap_window_ms:
                    target_end = max(ev.start + min_duration_ms, cut - 80)
                    if target_end > ev.start:
                        # CPS-Aware Safety Guard: ensure snapping does not spike CPS above readable limits (> 17.0 cps)
                        txt = getattr(ev, "plaintext", None) or getattr(ev, "text", "") or ""
                        clean_txt = re.sub(r"\{[^\}]*\}", "", txt).strip()
                        dur_s = max(0.05, (target_end - ev.start) / 1000.0)
                        post_cps = len(clean_txt) / dur_s if clean_txt else 0.0
                        if len(clean_txt) > 20 and post_cps > 17.0:
                            # Do not snap if it hurts human eye readability
                            continue
                        ev.end = target_end
                        snapped_count += 1
                        break

            # Safeguard integrity
            if ev.end <= ev.start:
                ev.start = orig_start
                ev.end = max(ev.start + min_duration_ms, orig_end)

        return events, snapped_count

    @staticmethod
    def is_shot_boundary(
        event_start_ms: int,
        prev_event_end_ms: Optional[int],
        scene_cuts_ms: List[int],
        tolerance_ms: int = 400
    ) -> bool:
        """
        Determines whether a shot/camera transition occurred between the previous subtitle event
        and the current subtitle event, based on FFmpeg scene cut timestamps (0.00 PLN).
        """
        if not scene_cuts_ms or prev_event_end_ms is None:
            return False

        min_boundary = max(0, prev_event_end_ms - tolerance_ms)
        max_boundary = event_start_ms + tolerance_ms
        for cut in scene_cuts_ms:
            if min_boundary <= cut <= max_boundary:
                return True
        return False

    @staticmethod
    def detect_black_frames_ffmpeg(
        video_path: str,
        min_duration_sec: float = 0.15,
        pix_th: float = 0.10,
        max_duration_sec: Optional[float] = None
    ) -> List[Tuple[int, int]]:
        """
        Detects Fade to Black (eyecatch, commercial break, temporal transition) intervals
        in milliseconds using native FFmpeg filter 'blackdetect'. Executes at 0.00 PLN.
        Returns: List of (start_ms, end_ms).
        """
        if not video_path or not os.path.exists(video_path):
            return []

        intervals: List[Tuple[int, int]] = []
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i", video_path,
            "-filter:v", f"blackdetect=d={min_duration_sec}:pix_th={pix_th}",
            "-f", "null",
            "-"
        ]
        if max_duration_sec:
            cmd.insert(4, "-t")
            cmd.insert(5, str(max_duration_sec))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=120
            )
            pattern = re.compile(r"black_start:([0-9\.]+)\s+black_end:([0-9\.]+)")
            for match in pattern.finditer(result.stderr):
                b_start = int(float(match.group(1)) * 1000)
                b_end = int(float(match.group(2)) * 1000)
                intervals.append((b_start, b_end))
        except Exception as e:
            logger.warning(f"Could not extract black frames via FFmpeg: {e}")

        return sorted(intervals, key=lambda x: x[0])

    @staticmethod
    def is_black_fade_boundary(
        event_start_ms: int,
        prev_event_end_ms: Optional[int],
        black_intervals_ms: List[Tuple[int, int]],
        tolerance_ms: int = 400
    ) -> bool:
        """
        Determines whether a Fade to Black occurred between the previous subtitle event
        and the current subtitle event (0.00 PLN).
        """
        if not black_intervals_ms or prev_event_end_ms is None:
            return False

        min_boundary = max(0, prev_event_end_ms - tolerance_ms)
        max_boundary = event_start_ms + tolerance_ms

        for b_start, b_end in black_intervals_ms:
            # Check if black interval falls between or overlaps the boundary
            if (min_boundary <= b_start <= max_boundary) or (min_boundary <= b_end <= max_boundary) or (b_start <= min_boundary and b_end >= max_boundary):
                return True
        return False

    @staticmethod
    def detect_silence_ffmpeg(
        audio_or_video_path: str,
        noise_db: float = -35.0,
        min_duration_sec: float = 0.3,
        max_duration_sec: Optional[float] = None
    ) -> List[Tuple[int, int]]:
        """
        Detects silent intervals in audio using native FFmpeg filter 'silencedetect' (0.00 PLN).
        Returns: List of (start_ms, end_ms).
        """
        if not audio_or_video_path or not os.path.exists(audio_or_video_path):
            return []

        silence_intervals: List[Tuple[int, int]] = []
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i", audio_or_video_path,
            "-filter:a", f"silencedetect=noise={noise_db}dB:d={min_duration_sec}",
            "-f", "null",
            "-"
        ]
        if max_duration_sec:
            cmd.insert(4, "-t")
            cmd.insert(5, str(max_duration_sec))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=120
            )
            
            current_start: Optional[int] = None
            start_pat = re.compile(r"silence_start:\s*([0-9\.]+)")
            end_pat = re.compile(r"silence_end:\s*([0-9\.]+)")

            for line in result.stderr.splitlines():
                sm = start_pat.search(line)
                if sm:
                    current_start = int(float(sm.group(1)) * 1000)
                em = end_pat.search(line)
                if em and current_start is not None:
                    end_ms = int(float(em.group(1)) * 1000)
                    silence_intervals.append((current_start, end_ms))
                    current_start = None

        except Exception as e:
            logger.warning(f"Could not extract silence via FFmpeg: {e}")

        return sorted(silence_intervals, key=lambda x: x[0])

    @staticmethod
    def detect_keyframes_ffmpeg(
        video_path: str,
        max_duration_sec: Optional[float] = None
    ) -> List[int]:
        """
        Detects keyframe (I-frame) timestamps in milliseconds using native FFmpeg filter (0.00 PLN).
        """
        if not video_path or not os.path.exists(video_path):
            return []

        keyframes_ms: List[int] = []
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i", video_path,
            "-filter:v", "select='eq(pict_type\\,I)',showinfo",
            "-f", "null",
            "-"
        ]
        if max_duration_sec:
            cmd.insert(4, "-t")
            cmd.insert(5, str(max_duration_sec))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=120
            )
            for line in result.stderr.splitlines():
                if "pts_time:" in line:
                    match = re.search(r"pts_time:([0-9\.]+)", line)
                    if match:
                        sec = float(match.group(1))
                        keyframes_ms.append(int(sec * 1000))
        except Exception as e:
            logger.warning(f"Could not extract keyframes via FFmpeg: {e}")

        return sorted(list(set(keyframes_ms)))

    @classmethod
    def snap_subtitles_to_cuts_and_keyframes(
        cls,
        events: List[Any],
        scene_cuts_ms: List[int],
        keyframes_ms: Optional[List[int]] = None,
        snap_window_ms: int = 250,
        keyframe_window_ms: int = 120,
        min_duration_ms: int = 700
    ) -> Tuple[List[Any], int]:
        """
        Snaps start/end to shot cuts first. If no shot cut is within snap_window_ms,
        snaps start timestamp to nearest preceding I-frame within keyframe_window_ms.
        """
        events, snapped_cuts = cls.snap_subtitles_to_cuts(
            events=events,
            scene_cuts_ms=scene_cuts_ms,
            snap_window_ms=snap_window_ms,
            min_duration_ms=min_duration_ms
        )
        if not keyframes_ms:
            return events, snapped_cuts

        snapped_keyframes = 0
        for ev in events:
            if not hasattr(ev, "start") or not hasattr(ev, "end"):
                continue

            # If start was not already snapped to a cut
            if not any(abs(ev.start - cut) <= 5 for cut in scene_cuts_ms):
                for kf in keyframes_ms:
                    if 0 <= (ev.start - kf) <= keyframe_window_ms:
                        if (ev.end - kf) >= min_duration_ms:
                            ev.start = kf
                            snapped_keyframes += 1
                            break

        return events, snapped_cuts + snapped_keyframes
