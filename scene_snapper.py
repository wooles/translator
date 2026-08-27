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
                        ev.end = target_end
                        snapped_count += 1
                        break

            # Safeguard integrity
            if ev.end <= ev.start:
                ev.start = orig_start
                ev.end = max(ev.start + min_duration_ms, orig_end)

        return events, snapped_count
