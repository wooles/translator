# -*- coding: utf-8 -*-
r"""
Automatyczny Synchronizator i Budowniczy Bazy Napisów (Translation Memory).

Obsługuje:
- Przeciąganie pojedynczych lub wielu plików wideo (.mkv, .mp4)
- Przeciąganie całych folderów (np. 'E:\Kingdom 6th Season')
- Automatyczną ekstrakcję angielskich napisów (.en.ass / .en.srt)
- Automatyczne wykrycie odpowiadających polskich napisów (.ass / .srt) w tym samym folderze
- Kopiowanie pełnych par (EN + PL) do folderu 'baza napisów'
- Automatyczne usuwanie tymczasowych angielskich napisów z folderu źródłowego (zachowuje idealny porządek)
- Błyskawiczne przeindeksowanie lokalnej bazy SQLite (translation_memory.db)
"""

import os
import sys
import shutil
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from extract_subtitles import get_subtitles_info, VIDEO_EXTENSIONS
from memory import TranslationMemory

BAZA_NAPISOW_DIR = Path(__file__).parent / "baza napisów"


def find_matching_polish_sub(video_path: Path) -> Optional[Path]:
    """
    Wyszukuje odpowiadający plik z polskimi napisami w folderze wideo.
    Sprawdza dokładną nazwę bazową oraz popularne warianty (.ass, .srt, .pl.ass, .pl.srt).
    """
    parent_dir = video_path.parent
    stem = video_path.stem

    # 1. Dokładne dopasowanie nazwy
    candidates = [
        parent_dir / f"{stem}.ass",
        parent_dir / f"{stem}.srt",
        parent_dir / f"{stem}.pl.ass",
        parent_dir / f"{stem}.pl.srt",
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return c

    # 2. Szukanie pliku .ass/.srt pasującego po numerze odcinka w tym samym folderze
    import re
    ep_match = re.search(r"[-_\s]0*(\d{1,4})(?:v\d+)?(?:[-_\s\.\[]|$)", stem)
    if ep_match:
        target_ep = ep_match.group(1).lstrip("0") or "0"
        for f in parent_dir.glob("*"):
            if f.is_file() and f.suffix.lower() in (".ass", ".srt"):
                if ".en." in f.name.lower() or ".ang." in f.name.lower():
                    continue
                f_ep_match = re.search(r"[-_\s]0*(\d{1,4})(?:v\d+)?(?:[-_\s\.\[]|$)", f.stem)
                if f_ep_match:
                    f_ep = f_ep_match.group(1).lstrip("0") or "0"
                    if f_ep == target_ep:
                        return f

    return None


def extract_english_track(video_path: Path, dest_dir: Path) -> Optional[Path]:
    """
    Wyciąga angielską ścieżkę napisów bezpośrednio do folderu docelowego.
    """
    tracks = get_subtitles_info(str(video_path))
    if not tracks:
        return None

    chosen_track = None
    for t in tracks:
        if t["language"] in ("eng", "en", "english") and "sign" not in t["title"].lower():
            chosen_track = t
            break
    if not chosen_track:
        for t in tracks:
            if t["language"] in ("eng", "en", "english"):
                chosen_track = t
                break
    if not chosen_track:
        chosen_track = tracks[0]

    codec = chosen_track["codec"]
    ext = ".ass" if ("ass" in codec or "ssa" in codec) else (".srt" if ("subrip" in codec or "srt" in codec) else ".ass")

    out_file = dest_dir / f"{video_path.stem}.en{ext}"
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(video_path),
        "-map", f"0:s:{chosen_track['sub_index']}",
        str(out_file)
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return out_file
    except Exception as e:
        print(f" [Błąd FFmpeg]: {video_path.name} -> {e}")
        return None


def sync_videos_to_baza(video_files: List[Path], baza_dir: Path = BAZA_NAPISOW_DIR) -> int:
    """
    Przetwarza listę plików wideo: wyciąga EN, paruje z PL, kopiuje parę do bazy i czyści śmieci.
    """
    baza_dir.mkdir(parents=True, exist_ok=True)
    synced_pairs = 0

    print("\n" + "═" * 70)
    print("  🚀 ROZPOCZYNANIE SYNCHRONIZACJI BAZY NAPISÓW (Translation Memory)")
    print(f"  Folder docelowy bazy: {baza_dir}")
    print(f"  Liczba plików wideo do przetworzenia: {len(video_files)}")
    print("═" * 70 + "\n")

    for idx, vpath in enumerate(video_files, 1):
        print(f"[{idx}/{len(video_files)}] Skanowanie: {vpath.name}")

        # 1. Sprawdzamy czy w folderze wideo są polskie napisy
        pl_sub_path = find_matching_polish_sub(vpath)
        if not pl_sub_path:
            print(f"  ⚠️  [Pominięto]: Brak polskich napisów (.ass/.srt) w folderze: {vpath.parent.name}")
            print(f"      Aby dodać odcinek do bazy, umieść obok wideo plik z polskimi napisami.")
            continue

        # 2. Wyciągamy angielskie napisy bezpośrednio do folderu bazy
        en_target_path = extract_english_track(vpath, dest_dir=baza_dir)
        if not en_target_path or not en_target_path.exists() or en_target_path.stat().st_size == 0:
            print(f"  ❌ [Błąd]: Nie udało się wyciągnąć angielskich napisów z {vpath.name}")
            continue

        # 3. Kopiujemy polskie napisy do folderu bazy (z zachowaniem spójnej nazwy)
        pl_target_ext = pl_sub_path.suffix
        pl_target_path = baza_dir / f"{vpath.stem}{pl_target_ext}"
        try:
            shutil.copy2(pl_sub_path, pl_target_path)
        except Exception as e:
            print(f"  ❌ [Błąd kopiowania PL]: {e}")
            continue

        # 4. Sprawdzamy i ewentualnie usuwamy tymczasowy angielski plik z folderu źródłowego (gdyby tam powstał)
        local_en_ass = vpath.parent / f"{vpath.stem}.en.ass"
        local_en_srt = vpath.parent / f"{vpath.stem}.en.srt"
        for temp_f in [local_en_ass, local_en_srt]:
            if temp_f.exists() and temp_f.is_file():
                try:
                    temp_f.unlink()
                except Exception:
                    pass

        synced_pairs += 1
        print(f"  ✅ [SPAROWANO I SKOPIOWANO DO BAZY]:")
        print(f"      ├─ EN: {en_target_path.name}")
        print(f"      └─ PL: {pl_target_path.name}")
        print(f"      (Folder źródłowy '{vpath.parent.name}' pozostawiony w 100% czysty)")

    # 5. Automatyczne przeindeksowanie bazy SQLite
    if synced_pairs > 0:
        print("\n" + "─" * 70)
        print("  🔄 AKTUALIZACJA I RE-INDEKSACJA PAMIĘCI TŁUMACZENIOWEJ (SQLite)...")
        tm = TranslationMemory()
        total_db_pairs = tm.index_database_directory(baza_dir)
        print(f"  ✨ [SUKCES]: Baza Pamięci Tłumaczeniowej zawiera teraz {total_db_pairs} aktywnych par dialogowych!")
        print("─" * 70 + "\n")
    else:
        print("\n[Info]: Nie dodano żadnych nowych par do bazy.\n")

    return synced_pairs


def main():
    parser = argparse.ArgumentParser(
        description="Automatyczny synchronizator par napisów EN+PL do bazy Translation Memory"
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        help="Ścieżki do plików wideo (.mkv) lub całych folderów"
    )
    args = parser.parse_args()

    input_paths = [Path(p) for p in args.inputs] if args.inputs else []
    if not input_paths:
        from extract_subtitles import pick_files_or_dir_gui
        print("[Info] Nie podano plików jako argumentu. Otwieram okno wyboru...")
        input_paths = pick_files_or_dir_gui()
        if not input_paths:
            print("[Info] Nie wybrano żadnych plików. Zamykam program.")
            sys.exit(0)

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
        print("[Błąd]: Nie znaleziono żadnych plików wideo (.mkv, .mp4).")
        sys.exit(1)

    sync_videos_to_baza(video_files)


if __name__ == "__main__":
    main()
