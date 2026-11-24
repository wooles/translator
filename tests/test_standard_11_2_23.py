"""
Zestaw testów regresyjnych dla Standardu 11.2.23:
1. test_def01_glossary_lock_preserves_inflected_multiword_term_with_newline (DEF-01)
2. test_def03_speaker_change_lowercase_gets_calibrated_p90_priority_in_f2 (DEF-03)
3. test_def02_scene_cut_4s_gap_resets_addressee_propagation (DEF-02)
4. test_obs02_prompt_character_registry_deduplicates_generic_aliases (OBS-02)
5. test_obs01_ram_only_parent_gender_reconciliation_without_disk_write (OBS-01)
"""

import json
import pytest
import pysubs2

from series_memory import SeriesBible
from scene_discourse import SpeakerTurn, resolve_all_speaker_turns, process_scene_discourse
from translator import MultimodalTranslator, enforce_locked_glossary_terms


@pytest.mark.unit
def test_def01_glossary_lock_preserves_inflected_multiword_term_with_newline():
    """
    DEF-01: Weryfikuje, że enforce_locked_glossary_terms zachowuje poprawną odmianę
    wielowyrazowego terminu ze znakiem łamania wiersza \\N z Fazy 2 i nie cofa jej do Fazy 1.
    Test nietautologiczny sprawdza również, że przy obcej podmianie termin kanoniczny jest przywracany.
    """
    glossary = [
        {
            "term_en": "Seven Grand Sorcerers",
            "translation_pl": "Siedmiu Wielkich Czarodziejów"
        }
    ]
    orig_en = "Not even rivaling the Seven Grand Sorcerers,"
    phase1_pl = "Nie dorównując Siedmiu Wielkich Czarodziejów,"
    phase2_candidate = "Nie dorównując Siedmiu\\NWielkim Czarodziejom,"

    # Asercja 1: wynik zachowuje formę F2 ("Wielkim Czarodziejom"), nie cofa jej do F1
    result1 = enforce_locked_glossary_terms(
        en_text=orig_en,
        candidate_pl=phase2_candidate,
        glossary_entries=glossary,
        phase1_pl=phase1_pl
    )
    assert "Wielkim Czarodziejom" in result1
    assert "Siedmiu\\NWielkim Czarodziejom" in result1
    assert result1 == phase2_candidate
    assert result1 != phase1_pl

    # Asercja 2 (kontrola nietautologiczna): gdy F2 całkowicie podmieni termin na obcy, funkcja reaguje i egzekwuje termin kanoniczny
    phase2_alien = "Nie dorównując Potężnym Magom,"
    result2 = enforce_locked_glossary_terms(
        en_text=orig_en,
        candidate_pl=phase2_alien,
        glossary_entries=glossary,
        phase1_pl=phase1_pl
    )
    assert result2 == phase1_pl


@pytest.mark.unit
def test_def03_speaker_change_lowercase_gets_calibrated_p90_priority_in_f2():
    """
    DEF-03: Kwestia nowego mówcy rozpoczynająca się małą literą otrzymuje skalibrowany priorytet P90
    bieżącej paczki, kwalifikując się do selektywnej Fazy 2 przy zachowaniu budżetu CoT LOW (2048).
    """
    translator = MultimodalTranslator(
        api_key="mock_k0",
        model="gemini-4-hydrogen",
        enable_verifier=True
    )

    # Budowa 30 linii o zróżnicowanym bazowym ryzyku
    pass1_items = []
    for i in range(28):
        pass1_items.append({
            "id": i,
            "speaker": "Postac_A",
            "actor": "Postac_A",
            "en": f"Standard test sentence {i} with some dialogue content.",
            "pl": f"Zwykłe zdanie testowe {i}.",
            "calque_score": 0.35 if (i % 3 == 0) else 0.0,
            "cps_warning": True if (i % 4 == 0) else False,
            "canonical_glossary_term": "Termin" if (i % 5 == 0) else None,
            "notes": ""
        })

    # Linia X (indeks 28): zmiana mówcy (Postac_A -> Postac_B), mała litera po wielokropku
    pass1_items.append({
        "id": 28,
        "speaker": "Postac_B",
        "actor": "Postac_B",
        "en": "Get some sleep over there.",
        "pl": "prześpij się tam trochę.",
        "notes": ""
    })

    # Linia Y (indeks 29): ten sam mówca (Postac_B -> Postac_B), mała litera po wielokropku
    pass1_items.append({
        "id": 29,
        "speaker": "Postac_B",
        "actor": "Postac_B",
        "en": "We managed to make it.",
        "pl": "udało się zdążyć.",
        "notes": ""
    })

    # Linia 27 miała wielokropek na końcu
    pass1_items[27]["pl"] = "To... absurd..."

    selected = translator._select_hydrogen_phase2_candidates(
        pass1_items=pass1_items,
        total_batches=9,
        episode_line_cap=115
    )

    # Linia X (nowy mówca) musi znaleźć się w wybranych kandydatach F2
    selected_pls = [it["pl"] for it in selected]
    assert "prześpij się tam trochę." in selected_pls

    # Linia X ma dopisaną notatkę korygującą
    item_x = next(it for it in selected if it["pl"] == "prześpij się tam trochę.")
    assert "[Korekta wielkiej litery na wejściu nowego mówcy]" in item_x.get("notes", "")

    # Linia Y (ten sam mówca) nie otrzymuje sztucznego bonusu i przy braku innych sygnałów nie wypiera linii o wyższym ryzyku
    assert "udało się zdążyć." not in selected_pls

    # Budżet CoT weryfikatora pozostaje ekonomiczny (LOW 2048)
    assert translator.verifier.calculate_effective_budget(selected) == 2048


@pytest.mark.unit
def test_def02_scene_cut_4s_gap_resets_addressee_propagation(tmp_path):
    """
    DEF-02: Pauza międzyscenowa (>= 3500 ms) lub cięcie sceny FFmpeg (gap >= 2500 ms)
    resetuje dziedziczenie adresata (target_speaker = UNSPECIFIED, target_gender != FEMALE).
    Wymiana wewnątrz sceny (< 2500 ms) zachowuje normalne łączenie z poprzednim mówcą.
    """
    sm = SeriesBible(anime_title="Seria Testowa", storage_dir=tmp_path)
    sm.data["characters"] = {
        "Postac_Zenska": {
            "gender": "FEMALE",
            "grammatical_gender": "FEMININE",
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["Postac_Zenska"],
        },
        "Postac_Meska_1": {
            "gender": "MALE",
            "grammatical_gender": "MASCULINE",
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["Postac_Meska_1"],
        },
        "Postac_Meska_2": {
            "gender": "MALE",
            "grammatical_gender": "MASCULINE",
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["Postac_Meska_2"],
        },
    }
    sm._rebuild_actor_aliases_index()

    # Tura 1: Postac_Zenska (FEMALE) kończy na 643190 ms
    t1 = SpeakerTurn(
        speaker="Postac_Zenska",
        events=[pysubs2.SSAEvent(start=640000, end=643190, text="Do zobaczenia jutro.", name="Postac_Zenska")]
    )
    # Tura 2: Postac_Meska_1 (MALE) mówi na 647190 ms (gap = 4000 ms, bez wołacza)
    t2 = SpeakerTurn(
        speaker="Postac_Meska_1",
        events=[pysubs2.SSAEvent(start=647190, end=652730, text="You should know this better than anyone!", name="Postac_Meska_1")]
    )
    # Tura 3: Postac_Meska_2 (MALE) odpowiada po 640 ms (start = 653370 ms)
    t3 = SpeakerTurn(
        speaker="Postac_Meska_2",
        events=[pysubs2.SSAEvent(start=653370, end=656000, text="I understand.", name="Postac_Meska_2")]
    )

    scene_cuts = [645145]
    resolve_all_speaker_turns([t1, t2, t3], series_bible=sm, scene_boundaries=scene_cuts)

    # Asercja 1: Tura 2 nie dziedziczy Postac_Zenska jako adresata
    assert t2.target_speaker in (None, "UNSPECIFIED")
    assert t2.target_actor in (None, "UNSPECIFIED")
    assert t2.target_gender != "FEMALE"

    # Asercja 2 (kontrola zachowawcza): Tura 3 (pauza 640 ms w obrębie tej samej sceny) łączy się z Postac_Meska_1 (MALE)
    assert t3.target_speaker == "Postac_Meska_1"
    assert t3.target_gender == "MALE"


@pytest.mark.unit
def test_obs02_prompt_character_registry_deduplicates_generic_aliases():
    """
    OBS-02: Sekcja ZNANE POSTACIE W ODCINKU deduplikuje redundantne aliasy P2
    o generycznym opisie ("Postać epizodyczna / tło"), gdy istnieje bogatszy wpis kanoniczny.
    """
    translator = MultimodalTranslator(
        api_key="mock_k0",
        model="gemini-4-hydrogen",
        enable_verifier=False
    )
    translator.character_registry = {
        "Alfa": "Postać epizodyczna / tło",
        "Alfa Kowalska": {
            "description": "kobieta (Bohaterka)",
            "aliases": ["Alfa", "Alfa Kowalska"],
            "has_verified_gender": True,
            "priority": "P0"
        },
        "Beta": "postać (Postać)"
    }

    dummy_event = pysubs2.SSAEvent(start=1000, end=2000, text="Kwestia testowa.", name="Alfa Kowalska")
    prompt = translator._prepare_batch_prompt(
        batch_events=[(0, dummy_event, "Test line.", "Alfa Kowalska")],
        history_context=[]
    )

    # Asercja: dokładnie 1 wpis dla Alfa Kowalska, 0 wpisów dla generycznego aliasu Alfa, zachowany unikalny wpis Beta
    assert "• Alfa Kowalska: kobieta (Bohaterka)" in prompt
    assert "• Alfa: Postać epizodyczna / tło" not in prompt
    assert "• Alfa:" not in prompt
    assert "• Beta: postać (Postać)" in prompt or "• Beta:" in prompt


@pytest.mark.unit
def test_obs01_ram_only_parent_gender_reconciliation_without_disk_write(tmp_path):
    """
    OBS-01: Uzgadnia płeć rodzica na podstawie relacji (np. 'Matko' -> FEMALE) w RAM
    bez dokonywania jakichkolwiek modyfikacji pliku bazy wiedzy na dysku (0 B diffu na dysku).
    """
    bible_path = tmp_path / "test_series_bible.json"
    bible_content = {
        "anime_title": "Test Series",
        "characters": {
            "Postac_Matka": {
                "name": "Postac_Matka",
                "gender": "MALE",
                "grammatical_gender": "MASCULINE",
                "description": "postać (Postać)",
                "confidence": 0.95,
                "priority": "P0"
            },
            "Postac_Ojciec": {
                "name": "Postac_Ojciec",
                "gender": "FEMALE",
                "grammatical_gender": "FEMININE",
                "description": "postać (Postać)",
                "confidence": 0.95,
                "priority": "P0"
            }
        },
        "relations": {
            "Protagonista -> Postac_Matka": "Zwrot: 'Matko' (syn - matka) [MĘŻCZYZNA (Adresat) - W 2. os. lp. 'ty' wymóg form męskich: byłeś / zrobiłeś / jesteś pewien]",
            "Protagonista -> Postac_Ojciec": "Zwrot: 'Ojcze' (córka - ojciec) [KOBIETA (Adresat) - W 2. os. lp. 'ty' wymóg form żeńskich: byłaś / zrobiłaś / jesteś pewna]"
        }
    }
    bible_path.write_text(json.dumps(bible_content, indent=2, ensure_ascii=False), encoding="utf-8")
    raw_before = bible_path.read_bytes()

    bible = SeriesBible(bible_path=bible_path, storage_dir=tmp_path)

    # Asercja 1 (RAM): Postac_Matka ma FEMALE/FEMININE, Postac_Ojciec ma MALE/MASCULINE, tagi w relations zaktualizowane
    char_matka = bible.data["characters"]["Postac_Matka"]
    assert char_matka["gender"] == "FEMALE"
    assert char_matka["grammatical_gender"] == "FEMININE"

    char_ojciec = bible.data["characters"]["Postac_Ojciec"]
    assert char_ojciec["gender"] == "MALE"
    assert char_ojciec["grammatical_gender"] == "MASCULINE"

    rel_matka = bible.data["relations"]["Protagonista -> Postac_Matka"]
    rel_matka_desc = rel_matka if isinstance(rel_matka, str) else rel_matka.get("description", "")
    assert "[KOBIETA (Adresat)" in rel_matka_desc
    assert "[MĘŻCZYZNA (Adresat)" not in rel_matka_desc

    rel_ojciec = bible.data["relations"]["Protagonista -> Postac_Ojciec"]
    rel_ojciec_desc = rel_ojciec if isinstance(rel_ojciec, str) else rel_ojciec.get("description", "")
    assert "[MĘŻCZYZNA (Adresat)" in rel_ojciec_desc
    assert "[KOBIETA (Adresat)" not in rel_ojciec_desc

    # Asercja 2 (RAM-only / brak mutacji dysku): dokładne 0 B zmiany na dysku
    assert bible_path.read_bytes() == raw_before
