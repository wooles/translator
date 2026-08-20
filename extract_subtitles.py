"""
Narzędzie do automatycznego, masowego wyciągania angielskich napisów (.ass / .srt) z plików wideo (.mkv, .mp4).
Obsługuje:
- Przeciąganie pojedynczych lub wielu plików wideo na raz
- Przeciąganie całych folderów
- Automatyczne wykrywanie angielskich ścieżek (eng / english / dialogi)
- Zachowanie oryginalnego formatu napisów (.ass z pełnym typesettingiem lub .srt)
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi", ".mov", ".m4v", ".webm"}

def get_subtitles_info(video_path: str) -> List[Dict[str, Any]]:
    """
    Zwraca szczegółową listę ścieżek napisów w pliku wideo.
    """
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        video_path
    ]
    import json
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        tracks = []
        sub_idx = 0
        for s in data.get("streams", []):
            if s.get("codec_type") == "subtitle":
                tags = s.get("tags", {})
                codec = s.get("codec_name", "ass").lower()
                tracks.append({
                    "sub_index": sub_idx,
                    "stream_index": s.get("index"),
                    "codec": codec,
                    "language": tags.get("language", "und").lower(),
                    "title": tags.get("title", "")
                })
                sub_idx += 1
        return tracks
    except Exception:
        return []

def extract_track_from_video(video_path: Path, output_dir: Optional[Path] = None, track_idx: Optional[int] = None) -> Optional[Path]:
    """
    Wyciąga angielską ścieżkę napisów z pliku wideo i zapisuje ją obok pliku lub we wskazanym folderze.
    """
    tracks = get_subtitles_info(str(video_path))
    if not tracks:
        print(f"[Pominięto]: {video_path.name} (brak wbudowanych ścieżek napisów)")
        return None

    # Wybór właściwej ścieżki (szukamy 'eng', 'en', 'dialogue' lub bierzemy wskazaną / pierwszą)
    chosen_track = None
    if track_idx is not None and 0 <= track_idx < len(tracks):
        chosen_track = tracks[track_idx]
    else:
        # Priorytet 1: Język 'eng' / 'en' z dialogami
        for t in tracks:
            if t["language"] in ("eng", "en", "english") and "sign" not in t["title"].lower():
                chosen_track = t
                break
        
        # Priorytet 2: Jakikolwiek 'eng'
        if not chosen_track:
            for t in tracks:
                if t["language"] in ("eng", "en", "english"):
                    chosen_track = t
                    break

        # Priorytet 3: Pierwsza dostępna ścieżka
        if not chosen_track:
            chosen_track = tracks[0]

    # Ustalenie formatu wyjściowego
    codec = chosen_track["codec"]
    if "ass" in codec or "ssa" in codec:
        ext = ".ass"
    elif "subrip" in codec or "srt" in codec:
        ext = ".srt"
    elif "pgs" in codec or "hdmv" in codec or "vobsub" in codec or "dvd" in codec:
        print(f"[Ostrzeżenie]: Ścieżka w {video_path.name} to napisy graficzne ({codec}). Ekstrakcja może wymagać OCR.")
        ext = ".sup"
    else:
        ext = ".ass"

    target_dir = output_dir if output_dir else video_path.parent
    target_dir.mkdir(parents=True, exist_ok=True)
    out_file = target_dir / f"{video_path.stem}.en{ext}"

    # Komenda ffmpeg do ekstrakcji
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(video_path),
        "-map", f"0:s:{chosen_track['sub_index']}",
        str(out_file)
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        lang_info = f"język={chosen_track['language']}, tytuł='{chosen_track['title']}'"
        print(f"[Sukces]: Wyciągnięto {out_file.name} (Ścieżka {chosen_track['sub_index']}: {lang_info})")
        return out_file
    except Exception as e:
        print(f"[Błąd ekstrakcji]: {video_path.name} -> {e}")
        return None

def pick_files_or_dir_gui() -> List[Path]:
    """
    Otwiera okienko wyboru plików dla Windows (GUI).
    """
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        files = filedialog.askopenfilenames(
            title="Wybierz pliki wideo do wyciągnięcia napisów",
            filetypes=[
                ("Pliki wideo", "*.mkv *.mp4 *.avi *.mov *.webm"),
                ("Wszystkie pliki", "*.*")
            ]
        )
        root.destroy()
        return [Path(f) for f in files] if files else []
    except Exception:
        return []

def main():
    parser = argparse.ArgumentParser(
        description="Ekstraktor angielskich napisów z plików wideo (.mkv, .mp4)"
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        help="Ścieżki do plików wideo lub folderów"
    )
    parser.add_argument(
        "--output-dir", "-o",
        help="Opcjonalny folder docelowy dla wyciągniętych napisów (domyślnie: obok wideo)"
    )
    parser.add_argument(
        "--track", "-t",
        type=int,
        default=None,
        help="Wymuś konkretny indeks ścieżki napisów (domyślnie: automatyczne wykrywanie angielskiej)"
    )

    args = parser.parse_args()

    input_paths = [Path(p) for p in args.inputs] if args.inputs else []
    
    if not input_paths:
        print("[Info] Nie podano plików jako argumentu. Otwieram okno wyboru...")
        input_paths = pick_files_or_dir_gui()
        if not input_paths:
            print("[Info] Nie wybrano żadnych plików. Zamykam program.")
            sys.exit(0)

    # Zbieranie wszystkich plików wideo (także z wnętrza przekazanych folderów)
    video_files: List[Path] = []
    for p in input_paths:
        if p.is_dir():
            for root_dir, _, files in os.walk(p):
                for f in files:
                    fpath = Path(root_dir) / f
                    if fpath.suffix.lower() in VIDEO_EXTENSIONS:
                        video_files.append(fpath)
        elif p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS:
            video_files.append(p)

    if not video_files:
        print("[Błąd]: Nie znaleziono żadnych obsługiwanych plików wideo (.mkv, .mp4, .avi).")
        sys.exit(1)

    print(f"\n=======================================================")
    print(f"  Ekstraktor Angielskich Napisów z Plików Wideo")
    print(f"  Znaleziono plików wideo do przetworzenia: {len(video_files)}")
    print(f"=======================================================\n")

    out_dir = Path(args.output_dir) if args.output_dir else None
    extracted_count = 0

    for i, vfile in enumerate(video_files, 1):
        print(f"[{i}/{len(video_files)}] Przetwarzanie: {vfile.name}")
        res = extract_track_from_video(vfile, output_dir=out_dir, track_idx=args.track)
        if res:
            extracted_count += 1

    print(f"\n=======================================================")
    print(f"  Zakończono! Pomyślnie wyciągnięto napisy dla {extracted_count}/{len(video_files)} plików.")
    print(f"=======================================================\n")

if __name__ == "__main__":
    main()
