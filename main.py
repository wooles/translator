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

def main():
    parser = argparse.ArgumentParser(
        description="Multimodalny Tłumacz Napisów z angielskiego na polski z analizą klatek wideo (Gemini 3.7 Flash)"
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Ścieżka do pliku wideo (.mkv, .mp4) lub pliku z napisami (.srt, .ass)"
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
        "--batch-size", "-b",
        type=int,
        default=int(os.getenv("BATCH_SIZE", "14")),
        help="Liczba kwestii dialogowych w jednej paczce (domyślnie: 14)"
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
        help="Ścieżka docelowa dla pliku z polskimi napisami"
    )

    args = parser.parse_args()

    chosen_input = args.input
    if not chosen_input:
        print("[Info] Nie podano pliku jako argumentu. Otwieram okno wyboru pliku...")
        chosen_input = pick_file_gui()
        if not chosen_input:
            print("[Info] Nie wybrano żadnego pliku. Zamykam program.")
            sys.exit(0)

    input_path = Path(chosen_input)
    if not input_path.exists():
        print(f"[Błąd]: Podany plik nie istnieje: {chosen_input}")
        sys.exit(1)

    video_file: Optional[Path] = None
    subs_file: Optional[Path] = None
    temp_subs_extracted = False

    ext = input_path.suffix.lower()

    if ext in VIDEO_EXTENSIONS:
        video_file = input_path
        if args.subs:
            subs_file = Path(args.subs)
        else:
            # Sprawdzamy czy w tym samym katalogu leży plik .srt o tej samej nazwie
            potential_subs = input_path.with_suffix(".srt")
            potential_subs_en = input_path.parent / f"{input_path.stem}.en.srt"
            potential_ass = input_path.with_suffix(".ass")

            if potential_subs_en.exists():
                subs_file = potential_subs_en
                print(f"[Wykryto napisy zewnętrzne]: {subs_file.name}")
            elif potential_subs.exists():
                subs_file = potential_subs
                print(f"[Wykryto napisy zewnętrzne]: {subs_file.name}")
            elif potential_ass.exists():
                subs_file = potential_ass
                print(f"[Wykryto napisy zewnętrzne]: {subs_file.name}")
            else:
                # Sprawdzamy wbudowane ścieżki w pliku wideo
                tracks = list_subtitle_tracks(str(video_file))
                if not tracks:
                    print("[Błąd]: Plik wideo nie zawiera wbudowanych napisów i nie znaleziono pliku zewnętrznego .srt/.ass.")
                    sys.exit(1)
                
                print(f"[Wykryto {len(tracks)} wbudowanych ścieżek napisów]:")
                chosen_track_idx = args.track
                for t in tracks:
                    marker = " -> [WYBRANA]" if t["sub_index"] == chosen_track_idx else ""
                    print(f"  Ścieżka {t['sub_index']}: Język={t['language']}, Tytuł={t['title']}, Format={t['codec']}{marker}")

                extracted_path = extract_embedded_subtitles(
                    video_path=str(video_file),
                    sub_index=chosen_track_idx
                )
                subs_file = Path(extracted_path)
                temp_subs_extracted = True
                print(f"[Sukces]: Wyodrębniono wbudowane napisy ze ścieżki {chosen_track_idx}")

    elif ext in SUBTITLE_EXTENSIONS:
        subs_file = input_path
        if args.video:
            video_file = Path(args.video)
        else:
            # Szukamy powiązanego pliku wideo o zbliżonej nazwie w tym samym katalogu
            stem = input_path.stem
            if stem.endswith(".en"):
                stem = stem[:-3]
            for vext in VIDEO_EXTENSIONS:
                cand = input_path.parent / f"{stem}{vext}"
                if cand.exists():
                    video_file = cand
                    print(f"[Wykryto powiązany plik wideo]: {video_file.name}")
                    break
    elif ext == ".json":
        print(f"[Autozapis]: Wykryto plik autozapisu JSON: {input_path.name}")
        stem = input_path.stem
        if stem.endswith(".checkpoint"):
            stem = stem[:-11]

        found = False
        # Szukamy powiązanego pliku wideo
        for vext in VIDEO_EXTENSIONS:
            cand_video = input_path.parent / f"{stem}{vext}"
            if cand_video.exists():
                video_file = cand_video
                tracks = list_subtitle_tracks(str(video_file))
                if tracks:
                    extracted_path = extract_embedded_subtitles(str(video_file), sub_index=0)
                    subs_file = Path(extracted_path)
                    temp_subs_extracted = True
                    found = True
                    print(f"[Powiązanie]: Znaleziono powiązany plik wideo: {video_file.name}")
                    break
        if not found:
            # Szukamy powiązanego pliku napisów
            for sext in SUBTITLE_EXTENSIONS:
                cand_subs = input_path.parent / f"{stem}{sext}"
                if cand_subs.exists():
                    subs_file = cand_subs
                    found = True
                    print(f"[Powiązanie]: Znaleziono powiązany plik napisów: {subs_file.name}")
                    break
        if not found:
            print(f"[Błąd]: Nie znaleziono pliku wideo ani napisów powiązanych z tym plikiem JSON: {stem}")
            sys.exit(1)
    else:
        print(f"[Błąd]: Nieobsługiwany format pliku: {ext}")
        sys.exit(1)

    # Inicjalizacja tłumacza
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
    
    # Dynamiczne wykrywanie najnowszych i najlepszych wersji modeli Gemini
    api_key_check = os.getenv("GEMINI_API_KEY")
    temp_client = genai.Client(api_key=api_key_check) if api_key_check else None
    best_models = resolve_best_models(temp_client)

    # Wybór profilu tłumaczenia
    model_p1 = args.model if args.model != "gemini-3.5-flash-lite" else None
    model_p2 = args.model_phase2

    if args.profile == "pro" or args.profile == "master":
        model_p1 = best_models["flash"]
        model_p2 = best_models["pro"]
    elif args.profile == "studio":
        model_p1 = best_models["flash_lite"]
        model_p2 = best_models["flash"]
    elif args.profile == "standard":
        model_p1 = best_models["flash_lite"]
        model_p2 = best_models["flash_lite"]
    elif not model_p2 and not model_p1:
        print("\n" + "─" * 68)
        print("  WYBÓR PROFILU JAKOŚCI TŁUMACZENIA (Auto-wykrywanie najnowszych modeli):")
        print(f"  [1] STANDARDOWY      [{best_models['flash_lite']} - 100% Darmowy, szybki]")
        print(f"  [2] STUDYJNY FLASH   [{best_models['flash_lite']} + {best_models['flash']} Redaktor Dialogów - 100% Free]")
        print(f"  [3] MASTER PRO ⭐   [{best_models['flash']} + {best_models['pro']} Redaktor Dialogów - Jakość Kinowa]")
        print("─" * 68)
        try:
            prof_choice = input("  Twój wybór [1 / 2 / 3] (Wciśnij Enter dla 3): ").strip()
            if prof_choice == "1":
                model_p1 = best_models["flash_lite"]
                model_p2 = best_models["flash_lite"]
            elif prof_choice == "2":
                model_p1 = best_models["flash_lite"]
                model_p2 = best_models["flash"]
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
            use_whisper=use_whisper
        )
    except ValueError as e:
        print(f"\n[Błąd Konfiguracji]: {e}")
        print("Upewnij się, że w pliku .env znajduje się poprawny GEMINI_API_KEY.")
        sys.exit(1)

    print(f"\n=======================================================")
    print(f"  Multimodal Video Subtitle Translator")
    print(f"  Model Faza 1 (Tłumaczenie + Wizja): {model_p1}")
    print(f"  Model Faza 2 (Redaktor Dialogów): {model_p2 if enable_verifier else 'Wyłączony'}")
    print(f"  Honoryfikatory: {'ZACHOWAJ (Fansub)' if keep_honorifics else 'USUŃ (Czysta polszczyzna/Netflix)'}")
    print(f"  Profiler Odcinka (Słowniczek): WŁĄCZONY")
    print(f"  Plik napisów: {subs_file}")
    print(f"  Plik wideo: {video_file if video_file else 'Brak (Tłumaczenie tekstowe)'}")
    print(f"=======================================================\n")

    # Uruchomienie procesu tłumaczenia
    final_output_path = args.output
    if not final_output_path and video_file:
        ext = subs_file.suffix if subs_file else ".ass"
        final_output_path = str(video_file.parent / f"{video_file.stem}.pl{ext}")

    try:
        result_subs_path = translator.translate_file(
            subs_path=str(subs_file),
            video_path=str(video_file) if video_file else None,
            output_path=final_output_path
        )
    finally:
        # Usuwanie tymczasowego pliku z wyciągniętymi napisami
        if temp_subs_extracted and subs_file and subs_file.exists():
            try:
                os.remove(str(subs_file))
            except OSError:
                pass

    print(f"\n[Gotowe!]: Polskie napisy wygenerowane pomyślnie w:\n-> {result_subs_path}")

    # Uruchomienie odtwarzacza jeśli zażądano
    if args.play and video_file and video_file.exists():
        launch_player(str(video_file), result_subs_path)

if __name__ == "__main__":
    main()
