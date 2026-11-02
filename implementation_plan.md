# 🏛️ PLAN ARCHITEKTONICZNY: WIELOWĄTKOWA SYNCHRONIZACJA I ATOMOWE BEZPIECZEŃSTWO SŁOWNIKÓW (ZERO 'DICTIONARY CHANGED SIZE DURING ITERATION')

**Status:** `OCZEKUJE NA AKCEPTACJĘ OPERATORA (USER APPROVAL GATE)`  
**Autor:** Główny Architekt Systemów AVT i Potoków Hybrydowych  
**Cel nadrzędny:** Całkowite, systemowe wyeliminowanie błędu współbieżności `RuntimeError: dictionary changed size during iteration` (Race Condition) występującego podczas równoległego tłumaczenia paczek (`ThreadPoolExecutor` z rotacją wielu kluczy API), bez obciążania modeli Gemini i przy zachowaniu 100% determinizmu oraz kosztu 0.00 PLN.

---

## 🔬 ROZDZIAŁ I: DIAGNOZA ŹRÓDŁOWA (ROOT CAUSE ANALYSIS)

### 1. Istota błędu w środowisku wykonawczym CPython
W języku Python (CPython) metody słownika:
- `dict.items()`
- `dict.keys()`
- `dict.values()`
nie zwracają statycznej listy wyrazów, lecz **żywe widoki słownika (dictionary views)**. Widok ten utrzymuje wewnętrzny wskaźnik do tablicy hashującej słownika.

Jeśli jakikolwiek wątek doda nowy klucz (`dict[k] = v`) lub usunie istniejący klucz (`del dict[k]`), następuje zmiana licznika rozmiaru słownika (`ma_used` w strukturze CPython `PyDictObject`). Gdy iterator w innym wątku pobiera kolejny element i wykryje rozbieżność rozmiaru, CPython natychmiast rzuca:
```text
RuntimeError: dictionary changed size during iteration
```

### 2. Dlaczego błąd wystąpił w trakcie tłumaczenia?
Podczas tłumaczenia z wieloma kluczami API (`MultiKeyClientPool`), system uruchamia równoległe przetwarzanie paczek dialogowych w puli wątków:
```python
with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
    future_to_bidx = { executor.submit(self._process_single_batch, ...): b_idx ... }
```
Wewnątrz metody `_process_single_batch`:
1. **Wątek A** (np. Paczka 1) otrzymuje odpowiedź z Fazy 1 i w linii 3266 wywołuje:
   ```python
   self._register_character_safe(char.name, char.gender, char.role)
   ```
   oraz podczas arbitrażu audio w linii 1802:
   ```python
   self.series_bible.update_character_gender_from_audio(spk_clean, "MALE")
   ```
   Obie te operacje **wstawiają nowe klucze** do współdzielonych obiektów:
   - `self.character_registry[clean_name] = new_desc`
   - `self.series_bible.data["characters"][clean_name] = ...`
   - `self.series_bible.data["declensions"][clean_name] = ...`

2. **Wątek B** (np. Paczka 2) w tym samym ułamku sekundy analizuje swoje kwestie dialogowe i iteruje bezpośrednio po widokach tych słowników:
   - W `detect_third_person_mentions` (linia 1158):
     `for full_name, details in character_registry.items():`
     oraz linia 1177:
     `for b_name, b_info in bible_chars.items():`
   - W `SeriesBible.format_scoped_for_batch` (linie 4117–4152):
     `for name, info in self.data.get("characters", {}).items():`
     `for c_name, c_decl in self.data.get("declensions", {}).items():`
   - W `SeriesBible.get_character_gender` (linie 2980, 2991):
     `for k, v in chars.items():`
   - W `SeriesBible.infer_scene_cast_from_text` (linia 3226):
     `for k in chars.keys():`
   - W `detect_scene_social_context` (linie 1279–1281):
     `all_known_chars.update(character_registry)`
   - W `Translator._arbitrate_speaker_gender` (linia 2046):
     `for cname in self.character_registry.keys():`
   - W `Translator._prepare_batch_prompt` (linia 2373):
     `for name, details in self.character_registry.items():`
   - W `Verifier.verify_batch` (`verifier.py:230`):
     `for name, details in character_registry.items():`

W momencie gdy Wątek A dodaje nowo odkrytą postać, iterator Wątku B napotyka zmianę rozmiaru słownika, Wątek B ulega załamaniu z wyjątkiem `RuntimeError`, a pętla główna rejestruje awarię paczki:
```text
🔴 [Błąd Paczki]: dictionary changed size during iteration
```

---

## 🗺️ ROZDZIAŁ II: PROTOKÓŁ 5 WARSTW (SYSTEMOWE ROZWIĄZANIE ARCHITEKTONICZNE)

| Warstwa | Komponent | Zadanie i mechanizm naprawczy |
| :--- | :--- | :--- |
| **Warstwa 1** | `profiler.py` / Wejście Paczek | Izolacja stanu wejściowego – przekazywanie do wątków roboczych niemutowalnych migawek rejestru postaci i pamięci sceny zamiast żywych referencji. |
| **Warstwa 2** | `series_memory.py` (`SeriesBible`) | 1. Implementacja reentrantnej blokady wątkowej `threading.RLock()` w `SeriesBible`.<br>2. Wszystkie mutacje (`update_character_gender_from_audio`, `update_from_episode_profile`, `save`, `load`) chronione przez `with self._lock:`.<br>3. Wprowadzenie atomowych metod zrzutu migawkowego: `get_characters_snapshot()`, `get_declensions_snapshot()`, `get_glossary_snapshot()`.<br>4. Bezwzględna konwersja wszystkich wewnętrznych iteracji na kopie `list(...)` lub `dict(...)`. |
| **Warstwa 3** | `translator.py` & `verifier.py` | 1. Implementacja `get_character_registry_snapshot()` w klasie `Translator` chronionego przez `self.lock`.<br>2. Zamiana wszystkich pętli `for ... in character_registry.items()` na `list(character_registry.items())` lub zrzut migawki.<br>3. Zabezpieczenie `detect_third_person_mentions`, `detect_scene_social_context`, `_arbitrate_speaker_gender` oraz `_prepare_batch_prompt` przed bezpośrednim dostępem do żywego słownika.<br>4. Bezpieczna iteracja w `verifier.py` linia 230: `list(character_registry.items())`. |
| **Warstwa 4** | `translator.py` (Kolejka Paczek) & `avt_linter.py` | 1. Zabezpieczenie punktów synchronizacji checkpointu (`checkpoint_payload`): tworzenie płytkich kopii `dict(translated_results)`, `dict(self.current_episode_tokens)`.<br>2. W `avt_linter.py`: zabezpieczenie wszystkich iteracji po `character_registry` za pomocą `list(character_registry.items())`. |
| **Warstwa 5** | `test_system.py` (Test 148) | Utworzenie testu wielowątkowego `test_multithreaded_concurrency_and_dictionary_mutation_safety_guard()`, symulującego 16 równoległych wątków intensywnie zapisujących nowe postacie i jednocześnie odczytujących/iterujących po `SeriesBible` i `character_registry` pod maksymalnym obciążeniem CPU (0.00 PLN). |

---

## 📋 ROZDZIAŁ III: SZCZEGÓŁOWY ZAKRES MODYFIKACJI KODU

### 1. `series_memory.py`:
- W `SeriesBible.__init__`:
  ```python
  import threading
  self._lock = threading.RLock()
  ```
- W metodach mutujących (`update_character_gender_from_audio`, `update_from_episode_profile`, `assimilate_quality_gate_invariants`, `_sanitize_bible_integrity`):
  Otoczenie operacji zapisu blokadą `with self._lock:`.
- W metodach odczytujących i formatujących (`format_scoped_for_batch`, `get_character_gender`, `infer_scene_cast_from_text`, `format_for_prompt`, `is_female_pair`):
  Wykonywanie iteracji wyłącznie po `list(self.data.get("characters", {}).items())`, `list(self.data.get("declensions", {}).items())` itp. z atomowym pobraniem.

### 2. `translator.py`:
- Dodanie metody:
  ```python
  def get_character_registry_snapshot(self) -> Dict[str, str]:
      with self.lock:
          return dict(self.character_registry)
  ```
- W `detect_third_person_mentions`:
  ```python
  if character_registry:
      for full_name, details in list(character_registry.items()):
  if series_bible and hasattr(series_bible, "data"):
      bible_chars = series_bible.data.get("characters", {})
      for b_name, b_info in list(bible_chars.items()):
  ```
- W `detect_scene_social_context`:
  ```python
  if character_registry:
      all_known_chars.update(dict(character_registry))
  if series_bible and hasattr(series_bible, "data") and "characters" in series_bible.data:
      for k, v in list(series_bible.data["characters"].items()):
  ```
- W `_arbitrate_speaker_gender`:
  ```python
  for cname in list(self.character_registry.keys()):
  ```
- W `_prepare_batch_prompt`:
  ```python
  for name, details in list(self.character_registry.items()):
  ```
- W `_resolve_line_addressee`:
  ```python
  if self.character_registry:
      canonical_entities.update(list(self.character_registry.keys()))
  if getattr(self, "series_bible", None) and hasattr(self.series_bible, "data"):
      canonical_entities.update(list(self.series_bible.data.get("characters", {}).keys()))
  ```
- W `checkpoint_payload`:
  Płytkie kopie `dict(translated_results)`, `dict(self.current_episode_tokens)`.

### 3. `verifier.py`:
- W linii 230:
  ```python
  for name, details in list(character_registry.items()):
  ```

### 4. `avt_linter.py`:
- W liniach 3887, 4019, 4051, 6066:
  Użycie `list(character_registry.items())` oraz `list(character_registry.keys())`.

### 5. `test_system.py`:
- Implementacja **Testu 148**:
  `test_multithreaded_concurrency_and_dictionary_mutation_safety_guard()`
  Uruchomienie 16 wątków w `concurrent.futures.ThreadPoolExecutor`, gdzie połowa wątków w pętli 100 iteracji rejestruje losowe nowe postacie i aktualizuje audio płci w `SeriesBible` i `character_registry`, a druga połowa równolegle wywołuje `format_scoped_for_batch`, `detect_third_person_mentions`, `get_character_gender` i `detect_scene_social_context`.
  Asercja: 0 wyjątków `RuntimeError`, 100% spójności danych, koszt 0.00 PLN.

---

## 🛡️ PROTOKÓŁ WERYFIKACJI I KRYTERIA SUKCESU
1. Brak jakichkolwiek modyfikacji kodu przed wyraźną zgodą użytkownika (Zasada 4).
2. Wszystkie testy regresyjne (147 dotychczasowych + Test 148) kończą się statusem **148/148 PASSED (100%)**.
3. Całkowite wyeliminowanie podatności współbieżności w całym cyklu życia tłumacza.
4. Zerowy koszt komponentów offline (0.00 PLN).
