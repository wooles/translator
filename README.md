# Multimodal Subtitle Translator (Gemini 3.7 Flash)

Inteligentne narzędzie w języku Python wykorzystujące model **Gemini 3.7 Flash** do automatycznego tłumaczenia napisów filmowych i anime z języka angielskiego na język polski.

Narzędzie analizuje **klatki wideo (kontekst wizualny)** w momencie trwania kwestii dialogowych, dzięki czemu bezbłędnie dobiera formy gramatyczne (rodzaj męski/żeński/nijaki, relacje formalne/nieformalne) oraz posiada **dwufazowy potok z dedykowanym modułem redakcji dialogów**, który eliminuje kalki językowe (np. *"I see"* $\rightarrow$ *„Rozumiem”*, a nie *„Widzę”*).

---

## Główne Funkcje

1. **Analiza Wizualna Kadrów (Multimodal Context)**:
   * Wyciąga klatkę wideo odpowiadającą mówiącej postaci.
   * Ustala płeć mówcy i rozmówcy (np. *„Zrobiłem”* vs *„Zrobiłam”*, *„Cieszę się, że przyszedłeś”* vs *„przyszłaś”*).
2. **Eliminacja Kalek Językowych (Anti-Calque Engine)**:
   * Wbudowana baza reguł eliminująca sztuczne dosłowne tłumaczenia (np. *„To ma sens”* zamiast *„To robi sens”*, *„Wszystko w porządku?”* zamiast *„Jesteś w porządku?”*).
3. **Dwufazowa Redakcja Dialogów (Dialogue Verifier)**:
   * **Faza 1**: Tłumaczenie multimodalne z klatkami wideo i kontekstem sceny.
   * **Faza 2**: Redakcja przez wirtualnego redaktora dialogów filmowych dbającego o naturalność polszczyzny i rytm czytania.
4. **Wygodna Obsługa**:
   * Przeciągnij i upuść plik wideo lub napisy na plik `translate_drag_and_drop.bat`.
   * Automatyczna obsługa wbudowanych ścieżek w plikach `.mkv` / `.mp4` lub zewnętrznych plików `.srt` / `.ass`.

---

## Szybki Start (Instalacja i Konfiguracja)

### 1. Konfiguracja Klucza API
1. Skopiuj plik `.env.example` do pliku `.env`:
   ```bash
   cp .env.example .env
   ```
2. Otwórz plik `.env` w dowolnym edytorze i wklej swój klucz API:
   ```env
   GEMINI_API_KEY=twoj_klucz_api_tutaj
   ```
   *(Klucz uzyskasz bezpłatnie na: [Google AI Studio](https://aistudio.google.com/))*

---

## Sposoby Użycia

### Opcja A: Przeciągnij i Upuść (Najprostsza)
Przeciągnij dowolny plik wideo (np. `odcinek.mkv`) lub plik napisów (np. `napisy.srt`) i upuść go bezpośrednio na plik **`translate_drag_and_drop.bat`**.

### Opcja B: Linia Poleceń (CLI)

Uruchomienie w środowisku wirtualnym:

```powershell
# Pełne automatyczne tłumaczenie wideo z wbudowanymi napisami:
.venv\Scripts\python main.py film.mkv

# Tłumaczenie z podglądem w odtwarzaczu (MPV/VLC) po zakończeniu:
.venv\Scripts\python main.py film.mkv --play

# Tłumaczenie z osobnym plikiem z napisami:
.venv\Scripts\python main.py --video film.mp4 --subs napisy_en.srt

# Szybkie tłumaczenie tekstowe (bez weryfikatora):
.venv\Scripts\python main.py napisy.srt --no-verify
```

---

## Struktura Projektu

- [`main.py`](file:///c:/Users/Piotrek/Desktop/translator/main.py) – Główny interfejs wiersza poleceń (CLI) i wykrywanie ścieżek wideo/napisów.
- [`translator.py`](file:///c:/Users/Piotrek/Desktop/translator/translator.py) – Silnik orkiestracji paczek dialogowych i zapytań do Gemini 3.7 Flash.
- [`verifier.py`](file:///c:/Users/Piotrek/Desktop/translator/verifier.py) – Redaktor dialogów eliminujący kalki językowe i sztywny styl (Faza 2).
- [`rules.py`](file:///c:/Users/Piotrek/Desktop/translator/rules.py) – Zbiór reguł anty-kalek, wytycznych wizualnych i promptów systemowych.
- [`extract.py`](file:///c:/Users/Piotrek/Desktop/translator/extract.py) – Ekstrakcja klatek wideo i wbudowanych ścieżek napisów przez `ffmpeg`.
- [`translate_drag_and_drop.bat`](file:///c:/Users/Piotrek/Desktop/translator/translate_drag_and_drop.bat) – Wygodny launcher dla Windows.
- [`test_system.py`](file:///c:/Users/Piotrek/Desktop/translator/test_system.py) – Zestaw testów weryfikacyjnych.
