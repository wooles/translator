"""
Główny punkt wejścia CLI / GUI dla Multimodalnego Tłumacza Napisów (Gemini 3.7 Flash).
"""

import os
import sys

# Wymuszenie pełnej obsługi znaków UTF-8 (w tym japońskich Kanji/Hiragany/Katakany) w konsoli Windows
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
    except Exception:
        pass
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import logging
import argparse
import subprocess
from typing import Optional, Tuple, List, Dict, Any
from pathlib import Path
# Wczytanie zmiennych środowiskowych z .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Wbudowany awaryjny parser pliku .env (gdyby python-dotenv nie był zainstalowany)
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip().strip("'\""))
        except Exception:
            pass

from extract import list_subtitle_tracks, extract_embedded_subtitles
from translator import MultimodalTranslator

VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi", ".webm", ".mov", ".m4v"}
SUBTITLE_EXTENSIONS = {".srt", ".ass", ".ssa", ".vtt", ".sub"}

def pick_file_gui() -> str:
    """
    Otwiera natywne okno wyboru pliku w systemie Windows/Linux/macOS.
    """
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        selected = filedialog.askopenfilename(
            title="Wybierz plik wideo lub plik z napisami do przetłumaczenia",
            filetypes=[
                ("Pliki wideo i napisów", "*.mkv *.mp4 *.avi *.webm *.mov *.srt *.ass *.ssa *.vtt"),
                ("Pliki wideo (*.mkv, *.mp4)", "*.mkv *.mp4 *.avi *.webm *.mov"),
                ("Pliki napisów (*.srt, *.ass)", "*.srt *.ass *.ssa *.vtt"),
                ("Wszystkie pliki", "*.*")
            ]
        )
        root.destroy()
        return selected
    except Exception:
        return ""

def launch_player(video_path: str, subs_path: str):
    """
    Próbuje uruchomić film z nowymi napisami w odtwarzaczu (mpv, vlc lub domyślnym systemowym).
    """
    print(f"\n[Odtwarzacz] Uruchamianie wideo z przetłumaczonymi napisami...")
    
    # 1. Próba MPV
    try:
        subprocess.Popen(["mpv", video_path, f"--sub-file={subs_path}"])
        return
    except Exception:
        pass

    # 2. Próba VLC
    try:
        subprocess.Popen(["vlc", video_path, f"--sub-file={subs_path}"])
        return
    except Exception:
        pass

    # 3. Domyślny program w Windows
    if os.name == "nt":
        try:
            os.startfile(video_path)
            return
        except Exception:
            pass

    print("[Info] Nie znaleziono mpv/vlc w PATH. Otwórz plik wideo ręcznie w swoim ulubionym odtwarzaczu.")

def natural_sort_key(s: str) -> list:
    """Umożliwia naturalne sortowanie nazw plików i odcinków (np. 1, 2, ..., 10, 11)."""
    import re
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', str(s))]


def collect_input_files(raw_inputs: list) -> list:
    """
    Zbiera i układa w kolejce pliki wideo, napisy lub całe foldery z odcinkami.
    """
    collected = []
    seen = set()

    for raw in raw_inputs:
        if not raw:
            continue
        p = Path(raw)
        if not p.exists():
            continue
        if p.is_dir():
            # Przeszukiwanie całego folderu
            for item in sorted(p.iterdir(), key=lambda x: natural_sort_key(x.name)):
                if item.is_file():
                    ext = item.suffix.lower()
                    if ext in VIDEO_EXTENSIONS:
                        if item.resolve() not in seen:
                            collected.append(item)
                            seen.add(item.resolve())
                    elif ext in SUBTITLE_EXTENSIONS:
                        has_video = any((item.parent / f"{item.stem}{vext}").exists() for vext in VIDEO_EXTENSIONS)
                        if not has_video and item.resolve() not in seen:
                            collected.append(item)
                            seen.add(item.resolve())
        elif p.is_file():
            if p.resolve() not in seen:
                collected.append(p)
                seen.add(p.resolve())

    return sorted(collected, key=lambda x: natural_sort_key(x.name))


def resolve_episode_files(
    input_path: Path,
    args_subs: Optional[str] = None,
    args_video: Optional[str] = None,
    args_track: int = 0
) -> Tuple[Optional[Path], Optional[Path], bool]:
    """
    Rozwiązuje powiązanie plik wideo <-> plik napisów dla pojedynczego odcinka.
    Zwraca: (video_file, subs_file, temp_subs_extracted)
    """
    video_file: Optional[Path] = None
    subs_file: Optional[Path] = None
    temp_subs_extracted = False

    ext = input_path.suffix.lower()

    if ext in VIDEO_EXTENSIONS:
        video_file = input_path
        if args_subs:
            subs_file = Path(args_subs)
        else:
            potential_subs = input_path.with_suffix(".srt")
            potential_subs_en = input_path.parent / f"{input_path.stem}.en.srt"
            potential_ass = input_path.with_suffix(".ass")

            if potential_subs_en.exists():
                subs_file = potential_subs_en
                print(f"  [Wykryto napisy zewnętrzne]: {subs_file.name}")
            elif potential_subs.exists():
                subs_file = potential_subs
                print(f"  [Wykryto napisy zewnętrzne]: {subs_file.name}")
            elif potential_ass.exists():
                subs_file = potential_ass
                print(f"  [Wykryto napisy zewnętrzne]: {subs_file.name}")
            else:
                tracks = list_subtitle_tracks(str(video_file))
                if not tracks:
                    print(f"  [Błąd]: Plik {video_file.name} nie zawiera napisów wbudowanych ani zewnętrznych.")
                    return None, None, False

                chosen_track_idx = args_track
                extracted_path = extract_embedded_subtitles(
                    video_path=str(video_file),
                    sub_index=chosen_track_idx
                )
                subs_file = Path(extracted_path)
                temp_subs_extracted = True
                print(f"  [Sukces]: Wyodrębniono wbudowane napisy ze ścieżki {chosen_track_idx}")

    elif ext in SUBTITLE_EXTENSIONS:
        subs_file = input_path
        if args_video:
            video_file = Path(args_video)
        else:
            stem = input_path.stem
            if stem.endswith(".en"):
                stem = stem[:-3]
            for vext in VIDEO_EXTENSIONS:
                cand = input_path.parent / f"{stem}{vext}"
                if cand.exists():
                    video_file = cand
                    print(f"  [Wykryto powiązany plik wideo]: {video_file.name}")
                    break

    elif ext == ".json":
        stem = input_path.stem
        if stem.endswith(".checkpoint"):
            stem = stem[:-11]
        for vext in VIDEO_EXTENSIONS:
            cand_video = input_path.parent / f"{stem}{vext}"
            if cand_video.exists():
                video_file = cand_video
                tracks = list_subtitle_tracks(str(video_file))
                if tracks:
                    extracted_path = extract_embedded_subtitles(str(video_file), sub_index=0)
                    subs_file = Path(extracted_path)
                    temp_subs_extracted = True
                    break
        if not subs_file:
            for sext in SUBTITLE_EXTENSIONS:
                cand_subs = input_path.parent / f"{stem}{sext}"
                if cand_subs.exists():
                    subs_file = cand_subs
                    break

    return video_file, subs_file, temp_subs_extracted


def main():
    parser = argparse.ArgumentParser(
        description="Multimodalny Tłumacz Napisów z angielskiego na polski z analizą klatek wideo (Gemini 3.7 Flash)"
    )
    parser.add_argument(
        "input",
        nargs="*",
        help="Ścieżka do jednego lub wielu plików wideo (.mkv, .mp4), napisów (.srt, .ass) lub całego folderu z sezonem"
    )
    parser.add_argument(
        "--video", "-v",
        help="Opcjonalna ścieżka do pliku wideo (jeśli jako główny argument podano plik .srt)"
    )
    parser.add_argument(
        "--subs", "-s",
        help="Opcjonalna ścieżka do pliku z napisami (jeśli jako główny argument podano plik wideo)"
    )
    parser.add_argument(
        "--track", "-t",
        type=int,
        default=0,
        help="Indeks ścieżki napisów do wyciągnięcia z pliku wideo (domyślnie 0)"
    )
    parser.add_argument(
        "--model", "-m",
        default=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
        help="Model Gemini dla Fazy 1 (domyślnie: gemini-3.5-flash-lite)"
    )
    parser.add_argument(
        "--model-phase2",
        default=os.getenv("GEMINI_MODEL_PHASE2", None),
        help="Opcjonalny model dla Fazy 2 Script Doctora (np. gemini-3.1-pro lub gemini-2.5-pro)"
    )
    parser.add_argument(
        "--profile",
        choices=["standard", "studio", "pro"],
        default=None,
        help="Profil tłumaczenia: 'standard' (100% Flash), 'studio' (Flash + Pro Script Doctor), 'pro' (Full Pro)"
    )
    parser.add_argument(
        "--no-whisper",
        action="store_true",
        help="Wyłącz lokalną transkrypcję japońskiego Whisper"
    )
    parser.add_argument(
        "--whisper-model",
        type=str,
        default="kotoba-tech/kotoba-whisper-v2.0-faster",
        help="Lokalny model Whisper (domyślnie: 'kotoba-tech/kotoba-whisper-v2.0-faster', opcje: 'kotoba', 'turbo', 'large-v3', 'anime')"
    )
    parser.add_argument(
        "--batch-size", "-b",
        type=int,
        default=int(os.getenv("BATCH_SIZE", "24")),
        help="Liczba kwestii dialogowych w jednej paczce (domyślnie: 24)"
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Pomiń II fazę (redakcję dialogów i weryfikację kalek)"
    )
    parser.add_argument(
        "--honorifics",
        action="store_true",
        default=None,
        help="Wymuś ZACHOWANIE japońskich honoryfikatorów (-kun, -chan, -san, -sama)"
    )
    parser.add_argument(
        "--no-honorifics",
        action="store_true",
        default=None,
        help="Wymuś USUNIĘCIE japońskich honoryfikatorów i zastąpienie czystą polszczyzną (styl Netflix)"
    )
    parser.add_argument(
        "--play", "-p",
        action="store_true",
        help="Uruchom film w odtwarzaczu po zakończeniu tłumaczenia"
    )
    parser.add_argument(
        "--output", "-o",
        help="Ścieżka docelowa dla pliku z polskimi napisami (dotyczy tylko pojedynczego pliku)"
    )

    args = parser.parse_args()

    raw_inputs = args.input if isinstance(args.input, list) and args.input else ([args.input] if args.input else [])
    if not raw_inputs:
        print("[Info] Nie podano pliku jako argumentu. Otwieram okno wyboru pliku...")
        chosen_input = pick_file_gui()
        if not chosen_input:
            print("[Info] Nie wybrano żadnego pliku. Zamykam program.")
            sys.exit(0)
        raw_inputs = [chosen_input]

    # Zbieranie i sortowanie kolejki plików
    queue = collect_input_files(raw_inputs)
    if not queue:
        print(f"[Błąd]: Nie znaleziono żadnych obsługiwanych plików wideo ani napisów.")
        sys.exit(1)

    total_episodes = len(queue)
    is_season_queue = total_episodes > 1

    if is_season_queue:
        print("\n" + "=" * 68)
        print(f"  🎬 WYKRYTO KOLEJKĘ SEZONOWĄ: {total_episodes} ODCINKÓW DO PRZETŁUMACZENIA")
        print("=" * 68)
        for idx, item in enumerate(queue, 1):
            print(f"  [{idx:02d}/{total_episodes:02d}] {item.name}")
        print("=" * 68)

    # Inicjalizacja ustawień i modeli (zadawane TYLKO RAZ na początku dla całej kolejki)
    enable_verifier = not args.no_verify and os.getenv("ENABLE_VERIFIER", "true").lower() == "true"

    # Wybór trybu honoryfikatorów: CLI -> Interaktywne menu w CMD -> .env
    if args.no_honorifics:
        keep_honorifics = False
    elif args.honorifics:
        keep_honorifics = True
    else:
        default_env = os.getenv("KEEP_HONORIFICS", "true").lower() == "true"
        default_label = "1 (Zachowaj)" if default_env else "2 (Usuń)"
        
        print("\n" + "─" * 58)
        print("  WYBÓR STYLU DLA JAPOŃSKICH HONORYFIKATORÓW:")
        print("  [1] ZACHOWAJ (-kun, -chan, -san, -sama) [Styl Fansub / Anime]")
        print("  [2] USUŃ i zastąp czystą polszczyzną    [Styl Netflix / Dubbing]")
        print("─" * 58)
        try:
            choice = input(f"  Twój wybór [1 / 2] (Wciśnij Enter dla {default_label}): ").strip()
            if choice == "2":
                keep_honorifics = False
            elif choice == "1":
                keep_honorifics = True
            else:
                keep_honorifics = default_env
        except (EOFError, KeyboardInterrupt):
            keep_honorifics = default_env

    from model_resolver import resolve_best_models
    from google import genai
    
    # Dynamiczne wykrywanie najnowszych modeli Gemini
    api_key_check = os.getenv("GEMINI_API_KEY")
    temp_client = genai.Client(api_key=api_key_check) if api_key_check else None
    best_models = resolve_best_models(temp_client)

    model_p1 = args.model if args.model != "gemini-3.5-flash-lite" else None
    model_p2 = args.model_phase2

    if args.profile in ["ultra", "ultra_pro", "cinema"]:
        model_p1 = best_models["pro"]
        model_p2 = best_models["pro"]
    elif args.profile in ["pro", "master"]:
        model_p1 = best_models["flash"]
        model_p2 = best_models["pro"]
    elif args.profile == "studio":
        model_p1 = best_models["flash"]
        model_p2 = best_models["flash"]
    elif args.profile == "standard":
        model_p1 = best_models["flash_lite"]
        model_p2 = best_models["flash_lite"]
    elif not model_p2 and not model_p1:
        from pricing_guard import PricingGuard
        cost_flash_est = PricingGuard.estimate_episode_cost_pln("2")
        cost_pro_est = PricingGuard.estimate_episode_cost_pln("3")
        cost_ultra_est = PricingGuard.estimate_episode_cost_pln("4")
        print("\n" + "─" * 68)
        print("  WYBÓR PROFILU JAKOŚCI TŁUMACZENIA (Auto-wykrywanie najnowszych modeli):")
        print(f"  [1] STANDARDOWY       [{best_models['flash_lite']} - 100% Darmowy, szybki]")
        print(f"  [2] STUDYJNY FLASH    [{best_models['flash']} + Redakcja Flash - Ekstremalnie tani (~{cost_flash_est:.2f} zł/odc)]")
        print(f"  [3] MASTER PRO ⭐    [{best_models['flash']} + {best_models['pro']} Redakcja Pro - Jakość Kinowa (~{cost_pro_est:.2f} zł/odc z Rabatem -75% Cache)]")
        print(f"  [4] KINOWY ULTRA 👑   [{best_models['pro']} + {best_models['pro']} Pełny Pro - Maksymalna Głębokość (~{cost_ultra_est:.2f} zł/odc z Rabatem -75% Cache)]")
        print("─" * 68)
        print(PricingGuard.get_pricing_status_banner())
        print("─" * 68)
        try:
            prof_choice = input("  Twój wybór [1 / 2 / 3 / 4] (Wciśnij Enter dla 3): ").strip()
            if prof_choice == "1":
                model_p1 = best_models["flash_lite"]
                model_p2 = best_models["flash_lite"]
            elif prof_choice == "2":
                model_p1 = best_models["flash"]
                model_p2 = best_models["flash"]
            elif prof_choice == "4":
                model_p1 = best_models["pro"]
                model_p2 = best_models["pro"]
            else:
                model_p1 = best_models["flash"]
                model_p2 = best_models["pro"]
        except (EOFError, KeyboardInterrupt):
            model_p1 = best_models["flash"]
            model_p2 = best_models["pro"]
    else:
        model_p1 = model_p1 or best_models["flash"]
        model_p2 = model_p2 or best_models["pro"]

    use_whisper = not args.no_whisper

    try:
        translator = MultimodalTranslator(
            model=model_p1,
            model_phase2=model_p2,
            batch_size=args.batch_size,
            enable_verifier=enable_verifier,
            keep_honorifics=keep_honorifics,
            use_whisper=use_whisper,
            whisper_model_size=args.whisper_model
        )
    except ValueError as e:
        print(f"\n[Błąd Konfiguracji]: {e}")
        print("Upewnij się, że w pliku .env znajduje się poprawny GEMINI_API_KEY.")
        sys.exit(1)

    completed_files = []

    # Główna pętla Kolejki Sezonowej
    for ep_idx, target_path in enumerate(queue, 1):
        if is_season_queue:
            print("\n" + "═" * 70)
            print(f"  📺 [KOLEJKA SEZONOWA: ODCINEK {ep_idx}/{total_episodes}] {target_path.name}")
            print("═" * 70)

        video_file, subs_file, temp_subs_extracted = resolve_episode_files(
            input_path=target_path,
            args_subs=args.subs,
            args_video=args.video,
            args_track=args.track
        )

        if not subs_file or not subs_file.exists():
            print(f"  [Pominięto]: Nie udało się przygotować napisów dla {target_path.name}")
            continue

        final_output_path = args.output if (not is_season_queue and args.output) else None
        if not final_output_path and video_file:
            ext = subs_file.suffix if subs_file else ".ass"
            final_output_path = str(video_file.parent / f"{video_file.stem}{ext}")

        try:
            result_subs_path = translator.translate_file(
                subs_path=str(subs_file),
                video_path=str(video_file) if video_file else None,
                output_path=final_output_path
            )
            completed_files.append((target_path.name, result_subs_path))
            print(f"\n[Sukces odcinka {ep_idx}/{total_episodes}]: Zapisano w -> {result_subs_path}")
        except Exception as e:
            print(f"\n[Błąd podczas tłumaczenia {target_path.name}]: {e}")
        finally:
            if temp_subs_extracted and subs_file and subs_file.exists():
                try:
                    os.remove(str(subs_file))
                except OSError:
                    pass

    # Podsumowanie końcowe
    print("\n" + "=" * 70)
    if is_season_queue:
        print(f"  🎉 ZAKOŃCZONO KOLEJKĘ SEZONOWĄ: Przetłumaczono {len(completed_files)}/{total_episodes} odcinków!")
        print("=" * 70)
        for name, out in completed_files:
            print(f"  ✔️ {name} -> {Path(out).name}")
    else:
        if completed_files:
            print(f"  🎉 Pomyślnie przetłumaczono: {completed_files[0][1]}")
    print("=" * 70 + "\n")

    # Uruchomienie odtwarzacza (tylko w trybie pojedynczego pliku)
    if not is_season_queue and args.play and queue and queue[0].suffix.lower() in VIDEO_EXTENSIONS and completed_files:
        launch_player(str(queue[0]), completed_files[0][1])


if __name__ == "__main__":
    main()
