# Multimodal Subtitle Translator (Studio Master Quality)

Inteligentne narzędzie w języku Python wykorzystujące modele **Gemini (Flash & Gemini 3.1 Pro)** oraz lokalny silnik **Whisper STT** do profesjonalnego tłumaczenia napisów filmowych i anime z języka angielskiego/japońskiego na język polski.

Oparte na **Kanonie Przekładu Audiowizualnego Arkadiusza Belczyka**, **Wizualnym OCR kadrów (1080p)**, **Słowniczku i Profilerze Odcinka**, **Pamięci Tłumaczeniowej (10 342 autentycznych par dialogowych)** oraz **dwufazowej architekturze redakcyjnej (Redaktor Dialogów)**.

---

## 🚀 Instalacja 1-Kliknięciem na Nowym Komputerze (1-Click Setup)

Na nowym komputerze po pobraniu repozytorium wystarczy uruchomić:
```powershell
# Opcja A (Najprostsza): Kliknij dwukrotnie plik:
setup_new_pc.bat

# Opcja B (PowerShell):
.\setup_new_pc.ps1
```
Skrypt automatycznie:
1. Sprawdzi i zainstaluje Pythona oraz FFmpeg.
2. Utworzy środowisko `.venv` i zainstaluje wszystkie biblioteki.
3. Skonfiguruje Twój klucz `GEMINI_API_KEY`.
4. Zaindeksuje bazę Translation Memory (10 000+ wzorców).
5. Przeprowadzi autotesty weryfikacyjne.

---

## 🌟 Kluczowe Funkcje i Architektura

1. **Lokalna Transkrypcja Mowy Japońskiej (Whisper STT)**:
   * Wyciąga oryginalną mowę japońską (Kanji/Kana) bezpośrednio z audio, eliminując błędy i uproszczenia w angielskich fansubach.
2. **Profiler Odcinka (Pre-pass Episode Profiler & Glossary)**:
   * Skanuje odcinek przed startem, ustala relacje między postaciami (kto per *„pani Teshima”*, kto na *„ty”*) oraz tworzy spójny słowniczek pojęć.
3. **Wizualny OCR Klatek Wideo (1080p)**:
   * Odczytuje napisy w tle, tablice szkolne, telefony i dymki mangowe (`いいよね〜`).
4. **Kanon Przekładu Audiowizualnego Arkadiusza Belczyka**:
   * Eliminacja zaimków „Ja”, naturalny szyk wyrazów, formuły Aisatsu (*Tadaima!* $\rightarrow$ *„Wróciłam!”*), eliminacja powtórzeń leksykalnych.
5. **Dwufazowa Redakcja Dialogów (Master Redaktor Dialogów)**:
   * **Faza 1**: Tłumaczenie multimodalne (Obraz + Audio + Whisper + Kontekst EN).
   * **Faza 2**: Redakcja przez wirtualnego redaktora dialogów (Gemini 3.1 Pro / Flash) dbającego o kunszt literacki i brak kalek.

---

## 🎮 Profile Jakości w Menu CMD

Przy uruchomieniu masz do wyboru 3 profile:
* **[1] STANDARDOWY**: Ultraszybki, 100% darmowy (Flash-Lite).
* **[2] STUDYJNY FLASH**: 100% darmowy, wysoka jakość (Flash + Flash Redaktor Dialogów).
* **[3] MASTER PRO ⭐**: Jakość kinowa studia dubbingu (Flash + Gemini 3.1 Pro Redaktor Dialogów z głębokim wnioskowaniem).

---

## 💻 Użycie

### Przeciągnij i Upuść (Windows):
Przeciągnij plik wideo (`.mkv`, `.mp4`) lub napisy (`.srt`, `.ass`) na plik **`translate_drag_and_drop.bat`**.

### Wiersz poleceń (CLI):
```powershell
# Tłumaczenie wideo w trybie Master Pro:
.venv\Scripts\python main.py "film.mkv" --profile pro

# Tłumaczenie z podglądem w odtwarzaczu (MPV/VLC):
.venv\Scripts\python main.py "film.mkv" --play

# Ekstrakcja napisów z wideo do pliku:
.venv\Scripts\python extract_subtitles.py "film.mkv"
```
