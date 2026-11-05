"""
Narzędzie migracyjne do konsolidacji rozszczepionych plików *_bible.json.

Uruchamiane RĘCZNIE przez operatora poza reżimem Z16 (nie jest częścią commita 10.6.3).

Użycie:
    python tools/consolidate_bibles.py --dry-run
    python tools/consolidate_bibles.py --apply
"""
import argparse
import datetime
import json
import sys
from pathlib import Path

# Dodaj katalog główny do sys.path, aby importować series_memory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from series_memory import consolidate_split_bibles, SERIES_MEMORY_DIR


def main():
    parser = argparse.ArgumentParser(
        description="Konsolidacja rozszczepionych plików *_bible.json pomiędzy grupami fansubskimi."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Tylko wyświetla wykryte pary duplikatów (bez zapisu).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Wykonuje konsolidację i przenosi plik wtórny do Artefakty/_KONSOLIDACJA_BIBLE/.",
    )
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        print("[INFO] Domyślnie uruchamiam --dry-run. Użyj --apply, aby wykonać konsolidację.")
        args.dry_run = True

    pairs = consolidate_split_bibles(SERIES_MEMORY_DIR, dry_run=args.dry_run)

    log_dir = Path(__file__).resolve().parent.parent / "Artefakty" / "_KONSOLIDACJA_BIBLE"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "migration.log"

    timestamp = datetime.datetime.now().isoformat()
    mode = "APPLY" if args.apply else "DRY-RUN"
    log_lines = [f"=== {timestamp} [{mode}] ==="]

    if not pairs:
        print("[INFO] Brak duplikatów do konsolidacji.")
        log_lines.append("Brak duplikatów do konsolidacji.")
    else:
        print(f"[INFO] Wykryto {len(pairs)} par(y) duplikatów:")
        for canonical, secondary in pairs:
            print(f"  - canonical: {canonical}  <-  secondary: {secondary}")
            log_lines.append(f"  canonical: {canonical}  <-  secondary: {secondary}")

    log_lines.append("")
    with log_path.open("a", encoding="utf-8") as f:
        f.write("\n".join(log_lines) + "\n")

    print(f"[INFO] Log zapisany do: {log_path}")


if __name__ == "__main__":
    main()
