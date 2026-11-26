"""
Zestaw nienaruszalnych, nietautologicznych testów regresyjnych dla Standardu 12.1.0:
- A-1: Strażnik spójności par międzyliniowych w Fazie 2 (split-sentence & lexical echo)
- A-3: Kierunkowy rejestr T-V per para (Mówca -> Adresat) z rozwiązywaniem aliasów
- A-4: Epizodyczna blokada tytułów arystokratycznych/stanowych w RAM (bez zapisu do JSON na dysku)
- A-5: Ekspansja skrótów liczbowych mln / mld / tys. w dialogu mówionym
"""

import json
import httpx
import pytest
import pysubs2
from google import genai
from google.genai import types as genai_types

from profiler import EpisodeProfile, CharacterRelationship
from series_memory import SeriesBible
from translator import (
    MultimodalTranslator,
    enforce_locked_glossary_terms,
    _is_split_sentence_pair,
    _is_lexical_echo_pair,
    _guard_phase2_split_pair_integrity,
    _resolve_tv_address_form,
    _extract_episode_honorific_title_locks,
    _expand_spoken_numeric_abbreviations,
    sanitize_sub_text,
)


def _make_mock_genai_client(handler) -> genai.Client:
    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    c = genai.Client(api_key="mock_k0", http_options=genai_types.HttpOptions(httpx_client=http_client))
    if getattr(c._api_client, "_httpx_client", None) is not http_client:
        c._api_client._httpx_client = http_client
    return c


class _DummyPbar:
    def write(self, msg: str) -> None:
        pass

    def set_postfix_str(self, s: str) -> None:
        pass

    def refresh(self) -> None:
        pass


def _make_prod_pass1_item(
    idx: int,
    en: str,
    pl: str,
    speaker_name: str = "Agent_A",
    start_ms: int = 1000,
    end_ms: int = 3000,
    calque_score: float = 0.0,
    is_sign: bool = False,
    is_song: bool = False,
    notes: str = "",
) -> dict:
    ev = pysubs2.SSAEvent(start=start_ms, end=end_ms, text=en, name=speaker_name, style="Default")
    return {
        "id": idx,
        "orig_idx": idx - 1,
        "event": ev,
        "style": "Default",
        "is_thought": False,
        "is_internal_monologue": False,
        "is_missing_translation": False,
        "is_blind_draft": False,
        "calque_score": calque_score,
        "duration_s": max(0.2, (end_ms - start_ms) / 1000.0),
        "time_gap_s": 0.0,
        "time_gap_ms": 0,
        "cps": 12.0,
        "start_ms": start_ms,
        "end_ms": end_ms,
        "en": en,
        "pl": pl,
        "prev_line_f1": "",
        "prev_line_en": "",
        "speaker_name": speaker_name,
        "speaker_gender": "mężczyzna",
        "speaker_confidence": 1.0,
        "addressee": None,
        "target_gender": None,
        "target_confidence": 0.0,
        "addressee_label": "",
        "telemetry_tag": f"[Mówca: {speaker_name} (MASCULINE)]",
        "declension_paradigms": [],
        "semiotic_layer": "",
        "screen_region": None,
        "visual_typesetting": None,
        "speaker_voice": "",
        "prosody": "",
        "audio_jp": "",
        "audio_alert": "",
        "ambiguity_note": "",
        "canonical_glossary_term": "",
        "relation_tag": "",
        "pragmatic_register": "",
        "visual_subtext": "",
        "literal_meaning": "",
        "cps_warning": "",
        "condensation_directive": "",
        "notes": notes,
        "third_person_subject": "",
        "plural_group_gender": "AMBIGUOUS",
        "you_group_gender": "AMBIGUOUS",
        "semantic_anchor": "",
        "is_sign": is_sign,
        "visual_type": "Napis ekranowy" if is_sign else "Dialog",
        "visual_details": "",
        "is_song": is_song,
        "active_scene_tone": "",
    }


@pytest.mark.unit
def test_a1_f2_selector_pairs_split_sentence_continuation_and_adds_notes():
    """
    A-1 (Warstwa 1): Gdy #10 jest częścią zdania rozbitego na #10 i #11 tego samego mówcy,
    selekcja #10 automatycznie paruje #11 w ramach sufitu <= 50% (<= 10 linii na 20)
    i dopisuje znaczniki spójności w notes obu elementów.
    """
    tr = MultimodalTranslator(api_key="mock_k0", model="gemini-4-hydrogen", enable_verifier=True)

    pass1_items = []
    for i in range(1, 21):
        st = i * 4000
        en_end = st + 2000
        if i == 10:
            pass1_items.append(_make_prod_pass1_item(
                idx=10,
                en="I want you to head to the outpost at once",
                pl="Macie natychmiast ruszyć na posterunek",
                speaker_name="Oficer_B",
                start_ms=40000,
                end_ms=42500,
                calque_score=0.75,
            ))
        elif i == 11:
            pass1_items.append(_make_prod_pass1_item(
                idx=11,
                en="and inspect the anomaly.",
                pl="i zbadać tę anomalię.",
                speaker_name="Oficer_B",
                start_ms=42500,
                end_ms=44500,
                calque_score=0.0,
            ))
        else:
            pass1_items.append(_make_prod_pass1_item(
                idx=i,
                en=f"Ordinary tactical observation sentence number {i}.",
                pl=f"Zwykła obserwacja taktyczna numer {i}.",
                speaker_name="Agent_A",
                start_ms=st,
                end_ms=en_end,
                calque_score=0.55 if i <= 9 else 0.0,
            ))

    assert _is_split_sentence_pair(pass1_items[9], pass1_items[10]) is True

    selected = tr._select_hydrogen_phase2_candidates(pass1_items, total_batches=6, episode_line_cap=115)
    selected_ids = [it["id"] for it in selected]

    assert 10 in selected_ids
    assert 11 in selected_ids
    assert len(selected) <= 10

    it10 = next(it for it in selected if it["id"] == 10)
    it11 = next(it for it in selected if it["id"] == 11)
    assert "[Para spójności z #11" in it10["notes"]
    assert "[Para spójności z #10" in it11["notes"]


@pytest.mark.unit
def test_a1_f2_selector_pairs_short_lexical_echo_across_speakers():
    """
    A-1 (Warstwa 1): Krótkie echo między mówcami (#6 powtarzające rdzeń z #5 w oknie <= 1500 ms)
    zostaje automatycznie wciągnięte do puli F2 razem z linią źródłową #5.
    """
    tr = MultimodalTranslator(api_key="mock_k0", model="gemini-4-hydrogen", enable_verifier=True)

    pass1_items = []
    for i in range(1, 21):
        st = i * 4000
        en_end = st + 2000
        if i == 5:
            pass1_items.append(_make_prod_pass1_item(
                idx=5,
                en="Should we call it an octodragon?",
                pl="Nazwiemy to krabosmokiem?",
                speaker_name="Agent_A",
                start_ms=20000,
                end_ms=22200,
                calque_score=0.72,
            ))
        elif i == 6:
            pass1_items.append(_make_prod_pass1_item(
                idx=6,
                en="Octodragon?",
                pl="Krabosmokiem?",
                speaker_name="Agent_B",
                start_ms=22200,
                end_ms=23500,
                calque_score=0.0,
            ))
        else:
            pass1_items.append(_make_prod_pass1_item(
                idx=i,
                en=f"Background briefing note number {i}.",
                pl=f"Notatka operacyjna numer {i}.",
                speaker_name="Agent_A",
                start_ms=st,
                end_ms=en_end,
                calque_score=0.50 if i <= 10 else 0.0,
            ))

    assert _is_lexical_echo_pair(pass1_items[4], pass1_items[5]) is True

    selected = tr._select_hydrogen_phase2_candidates(pass1_items, total_batches=6, episode_line_cap=115)
    selected_ids = [it["id"] for it in selected]

    assert 5 in selected_ids
    assert 6 in selected_ids
    assert len(selected) <= 10


@pytest.mark.unit
def test_a1_post_f2_guard_prevents_broken_infinitive_or_period_when_next_unverified():
    """
    A-1 (Warstwa 2): Deterministyczny strażnik _guard_phase2_split_pair_integrity wycofuje linię #10
    do spójnego F1 przy konflikcie modalnym z niezweryfikowanym bezokolicznikiem w #11,
    a w przypadku samej dopisanej kropki bez konfliktu modalnego usuwa wyłącznie końcową kropkę.
    """
    # Przypadek 1: Konflikt modalny (F1: "Macie ... ruszyć" + #11 "i zbadać ...", F2: "Ruszajcie ... .")
    it10_modal = _make_prod_pass1_item(
        idx=10,
        en="I want you to head to the outpost at once",
        pl="Macie natychmiast ruszyć na posterunek",
        speaker_name="Oficer_B",
        start_ms=10000,
        end_ms=12000,
    )
    it11_inf = _make_prod_pass1_item(
        idx=11,
        en="and inspect the anomaly.",
        pl="i zbadać tę anomalię.",
        speaker_name="Oficer_B",
        start_ms=12000,
        end_ms=14000,
    )
    refined_dict_1 = {10: "Ruszajcie natychmiast na posterunek.", 11: sanitize_sub_text(it11_inf["pl"])}
    _guard_phase2_split_pair_integrity([it10_modal, it11_inf], refined_dict_1, verified_ids={10})
    assert refined_dict_1[10] == "Macie natychmiast ruszyć na posterunek"

    # Przypadek 2: Bez konfliktu modalnego — usunięcie wyłącznie błędnie dodanej kropki
    it20_nomodal = _make_prod_pass1_item(
        idx=20,
        en="We found the hidden courier archive",
        pl="Znaleźliśmy ukryte archiwum kuriera",
        speaker_name="Agent_A",
        start_ms=20000,
        end_ms=22000,
    )
    it21_cont = _make_prod_pass1_item(
        idx=21,
        en="inside the eastern watchtower.",
        pl="wewnątrz wschodniej strażnicy.",
        speaker_name="Agent_A",
        start_ms=22000,
        end_ms=24000,
    )
    refined_dict_2 = {20: "Odkryliśmy tajne archiwum kuriera.", 21: sanitize_sub_text(it21_cont["pl"])}
    _guard_phase2_split_pair_integrity([it20_nomodal, it21_cont], refined_dict_2, verified_ids={20})
    assert refined_dict_2[20] == "Odkryliśmy tajne archiwum kuriera"


@pytest.mark.unit
def test_a3_tv_resolver_uses_aliases_and_preserves_asymmetric_direction(tmp_path):
    """
    A-3: Kierunkowy resolver T-V rozwiązuje aliasy z SeriesBible i bezwzględnie izoluje kierunek:
    Nowak -> Anna zwraca formę formalną ('pan/pani'), Anna -> Nowak zwraca 'na ty',
    a brak relacji (lub obca postać) zwraca None.
    """
    sb = SeriesBible(anime_title="Seria Alfa", storage_dir=tmp_path)
    sb.data["characters"] = {
        "Kowalska Anna": {
            "name": "Kowalska Anna",
            "gender": "FEMALE",
            "grammatical_gender": "FEMININE",
            "confidence": 0.95,
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["Anna", "Kowalska", "Kowalska Anna"],
            "description": "kobieta (postać)",
            "entity_category": "ANTHROPONYM",
        },
        "Nowak": {
            "name": "Nowak",
            "gender": "MALE",
            "grammatical_gender": "MASCULINE",
            "confidence": 0.95,
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["Nowak"],
            "description": "mężczyzna (postać)",
            "entity_category": "ANTHROPONYM",
        },
    }
    sb.data["relations"] = {
        "Anna -> Nowak": "Zwrot: 'na ty / Nowak' (współpracownicy) [MĘŻCZYZNA (Adresat) - W 2. os. lp. 'ty' wymóg form męskich]",
        "Nowak -> Kowalska Anna": "Zwrot: 'pani Kowalska / pani Anno' (współpracownicy) [KOBIETA (Adresat) - W 2. os. lp. 'ty' wymóg form żeńskich]",
    }

    res_formal = _resolve_tv_address_form("Nowak", "Anna", sb)
    assert res_formal is not None and res_formal.startswith("pan/pani")
    assert "pani Kowalska" in res_formal

    res_informal = _resolve_tv_address_form("Anna", "Nowak", sb)
    assert res_informal is not None and res_informal.startswith("na ty")

    assert _resolve_tv_address_form("Nowak", "Nieznajomy_Z", sb) is None
    assert _resolve_tv_address_form("Nowak", "Grupa Mężczyzn (Mężczyźni)", sb) is None


@pytest.mark.unit
def test_a3_tv_hint_injected_into_f1_prompt_and_f2_notes_without_cot_escalation(tmp_path, monkeypatch):
    """
    A-3: Dyrektywa Rejestr T-V jest wstrzykiwana do promptu F1 (_prepare_batch_prompt) oraz
    do notes w _process_phase1_only bez eskalacji CoT (budżet pozostaje 2048 LOW).
    """
    monkeypatch.setattr("time.sleep", lambda s: None)
    monkeypatch.setattr("client_factory.global_rate_limiter.acquire", lambda: None)
    monkeypatch.setattr("context_cache.ContextCacheManager.get_or_create_cache", lambda *a, **kw: "__IMPLICIT_CACHE_95__")

    sb = SeriesBible(anime_title="Seria Alfa", storage_dir=tmp_path)
    sb.data["characters"] = {
        "Kowalska Anna": {
            "name": "Kowalska Anna",
            "gender": "FEMALE",
            "grammatical_gender": "FEMININE",
            "confidence": 0.95,
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["Anna", "Kowalska", "Kowalska Anna"],
            "description": "kobieta (postać)",
            "entity_category": "ANTHROPONYM",
        },
        "Nowak": {
            "name": "Nowak",
            "gender": "MALE",
            "grammatical_gender": "MASCULINE",
            "confidence": 0.95,
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["Nowak"],
            "description": "mężczyzna (postać)",
            "entity_category": "ANTHROPONYM",
        },
    }
    sb.data["relations"] = {
        "Nowak -> Kowalska Anna": "Zwrot: 'pani Kowalska / pani Anno' (współpracownicy)",
        "Anna -> Nowak": "Zwrot: 'na ty / Nowak' (współpracownicy)",
    }

    ev1 = pysubs2.SSAEvent(start=1000, end=2500, name="Anna", text="The report is ready.")
    ev2 = pysubs2.SSAEvent(start=2600, end=4200, name="Nowak", text="Do you have any notes on it?")
    batch_events = [(0, ev1, ev1.text, ""), (1, ev2, ev2.text, "")]

    def handler(request: httpx.Request) -> httpx.Response:
        body = {
            "scene_diagnosis": None,
            "translations": [
                {"id": 1, "polish_text": "Raport jest gotowy.", "speaker_name": "Anna"},
                {"id": 2, "polish_text": "Sprawdziłaś te dane?", "speaker_name": "Nowak"},
            ],
            "characters_identified": [],
        }
        return httpx.Response(
            200,
            json={
                "candidates": [{"content": {"role": "model", "parts": [{"text": json.dumps(body)}]}}],
                "usageMetadata": {"promptTokenCount": 800, "cachedContentTokenCount": 0, "candidatesTokenCount": 80, "thoughtsTokenCount": 0},
            },
        )

    tr = MultimodalTranslator(api_key="mock_k0", model="gemini-4-hydrogen", enable_verifier=True)
    mock_c = _make_mock_genai_client(handler)
    tr.client_pool_f1.clients = [mock_c]
    tr.client_pool.clients = [mock_c]
    tr.client = mock_c
    tr.series_bible = sb
    tr.character_registry = {
        "Nowak": "mężczyzna (postać)",
        "Kowalska Anna": "kobieta (postać)",
    }

    prompt_f1 = tr._prepare_batch_prompt(batch_events=batch_events, history_context=[])
    assert "Rejestr T-V (Nowak -> Anna): pan/pani (pani Kowalska / pani Anno)" in prompt_f1

    p1_data = tr._process_phase1_only(
        b_idx=0,
        batch=batch_events,
        untranslated_in_batch=batch_events,
        batches=[batch_events],
        video_path=None,
        is_ass=True,
        anime_meta=None,
        episode_profile=None,
        anime_context_str="",
        episode_profile_str="",
        series_bible_str="",
        manga_canon_str="",
        combined_glossary={},
        all_user_rules=[],
        history=[],
        pbar=_DummyPbar(),
    )
    it2 = p1_data["pass1_items"][1]
    assert "[Zwrot T-V: pan/pani (pani Kowalska / pani Anno)]" in it2["notes"]
    assert not it2["audio_alert"]
    assert not it2["ambiguity_note"]
    assert tr.verifier.calculate_effective_budget(p1_data["pass1_items"]) == 2048


@pytest.mark.unit
def test_a4_aristocratic_title_lock_unifies_repeated_lady_lord_in_ram_only(tmp_path):
    """
    A-4: Powtarzający się w odcinku tytuł arystokratyczny ('Lady Aurelia' >= 2 razy) generuje
    wpis RAM-only {'Lady Aurelia': 'lady Aurelia'} bez zapisu na dysk i bez nadpisywania Kanonu/Biblii,
    a enforce_locked_glossary_terms broni spójności 'lady Aurelia' przed dryfem na 'panna Aurelia'.
    """
    events = [
        pysubs2.SSAEvent(start=1000, end=2500, name="Agent_A", text="The courier and Lady Aurelia departed at dawn."),
        pysubs2.SSAEvent(start=3000, end=4500, name="Oficer_B", text="Poor Lady Aurelia had no idea about the ambush."),
        pysubs2.SSAEvent(start=5000, end=6500, name="Agent_A", text="Please look after Lady Aurelia tonight."),
        pysubs2.SSAEvent(start=7000, end=8000, name="Agent_A", text="Lord Please do not wait here."),
    ]
    locks = _extract_episode_honorific_title_locks(events, existing_glossary={})
    assert locks == {"Lady Aurelia": "lady Aurelia"}
    assert "Lord Please" not in locks

    # Szacunek hierarchii: istniejący wpis z Kanonu Mangi / SeriesBible nie jest nadpisywany
    canon_glossary = {"Lady Aurelia": "pani Aurelia"}
    locks_with_canon = _extract_episode_honorific_title_locks(events, existing_glossary=canon_glossary)
    assert "Lady Aurelia" not in locks_with_canon

    # Weryfikacja twardej ochrony przed dryfem w F2 przy pomocy enforce_locked_glossary_terms
    gloss_entries = [{"term_en": "Lady Aurelia", "translation_pl": locks["Lady Aurelia"]}]
    restored = enforce_locked_glossary_terms(
        en_text="Please look after Lady Aurelia tonight.",
        candidate_pl="Zaopiekuj się dzisiejszej nocy panną Aurelią.",
        glossary_entries=gloss_entries,
        phase1_pl="Zaopiekuj się dzisiejszej nocy lady Aurelią.",
    )
    assert "lady Aurelią" in restored
    assert "panną Aurelią" not in restored


@pytest.mark.unit
def test_a5_spoken_numeric_abbreviation_expansion_preserves_signs_and_ass_tags():
    """
    A-5: _expand_spoken_numeric_abbreviations rozwija mln / mld / tys. w dialogu z poprawną
    polską fleksją i interpunkcją, chroniąc tagi ASS {...} oraz napisy ekranowe (is_sign=True).
    """
    assert _expand_spoken_numeric_abbreviations("Pożyczę 500 mln!", is_sign=False) == "Pożyczę 500 milionów!"
    assert _expand_spoken_numeric_abbreviations("Mamy 2 mln na koncie.", is_sign=False) == "Mamy 2 miliony na koncie."
    assert _expand_spoken_numeric_abbreviations("To 1 mln jenów.", is_sign=False) == "To 1 milion jenów."
    assert _expand_spoken_numeric_abbreviations("Kosztuje 1,5 mln.", is_sign=False) == "Kosztuje 1,5 miliona."
    assert _expand_spoken_numeric_abbreviations(r"{\i1}Zostało 5 tys. metrów.{\i0}", is_sign=False) == r"{\i1}Zostało 5 tysięcy metrów.{\i0}"
    assert _expand_spoken_numeric_abbreviations("Budżet to 3 mld.", is_sign=False) == "Budżet to 3 miliardy."

    # Napis ekranowy (is_sign=True) pozostaje nienaruszony
    assert _expand_spoken_numeric_abbreviations("500 mln", is_sign=True) == "500 mln"


@pytest.mark.unit
def test_12_1_0_offline_replay_on_12_0_0_benchmark_patterns(tmp_path):
    """
    Zintegrowany replay offline na wzorcach zjawisk wykrytych w benchmarku 12.0.0
    (nazwy w 100% syntetyczne Z1): A-1 parowanie, A-3 T-V, A-4 lock tytułów, A-5 ekspansja liczb.
    """
    sb = SeriesBible(anime_title="Seria Alfa", storage_dir=tmp_path)
    sb.data["characters"] = {
        "Dama Celina": {
            "name": "Dama Celina",
            "gender": "FEMALE",
            "grammatical_gender": "FEMININE",
            "confidence": 0.95,
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["Celina", "Dama Celina"],
            "description": "kobieta (postać)",
            "entity_category": "ANTHROPONYM",
        },
        "Oficer_B": {
            "name": "Oficer_B",
            "gender": "MALE",
            "grammatical_gender": "MASCULINE",
            "confidence": 0.95,
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["Oficer_B"],
            "description": "mężczyzna (postać)",
            "entity_category": "ANTHROPONYM",
        },
    }
    sb.data["relations"] = {
        "Oficer_B -> Dama Celina": "Zwrot: 'pani Celino / pani Damo' (współpracownicy)",
        "Celina -> Oficer_B": "Zwrot: 'na ty / Oficer_B' (współpracownicy)",
    }

    tr = MultimodalTranslator(api_key="mock_k0", model="gemini-4-hydrogen", enable_verifier=True)
    tr.series_bible = sb

    # A-1: rozbite zdanie i echo + A-5: skrót liczbowy po F2
    items = [
        _make_prod_pass1_item(i, f"Control line {i} stays neutral here.", f"Linia kontrolna {i}.")
        for i in range(1, 13)
    ]
    items.append(_make_prod_pass1_item(
        13, "I want you to head to the vault right now", "Macie natychmiast ruszyć do skarbca",
        speaker_name="Oficer_B", start_ms=52000, end_ms=54000, calque_score=0.75,
    ))
    items.append(_make_prod_pass1_item(
        14, "and verify every crate.", "i sprawdzić każdą skrzynię.",
        speaker_name="Oficer_B", start_ms=54000, end_ms=56000, calque_score=0.0,
    ))
    items.append(_make_prod_pass1_item(
        15, "Should we call it an octodragon?", "Nazwiemy to krabosmokiem?",
        speaker_name="Agent_A", start_ms=57000, end_ms=59000, calque_score=0.72,
    ))
    items.append(_make_prod_pass1_item(
        16, "Octodragon?", "Krabosmokiem?",
        speaker_name="Agent_B", start_ms=59000, end_ms=60500, calque_score=0.0,
    ))
    selected = tr._select_hydrogen_phase2_candidates(items, total_batches=6, episode_line_cap=115)
    sel_ids = {it["id"] for it in selected}
    assert {13, 14, 15, 16}.issubset(sel_ids)

    # A-3: asymetryczne T-V z zachowaniem formalnej formy w kierunku Oficer_B -> Celina
    assert _resolve_tv_address_form("Oficer_B", "Celina", sb).startswith("pan/pani")
    assert _resolve_tv_address_form("Celina", "Oficer_B", sb).startswith("na ty")

    # A-4 + A-5
    ev_locks = _extract_episode_honorific_title_locks([
        pysubs2.SSAEvent(start=1000, end=2000, text="Lady Aurelia met Baron Viktor yesterday."),
        pysubs2.SSAEvent(start=3000, end=4000, text="Baron Viktor escorted Lady Aurelia home."),
    ])
    assert ev_locks == {"Lady Aurelia": "lady Aurelia", "Baron Viktor": "baron Viktor"}
    assert _expand_spoken_numeric_abbreviations("Pożyczę 500 mln!", is_sign=False) == "Pożyczę 500 milionów!"


@pytest.mark.unit
def test_bug1_a3_ty_with_vocative_title_stays_informal(tmp_path):
    """
    BUG #1 (A-3): Jawna deklaracja 'Ty' połączona po ukośniku z tytułem-wołaczem ('Ty (Dowódca_B) / Mistrzyni')
    pozostaje relacją nieformalną ('na ty'), natomiast jawne 'Pan/Pani' lub sam tytuł bez 'ty' ('Pan / Panie Prezesie / Mistrzu Gildii')
    zachowuje formę dystansową 'pan/pani'.
    """
    sb = SeriesBible(anime_title="Seria Beta", storage_dir=tmp_path)
    sb.data["characters"] = {
        "Agent_A": {
            "name": "Agent_A",
            "gender": "FEMALE",
            "grammatical_gender": "FEMININE",
            "confidence": 0.95,
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["Agent_A"],
            "description": "kobieta (postać)",
            "entity_category": "ANTHROPONYM",
        },
        "Dowódca_B": {
            "name": "Dowódca_B",
            "gender": "FEMALE",
            "grammatical_gender": "FEMININE",
            "confidence": 0.95,
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["Dowódca_B"],
            "description": "kobieta (postać)",
            "entity_category": "ANTHROPONYM",
        },
        "Szef_C": {
            "name": "Szef_C",
            "gender": "MALE",
            "grammatical_gender": "MASCULINE",
            "confidence": 0.95,
            "priority": "P0",
            "has_verified_gender": True,
            "aliases": ["Szef_C"],
            "description": "mężczyzna (postać)",
            "entity_category": "ANTHROPONYM",
        },
    }
    sb.data["relations"] = {
        "Agent_A -> Dowódca_B": "Zwrot: 'Ty (Dowódca_B) / Mistrzyni' (Głęboki szacunek)",
        "Agent_A -> Szef_C": "Zwrot: 'Pan / Panie Prezesie / Mistrzu Gildii'",
    }

    res_ty_title = _resolve_tv_address_form("Agent_A", "Dowódca_B", sb)
    assert res_ty_title == "na ty (Ty (Dowódca_B) / Mistrzyni)"

    res_formal = _resolve_tv_address_form("Agent_A", "Szef_C", sb)
    assert res_formal == "pan/pani (Pan / Panie Prezesie / Mistrzu Gildii)"


@pytest.mark.unit
def test_bug2_a1_modal_rollback_fires_even_without_added_period():
    """
    BUG #2 (A-1 Warstwa 2): Gdy F2 usuwa konstrukcję modalną rządzącą bezokolicznikiem w niezweryfikowanym
    następniku (#10 -> #11) i nie dopisuje kropki końcowej, _guard_phase2_split_pair_integrity
    i tak przywraca spójną formę modalną z F1.
    """
    it10 = _make_prod_pass1_item(
        idx=10,
        en="I want you to head to the outpost at once",
        pl="Macie natychmiast ruszyć na posterunek",
        speaker_name="Oficer_B",
        start_ms=10000,
        end_ms=12000,
    )
    it11 = _make_prod_pass1_item(
        idx=11,
        en="and inspect the anomaly.",
        pl="i zbadać tę anomalię.",
        speaker_name="Oficer_B",
        start_ms=12000,
        end_ms=14000,
    )
    refined_dict = {10: "Ruszajcie natychmiast na posterunek", 11: sanitize_sub_text(it11["pl"])}
    _guard_phase2_split_pair_integrity([it10, it11], refined_dict, verified_ids={10})
    assert refined_dict[10] == "Macie natychmiast ruszyć na posterunek"


@pytest.mark.unit
def test_bug3_a5_preserves_ellipsis_after_tys_mln():
    """
    BUG #3 (A-5): _SPOKEN_NUMERIC_ABBR_RE nie konsumuje pierwszej kropki wielokropka
    po skrótach 'tys'/'mln', zachowując pełne trzy kropki (...).
    """
    assert _expand_spoken_numeric_abbreviations("Zostało 5 tys...", is_sign=False) == "Zostało 5 tysięcy..."
    assert _expand_spoken_numeric_abbreviations("Pożyczę 500 mln...", is_sign=False) == "Pożyczę 500 milionów..."
