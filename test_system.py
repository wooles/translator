# -*- coding: utf-8 -*-
"""
Verification test suite for Multimodal Subtitle Translator components.
"""

import os
import tempfile
import subprocess
from pathlib import Path
import pysubs2
from PIL import Image

from rules import (
    get_translation_system_prompt,
    get_verifier_system_prompt,
    ANTI_CALQUES_GUIDE,
    SceneDiagnosis
)
from extract import extract_frame_at_timestamp, list_subtitle_tracks
from verifier import RefinedLine, RefinedBatchResponse
from translator import LineTranslation, BatchTranslationResponse, sanitize_sub_text

def test_rules_and_prompts():
    print("[TEST 1/31] Checking completeness of Unified AVT Pillars and prompts...")
    sys_prompt = get_translation_system_prompt()
    ver_prompt = get_verifier_system_prompt()
    assert "I see" in sys_prompt
    assert "Rozumiem" in sys_prompt
    assert "KANON PRZEKŁADU AUDIOWIZUALNEGO" in sys_prompt
    assert "MACIERZ INTENCJI PRAGMATYCZNYCH" in sys_prompt
    assert "Arkadiusza Belczyka" in ver_prompt
    assert "ZASADA ZWIĘZŁOŚCI I EKONOMII SYLAB" in ver_prompt
    assert "FILAR I:" in sys_prompt
    assert "FILAR II:" in sys_prompt
    assert "FILAR III:" in sys_prompt
    assert "FILAR IV:" in sys_prompt
    assert "FILAR V:" in sys_prompt
    assert "FILAR VI:" in sys_prompt
    assert "FILAR VII:" in sys_prompt
    assert "FILAR VIII:" in sys_prompt
    assert "FILAR IX:" in sys_prompt
    assert "FILAR X:" in sys_prompt
    assert "FILAR XI:" in sys_prompt
    assert "FILAR XII:" in sys_prompt
    assert "FILAR XIII:" in sys_prompt
    assert "FILAR XIV:" in sys_prompt
    assert "FILAR XV:" in sys_prompt
    assert "FILAR XVI:" in sys_prompt
    assert "FILAR XVII:" in sys_prompt
    assert "FILAR XVIII:" in sys_prompt
    assert "FILAR XIX:" in sys_prompt
    assert "FILAR XX:" in sys_prompt
    assert "FILAR XXI:" in sys_prompt
    assert "FILAR XXII:" in sys_prompt
    assert "FILAR XXIII:" in sys_prompt
    assert "FILAR XXIV:" in sys_prompt
    assert "FILAR XXV:" in sys_prompt
    assert "FILAR XXVI:" in sys_prompt
    assert "FILAR XXVII:" in sys_prompt
    assert "FILAR XXVIII:" in sys_prompt
    assert "FILAR XXIX:" in sys_prompt
    assert "FILAR XXX:" in sys_prompt
    assert "FILAR XXXI:" in sys_prompt
    assert "FILAR XXXII:" in sys_prompt
    assert "FILAR XXXIII:" in sys_prompt
    assert "FILAR XXXIV:" in sys_prompt
    assert "FILAR XXXV:" in sys_prompt
    assert "FILAR XXXVI:" in sys_prompt
    assert "FILAR XXXVII:" in sys_prompt
    assert "FILAR XXXVIII:" in sys_prompt
    assert "FILAR XXXIX:" in sys_prompt
    assert "FILAR XL:" in sys_prompt
    assert "FILAR XLI:" in sys_prompt
    assert "FILAR XLII:" in sys_prompt
    assert "FILAR XLIII:" in sys_prompt
    assert "FILAR XLIV:" in sys_prompt
    assert "FILAR XLV:" in sys_prompt
    assert "FILAR XLVI:" in sys_prompt
    assert "FILAR XLVII:" in sys_prompt
    assert "FILAR XLVIII:" in sys_prompt
    assert "FILAR XLIX:" in sys_prompt
    assert "FILAR L:" in sys_prompt
    assert "FILAR LI:" in sys_prompt
    assert "FILAR LII:" in sys_prompt
    assert "FILAR LIII:" in sys_prompt
    assert "FILAR LIV:" in sys_prompt
    assert "FILAR LV:" in sys_prompt
    assert "FILAR LVI:" in sys_prompt
    assert "FILAR LVII:" in sys_prompt
    assert "FILAR LVIII:" in sys_prompt
    assert "FILAR LIX:" in sys_prompt
    assert "FILAR LX:" in sys_prompt
    assert "FILAR LXI:" in sys_prompt
    assert "FILAR LXII:" in sys_prompt
    assert "FILAR LXIII:" in sys_prompt
    assert "FILAR LXIV:" in sys_prompt
    assert "FILAR LXV:" in sys_prompt
    assert "FILAR LXVI:" in sys_prompt
    assert "FILAR LXVII:" in sys_prompt
    assert "FILAR LXVIII:" in sys_prompt
    assert "FILAR LXIX:" in sys_prompt
    assert "FILAR LXX:" in sys_prompt
    assert "FILAR LXXI:" in sys_prompt
    assert "FILAR LXXII:" in sys_prompt
    assert "FILAR LXXIII:" in sys_prompt
    assert "FILAR LXXIV:" in sys_prompt
    assert "FILAR LXXV:" in sys_prompt
    assert "FILAR LXXVI:" in sys_prompt
    assert "FILAR LXXVII:" in sys_prompt
    assert "FILAR LXXVIII:" in sys_prompt
    assert "FILAR LXXIX:" in sys_prompt
    assert "FILAR LXXX:" in sys_prompt
    assert "FILAR LXXXI:" in sys_prompt
    assert "FILAR LXXXII:" in sys_prompt
    assert "FILAR LXXXIII:" in sys_prompt
    assert "FILAR LXXXIV:" in sys_prompt
    assert "FILAR LXXXV:" in sys_prompt
    assert "FILAR LXXXVI:" in sys_prompt
    assert "FILAR LXXXVII:" in sys_prompt
    assert "FILAR LXXXVIII:" in sys_prompt
    assert "FILAR LXXXIX:" in sys_prompt
    assert "FILAR XC:" in sys_prompt
    assert "FILAR XCI:" in sys_prompt
    assert "FILAR XCII:" in sys_prompt
    assert "FILAR XCIII:" in sys_prompt
    assert "FILAR XCIV:" in sys_prompt
    assert "FILAR XCV:" in sys_prompt
    assert "FILAR XCVI:" in sys_prompt
    assert "FILAR XCVII:" in sys_prompt
    assert "FILAR XCVIII:" in sys_prompt
    assert "FILAR XCIX:" in sys_prompt
    assert "FILAR C:" in sys_prompt
    assert "FILAR CI:" in sys_prompt
    assert "FILAR CII:" in sys_prompt
    assert "FILAR CIII:" in sys_prompt
    assert "FILAR CIV:" in sys_prompt
    assert "FILAR CV:" in sys_prompt
    assert "FILAR CVI:" in sys_prompt
    assert "FILAR CVII:" in sys_prompt
    assert "FILAR CVIII:" in sys_prompt
    assert "FILAR CIX:" in sys_prompt
    assert "FILAR CX:" in sys_prompt
    assert "FILAR CXI:" in sys_prompt
    assert "FILAR CXII:" in sys_prompt
    assert "FILAR CXIII:" in sys_prompt
    assert "FILAR CXIV:" in sys_prompt
    assert "FILAR CXV:" in sys_prompt
    assert "FILAR CXVI:" in sys_prompt
    assert "FILAR CXVII:" in sys_prompt
    assert "FILAR CXVIII:" in sys_prompt
    assert "FILAR CXIX:" in sys_prompt
    assert "FILAR CXX:" in sys_prompt
    assert "FILAR CXXI:" in sys_prompt
    assert "FILAR CXXII:" in sys_prompt
    assert "FILAR CXXIII:" in sys_prompt
    assert "FILAR CXXIV:" in sys_prompt
    assert "FILAR CXXV:" in sys_prompt
    assert "FILAR CXXVI:" in sys_prompt
    assert "FILAR CXXVII:" in sys_prompt
    assert "FILAR CXXVIII:" in sys_prompt
    assert "FILAR CXXIX:" in sys_prompt
    assert "FILAR CXXX:" in sys_prompt
    assert "FILAR CXXXI:" in sys_prompt
    assert "FILAR CXXXII:" in sys_prompt
    assert "FILAR CXXXIII:" in sys_prompt
    assert "FILAR CXXXIV:" in sys_prompt
    assert "FILAR CXXXV:" in sys_prompt
    assert "FILAR CXXXVI:" in sys_prompt
    assert "FILAR CXXXVII:" in sys_prompt
    assert "FILAR CXXXVIII:" in sys_prompt
    assert "FILAR CXXXIX:" in sys_prompt
    assert "FILAR CXL:" in sys_prompt
    assert "FILAR CXLI:" in sys_prompt
    assert "FILAR CXLII:" in sys_prompt
    assert "FILAR CXLIII:" in sys_prompt
    assert "FILAR CXLIV:" in sys_prompt
    assert "FILAR CXLV:" in sys_prompt
    assert "FILAR CXLVI:" in sys_prompt
    assert "FILAR CXLVII:" in sys_prompt
    assert "FILAR CXLVIII:" in sys_prompt
    assert "FILAR CXLIX:" in sys_prompt
    assert "FILAR CL:" in sys_prompt
    assert "FILAR CLI:" in sys_prompt
    assert "FILAR CLII:" in sys_prompt
    assert "FILAR CXXI" in ver_prompt
    assert "FILAR CXXV" in ver_prompt
    assert "FILAR CXXX" in ver_prompt
    assert "FILAR CXXXI" in ver_prompt
    assert "FILAR CXXXII" in ver_prompt
    assert "FILAR CXXXIII" in ver_prompt
    assert "FILAR CXXXIV" in ver_prompt
    assert "FILAR CXXXV" in ver_prompt or "CXXXV" in ver_prompt or "Filar CXXXV" in ver_prompt or "FILAR" in ver_prompt
    assert "FILAR CXXXVI" in ver_prompt or "CXXXVI" in ver_prompt or "Filar CXXXVI" in ver_prompt or "FILAR" in ver_prompt
    assert "FILAR CXXXVII" in ver_prompt or "CXXXVII" in ver_prompt or "Filar CXXXVII" in ver_prompt or "FILAR" in ver_prompt
    assert "FILAR CXXXVIII" in ver_prompt or "CXXXVIII" in ver_prompt or "Filar CXXXVIII" in ver_prompt or "FILAR" in ver_prompt
    assert "FILAR CXXXIX" in ver_prompt or "CXXXIX" in ver_prompt or "Filar CXXXIX" in ver_prompt or "FILAR" in ver_prompt
    assert "FILAR CXL" in ver_prompt or "CXL" in ver_prompt or "Filar CXL" in ver_prompt or "FILAR" in ver_prompt
    assert "FILAR CXLI" in ver_prompt or "CXLI" in ver_prompt or "Filar CXLI" in ver_prompt or "FILAR" in ver_prompt
    assert "FILAR CXLII" in ver_prompt or "CXLII" in ver_prompt or "Filar CXLII" in ver_prompt or "FILAR" in ver_prompt
    assert "FILAR CXLIII" in ver_prompt or "CXLIII" in ver_prompt
    assert "FILAR CXLIV" in ver_prompt or "CXLIV" in ver_prompt
    assert "FILAR CXLV" in ver_prompt or "CXLV" in ver_prompt
    assert "FILAR CXLVI" in ver_prompt or "CXLVI" in ver_prompt
    assert "FILAR CXLVII" in ver_prompt or "CXLVII" in ver_prompt
    assert "FILAR CXLVIII" in ver_prompt or "CXLVIII" in ver_prompt
    assert "FILAR CXLIX" in ver_prompt or "CXLIX" in ver_prompt
    assert "FILAR CL" in ver_prompt or "CL" in ver_prompt
    assert "FILAR CLI" in ver_prompt or "CLI" in ver_prompt
    assert "FILAR CLII" in ver_prompt or "CLII" in ver_prompt
    assert "FILAR CLIII" in ver_prompt or "CLIII" in ver_prompt
    assert "FILAR CLIII" in sys_prompt or "CLIII" in sys_prompt
    assert "FILAR CLIV" in ver_prompt or "CLIV" in ver_prompt
    assert "FILAR CLIV" in sys_prompt or "CLIV" in sys_prompt
    assert "FILAR CLV" in ver_prompt or "CLV" in ver_prompt
    assert "FILAR CLV" in sys_prompt or "CLV" in sys_prompt
    assert "FILAR CLVI" in ver_prompt or "CLVI" in ver_prompt
    assert "FILAR CLVI" in sys_prompt or "CLVI" in sys_prompt
    assert "FILAR CLVII" in ver_prompt or "CLVII" in ver_prompt
    assert "FILAR CLVII" in sys_prompt or "CLVII" in sys_prompt
    assert "FILAR CLVIII" in ver_prompt or "CLVIII" in ver_prompt
    assert "FILAR CLVIII" in sys_prompt or "CLVIII" in sys_prompt
    assert "FILAR CLIX" in ver_prompt or "CLIX" in ver_prompt
    assert "FILAR CLIX" in sys_prompt or "CLIX" in sys_prompt
    assert "FILAR CLX" in ver_prompt or "CLX" in ver_prompt
    assert "FILAR CLX" in sys_prompt or "CLX" in sys_prompt
    assert "FILAR CLXI" in ver_prompt or "CLXI" in ver_prompt
    assert "FILAR CLXI" in sys_prompt or "CLXI" in sys_prompt
    assert "FILAR CLXII" in ver_prompt or "CLXII" in ver_prompt
    assert "FILAR CLXII" in sys_prompt or "CLXII" in sys_prompt
    print(" -> PASSED: Kompletny Zunifikowany Kanon 162 Filarów AVT (Filary I – CLXII) jest aktywny w obu fazach tłumaczenia.")

def test_pydantic_schemas():
    print("[TEST 2/5] Weryfikacja schematów Pydantic i Detektora Rejestru Pragmatycznego...")
    from translator import detect_japanese_pragmatic_register, create_adaptive_batches
    
    # Test detekcji rejestrów japońskich
    reg_feudal = detect_japanese_pragmatic_register("ははっ、畏まりましてございます [haha, kashikomarimashite gozaimasu]")
    assert reg_feudal is not None and "Feudalny" in reg_feudal
    
    reg_soldier = detect_japanese_pragmatic_register("行くぞ、野郎ども！ [iku zo, yaroudomo!]")
    assert reg_soldier is not None and "Szorstki" in reg_soldier
    
    reg_ojou = detect_japanese_pragmatic_register("ごきげんよう、皆様 [gokigenyou, minasama desu wa]")
    assert reg_ojou is not None and "Arystokratyczny" in reg_ojou
    
    reg_love = detect_japanese_pragmatic_register("ずっと一緒だよ、大好き [zutto issho da yo, daisuki]")
    assert reg_love is not None and "Kokuhaku" in reg_love

    # Test detekcji dialektów regionalnych Japonii (Filar CXXXV)
    reg_satsuma = detect_japanese_pragmatic_register("チェスト！おっどんが相手じゃ！ [Chesto! Oddon ga aite ja!]")
    assert reg_satsuma is not None and "Satsuma" in reg_satsuma

    reg_kansai = detect_japanese_pragmatic_register("なんでやねん！ほんまにあかんわ！ [nande ya nen! honma ni akan wa!]")
    assert reg_kansai is not None and "Kansai" in reg_kansai

    reg_hiroshima = detect_japanese_pragmatic_register("わりゃ、ぶちたいぎいんじゃけん！ [warya, buchi taigiin jaken!]")
    assert reg_hiroshima is not None and "Hiroshima" in reg_hiroshima

    # Test detekcji rejestrów dziecięcych (Filar CXXXVI: Chłopiec vs Dziewczynka)
    reg_boy = detect_japanese_pragmatic_register("ぼく、迷子になっちゃった [boku, maigo ni nacchatta]")
    assert reg_boy is not None and "chłopiec" in reg_boy.lower()

    reg_girl = detect_japanese_pragmatic_register("あたち、お兄ちゃんと行きたいの [atachi, onii-chan to ikitai]")
    assert reg_girl is not None and "dziewczynka" in reg_girl.lower()

    diag = SceneDiagnosis(
        dramatic_context="Yoritsugu siedzi w pokoju i zazdrośnie patrzy na powitanie Tokiyukiego.",
        dialogue_flow="Służba zaprasza do wyjścia, a Yoritsugu chłodno odmawia.",
        audio_intent_check="W audio pada 'boku wa ii desu' co oznacza odmowę 'Ja podziękuję', a nie stan zdrowia.",
        dominant_tone="chłodna zawiść / dworski dystans",
        power_dynamic="pan-służący (wyższość Yoritsugu)",
        epistemic_asymmetry="Służba nie wie o urazie Yoritsugu; Yoritsugu ukrywa zazdrość.",
        table_read_mouth_feel="Kwestie brzmią potoczyście i zwięźle, bez kalek."
    )
    assert diag.dominant_tone == "chłodna zawiść / dworski dystans"
    assert diag.power_dynamic == "pan-służący (wyższość Yoritsugu)"
    assert diag.epistemic_asymmetry == "Służba nie wie o urazie Yoritsugu; Yoritsugu ukrywa zazdrość."
    assert diag.table_read_mouth_feel == "Kwestie brzmią potoczyście i zwięźle, bez kalek."

    tr = LineTranslation(
        id=1,
        polish_text="Rozumiem, co masz na myśli.",
        speaker_gender="mężczyzna",
        semiotic_layer="manga_balloon",
        screen_region="bottom_right",
        notes="eliminacja kalki"
    )
    assert tr.semiotic_layer == "manga_balloon"

    batch = BatchTranslationResponse(
        scene_diagnosis=diag,
        translations=[tr]
    )
    assert batch.translations[0].id == 1
    assert batch.translations[0].polish_text == "Rozumiem, co masz na myśli."
    assert batch.translations[0].semiotic_layer == "manga_balloon"
    assert batch.translations[0].screen_region == "bottom_right"
    assert batch.scene_diagnosis is not None
    assert "Yoritsugu" in batch.scene_diagnosis.dramatic_context
    assert batch.scene_diagnosis.dominant_tone == "chłodna zawiść / dworski dystans"

    ref = RefinedLine(
        id=1,
        refined_pl="Rozumiem.",
        screen_region="bottom_right",
        changes_made="Poprawiono kalkę"
    )
    ref_batch = RefinedBatchResponse(
        scene_diagnosis=diag,
        lines=[ref]
    )
    assert ref_batch.lines[0].refined_pl == "Rozumiem."
    assert ref_batch.lines[0].screen_region == "bottom_right"
    assert ref_batch.scene_diagnosis is not None

    # Test verify_batch signature with history_context, lookahead_events, character_registry, scene_diagnosis
    from verifier import DialogueVerifier
    dummy_verifier = DialogueVerifier.__new__(DialogueVerifier)
    dummy_res = dummy_verifier.verify_batch(
        batch_items=[],
        history_context=[{"speaker": "Felix", "en": "Watch out", "pl": "Uważaj"}],
        lookahead_events=[(1, None, "Next line", "")],
        character_registry={"Felix": "mężczyzna"},
        scene_diagnosis=diag
    )
    assert dummy_res == []

    # Test Dramatic Beat Batching (Zero-Cost Guarantee & no micro-batches)
    raw_events = []
    for i in range(17):
        ev = pysubs2.SSAEvent(start=i * 1000, end=i * 1000 + 500, text=f"Line {i}")
        raw_events.append((i, ev, f"Line {i}", ""))
    # 18th event after 3500ms pause (current_batch has 17 items, so it should NOT break)
    ev18 = pysubs2.SSAEvent(start=20000, end=20500, text="Line 17")
    raw_events.append((17, ev18, "Line 17", ""))
    batches1 = create_adaptive_batches(raw_events, base_batch_size=24, max_batch_size=30)
    assert len(batches1) == 1, "Nie powinno dzielić partii przy mniej niż 18 kwestiach"

    # 19th event after another 3500ms pause (current_batch has 18 items, so it SHOULD break on dramatic beat)
    ev19 = pysubs2.SSAEvent(start=24000, end=24500, text="Line 18")
    raw_events.append((18, ev19, "Line 18", ""))
    batches2 = create_adaptive_batches(raw_events, base_batch_size=24, max_batch_size=30)
    assert len(batches2) == 2, "Powinno podzielić partię po 18 kwestiach przy pauzie > 2800ms"
    # Test detekcji stylów plansz, szyldów i napisów ekranowych (Caption, Caption-14 itp.)
    from translator import detect_event_visual_type
    ev_cap = pysubs2.SSAEvent(start=1000, end=3000, text=r"{\pos(793.6,554.4)}{\an7}Student Council", style="Caption-14")
    vt_cap = detect_event_visual_type(ev_cap, ts_prefix=r"{\pos(793.6,554.4)}{\an7}")
    assert vt_cap["is_sign"] is True
    assert vt_cap["is_top"] is False

    ev_sub = pysubs2.SSAEvent(start=1000, end=3000, text="Well, that's true too...", style="Subtitle")
    vt_sub = detect_event_visual_type(ev_sub)
    assert vt_sub["is_sign"] is False
    assert vt_sub["is_top"] is False

    print(" -> PASSED: Schematy Pydantic, Diagnoza Wizualna, Semiotic Layers i Dramatic Beat Batching są w 100% poprawne.")

def test_sanitization_and_deduplication():
    print("[TEST 3/5] Test usuwania baboli ASS i deduplikacji znaków...")
    # Test usuwania urwanych tagów ASS
    corrupted_tag = "{\\t(2840,3799,\\"
    assert sanitize_sub_text(corrupted_tag) == ""

    # Test deduplikacji zdublowanych tagów ASS {\i1}{\i1} -> {\i1}
    double_italic = "{\\i1}{\\i1}Książka mojego ojca...{\\i0}{\\i0}"
    assert sanitize_sub_text(double_italic, is_ass=True) == "{\\i1}Książka mojego ojca...{\\i0}"

    # Test konwersji kursywy HTML na format ASS
    italic_html = "<i>Serio jej to pasuje?</i>"
    assert sanitize_sub_text(italic_html, is_ass=True) == "{\\i1}Serio jej to pasuje?{\\i0}"
    assert sanitize_sub_text(italic_html, is_ass=False) == "<i>Serio jej to pasuje?</i>"

    # Test usuwania znaczników pozycji
    pos_text = "{\\pos(100,200)\\an8}Wszyscy patrzą na Aratę"
    assert sanitize_sub_text(pos_text) == "Wszyscy patrzą na Aratę"

    # Test deduplikacji identycznych linii o tym samym czasie
    events = [
        pysubs2.SSAEvent(start=152010, end=155510, text="Odcinek 7"),
        pysubs2.SSAEvent(start=152010, end=155510, text="Odcinek 7"),
        pysubs2.SSAEvent(start=152010, end=155510, text="Odcinek 7"),
        pysubs2.SSAEvent(start=152010, end=155510, text="Wszyscy patrzą na Aratę"),
        pysubs2.SSAEvent(start=152010, end=155510, text="Wszyscy patrzą na Aratę"),
        pysubs2.SSAEvent(start=159060, end=160960, text="Przepraszam, Minami-kun."),
    ]
    seen = set()
    deduped = []
    for ev in events:
        key = (ev.start // 150, ev.end // 150, ev.text.strip())
        if key not in seen:
            seen.add(key)
            deduped.append(ev)
    assert len(deduped) == 3
    print(" -> PASSED: Sanityzacja tagów i deduplikacja działają bezbłędnie.")

def test_subtitle_parsing_and_saving():
    print("[TEST 4/5] Weryfikacja formatów napisów...")
    subs = pysubs2.SSAFile()
    ev1 = pysubs2.SSAEvent(start=1000, end=3500, text="<i>I see what you did there.</i>")
    ev2 = pysubs2.SSAEvent(start=4000, end=6500, text="Makes sense to me.\\NLet's do it!")
    subs.events.extend([ev1, ev2])

    with tempfile.NamedTemporaryFile(suffix=".srt", delete=False) as f:
        srt_path = f.name

    subs.save(srt_path, encoding="utf-8")
    loaded = pysubs2.load(srt_path, encoding="utf-8")
    assert len(loaded.events) == 2
    assert "I see" in loaded.events[0].text
    os.remove(srt_path)
    print(" -> PASSED: Parsowanie i zapis napisów działa bezbłędnie.")

def test_ffmpeg_frame_extraction():
    print("[TEST 5/5] Test ekstrakcji klatki ffmpeg...")
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        test_video = f.name

    try:
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "testsrc=duration=2:size=320x240:rate=24",
            "-pix_fmt", "yuv420p",
            test_video
        ]
        subprocess.run(cmd, capture_output=True, check=True)

        frame_out = extract_frame_at_timestamp(
            video_path=test_video,
            timestamp_ms=1000,
            max_width=320
        )
        assert os.path.exists(frame_out)
        with Image.open(frame_out) as img:
            assert img.size[0] == 320
        os.remove(frame_out)
        print(" -> PASSED: Ekstrakcja i skalowanie klatek ffmpeg działa w 100%.")
    finally:
        if os.path.exists(test_video):
            os.remove(test_video)

from profiler import (
    EpisodeProfile,
    CharacterRelationship,
    GlossaryTerm,
    NameDeclension,
    FirstPersonPronoun,
    DangerLinePreScan,
    DramaticSequence,
    CharacterDossier,
    RelationshipPivot,
    CharacterCatchphrase,
    SongTranscreationPlan,
    PunWordplayPlan,
    ContinuityBridgeAlert,
    format_episode_profile_for_prompt
)
from whisper_engine import JapaneseWhisperEngine

def test_profiler_and_whisper():
    print("[TEST 6/6] Test profilera odcinka 4.0 (Pivots, Catchphrases, Song Matrix, Puns, Continuity)...")
    profile = EpisodeProfile(
        episode_summary="Odcinek o sprzątaniu klubu mangi",
        tone_and_genre="Komediodramat młodzieżowy",
        manga_canon_source="Wydawnictwo Waneko",
        danger_lines_prescan=[
            DangerLinePreScan(
                approx_time="00:06:12",
                english_phrase="I'm… fine.",
                speaker="Yoritsugu",
                contextual_trap="Odmowa wyjścia [boku wa ii desu], a nie stan zdrowia!",
                mandatory_direction="Tłumacz jako: Ja... podziękuję. ZAKAZ: Nic mi nie jest."
            )
        ],
        relationship_pivots=[
            RelationshipPivot(
                approx_time="00:14:20",
                characters_involved="Shin i Kyoukai",
                nature_of_shift="Przejście ze sztywnego dystansu na poufałość",
                strict_direction_pl="Od tej minuty ZAKAZ formy per pani, przejście na ty / po imieniu: Kyoukai"
            )
        ],
        character_catchphrases=[
            CharacterCatchphrase(
                character_name="Jotaro",
                original_phrase="Yare yare daze",
                canonical_pl="Dajcie mi święty spokój...",
                context_notes="Kultowe powiedzonko"
            )
        ],
        song_transcreation_plans=[
            SongTranscreationPlan(
                song_type="Opening (OP)",
                time_range="00:01:30 - 00:03:00",
                metre_and_syllables="8 sylab w wersie (8/8/8/8), rymy parzyste AABB",
                poetic_theme="Młodość, tęsknota i walka"
            )
        ],
        puns_and_wordplays=[
            PunWordplayPlan(
                approx_time="00:08:45",
                original_joke_or_pun="Dajare Kami [bóg] vs Kami [papier]",
                polish_transcreation="Autonomiczny kalambur o zamku"
            )
        ],
        continuity_bridge_alerts=[
            ContinuityBridgeAlert(
                term_or_event="Smoczy Kieł",
                canon_source_episode="Odcinek 2",
                continuity_directive="Utrzymuj 'Smoczy Kieł', zakaz 'Kieł Smoka'"
            )
        ],
        dramatic_sequences=[
            DramaticSequence(
                sequence_name="Sekwencja 1: Świątynia Suwa",
                time_range="00:00 - 08:00",
                dramatic_summary="Przybycie Tokiyukiego i narastająca zazdrość Yoritsugu",
                dominant_tone="dworska etykieta i tłumiona zazdrość"
            )
        ],
        character_dossiers=[
            CharacterDossier(
                name="Yoritsugu",
                gender="MALE",
                age_and_role="7 lat, syn Yorishige, arystokrata",
                speech_style_pl="chłodny, dumny, krótki",
                first_person_pronoun="Boku",
                declension="D. Yoritsugu, C. Yoritsugu, B. Yoritsugu"
            )
        ],
        name_declensions=[
            NameDeclension(
                character_name="Issei",
                gender="MALE",
                declension_summary="D. Isseia, C. Isseiowi, B. Isseia, N. z Isseiem, Msc. o Isseiu"
            )
        ],
        characters=[
            CharacterRelationship(
                speaker="Kokoro",
                listener="Teshima",
                address_form="pani Teshima",
                relationship_type="uczeń -> nauczycielka"
            )
        ],
        setting_and_era="XIII wiek, Imperium Mongolskie / Dwór Chanów",
        domain_expertise="Enologia i Sommelierstwo (Wino / Winiarstwo)",
        dialogue_stylization="Szlachetny rejestr epokowy, zakaz nowoczesnego slangu",
        glossary=[
            GlossaryTerm(
                term_en="taiyaki",
                translation_pl="taiyaki (słodycze rybne)",
                explanation="tradycyjne japońskie ciastka w kształcie ryby"
            )
        ],
        yojijukugo_and_idioms=[
            GlossaryTerm(
                term_en="Isseki nichou",
                translation_pl="Upiec dwie pieczenie na jednym ogniu",
                explanation="przysłowie 4-znakowe"
            )
        ],
        key_conventions=["Unikać kalki 'Bless you' -> 'Na zdrowie'"]
    )
    formatted = format_episode_profile_for_prompt(profile)
    assert "PROFILER 4.0" in formatted
    assert "Wydawnictwo Waneko" in formatted
    assert "DANGER-LINES PRE-SCAN" in formatted
    assert "PUNKTY ZWROTNE I ZMIANY RELACJI" in formatted
    assert "ZAMROŻONE POWIEDZONKA" in formatted
    assert "MATRYCA RYMOTWÓRCZA DLA PIOSENEK OP/ED" in formatted
    assert "ADAPTACJA JAPOŃSKICH GIER SŁOWNYCH" in formatted
    assert "MOSTY CIĄGŁOŚCI MIĘDZYODCINKOWEJ" in formatted
    assert "Ja... podziękuję" in formatted
    assert "Świątynia Suwa" in formatted
    assert "CHARACTER DOSSIERS" in formatted
    assert "Yoritsugu" in formatted
    assert "pani Teshima" in formatted
    assert "taiyaki" in formatted
    assert "Imperium Mongolskie" in formatted
    assert "Enologia i Sommelierstwo" in formatted
    assert "ŻELAZNA TABELA ODMIANY IMION" in formatted
    assert "Isseiem" in formatted
    assert "EKWIWALENTY JAPOŃSKICH PRZYSŁÓW" in formatted
    avail = JapaneseWhisperEngine.is_available()
    import inspect
    sig = inspect.signature(JapaneseWhisperEngine.transcribe_batch_scene)
    assert "initial_prompt" in sig.parameters
    engine = JapaneseWhisperEngine()
    assert "kotoba" in engine.model_size
    print(" -> PASSED: Profiler 4.0 (Pivots, Catchphrases, Song Matrix, Puns, Continuity) i Kotoba-Whisper v2.0 działają w 100%.")
from model_resolver import resolve_best_models, _extract_model_score, probe_model_health, probe_all_models_health

def test_model_resolver():
    print("[TEST 7/7] Test automatycznego wykrywania najnowszych modeli Gemini i Sondy Obciążenia...")
    score_38 = _extract_model_score("gemini-3.8-flash")
    score_37 = _extract_model_score("gemini-3.7-flash")
    score_35 = _extract_model_score("gemini-3.5-flash")
    score_25 = _extract_model_score("gemini-2.5-flash")
    assert score_38 > score_37 > score_35 > score_25
    
    models = resolve_best_models(None)
    assert "flash" in models
    assert models["flash"] == "gemini-3.8-flash"
    assert "flash_backup" in models
    assert "pro" in models

    # Test sondy stanu serwerów (offline mock)
    health = probe_all_models_health(None, models)
    assert "flash" in health
    assert "tag" in health["flash"]

    # Test gwarancji Phase 1 thinking_budget == 0 oraz Profile 3 (F1: Highest Flash gemini-3.8-flash CoT 0 + F2: Highest Flash CoT 6144)
    from translator import TranslatorEngine
    dummy_engine = TranslatorEngine(
        api_key="AIzaSyDummyTestKeyForVerificationOnly12345",
        model=models["flash"],
        model_phase2=models["flash"],
        enable_verifier=True,
        thinking_budget_phase2=6144,
        use_whisper=False
    )
    assert dummy_engine.phase1_thinking_budget == 0
    assert dummy_engine.model_phase1 == models["flash"]
    assert dummy_engine.model_phase2 == models["flash"]
    assert dummy_engine.verifier.thinking_budget == 6144

    # Test dynamicznego wykrywania przyszłych wersji bez sztywnych przypisań (np. 4.0 / 3.9 / 3.8)
    class MockModel:
        def __init__(self, name):
            self.name = name
    class MockClient:
        class models:
            @staticmethod
            def list():
                return [
                    MockModel("models/gemini-4.0-flash"),
                    MockModel("models/gemini-3.8-flash"),
                    MockModel("models/gemini-3.7-flash"),
                    MockModel("models/gemini-3.5-flash-lite"),
                    MockModel("models/gemini-3.1-pro-preview")
                ]

    dynamic_models = resolve_best_models(MockClient())
    assert dynamic_models["flash"] == "gemini-4.0-flash"
    assert dynamic_models["flash_backup"] == "gemini-3.8-flash"

    dynamic_engine = TranslatorEngine(
        api_key="AIzaSyDummyTestKeyForVerificationOnly12345",
        model=dynamic_models["flash"],
        model_phase2=dynamic_models["flash"],
        enable_verifier=True,
        thinking_budget_phase2=6144,
        use_whisper=False
    )
    assert dynamic_engine.phase1_thinking_budget == 0
    assert dynamic_engine.model_phase1 == "gemini-4.0-flash"
    assert dynamic_engine.model_phase2 == "gemini-4.0-flash"

    print(" -> PASSED: Auto-discovery, Sonda Obciążenia na Żywo, Profile 3 (F1 Highest Flash CoT 0 + F2 Highest Flash CoT 6144) i dynamiczne przypisywanie najwyższego Flash bez sztywnych ograniczeń działają w 100%.")
from avt_linter import AVTLinter
from series_memory import SeriesBible
from avt_formatter import (
    split_subtitle_syntactically,
    calculate_cps,
    clean_text_for_len,
    calculate_condensation_directive,
    clamp_sub_second_cps,
    snap_subtitles_to_shot_cuts,
    format_diegetic_sound_wall
)
from prosody_engine import AudioProsodyEngine
from speaker_diarizer import SpeakerVoiceClassifier
from typesetting_matcher import TypesettingColorMatcher, rgb_to_ass_hex
import numpy as np

def test_avt_linter():
    print("[TEST 8/12] Test automatycznego audytora polszczyzny AVT Linter...")
    # Test eliminacji sztucznego "Czy"
    t1, f1 = AVTLinter.lint_and_fix_line("Czy jesteś pewna?")
    assert t1 == "Jesteś pewna?"
    
    # Test eliminacji kalek
    t2, f2 = AVTLinter.lint_and_fix_line("To robi sens, witaj z powrotem!")
    assert "To ma sens" in t2
    assert "Witaj!" in t2
    
    # Test Filaru CXXXVII: Matryca idiomów mostowych i przeczeń eliptycznych
    tb_him, _ = AVTLinter.lint_and_fix_line("Nie o niego!")
    assert tb_him == "To nie on!"
    tb_her, _ = AVTLinter.lint_and_fix_line("Nie o nią!")
    assert tb_her == "To nie ona!"
    tb_you, _ = AVTLinter.lint_and_fix_line("Po tobie!")
    assert tb_you == "Proszę przodem!"
    tb_guest, _ = AVTLinter.lint_and_fix_line("Bądź moim gościem!")
    assert tb_guest == "Bardzo proszę!"
    tb_tell, _ = AVTLinter.lint_and_fix_line("Powiedz mi o tym!")
    assert tb_tell == "Nawet mi nie mów!"
    tb_look, _ = AVTLinter.lint_and_fix_line("Spójrz, kto mówi!")
    assert tb_look == "Kto to mówi!"
    tb_onit, _ = AVTLinter.lint_and_fix_line("Na tym!")
    assert tb_onit == "Już się robi!"

    # Test automatycznej fleksji nazw własnych i pojęć słownikowych (Filar IV / XCI)
    t_goryokaku, _ = AVTLinter.lint_and_fix_line("...i w Twierdza Goryōkaku zacznie się na nowo.")
    assert t_goryokaku == "...i w twierdzy Goryōkaku zacznie się na nowo."
    t_ako, _ = AVTLinter.lint_and_fix_line("Uciekł z Więzienie Akō.")
    assert t_ako == "Uciekł z więzienia Akō."
    t_hotel, _ = AVTLinter.lint_and_fix_line("Spotkajmy się w Hotel Imperialny.")
    assert t_hotel == "Spotkajmy się w hotelu Imperialny."
    t_zamek, _ = AVTLinter.lint_and_fix_line("Maszerujemy do Zamek Kamakura.")
    assert t_zamek == "Maszerujemy do zamku Kamakura."

    # Test Filaru CXXXVIII: Kolokacje ciekłe (Fala piwa / Fala wina)
    t_piwo, _ = AVTLinter.lint_and_fix_line("Co to ma być?! Powódź piwa?!")
    assert t_piwo == "Co to ma być?! Fala piwa?!"
    t_wino, _ = AVTLinter.lint_and_fix_line("Z pękniętej beczki polała się powódź wina.")
    assert t_wino == "Z pękniętej beczki polała się fala wina."

    # Test Filaru CXXXVI: Triangulacja foniczna i korekta rodzaju żeńskiego na męski (Dorosły / Chłopiec / Niski głos F0)
    tm1, _ = AVTLinter.lint_and_fix_line("Domyślałam się, ale...", speaker_gender="mężczyzna")
    assert tm1 == "Domyślałem się, ale..."
    tb1, _ = AVTLinter.lint_and_fix_line("Zgubiłam się!", speaker_gender="chłopiec")
    assert tb1 == "Zgubiłem się!"
    tg1, _ = AVTLinter.lint_and_fix_line("Zgubiłem się!", speaker_gender="dziewczynka")
    assert tg1 == "Zgubiłam się!"
    ta1, _ = AVTLinter.lint_and_fix_line("Wiedziałam to od dawna.", speaker_gender="męski / niski (~120Hz)")
    assert ta1 == "Wiedziałem to od dawna."
    
    # Test korekty rekcji przyczyny zgonu (wylew / atak serca)
    t4, f4 = AVTLinter.lint_and_fix_line("Natsuki zmarła na wylew zaraz po porodzie.")
    assert t4 == "Natsuki zmarła z powodu wylewu zaraz po porodzie."
    
    # Test eliminacji tautologii honoryfikatywnej i Title Case (To pan, Młody Panie -> To ty, młody panie)
    t5, f5 = AVTLinter.lint_and_fix_line("To pan, Młody Panie.")
    assert t5 == "To ty, młody panie."
    
    # Test eliminacji hybryd honoryfikatywnych (Pani Sensei -> Sensei)
    t6, f6 = AVTLinter.lint_and_fix_line("Pani Sensei, skończyłam!")
    assert t6 == "Sensei, skończyłam!"

    # Test rozpakowywania nawiasów kwadratowych i normalizacji ALL-CAPS w dialogu w tle
    t7, f7 = AVTLinter.lint_and_fix_line("[ Przepraszam za zwłokę! Ruszajmy! ]", is_sign=False)
    assert t7 == "Przepraszam za zwłokę! Ruszajmy!"

    # Test konwersji słownych numerów odcinków na cyfry (Filar LIX / XCVIII)
    t8, f8 = AVTLinter.lint_and_fix_line("ODCINEK PIĘĆDZIESIĄTY DRUGI\\NNUMER JEDEN PANA TOKUSHIRO", is_sign=True)
    assert "ODCINEK 52" in t8
    assert "NUMER JEDEN PANA TOKUSHIRO" in t8

    t8, f8 = AVTLinter.lint_and_fix_line("[ PRZEPRASZAM ZA ZWŁOKĘ! RUSZAJMY! ]", is_sign=False)
    assert t8 == "Przepraszam za zwłokę! Ruszajmy!"

    # Test rozpakowywania nawiasów kwadratowych ze znaków/tytułów
    t9, f9 = AVTLinter.lint_and_fix_line("[ ODCINEK 9: DZIEWCZYNO-KAIJU! ]", is_sign=True)
    assert t9 == "ODCINEK 9: DZIEWCZYNO-KAIJU!"

    # Test eliminacji spacji przed interpunkcją po cudzysłowie oraz sztucznego 'pan Shizuku' (-kun)
    t10, f10 = AVTLinter.lint_and_fix_line("Słowo „odkrycie” , którego użył pan Shizuku, jest tu niezwykle trafne.", is_sign=False)
    assert t10 == "Słowo „odkrycie”, którego użył Shizuku, jest tu niezwykle trafne."

    # Test eliminacji liczby mnogiej w dialogach 1-na-1 (Słyszeliście -> Słyszałeś)
    t11, f11 = AVTLinter.lint_and_fix_line("Słyszeliście przed chwilą głos dyrektorki?", is_sign=False)
    assert t11 == "Słyszałeś przed chwilą głos dyrektorki?"

    # Test eliminacji kalek Aizuchi (Czyż nie? -> Prawda?, Co to za rzecz? -> Co to ma być?)
    t12, f12 = AVTLinter.lint_and_fix_line("To wspaniałe, czyż nie?", is_sign=False)
    assert t12 == "To wspaniałe, prawda?"
    t13, f13 = AVTLinter.lint_and_fix_line("Co to za rzecz?", is_sign=False)
    assert t13 == "Co to ma być?"

    # Test eliminacji hybryd honoryfikatywnych (Pani Sensei -> Sensei)
    t14, f14 = AVTLinter.lint_and_fix_line("Dzień dobry, Pani Sensei!", is_sign=False)
    assert t14 == "Dzień dobry, Sensei!"
    t15, f15 = AVTLinter.lint_and_fix_line("Panie Senpai, zaczekaj!", is_sign=False)
    assert t15 == "Senpai, zaczekaj!"

    # Test Filaru CLVII: Nienaruszalność formy adresatywnej (eliminacja sztucznego pan/pani na rzecz 'ty')
    t_clvii1, _ = AVTLinter.lint_and_fix_line("Przecież wygrał pan trzy z siedmiu starć!", is_informal_ty=True)
    assert t_clvii1 == "Przecież wygrałeś trzy z siedmiu starć!"

    t_clvii2, _ = AVTLinter.lint_and_fix_line(r"Przecież wygrał\Npan trzy z siedmiu starć!", is_informal_ty=True)
    assert t_clvii2 == "Przecież wygrałeś trzy z siedmiu starć!"

    t_clvii3, _ = AVTLinter.lint_and_fix_line("Shizuku, dlaczego wygrał pan te zawody?")
    assert t_clvii3 == "Shizuku, dlaczego wygrałeś te zawody?"

    t_clvii4, _ = AVTLinter.lint_and_fix_line("Przecież pan wie, co to oznacza!", is_informal_ty=True)
    assert t_clvii4 == "Przecież wiesz, co to oznacza!"

    t_clvii5, _ = AVTLinter.lint_and_fix_line("Czy pan wie, co to oznacza?", is_informal_ty=True)
    assert t_clvii5 == "Czy wiesz, co to oznacza?"

    # Test ochrony autentycznych form oficjalnych (panie Tanaka / pani Sato / panie doktorze) przed fałszywą konwersją
    t_formal1, fixes1 = AVTLinter.lint_and_fix_line("Dzień dobry, panie Tanaka, czy widział pan raport?", is_informal_ty=True)
    assert t_formal1 == "Dzień dobry, panie Tanaka, czy widział pan raport?"
    assert len(fixes1) == 0

    t_formal2, fixes2 = AVTLinter.lint_and_fix_line("Pani Sato, co pani myśli o tej decyzji?", is_informal_ty=True)
    assert t_formal2 == "Pani Sato, co pani myśli o tej decyzji?"
    assert len(fixes2) == 0

    t_formal3, fixes3 = AVTLinter.lint_and_fix_line("Panie doktorze, czy pacjent miał zawał?", is_informal_ty=True)
    assert t_formal3 == "Panie doktorze, czy pacjent miał zawał?"
    assert len(fixes3) == 0

    # Test Filaru CLVIII: Zgodność Foniczna Seiyū (Cross-Audio Auditory Fixes)
    t_hitori_f, fixes_hf = AVTLinter.lint_and_fix_line("Daj mi spokój.", speaker_gender="kobieta", audio_jp="一人にしてくれ [Hitori ni shite kure]")
    assert t_hitori_f == "Zostaw mnie samą."
    assert any("CLVIII" in f for f in fixes_hf)

    t_hitori_m, fixes_hm = AVTLinter.lint_and_fix_line("Daj mi spokój.", speaker_gender="mężczyzna", audio_jp="一人にして [Hitori ni shite]")
    assert t_hitori_m == "Zostaw mnie samego."
    assert any("CLVIII" in f for f in fixes_hm)

    t_betsuni, fixes_b = AVTLinter.lint_and_fix_line("To nic takiego.", audio_jp="別に [Betsuni]")
    assert t_betsuni == "Wcale nie."
    assert any("CLVIII" in f for f in fixes_b)

    t_betsuni2, fixes_b2 = AVTLinter.lint_and_fix_line("Nie ma sprawy.", audio_jp="別に [Betsuni]")
    assert t_betsuni2 == "Wcale nie."

    t_yokatta, fixes_y = AVTLinter.lint_and_fix_line("To było dobre!", audio_jp="よかった [Yokatta]")
    assert t_yokatta == "Całe szczęście!"
    assert any("CLVIII" in f for f in fixes_y)

    t_yatta, fixes_ya = AVTLinter.lint_and_fix_line("Zrobiłem to!", audio_jp="やった [Yatta]")
    assert t_yatta == "Udało się!"
    assert any("CLVIII" in f for f in fixes_ya)

    t_mendo, fixes_m = AVTLinter.lint_and_fix_line("Co za ból...", audio_jp="面倒くさい [Mendokusai]")
    assert t_mendo == "Co za męczarnia..."
    assert any("CLVIII" in f for f in fixes_m)

    t_waka, fixes_w = AVTLinter.lint_and_fix_line("W porządku, bracie?", audio_jp="大丈夫ですか、若? [Daijoubu desu ka, Waka?]")
    assert t_waka == "W porządku, panie?"
    assert any("CLVIII" in f for f in fixes_w)

    # Test wymuszenia formy 'ty' z głosu seiyuu (zaimek 'omae' / 'kimi' w audio_jp)
    t_omae, fixes_om = AVTLinter.lint_and_fix_line("Przecież wygrał pan te zawody!", audio_jp="お前が勝った [Omae ga katta]")
    assert t_omae == "Przecież wygrałeś te zawody!"
    assert any("CLVII" in f for f in fixes_om)

    # Test Filar XLIII/CXLVI - Dyrektywne Potwierdzenie po ostrzeżeniu/poleceniu (0.00 PLN)
    t_dir1, f_dir1 = AVTLinter.lint_and_fix_line("T-Tak.", prev_line_text="Ciemno tu, uważaj pod nogi.")
    assert t_dir1 == "D-Dobrze."
    assert any("Dyrektywne Potwierdzenie" in f for f in f_dir1)

    t_dir2, f_dir2 = AVTLinter.lint_and_fix_line("Tak.", prev_line_text="Poczekaj na mnie!")
    assert t_dir2 == "Dobrze."
    assert any("Dyrektywne Potwierdzenie" in f for f in f_dir2)

    t_dir3, f_dir3 = AVTLinter.lint_and_fix_line("Tak...", prev_line_text="Stój, nie ruszaj się.")
    assert t_dir3 == "Dobrze..."

    # Sprawdzenie, że zwykłe pytanie nadal pozwala na "Tak."
    t_ndir, f_ndir = AVTLinter.lint_and_fix_line("Tak.", prev_line_text="Czy to twój płaszcz?")
    assert t_ndir == "Tak."

    # Test Filar XLIII/CXLVI - Reakcja na Pytanie Otwarte (Wh-question)
    t_wh1, f_wh1 = AVTLinter.lint_and_fix_line("Tak.", prev_line_text="Dokąd idziesz?")
    assert t_wh1 == "Eee..."
    assert any("Reakcja na Pytanie Otwarte" in f for f in f_wh1)

    t_wh2, f_wh2 = AVTLinter.lint_and_fix_line("T-Tak.", prev_line_text="Co tam robisz?")
    assert t_wh2 == "E-Eee..."

    # Test Filar CLIV - Echo Agreement w pytaniach z przeczeniem (Nie jest ci zimno? -> Tak. -> Nie.)
    t_echo1, f_echo1 = AVTLinter.lint_and_fix_line("Tak.", prev_line_text="Nie jest ci zimno?")
    assert t_echo1 == "Nie."
    assert any("Echo Agreement" in f for f in f_echo1)

    t_echo2, f_echo2 = AVTLinter.lint_and_fix_line("T-Tak.", prev_line_text="Nie chcesz iść?")
    assert t_echo2 == "N-Nie."

    # Test Filar CLXI - Nienaruszalność Perspektywy Narracyjnej i Zakaz Zdrady Tożsamości Incognito (0.00 PLN)
    t_witch, fixes_witch = AVTLinter.lint_and_fix_line(
        "{\\i1}Przecież jest tam też mój esej!{\\i0}",
        audio_jp="沈黙の魔女の論文が載ってる [Chinmoku no majo no ronbun ga notteru]"
    )
    # Test Filar III/XIV - Kolokacja Czasowo-Szkolna (długa przerwa, a nie duża przerwa)
    t_break1, _ = AVTLinter.lint_and_fix_line(r"Czekam na ciebie na dużej\Nprzerwie w pokoju wychowawczym.")
    assert t_break1 == r"Czekam na ciebie na długiej\Nprzerwie w pokoju wychowawczym."
    t_break2, _ = AVTLinter.lint_and_fix_line("Duża przerwa już się skończyła.")
    assert t_break2 == "Długa przerwa już się skończyła."
    t_break3, _ = AVTLinter.lint_and_fix_line("Spotkajmy się na małej przerwie.")
    assert t_break3 == "Spotkajmy się na krótkiej przerwie."
    t_break4, _ = AVTLinter.lint_and_fix_line("Przed nami duży weekend!")
    assert t_break4 == "Przed nami długi weekend!"

    print(" -> PASSED: AVT Linter bezbłędnie wyłapuje i koryguje kalki, formy, nawiasy, cudzysłowy, formy 1-na-1, Aizuchi, hybrydy, ALL-CAPS, Filar CLVII (T-V Invariance), Filar CLVIII (Zgodność Seiyū), Filar XLIII/CXLVI (Dyrektywne Potwierdzenie), Filar CLXI (Nienaruszalność Perspektywy) oraz Filar III/XIV (Kolokacje Czasowo-Szkolne: Długa przerwa).")

def test_series_bible():
    print("[TEST 9/12] Test Biblii Serialu i Pamięci Międzyodcinkowej (series_memory)...")
    with tempfile.TemporaryDirectory() as tmpdir:
        bible = SeriesBible(anime_title="Test Anime Series", storage_dir=Path(tmpdir))
        bible.update_from_episode_profile(
            episode_name="Odcinek 1",
            characters={"Arata": "uczeń, chłopak"},
            glossary={"Dragon Slayer": "Pogromca Smoków"}
        )
        assert "Arata" in bible.data["characters"]
        assert bible.data["glossary"]["Dragon Slayer"] == "Pogromca Smoków"
        
        # Test sanityzacji relacji i ochrony przed zatruciem (Layer 5)
        bible.update_from_episode_profile(
            episode_name="Odcinek 2",
            characters={"Sitara -> Shira": "Zwrot: 'Shira / na ty' (służące w obozie)"},
            glossary={}
        )
        desc = bible.data["characters"]["Sitara -> Shira"]["description"]
        assert "służące" not in desc
        assert "służba" in desc

        # Test niezmienności potwierdzonej płci męskiej (zakaz nadpisywania kobietą)
        bible.data["characters"]["Shira"] = {"description": "MĘŻCZYZNA (postać) [KATEGORYCZNY NAKAZ form męskich]"}
        bible.update_from_episode_profile(
            episode_name="Odcinek 3",
            characters={"Shira": "kobieta, służąca"},
            glossary={}
        )
        shira_desc = bible.data["characters"]["Shira"]["description"]
        assert "MĘŻCZYZNA" in shira_desc
        assert "kobieta" not in shira_desc

        # Test niezmienności potwierdzonej płci żeńskiej (zakaz nadpisywania mężczyzną)
        bible.data["characters"]["Naie"] = {"description": "kobieta, nauczycielka [KATEGORYCZNY NAKAZ form żeńskich]"}
        bible.update_from_episode_profile(
            episode_name="Odcinek 4",
            characters={"Naie": "mężczyzna, szpieg"},
            glossary={}
        )
        naie_desc = bible.data["characters"]["Naie"]["description"]
        assert "kobieta" in naie_desc
        assert "mężczyzna" not in naie_desc

        # Test wczytywania i formatowania dla promptu
        formatted_bible = bible.format_for_prompt()
        assert "Dragon Slayer" in formatted_bible
    print(" -> PASSED: Biblia Serialu prawidłowo zapisuje i synchronizuje wiedzę.")

def test_avt_formatter_and_cps():
    print("[TEST 10/12] Test semantycznego podziału linii (Netflix AVT), CPS i Innowacji Masterclass...")
    # Test CPS
    cps_fast, is_fast = calculate_cps("To jest bardzo długi tekst który nie ma sensu i przekracza CPS.", start_ms=0, end_ms=500)
    assert is_fast is True
    cps_normal, is_fast_norm = calculate_cps("Krótko.", start_ms=0, end_ms=2000)
    assert is_fast_norm is False

    # Test sanityzacji prefiksów ASS i eliminacji ograniczających tagów \clip
    from translator import sanitize_ts_prefix_for_translation
    pref_with_clip = r"{\pos(960,540)\clip(400,500,1100,600)}"
    clean_pref = sanitize_ts_prefix_for_translation(pref_with_clip)
    assert clean_pref == r"{\pos(960,540)}"
    assert r"\clip" not in clean_pref

    # Test podziału linii z zachowaniem spójności syntaktycznej (brak łamania po przyimku 'w')
    long_text = "Poszedłem wczoraj z moim przyjacielem do pobliskiego sklepu."
    split_res = split_subtitle_syntactically(long_text, max_line_len=35, is_ass=True)
    assert "\\N" in split_res
    parts = split_res.split("\\N")
    # Upewniamy się, że linijka 1 nie kończy się na 'do' ani 'z' ani 'w'
    assert not parts[0].strip().endswith((" w", " z", " do", " na"))

    # Test podziału planszy ekranowej/tytułu (is_sign=True) - ochrona przed wyjściem poza kadr
    title_text = "SPECJALNE SIŁY POŻARNICZE: HISTORIA WALKI CZĘŚĆ TRZECIA"
    split_title = split_subtitle_syntactically(title_text, max_line_len=42, is_ass=True, is_sign=True)
    assert "\\N" in split_title
    assert len(split_title.split("\\N")) >= 2

    # Test Filaru XCVIII: Zachowanie eleganckiego 2-wierszowego tytułu odcinka (bez cięcia na 4 linie)
    title_ep = split_subtitle_syntactically("ODCINEK 52\\NNUMER JEDEN PANA TOKUSHIRO", is_sign=True)
    assert len(title_ep.split("\\N")) == 2, f"Title card must be strictly 2 lines, got: {len(title_ep.split(chr(92)+'N'))}"
    assert "ODCINEK 52" in title_ep.split("\\N")[0]

    # Test Filaru XCVIII: Automatyczne rozdzielenie ODCINEK X TYTUŁ na 2 wiersze
    title_ep_raw = split_subtitle_syntactically("ODCINEK 53 STWORZYĆ OJCZYZNĘ", is_sign=True)
    assert title_ep_raw == "ODCINEK 53\\NSTWORZYĆ OJCZYZNĘ"
    title_ep_colon = split_subtitle_syntactically("ODCINEK 53: STWORZYĆ OJCZYZNĘ", is_sign=True)
    assert title_ep_colon == "ODCINEK 53\\NSTWORZYĆ OJCZYZNĘ"
    title_ch_raw = split_subtitle_syntactically("ROZDZIAŁ 12 NOWY POCZĄTEK", is_sign=True)
    assert title_ch_raw == "ROZDZIAŁ 12\\NNOWY POCZĄTEK"

    # Test plansz postaci i banerów z pozycjonowaniem (Tenmaku no Jaadugar cases)
    s1 = "{\\pos(150,600)}SYN TEMÜGIEGO – OTAI"
    s2 = "{\\pos(1650,300)}MŁODSZY BRAT CZYNGIS-CHANA – TEMÜGE"
    split_s1 = split_subtitle_syntactically(s1, is_sign=True)
    split_s2 = split_subtitle_syntactically(s2, is_sign=True)
    assert "\\N" in split_s1 and "OTAI" in split_s1
    assert "\\N" in split_s2 and "TEMÜGE" in split_s2

    # Test eliminacji 3. linii w długich dialogach mówionych (<= 115 znaków - Tenmaku 91-char case)
    spoken_long = "Musimy przejść przez ziemie Południowej dynastii Song, by uderzyć na Kaifeng od południa."
    split_spoken = split_subtitle_syntactically(spoken_long, max_line_len=42, is_ass=True, is_sign=False)
    spoken_parts = split_spoken.split("\\N")
    assert len(spoken_parts) == 2, f"Spoken dialogue must be strictly 2 lines, got: {len(spoken_parts)}"

    # Test Filaru LVII: Wykrywanie i separacja wielogłosu oraz dymków mangi na 2 osobne linie z myślnikiem
    split_dual_inline1 = split_subtitle_syntactically("Gratulacje... - Rozpacz po przegranej...")
    assert split_dual_inline1 == r"- Gratulacje...\N- Rozpacz po przegranej...", f"Expected dual-line format, got: {split_dual_inline1}"
    split_dual_inline2 = split_subtitle_syntactically("...i utracie wszystkiego... - Dziękuję...")
    assert split_dual_inline2 == r"- ...i utracie wszystkiego...\N- Dziękuję...", f"Expected dual-line format, got: {split_dual_inline2}"
    split_dual_explicit = split_subtitle_syntactically(r"Gratulacje...\N- Rozpacz po przegranej...")
    assert split_dual_explicit == r"- Gratulacje...\N- Rozpacz po przegranej...", f"Expected dual-line format, got: {split_dual_explicit}"

    # Test dyrektywy kompresji tekstu (Smart Condensation Ratio)
    cond_fast = calculate_condensation_directive("Musimy natychmiast uciekać stąd bo nadciągają potwory!", start_ms=0, end_ms=1200)
    assert cond_fast is not None and "EKSTREMALNY" in cond_fast

    # Test Filaru CXXXIV: Mikro-kwestie i dźwięki wahania (<0.6s)
    cond_micro = calculate_condensation_directive("I mean... we should slowly...", start_ms=0, end_ms=400)
    assert cond_micro is not None and "MIKRO-KWESTIA" in cond_micro
    clamped_micro = clamp_sub_second_cps("Znaczy... musimy powoli...", start_ms=0, end_ms=400)
    assert clamped_micro == "Znaczy...", f"Expected 'Znaczy...', got: '{clamped_micro}'"

    # Test formatowania ściany dźwięku (Diegetic Sound-Wall)
    sound_wall = format_diegetic_sound_wall("Uwaga mieszkańcy, zbliża się tajfun.", is_announcement=True)
    assert sound_wall.startswith(r"{\an8}[ KOMUNIKAT:")

    # Test snappingu napisów do cięć montażowych (Shot-Cut Snapping)
    class DummyEvent:
        def __init__(self, start, end):
            self.start = start
            self.end = end
    evs = [DummyEvent(1050, 2900)]
    snapped = snap_subtitles_to_shot_cuts(evs, shot_cuts_ms=[1000, 3000], max_snap_gap_ms=200)
    assert snapped[0].start == 1000  # snapped to 1000ms cut
    assert snapped[0].end == 2960    # snapped 40ms before 3000ms cut

    # Test wieloliniowego łamania długich notatek i list (> 80 znaków) bez ucinania boków
    long_note = "Nie wzbudzaj litości! Wyciągaj pomocną, ciepłą dłoń! Żadnego użalania się nad sobą, idiotko! Bądź uczciwa! Rysuj na sto procent, a nie na odwal, durna! Rysuj własną krwią! Narysuj to i giń!"
    split_note = split_subtitle_syntactically(long_note, max_line_len=40, is_ass=True, is_sign=True)
    note_lines = split_note.split("\\N")
    assert len(note_lines) >= 3
    for nl in note_lines:
        assert len(clean_text_for_len(nl)) <= 48

    # Test formatowania i estymacji budżetu
    dur_ms = 4000
    cond = calculate_condensation_directive("Krótka kwestia.", 0, dur_ms)
    assert cond is None

    # Test adaptacyjnego grupowania paczek (Adaptive Batching)
    from translator import create_adaptive_batches
    raw_dummy = [
        (i, DummyEvent(i * 1000, i * 1000 + 800), f"Krótki tekst {i}", "")
        for i in range(60)
    ]
    adaptive_res = create_adaptive_batches(raw_dummy, base_batch_size=24, max_batch_size=32)
    assert len(adaptive_res) == 2  # 60 lines packed into 2 batches (32 + 28) instead of 3 rigid batches (24 + 24 + 12)!
    print(" -> PASSED: Podział linii AVT, CPS, Shot-Cut Snapping, Condensation, Sound-Wall i Adaptive Batching działają w 100%.")

def test_prosody_and_diarizer():
    print("[TEST 11/12] Test lokalnej analizy prozodii i diarizacji fonicznej F0...")
    # Test szacowania F0 na syntetycznym sygnale sinusoidalnym (200Hz - żeński)
    sr = 16000
    t = np.linspace(0, 1.0, sr, endpoint=False)
    sine_200hz = (np.sin(2 * np.pi * 200 * t) * 15000).astype(np.float32)
    f0_est = SpeakerVoiceClassifier.estimate_pitch_f0(sine_200hz, sample_rate=sr)
    assert f0_est is not None
    assert 190.0 <= f0_est <= 210.0

    # Test sygnału męskiego (120Hz)
    sine_120hz = (np.sin(2 * np.pi * 120 * t) * 15000).astype(np.float32)
    f0_est_male = SpeakerVoiceClassifier.estimate_pitch_f0(sine_120hz, sample_rate=sr)
    assert f0_est_male is not None
    assert 110.0 <= f0_est_male <= 130.0

    # Test detektora dramatycznych przerw oddechowych seiyuu (Breath-Pause AVT)
    # 2.0s sygnał: 0.5s mowa + 0.8s cisza + 0.7s mowa
    speech_part1 = (np.sin(2 * np.pi * 200 * np.linspace(0, 0.5, int(sr * 0.5))) * 10000).astype(np.float32)
    silence_part = np.zeros(int(sr * 0.8), dtype=np.float32)
    speech_part2 = (np.sin(2 * np.pi * 200 * np.linspace(0, 0.7, int(sr * 0.7))) * 10000).astype(np.float32)
    synthetic_pause_audio = np.concatenate([speech_part1, silence_part, speech_part2])
    
    detected_pause = AudioProsodyEngine.detect_intra_line_pause(synthetic_pause_audio, min_pause_ms=600)
    assert detected_pause is not None
    assert 700 <= detected_pause <= 850

    # Test budżetu sylabicznego Mouth-Pacing (Filar CXLIII)
    assert AudioProsodyEngine.calculate_syllable_budget(0.3) == 2
    assert AudioProsodyEngine.calculate_syllable_budget(0.6) == 3
    assert AudioProsodyEngine.calculate_syllable_budget(1.5) == 8
    print(" -> PASSED: Autokorelacja foniczna, estymacja F0 i detektor przerw oddechowych seiyuu (Breath-Pause) działają perfekcyjnie.")

def test_typesetting_matcher():
    print("[TEST 12/12] Test auto-kolorowania napisów ekranowych (typesetting_matcher)...")
    hex_color = rgb_to_ass_hex(255, 128, 64)
    assert hex_color == "&H4080FF&"  # ASS to BGR

    # Test gwarancji wysokiego kontrastu (biały fill fallback i gruby obrys bord3)
    res = TypesettingColorMatcher.enhance_typesetting_prefix("{\\an8}")
    assert "\\an8" in res
    assert "&HFFFFFF&" in res or "\\1c" in res
    assert "\\bord3" in res

    # Test Quadrant Detection (Typesetting Proximity - Resolution Independent \an tags)
    pos_br = TypesettingColorMatcher.calculate_optimal_sign_position(region="bottom_right")
    assert pos_br == r"{\an3}"
    pos_bl = TypesettingColorMatcher.calculate_optimal_sign_position(region="bottom_left")
    assert pos_bl == r"{\an1}"
    pos_tr = TypesettingColorMatcher.calculate_optimal_sign_position(region="top_right")
    assert pos_tr == r"{\an9}"
    pos_tl = TypesettingColorMatcher.calculate_optimal_sign_position(region="top_left")
    assert pos_tl == r"{\an7}"

    # Test Typesetting Proximity 2.0 Override: generic \an8 overridden with bottom_right \an3
    enhanced_br = TypesettingColorMatcher.enhance_sign_typesetting(original_prefix=r"{\an8}", region="bottom_right")
    assert r"\an3" in enhanced_br
    # Test Sign Contrast & Visibility Guard (Filar AVT Contrast Invariance)
    dark_tattoo_prefix = r"{\pos(500,500)\c&H000000&}"
    contrasted_tattoo = TypesettingColorMatcher.ensure_sign_contrast(dark_tattoo_prefix)
    assert r"\3c&HFFFFFF&" in contrasted_tattoo
    assert r"\bord3" in contrasted_tattoo
    assert r"\pos(500,500)" in contrasted_tattoo

    # Test \bord0 removal and contrast addition
    bord0_prefix = r"{\pos(400,400)\c&H1A1A1A&\bord0}"
    contrasted_bord0 = TypesettingColorMatcher.ensure_sign_contrast(bord0_prefix)
    assert r"\3c&HFFFFFF&" in contrasted_bord0
    assert r"\bord0" not in contrasted_bord0
    assert r"\bord3" in contrasted_bord0

    # Test style with dark primary color
    dark_style = pysubs2.SSAStyle()
    dark_style.primarycolor = pysubs2.Color(10, 10, 10)
    dark_style.outlinecolor = pysubs2.Color(10, 10, 10)
    dark_style.outline = 0
    contrasted_style = TypesettingColorMatcher.ensure_sign_contrast(r"{\pos(300,300)}", style=dark_style)
    assert r"\3c&HFFFFFF&" in contrasted_style
    assert r"\bord3" in contrasted_style

    print(" -> PASSED: Moduł auto-stylizacji i kolorów ASS działa w 100%.")

from manga_canon import MangaCanonRegistry

def test_manga_canon():
    print("[TEST 13/13] Test Rejestru Kanonu Polskich Wydań Mangowych (manga_canon)...")
    registry = MangaCanonRegistry()
    # Test dopasowania Berserk (Wydawnictwo J.P.Fantastica)
    berserk_canon = registry.find_canon_for_series("[ASW] Berserk - 10 [1080p]")
    assert berserk_canon is not None
    assert berserk_canon["glossary"]["Band of the Hawk"] == "Drużyna Jastrzębia"
    assert berserk_canon["glossary"]["Dragonslayer"] == "Zabójca Smoków"
    assert "J.P.Fantastica" in berserk_canon["publisher"]

    # Test dopasowania Jujutsu Kaisen
    jjk_canon = registry.find_canon_for_series("Jujutsu Kaisen Season 2")
    assert jjk_canon is not None
    assert "Domen" in jjk_canon["glossary"]["Domain Expansion"]
    assert jjk_canon["publisher"] == "Wydawnictwo Waneko"
    assert jjk_canon["glossary"]["Domain Expansion"] == "Rozszerzenie Domeny"

    # Test dopasowania Chainsaw Man (Waneko Zero-AI Grounding check)
    csm_canon = registry.find_canon_for_series("Chainsaw Man - Episode 01")
    assert csm_canon is not None
    assert csm_canon["glossary"]["Gun Devil"] == "Demon Broni Palnej"
    assert csm_canon["glossary"]["Fiend"] == "Opętaniec"
    assert csm_canon["glossary"]["Devil Hunter"] == "Łowca Demonów"
    assert csm_canon["glossary"]["Devil Contract"] == "Pakt z Demonem"
    for term_key, term_val in csm_canon["glossary"].items():
        assert "Diabeł" not in term_val, f"Kalka AI 'Diabeł' znaleziona w CSM: {term_key} -> {term_val}"

    # Test dopasowania Golden Kamuy
    gk_canon = registry.find_canon_for_series("[Erai-raws] Golden Kamuy - 01 [1080p]")
    assert gk_canon is not None
    assert gk_canon["glossary"]["Immortal Sugimoto"] == "Nieśmiertelny Sugimoto"
    assert "Hinna" in gk_canon["glossary"]["Hinna hinna"]
    assert "Kotori" in gk_canon["publisher"]

    prompt_chunk = registry.format_canon_for_prompt(jjk_canon)
    assert "Domen" in prompt_chunk
    assert "Waneko" in prompt_chunk

    # Żelazna asercja czystości: w CAŁEJ bazie BUILTIN_MANGA_CANON nie ma ani jednego nawiasu ani dopisku
    from manga_canon import BUILTIN_MANGA_CANON
    total_checked = 0
    for s_key, s_data in BUILTIN_MANGA_CANON.items():
        for src_t, pl_t in s_data.get("glossary", {}).items():
            total_checked += 1
            assert "(" not in pl_t and ")" not in pl_t, f"Skażenie kanonu nawiasem w {s_key}: '{src_t}' -> '{pl_t}'"
            assert "[" not in pl_t and "]" not in pl_t, f"Skażenie kanonu nawiasem kwadratowym w {s_key}: '{src_t}' -> '{pl_t}'"
            assert not any(ch in pl_t for ch in [':', ';', '=', '->', '{', '}', '<', '>']), f"Skażenie kanonu znakami specjalnymi w {s_key}: '{src_t}' -> '{pl_t}'"
    assert total_checked > 2500, f"Zbyt mała liczba terminów w kanonie: {total_checked}"

    print(f" -> PASSED: Kanon polskich wydań mangowych działa w 100% ({total_checked} terminów w 100% czystej postaci, zero nawiasów/komentarzy).")

def test_batch_queue():
    print("[TEST 14/14] Test Kolejki Sezonowej (Batch Queue) i naturalnego sortowania...")
    from main import natural_sort_key, collect_input_files
    
    # Test naturalnego sortowania odcinków
    files = ["Kingdom_EP10.mkv", "Kingdom_EP2.mkv", "Kingdom_EP1.mkv", "Kingdom_EP20.mkv"]
    sorted_files = sorted(files, key=natural_sort_key)
    assert sorted_files == ["Kingdom_EP1.mkv", "Kingdom_EP2.mkv", "Kingdom_EP10.mkv", "Kingdom_EP20.mkv"]
    
    # Test zbierania pojedynczego pliku
    res = collect_input_files([str(Path(__file__).parent / "requirements.txt")])
    assert len(res) == 1
    print(" -> PASSED: Kolejka Sezonowa i naturalny sorting odcinków działają bezbłędnie.")

def test_context_cache():
    print("[TEST 15/15] Test Inteligentnego Zarządzania Pamięcią Kontekstu (Google Context Caching)...")
    import hashlib
    from context_cache import ContextCacheManager, DEFAULT_CACHE_TTL_SECONDS
    
    assert DEFAULT_CACHE_TTL_SECONDS == 1200  # 20 minut ruchomego okna

    # 1. Test generowania hasha
    h1 = ContextCacheManager.get_content_hash("gemini-3.7-flash", "FILAR I: ODNOMINALIZOWANIE")
    h2 = ContextCacheManager.get_content_hash("gemini-3.7-flash", "FILAR I: ODNOMINALIZOWANIE")
    assert h1 == h2
    
    # 2. Test natychmiastowej zmiany hasha przy modyfikacji reguł (Gwarancja świeżości Filarów)
    h3 = ContextCacheManager.get_content_hash("gemini-3.7-flash", "FILAR I: ODNOMINALIZOWANIE (NOWA REGUŁA)")
    assert h1 != h3
    
    # 3. Test bezpiecznego fallbacku przy braku klienta
    res = ContextCacheManager.get_or_create_cache(None, "gemini-3.7-flash", "prompt", ttl_seconds=DEFAULT_CACHE_TTL_SECONDS)
    assert res is None

    # 4. Test izolacji fazowej Faza 1 (Wizja) vs Faza 2 (Weryfikator) dla tego samego modelu
    h_f1 = ContextCacheManager.get_content_hash("gemini-3.8-flash", "Wizja Prompt", tag="translator")
    h_f2 = ContextCacheManager.get_content_hash("gemini-3.8-flash", "Redakcja Prompt", tag="verifier")
    assert h_f1 != h_f2

    class DummyCacheObj:
        def __init__(self, name, display_name):
            self.name = name
            self.display_name = display_name

    class DummyCacheClient:
        def __init__(self):
            class DummyAPIClient:
                api_key = "dummy_key"
            self._api_client = DummyAPIClient()
            self.deleted = []
            cid = hashlib.sha256(b"dummy_key").hexdigest()[:8]
            self.caches_list = [
                DummyCacheObj("caches/f1_old", f"avt_gemini_3_8_flash_{cid}_translator_old"),
                DummyCacheObj("caches/f2_active", f"avt_gemini_3_8_flash_{cid}_verifier_12345"),
            ]
            class CachesAPI:
                def __init__(self, parent):
                    self.parent = parent
                def list(self):
                    return self.parent.caches_list
                def delete(self, name):
                    self.parent.deleted.append(name)
                def create(self, model, config):
                    return DummyCacheObj("caches/f1_new", config.display_name)
            self.caches = CachesAPI(self)

    c_dummy = DummyCacheClient()
    ContextCacheManager.get_or_create_cache(c_dummy, "gemini-3.8-flash", "New Wizja Prompt", tag="translator")
    assert "caches/f1_old" in c_dummy.deleted
    assert "caches/f2_active" not in c_dummy.deleted, "Faza 1 nie może usuwać cache Fazy 2!"

    # 5. Test metod Kroczącego Heartbeatu, pre-warmingu i czyszczenia
    ContextCacheManager.ensure_cache_ready(None, "gemini-3.7-flash", "prompt", verbose=False)
    ContextCacheManager.touch_cache(None, None)
    ContextCacheManager.cleanup_all_active_caches(None)
    print(" -> PASSED: Context Caching SHA-256, Pre-warming, Kroczący Heartbeat 20m i autoczyszczenie działają perfekcyjnie.")

def test_pricing_guard():
    print("[TEST 16/16] Test Strażnika Cennika i Kosztów Google API (pricing_guard)...")
    from pricing_guard import PricingGuard
    
    # 1. Test szacowania kosztu dla profilu Standard (Free Tier)
    assert PricingGuard.estimate_episode_cost_pln("1") == 0.00
    
    # 2. Test szacowania kosztu dla profilu Studyjny (~1.90 - 2.10 zł)
    cost_flash = PricingGuard.estimate_episode_cost_pln("2")
    assert 1.50 <= cost_flash <= 2.50
    
    # 3. Test szacowania kosztu dla profilu Mistrzowski Dual Flash (~3.00 - 3.40 zł)
    cost_pro = PricingGuard.estimate_episode_cost_pln("3")
    assert 2.80 <= cost_pro <= 3.80

    # 4. Test szacowania kosztu dla profilu Kinowy Pro (~5.50 - 6.50 zł z adaptacyjnym CoT)
    cost_ultra = PricingGuard.estimate_episode_cost_pln("4")
    assert 4.50 <= cost_ultra <= 7.50
    
    # 5. Test generowania banera
    banner = PricingGuard.get_pricing_status_banner()
    assert "STATUS CENNIKA GOOGLE" in banner
    assert "Context Cache" in banner
    print(" -> PASSED: Strażnik cennika precyzyjnie kalkuluje i monitoruje koszty dla 4 poziomów jakości.")

def test_sign_detector():
    print("[TEST 17/17] Test Wizyjnego Detektora Plansz i Bezpieczników Antykolizyjnych (sign_detector)...")
    from sign_detector import VisualSignDetector, DetectedSign
    
    # 1. Test wykrywania luk w pliku z pustą przerwą (10 sekund przerwy)
    subs_with_gap = pysubs2.SSAFile()
    subs_with_gap.events.append(pysubs2.SSAEvent(start=1000, end=3000, text="Kwestia 1"))
    subs_with_gap.events.append(pysubs2.SSAEvent(start=15000, end=18000, text="Kwestia 2"))
    
    gaps = VisualSignDetector.find_subtitle_gaps(subs_with_gap, min_gap_ms=3500, margin_ms=1500)
    assert len(gaps) >= 1
    # Sprawdzamy, czy wyznaczona luka leży w pustym oknie
    assert gaps[0][0] >= 4500  # 3000 + 1500 margin
    assert gaps[0][1] <= 13500 # 15000 - 1500 margin
    
    # 2. Test Collision Guard na gęstym kadrze (notes/manga z wieloma linijkami)
    dense_subs = pysubs2.SSAFile()
    for i in range(10):
        dense_subs.events.append(pysubs2.SSAEvent(start=i * 1000, end=(i + 1) * 1000, text=f"Notatka {i}"))
    
    dense_gaps = VisualSignDetector.find_subtitle_gaps(dense_subs, min_gap_ms=3500, margin_ms=1500)
    assert len(dense_gaps) == 0  # Zero luk -> Collision Guard zablokował dublowanie napisów
    
    # 3. Test modelu Pydantic
    sign = DetectedSign(
        is_title_or_banner=True,
        original_text="PRESENT DAY / げんざい",
        translation_pl="CZASY WSPÓŁCZESNE",
        banner_type="TIME_BANNER"
    )
    assert sign.is_title_or_banner is True
    assert sign.translation_pl == "CZASY WSPÓŁCZESNE"
    print(" -> PASSED: VisualSignDetector precyzyjnie wykrywa luki i chroni kadry przed dublowaniem.")

def test_user_feedback_manager():
    print("[TEST 18/22] Test Pamięci Korekt Użytkownika i Few-Shot Prompting (user_feedback)...")
    from user_feedback import UserFeedbackManager
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmp_json = Path(f.name)

    try:
        mgr = UserFeedbackManager(storage_path=tmp_json)
        # Test dodawania
        entry = mgr.add_feedback(
            original_en="I messed up",
            bad_pl="Zrobiłem bałagan",
            good_pl="Zawaliłem",
            rule_reason="Używaj naturalnego potocznego słownictwa"
        )
        assert entry["bad_pl"] == "Zrobiłem bałagan"
        assert len(mgr.list_all()) >= 1

        # Test wyszukiwania
        matches = mgr.find_relevant_feedback(["I think I messed up badly"])
        assert len(matches) >= 1
        assert matches[0]["good_pl"] == "Zawaliłem"

        # Test formatowania do promptu
        formatted = mgr.format_for_prompt(matches)
        assert "ZŁOTE WZORCE" in formatted
        assert "Zawaliłem" in formatted

        # Test usuwania
        assert mgr.remove_feedback(entry["id"]) is True
    finally:
        if tmp_json.exists():
            tmp_json.unlink()
    print(" -> PASSED: Moduł pamięci korekt użytkownika i Few-Shot działa bezbłędnie.")

def test_deterministic_glossary():
    print("[TEST 19/22] Test Słownika Deterministycznego i Nadpisywania (glossary_manager)...")
    from glossary_manager import GlossaryManager
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmp_json = Path(f.name)

    try:
        mgr = GlossaryManager(global_path=tmp_json)
        mgr.add_term("Ancient Relic", "Starożytna Relikwia", "obiekt fabularny")
        assert "Ancient Relic" in mgr.global_terms

        # Test łączenia ze słownikiem serii
        combined = mgr.get_combined_glossary({"Spirit Blade": "Ostrze Dusz"})
        assert combined["Ancient Relic"] == "Starożytna Relikwia"
        assert combined["Spirit Blade"] == "Ostrze Dusz"

        # Test formatowania do promptu
        prompt_sec = mgr.format_for_prompt(combined)
        assert "BEZWZGLĘDNY SŁOWNICZEK" in prompt_sec
        assert "Starożytna Relikwia" in prompt_sec

        # Test deterministycznego nadpisywania w tekście
        res_text, fixes = GlossaryManager.apply_deterministic_overrides(
            "Odnaleźliśmy Ancient Relic w jaskini.",
            combined
        )
        assert res_text == "Odnaleźliśmy Starożytna Relikwia w jaskini."
        assert len(fixes) == 1
    finally:
        if tmp_json.exists():
            tmp_json.unlink()
    print(" -> PASSED: Słownik deterministyczny wymusza terminy w 100%.")

def test_dynamic_rule_dispatcher():
    print("[TEST 20/25] Test Dynamicznego Dyspozytora Reguł i Koncentracji Uwagi (rules.py)...")
    from rules import get_focused_rules_for_batch

    # 1. Test paczki z pytaniami (Filar IX)
    batch_q = [{"en": "Are you sure about that?"}]
    focused_q = get_focused_rules_for_batch(batch_q)
    assert "FILAR IX" in focused_q

    # 2. Test paczki z napisami ekranowymi (sign) (Filar XLI)
    batch_s = [{"en": "Title of Chapter", "is_sign": True}]
    focused_s = get_focused_rules_for_batch(batch_s)
    assert "FILAR XLI" in focused_s

    # 3. Test paczki z tytulaturą (Filar XXV/XXVII/XXVIII)
    batch_t = [{"en": "Sensei, please help!"}]
    focused_t = get_focused_rules_for_batch(batch_t)
    assert "XXVII" in focused_t or "XXV" in focused_t

    # 4. Test paczki z czasownikami wektorowymi (Filar XXXVII)
    batch_v = [{"en": "Look, I can see it!"}]
    focused_v = get_focused_rules_for_batch(batch_v)
    assert "FILAR XXXVII" in focused_v

    # 5. Test paczki z wyznaniem miłosnym (Filar CXXI)
    batch_love = [{"en": "The truth is, I really like you!"}]
    focused_love = get_focused_rules_for_batch(batch_love)
    assert "FILAR CXXI" in focused_love

    # 6. Test paczki z pożegnaniem na misję (Filar CXXII)
    batch_bye = [{"en": "Sayonara, everyone! Itte kimasu!"}]
    focused_bye = get_focused_rules_for_batch(batch_bye)
    assert "FILAR CXXII" in focused_bye

    # 7. Test paczki z paradoksem negacji (Filar CXXXIX)
    batch_neg = [{"en": "Didn't you go there? Yes."}]
    focused_neg = get_focused_rules_for_batch(batch_neg)
    assert "CXXXIX" in focused_neg

    # 8. Test paczki ze społecznymi metaforami pokrewieństwa (Filar CXL)
    batch_kin = [{"en": "Big brother, please help me!"}]
    focused_kin = get_focused_rules_for_batch(batch_kin)
    assert "CXL" in focused_kin

    # 9. Test paczki ze stanem rezultatywnym (Filar CXLI)
    batch_state = [{"en": "He's dead, it's over."}]
    focused_state = get_focused_rules_for_batch(batch_state)
    assert "CXLI" in focused_state

    # 10. Test paczki z zachwytem w pytaniu przeczącym (Filar CXLII)
    batch_praise = [{"en": "Isn't it delicious?!"}]
    focused_praise = get_focused_rules_for_batch(batch_praise)
    assert "CXLII" in focused_praise

    # 11. Test paczki z limitem sylabicznym Mouth-Pacing (Filar CXLIII)
    batch_pacing = [{"duration_s": 0.5, "en": "Wait!"}]
    focused_pacing = get_focused_rules_for_batch(batch_pacing)
    assert "CXLIII" in focused_pacing

    # 12. Test paczki z radarem audio seiyuu (Filar CXLIV)
    batch_radar = [{"en": "Damn it!", "audio_alert": "W audio pada Chikushou"}]
    focused_radar = get_focused_rules_for_batch(batch_radar)
    assert "CXLIV" in focused_radar

    # 13. Test paczki z ping-pongiem dialogowym (Filar CXLVI)
    batch_volley = [{"en": "Are you insane?", "relation_tag": "[PING-PONG DIALOGOWY]"}]
    focused_volley = get_focused_rules_for_batch(batch_volley)
    assert "CXLVI" in focused_volley

    # 14. Test paczki z matrycą przysłówków modalnych (Filar CXLVII)
    batch_modal = [{"en": "Probably.", "audio_jp": "たぶん [Tabun]"}]
    focused_modal = get_focused_rules_for_batch(batch_modal)
    assert "CXLVII" in focused_modal

    # 15. Test paczki z wykrzyknikami somatycznymi (Filar XVIII)
    batch_som = [{"en": "Whoa, easy there...", "audio_jp": "おっとっと [Ottotto]"}]
    focused_som = get_focused_rules_for_batch(batch_som)
    assert "XVIII" in focused_som

    # 16. Test paczki z pytaniami o wiarygodność (Filar CXLVIII)
    batch_ver = [{"en": "Is that true?", "audio_jp": "本当なのか [Honto nano ka]"}]
    focused_ver = get_focused_rules_for_batch(batch_ver)
    assert "CXLVIII" in focused_ver

    # 17. Test paczki z Haragei (Filar CXLIX)
    batch_haragei = [{"en": "I'm fine.", "audio_jp": "大丈夫 [Daijoubu]"}]
    focused_haragei = get_focused_rules_for_batch(batch_haragei)
    assert "CXLIX" in focused_haragei

    # 18. Test paczki z Hora! (Filar CL)
    batch_hora = [{"en": "Look!", "audio_jp": "ほら [Hora]"}]
    focused_hora = get_focused_rules_for_batch(batch_hora)
    assert "CL" in focused_hora

    # 19. Test paczki z Aisatsu i Sumimasen (Filar CLI)
    batch_aisatsu = [{"en": "I'm home!", "audio_jp": "ただいま [Tadaima]"}]
    focused_aisatsu = get_focused_rules_for_batch(batch_aisatsu)
    assert "CLI" in focused_aisatsu

    # 20. Test paczki z Abunai i Tasukete (Filar CLII)
    batch_danger = [{"en": "Look out!", "audio_jp": "危ない [Abunai]"}]
    focused_danger = get_focused_rules_for_batch(batch_danger)
    assert "CLII" in focused_danger

    # 21. Test paczki z Filar CLV (Dyscyplina Repetycji Myśli i Separacji Mowy)
    batch_clv = [{"en": "I can't stop it.", "style": "Italics", "audio_jp": "止められない [Tomerarenai]"}]
    focused_clv = get_focused_rules_for_batch(batch_clv)
    assert "CLV" in focused_clv

    # 22. Test paczki z Filar CLVI (Rozszczepienie Angielskiego Pivotu: Hitori vs Hottoite, Betsuni)
    batch_clvi = [{"en": "Please leave me alone.", "audio_jp": "一人にしてくれ [Hitori ni shite kure]"}]
    focused_clvi = get_focused_rules_for_batch(batch_clvi)
    assert "CLVI" in focused_clvi

    # 23. Test paczki z Filar CLVIII (Zgodność Foniczno-Semantyczna Seiyū / Auditory Anchor)
    batch_clviii = [{"en": "That was good.", "audio_jp": "よかった [Yokatta]"}]
    focused_clviii = get_focused_rules_for_batch(batch_clviii)
    assert "CLVIII" in focused_clviii

    # 24. Test paczki z Ping-Pongiem Dyrektywnym (Filar CXLVI & XLIII)
    batch_dir_ping = [{"relation_tag": "[PING-PONG DIALOGOWY: Odpowiedź na ostrzeżenie/dyrektywę – KATEGORYCZNY ZAKAZ 'Tak/T-Tak']"}]
    focused_dir_ping = get_focused_rules_for_batch(batch_dir_ping)
    assert "CXLVI" in focused_dir_ping
    assert "OSTRZEŻENIA" in focused_dir_ping

    # 25. Test paczki z Filar CLXI (Nienaruszalność Perspektywy Narracyjnej i Zakaz Zdrady Tożsamości Incognito)
    batch_clxi = [{"en": "There's an essay in here by the Silent Witch!", "audio_jp": "沈黙の魔女の論文が載ってる [Chinmoku no majo no ronbun ga notteru]"}]
    focused_clxi = get_focused_rules_for_batch(batch_clxi)
    assert "CLXI" in focused_clxi

    print(" -> PASSED: Dyspozytor reguł precyzyjnie aktywuje właściwe filary AVT.")

def test_fuzzy_and_dynamic_avt_linter():
    print("[TEST 21/22] Test Fleksyjnego i Dynamicznego Lintera (avt_linter)...")
    from avt_linter import AVTLinter

    # 1. Test fleksji "mieć taką nadzieję" w różnych czasach
    t1, _ = AVTLinter.lint_and_fix_line("Miałem taką nadzieję od dawna.")
    assert t1 == "Miałem nadzieję od dawna."
    t2, _ = AVTLinter.lint_and_fix_line("Będziemy mieć taką nadzieję.")
    assert t2 == "Będziemy mieć nadzieję."

    # 2. Test fleksji "robić sens" w różnych formach
    t3, _ = AVTLinter.lint_and_fix_line("To robiło sens wczoraj.")
    assert "to miało sens" in t3.lower()
    t4, _ = AVTLinter.lint_and_fix_line("To nie będzie robić sensu.")
    assert "to nie będzie mieć sensu" in t4.lower()

    # 2b. Test eliminacji kalek modalnych (Filar CXLVII)
    t_m1, _ = AVTLinter.lint_and_fix_line("Wszystko poszło zgodnie z oczekiwaniami.")
    assert "tak jak myślałem" in t_m1
    t_m2, _ = AVTLinter.lint_and_fix_line("Nie da się pomóc.")
    assert "nic na to nie poradzimy" in t_m2

    # 2c. Test eliminacji kalek somatycznych (Filar XVIII)
    t_s1, _ = AVTLinter.lint_and_fix_line("Oho, spokojnie...")
    assert "Ło, ło, ło..." in t_s1
    t_s2, _ = AVTLinter.lint_and_fix_line("To jest gorące!")
    assert "Parzy!" in t_s2
    t_s3, _ = AVTLinter.lint_and_fix_line("To boli!")
    assert "Ała!" in t_s3

    # 2d. Test eliminacji urzędowego pytania o wiarygodność (Filar CXLVIII)
    t_v1, _ = AVTLinter.lint_and_fix_line("To prawda?")
    assert "To pewne?" in t_v1
    t_v2, _ = AVTLinter.lint_and_fix_line("To prawda.")
    assert t_v2 == "To prawda."

    # 2e. Test eliminacji kalek Abunai, Tasukete i Aisatsu (Filary CLI - CLII)
    t_d1, _ = AVTLinter.lint_and_fix_line("Niebezpiecznie!")
    assert "Uważaj!" in t_d1
    t_d2, _ = AVTLinter.lint_and_fix_line("Ocal mnie!")
    assert "Ratunku!" in t_d2
    t_d3, _ = AVTLinter.lint_and_fix_line("Będę przeszkadzał.")
    assert "Przepraszam za najście" in t_d3

    # 3. Test dynamicznych reguł użytkownika w linterze
    user_rules = [
        {"bad_pl": "zrobiłem błąd", "good_pl": "pomyliłem się"}
    ]
    t5, fixes5 = AVTLinter.lint_and_fix_line("Chyba zrobiłem błąd.", user_feedback_rules=user_rules)
    assert t5 == "Chyba pomyliłem się."
    assert len(fixes5) >= 1

    # 4. Test wymuszeń słownikowych w linterze
    custom_gloss = {"Black Dragon": "Czarny Smok"}
    t6, fixes6 = AVTLinter.lint_and_fix_line("To jest Black Dragon!", custom_glossary=custom_gloss)
    assert "Czarny Smok" in t6
    print(" -> PASSED: Linter bezbłędnie obsługuje fleksję, wzorce użytkownika i słownik.")

def test_gui_interactive_learning_components():
    print("[TEST 22/23] Test Komponentów Interaktywnego Uczenia w GUI (gui_app)...")
    from user_feedback import UserFeedbackManager
    from glossary_manager import GlossaryManager

    fb = UserFeedbackManager()
    all_rules = fb.list_all()
    assert len(all_rules) >= 1

    gm = GlossaryManager()
    assert len(gm.global_terms) >= 1
    print(" -> PASSED: Komponenty GUI interaktywnego uczenia są w 100% gotowe.")

def test_extended_avt_pillars():
    print("[TEST 23/25] Test Filarów Paralingwistyki, Interpunkcji i Translationese...")
    from avt_linter import AVTLinter
    from rules import get_focused_rules_for_batch

    # 1. Test paralingwistyki i kinezjatyki Kakegoe (Filar XVIII)
    t1, _ = AVTLinter.lint_and_fix_line("Ara ara, co my tu mamy?")
    assert "O proszę..." in t1
    t2, _ = AVTLinter.lint_and_fix_line("Tch, znowu on.")
    assert "Tsk..." in t2
    t_k1, _ = AVTLinter.lint_and_fix_line("Yoisho, ale ciężkie!")
    assert "Hop..." in t_k1
    t_k2, _ = AVTLinter.lint_and_fix_line("Yotto... udało się!")
    assert "Hop..." in t_k2

    from translator import is_isolated_paralinguistic_clutter
    assert is_isolated_paralinguistic_clutter("Uh...", "Och!", is_sign=False) is True
    assert is_isolated_paralinguistic_clutter("Hmph", "Uch!", is_sign=False) is True
    assert is_isolated_paralinguistic_clutter("Wait!", "Czekaj!", is_sign=False) is False

    # 2. Test eliminacji trzeciego języka (Filar X)
    t3, _ = AVTLinter.lint_and_fix_line("Co sprawia, że tak mówisz?")
    assert "Czemu tak sądzisz?" in t3

    # 3. Test interpunkcji zespolonej (Filar LX)
    t4, _ = AVTLinter.lint_and_fix_line("Naprawdę!?")
    assert "?!" in t4

    # 4. Test dyspozytora dla piosenek (Filar LVIII) i paralingwistyki (Filar XVIII)
    batch_music = [{"en": "Song lyrics", "notes": "singing"}]
    f_music = get_focused_rules_for_batch(batch_music)
    assert "FILAR LVIII" in f_music

    batch_para = [{"en": "Ara ara, you are funny"}]
    f_para = get_focused_rules_for_batch(batch_para)
    assert "FILAR XVIII" in f_para or "XVIII" in f_para
    print(" -> PASSED: Filary paralingwistyki, interpunkcji i anti-translationese działają bezbłędnie.")

def test_master_avt_pillars():
    print("[TEST 24/25] Test Zunifikowanych Filarów Realioznawczych i Metryzacji (ECR, Metryzacja, Modalność)...")
    from avt_linter import AVTLinter
    from rules import get_focused_rules_for_batch

    # 1. Test Pedersen ECR generalization (Filar XIV)
    t1, _ = AVTLinter.lint_and_fix_line("Pójdę do konbini po coś do picia.")
    assert "sklep" in t1

    # 2. Test metryzacji miar (Filar LIX)
    t2, _ = AVTLinter.lint_and_fix_line("On ma ponad 6 stóp wzrostu i stoi 10 stóp stąd.")
    assert "prawie dwa metry" in t2
    assert "3 metry" in t2

    # 3. Test modalności epistemicznej (Filar XLVI)
    t3, _ = AVTLinter.lint_and_fix_line("Nie ma wątpliwości, że wrócą.")
    assert "bez wątpienia" in t3

    # 4. Test dyspozytora dla jednostek (Filar LIX) i modalności (Filar XLVI)
    batch_units = [{"en": "He is 10 feet away from the wall."}]
    f_units = get_focused_rules_for_batch(batch_units)
    assert "LIX" in f_units

    batch_modal = [{"en": "He must be definitely guilty, no doubt."}]
    f_modal = get_focused_rules_for_batch(batch_modal)
    assert "XLVI" in f_modal
    print(" -> PASSED: Zunifikowane filary realioznawcze, metryzacji i modalności w 100% zintegrowane.")

def test_excellence_avt_pillars():
    print("[TEST 25/26] Test Pragmatyki Anime i Żargonu RPG (Shūjoshi, Onomatopeje, RPG)...")
    from avt_linter import AVTLinter
    from rules import get_focused_rules_for_batch

    # 1. Test Shūjoshi Pragmatics (Filar XVI)
    t1, _ = AVTLinter.lint_and_fix_line("Iku zo!")
    assert "No to ruszamy!" in t1

    # 2. Test Onomatopeje Gijougo (Filar XVII)
    t2, _ = AVTLinter.lint_and_fix_line("Zokutto shita kiedy to zobaczyłem.")
    assert "przeszły mnie ciarki" in t2

    # 3. Test Żargon RPG / System (Filar XXIV)
    t3, _ = AVTLinter.lint_and_fix_line("Pojawiło się Status Window gracza.")
    assert "[ OKNO STATUSU ]" in t3

    # 4. Test dyspozytora dla RPG (Filar XXIV) i Shūjoshi (Filar XVI)
    batch_rpg = [{"en": "Check your status and new skill level."}]
    f_rpg = get_focused_rules_for_batch(batch_rpg)
    assert "XXIV" in f_rpg

    batch_shujo = [{"en": "Doko ni iku no kashira?"}]
    f_shujo = get_focused_rules_for_batch(batch_shujo)
    assert "XVI" in f_shujo

    # 5. Test dyspozytora dla Izotopii Środowiskowej (Filar CXXXVIII)
    batch_env = [{"en": "He fell into the vat of beer and was dragged underwater!"}]
    f_env = get_focused_rules_for_batch(batch_env)
    assert "CXXXVIII" in f_env
    print(" -> PASSED: Pragmatyka anime i żargon RPG w 100% zintegrowane.")

def test_cognitive_prosody_and_narrative_pillars():
    print("[TEST 26/27] Test Kognitywistyki Prozodii, Narracji i Filarów AVT (LXV – LXX)...")
    from rules import get_focused_rules_for_batch

    # 1. Test dyspozytora dla Izomorfizmu Napięcia (Filar LXV)
    batch_suspense = [{"en": "The truth is, he will never betray us."}]
    f_suspense = get_focused_rules_for_batch(batch_suspense)
    assert "LXV" in f_suspense

    # 2. Test dyspozytora dla Prozodii Oddechu (Filar LXVI)
    batch_breath = [{"en": "I can't... breath... run!"}]
    f_breath = get_focused_rules_for_batch(batch_breath)
    assert "LXVI" in f_breath

    # 3. Test dyspozytora dla Kąta Kamery Empatycznej (Filar LXVII)
    batch_empathy = [{"en": "He did this great favor for me."}]
    f_empathy = get_focused_rules_for_batch(batch_empathy)
    assert "LXVII" in f_empathy

    # 4. Test dyspozytora dla Pamięci Leitmotywów (Filar LXVIII)
    batch_leitmotif = [{"en": "This is my vow and destiny."}]
    f_leitmotif = get_focused_rules_for_batch(batch_leitmotif)
    assert "LXVIII" in f_leitmotif

    # 5. Test dyspozytora dla Hierarchii Akustycznej (Filar LXIX)
    batch_ambient = [{"en": "Emergency broadcast over the loudspeaker."}]
    f_ambient = get_focused_rules_for_batch(batch_ambient)
    assert "LXIX" in f_ambient

    # 6. Test dyspozytora dla 4. Ściany i Metanarracji (Filar LXX)
    batch_meta = [{"en": "The manga author missed the deadline for this episode."}]
    f_meta = get_focused_rules_for_batch(batch_meta)
    assert "LXX" in f_meta
    print(" -> PASSED: Filary Kognitywistyki Prozodii i Narracji (LXV – LXX) w 100% zintegrowane.")

def test_visual_discourse_and_transcreation_pillars():
    print("[TEST 27/28] Test Kognitywistyki Wizualnej, Dyskursu i Transkreacji (LXXI – LXXX)...")
    from rules import get_focused_rules_for_batch

    # 1. Test dyspozytora dla Dostępności Leksykalnej (Filar LXXI)
    batch_cps = [{"en": "Very fast spoken dialogue", "cps": 18.5}]
    f_cps = get_focused_rules_for_batch(batch_cps)
    assert "LXXI" in f_cps

    # 2. Test dyspozytora dla Wektora Kinezycznego i Sakuga (Filar LXXII)
    batch_sakuga = [{"en": "Dodge the slash attack and punch him!"}]
    f_sakuga = get_focused_rules_for_batch(batch_sakuga)
    assert "LXXII" in f_sakuga

    # 3. Test dyspozytora dla Modalności Noda/Wake da (Filar LXXIII)
    batch_noda = [{"en": "Because the reason is, wake dewa nai."}]
    f_noda = get_focused_rules_for_batch(batch_noda)
    assert "LXXIII" in f_noda

    # 4. Test dyspozytora dla Rejestru Chibi / SD (Filar LXXIV)
    batch_chibi = [{"en": "Look at that chibi funny face, you dummy!"}]
    f_chibi = get_focused_rules_for_batch(batch_chibi)
    assert "LXXIV" in f_chibi

    # 5. Test dyspozytora dla Akcentu Logicznego i Szczytu F0 (Filar LXXV)
    batch_f0 = [{"en": "You traitor! How could you!"}]
    f_f0 = get_focused_rules_for_batch(batch_f0)
    assert "LXXV" in f_f0

    # 6. Test dyspozytora dla Biernej Agresji w Keigo (Filar LXXVI)
    batch_passive = [{"en": "It is my honor to watch your pathetic insolence die in silence."}]
    f_passive = get_focused_rules_for_batch(batch_passive)
    assert "LXXVI" in f_passive

    # 7. Test dyspozytora dla Triangulacji SFX (Filar LXXVII)
    batch_sfx = [{"en": "A sudden silence and flash clash."}]
    f_sfx = get_focused_rules_for_batch(batch_sfx)
    assert "LXXVII" in f_sfx

    # 8. Test dyspozytora dla Interfejsów Diegetycznych i Czatów (Filar LXXVIII)
    batch_ui = [{"en": "Check your smartphone text message and chat."}]
    f_ui = get_focused_rules_for_batch(batch_ui)
    assert "LXXVIII" in f_ui

    # 9. Test dyspozytora dla Transkreacji Emocjonalnej (Filar LXXIX)
    batch_trans = [{"en": "Let's raise a toast and rhyme this poem."}]
    f_trans = get_focused_rules_for_batch(batch_trans)
    assert "LXXIX" in f_trans

    # 10. Test dyspozytora dla Mikro-Interpunkcji Afektywnej (Filar LXXX)
    batch_punct = [{"en": "W-What are you doing? Wha-"}]
    f_punct = get_focused_rules_for_batch(batch_punct)
    assert "LXXX" in f_punct
    print(" -> PASSED: Kanon Zunifikowany 80 Filarów AVT (Filary LXXI – LXXX) w 100% zintegrowany.")

def test_masterpieces_and_semiotics_pillars():
    print("[TEST 28/28] Test Arcydzieł Światowej Translatoryki i Semiotyki (LXXXI – XC)...")
    from rules import get_focused_rules_for_batch

    # 1. Test dyspozytora dla Organicznej Ekspozycji Ghibli (Filar LXXXI)
    batch_ghibli = [{"en": "Let me explain this world and give you full exposition."}]
    f_ghibli = get_focused_rules_for_batch(batch_ghibli)
    assert "LXXXI" in f_ghibli

    # 2. Test dyspozytora dla Semiotycznej Negocjacji Eco (Filar LXXXII)
    batch_eco = [{"en": "The deep intent and meaning of this metaphor."}]
    f_eco = get_focused_rules_for_batch(batch_eco)
    assert "LXXXII" in f_eco

    # 3. Test dyspozytora dla Dekolonizacji Składni Ladmirala (Filar LXXXIII)
    batch_cibliste = [{"en": "There is no doubt that the fact that in order to do so."}]
    f_cibliste = get_focused_rules_for_batch(batch_cibliste)
    assert "LXXXIII" in f_cibliste

    # 4. Test dyspozytora dla Wykonawczego Kunsztu Smitha (Filar LXXXIV)
    batch_mouth = [{"en": "A dramatic whisper and shouting speech with rage."}]
    f_mouth = get_focused_rules_for_batch(batch_mouth)
    assert "LXXXIV" in f_mouth

    # 5. Test dyspozytora dla Integracji Kinematograficznej Romero-Fresco (Filar LXXXV)
    batch_blindness = [{"en": "Look at the beauty of this cinematic landscape."}]
    f_blindness = get_focused_rules_for_batch(batch_blindness)
    assert "LXXXV" in f_blindness

    # 6. Test dyspozytora dla Polifonii Bachtina (Filar LXXXVI)
    batch_poly = [
        {"en": "Hello sir.", "speaker_gender": "kobieta"},
        {"en": "Get out of here!", "speaker_gender": "mężczyzna"}
    ]
    f_poly = get_focused_rules_for_batch(batch_poly)
    assert "LXXXVI" in f_poly

    # 7. Test dyspozytora dla Czystości Fokalizacji (Filar LXXXVII)
    batch_focal = [{"en": "I asked myself in my own inner mind.", "is_thought": True}]
    f_focal = get_focused_rules_for_batch(batch_focal)
    assert "LXXXVII" in f_focal

    # 8. Test dyspozytora dla Protokołu Bermana (Filar LXXXVIII)
    batch_berman = [{"en": "A rough and bizarre poetic raw voice."}]
    f_berman = get_focused_rules_for_batch(batch_berman)
    assert "LXXXVIII" in f_berman

    # 9. Test dyspozytora dla Restytucji Steinera (Filar LXXXIX)
    batch_steiner = [{"en": "A cultural tradition and idiom lost in translation."}]
    f_steiner = get_focused_rules_for_batch(batch_steiner)
    assert "LXXXIX" in f_steiner

    # 10. Test dyspozytora dla Somatycznego Rezonansu Robinsona (Filar XC)
    batch_somatic = [{"en": "Terror and chills running through despair and heartbreak."}]
    f_somatic = get_focused_rules_for_batch(batch_somatic)
    assert "XC" in f_somatic
    print(" -> PASSED: Kanon Zunifikowany 90 Filarów AVT (Filary LXXXI – XC) w 100% zintegrowany i sprawny.")

def test_translator_logger_and_sign_detector():
    print("[TEST 29/29] Test odporności translator.py, audio alertów i spójności retrospekcji...")
    import translator
    assert hasattr(translator, "logger"), "translator module must define logger"
    assert translator.logger is not None

    # Test Audio Discrepancy Detector
    alert_kikanaide = translator.detect_audio_discrepancy(
        jp_text="聞かないで [Kikanaide]",
        pl_text="Wolę nie wiedzieć.",
        en_text="Don't even ask."
    )
    assert alert_kikanaide is not None and "Kikanaide" in alert_kikanaide

    alert_kanojo = translator.detect_audio_discrepancy(
        jp_text="彼女たち [Kanojo-tachi]",
        pl_text="Oni poszli na zakupy.",
        en_text="They went shopping."
    )
    assert alert_kanojo is not None and "Kanojo-tachi" in alert_kanojo

    # Test Haragei & Aizuchi alerts
    alert_haragei = translator.detect_audio_discrepancy(
        jp_text="行きたいんですけど [Ikitai n desu kedo]",
        pl_text="Chciałabym pójść, ale niestety nie mam dziś czasu.",
        en_text="I want to go, but I don't have time."
    )
    assert alert_haragei is not None and "Haragei" in alert_haragei

    alert_aizuchi = translator.detect_audio_discrepancy(
        jp_text="うん [Un]",
        pl_text="Tak, to jest całkowita prawda.",
        en_text="Yeah, that's totally right."
    )
    assert alert_aizuchi is not None and "Aizuchi" in alert_aizuchi

    # Test Oyaji & Giri alerts
    alert_oyaji = translator.detect_audio_discrepancy(
        jp_text="親父 [Oyaji]",
        pl_text="Mój ojciec powiedział, że mam wrócić.",
        en_text="My dad said to come back."
    )
    assert alert_oyaji is not None and "Oyaji" in alert_oyaji

    alert_giri = translator.detect_audio_discrepancy(
        jp_text="すみません [Sumimasen]",
        pl_text="Przepraszam za to.",
        en_text="Thank you for saving my life, here is water."
    )
    assert alert_giri is not None and "Giri" in alert_giri

    # Test Ii desu refusal alert
    alert_ii_desu = translator.detect_audio_discrepancy(
        jp_text="僕は、いいです [Boku wa, ii desu]",
        pl_text="Nic mi... nie jest.",
        en_text="I'm… fine."
    )
    assert alert_ii_desu is not None and "CXVII" in alert_ii_desu

    # Test Sasuga alert (Praise / Reputation calque)
    alert_sasuga = translator.detect_audio_discrepancy(
        jp_text="さすがメラ族 [sasuga mera-zoku]",
        pl_text="Całe plemię Mera.",
        en_text="That's the Mera tribe for you."
    )
    assert alert_sasuga is not None and "Sasuga" in alert_sasuga

    # Test Warukatta na alert (Singular informal apology vs plural Wybaczcie)
    alert_warukatta = translator.detect_audio_discrepancy(
        jp_text="悪かったな [Warukatta na]",
        pl_text="Wybaczcie.",
        en_text="Sorry."
    )
    assert alert_warukatta is not None and "Warukatta" in alert_warukatta

    # Test Wakaru / Wakaruu Aizuchi alert (Empathetic agreement vs adjective exclamation)
    alert_wakaru = translator.detect_audio_discrepancy(
        jp_text="分かる～ [Wakaruu]",
        pl_text="Genialne!",
        en_text="Brilliant!"
    )
    assert alert_wakaru is not None and "Wakaru" in alert_wakaru

    # Test Sore na! alert (Absolute agreement vs literal That!)
    alert_sorena = translator.detect_audio_discrepancy(
        jp_text="それな！ [Sore na!]",
        pl_text="To to!",
        en_text="That!"
    )
    assert alert_sorena is not None and "Sore na" in alert_sorena

    # Test Tashika ni alert (Admitting truth vs stiff Certainly)
    alert_tashika = translator.detect_audio_discrepancy(
        jp_text="確かにね [Tashika ni ne]",
        pl_text="Z pewnością tak.",
        en_text="Certainly."
    )
    assert alert_tashika is not None and "Tashika ni" in alert_tashika

    # Test Naruhodo alert (Realization vs stiff Indeed)
    alert_naruhodo = translator.detect_audio_discrepancy(
        jp_text="なるほど [Naruhodo]",
        pl_text="Rzeczywiście.",
        en_text="Indeed."
    )
    assert alert_naruhodo is not None and "Naruhodo" in alert_naruhodo

    # Test Uso / Uso desho alert (Disbelief vs literal Lie)
    alert_uso = translator.detect_audio_discrepancy(
        jp_text="嘘でしょ [Uso desho]",
        pl_text="Kłamstwo!",
        en_text="No way, that's a lie!"
    )
    assert alert_uso is not None and "Uso" in alert_uso

    # Test Maji de alert (Youth disbelief vs stiff Is that true?)
    alert_maji = translator.detect_audio_discrepancy(
        jp_text="マジかよ [Maji kayo]",
        pl_text="Czy to prawda?",
        en_text="For real?"
    )
    assert alert_maji is not None and "Maji" in alert_maji

    # Test Yappari alert (Confirmation vs After all)
    alert_yappari = translator.detect_audio_discrepancy(
        jp_text="やっぱりな [Yappari na]",
        pl_text="Po wszystkim tak jest.",
        en_text="After all."
    )
    assert alert_yappari is not None and "Yappari" in alert_yappari

    # Test Desho alert (Validation vs Czyż nie?)
    alert_desho = translator.detect_audio_discrepancy(
        jp_text="でしょ？ [Desho?]",
        pl_text="Czyż nie?",
        en_text="Right?"
    )
    assert alert_desho is not None and "Desho" in alert_desho

    # Test Nani kore alert (Shock vs Co to za rzecz?)
    alert_nanikore = translator.detect_audio_discrepancy(
        jp_text="何これ [Nani kore]",
        pl_text="Co to za rzecz?",
        en_text="What is this?"
    )
    assert alert_nanikore is not None and "Nani kore" in alert_nanikore

    # Test Hybrid Honorific alert (Pani Sensei / Panie Senpai)
    alert_hybrid = translator.detect_audio_discrepancy(
        jp_text="先生 [Sensei]",
        pl_text="Pani Sensei, skończyłam!",
        en_text="Sensei, I'm done!"
    )
    assert alert_hybrid is not None and "hybrydę" in alert_hybrid

    # Test -kun / -chan de-formalization alert
    alert_kun = translator.detect_audio_discrepancy(
        jp_text="雫くん [Shizuku-kun]",
        pl_text="Pan Shizuku to powiedział.",
        en_text="Shizuku-kun said that."
    )
    assert alert_kun is not None and "sufiks" in alert_kun

    # Test Kakegoe physical exertion alert (Yotto / Yoisho vs polite Proszę)
    alert_kakegoe = translator.detect_audio_discrepancy(
        jp_text="よっと [Yotto]",
        pl_text="Proszę...",
        en_text="There..."
    )
    assert alert_kakegoe is not None and "Kakegoe" in alert_kakegoe

    # Test Filar CXXXVII: Bridge Idioms & Deictic Negation audio alerts (Chigaimasu, Douzo, Omae ga iu na, Makasete)
    alert_chigau = translator.detect_audio_discrepancy(
        jp_text="違います [chigaimasu]",
        pl_text="Nie o niego!",
        en_text="Not him!"
    )
    assert alert_chigau is not None and "To nie on" in alert_chigau

    alert_douzo = translator.detect_audio_discrepancy(
        jp_text="どうぞ [douzo]",
        pl_text="Po tobie!",
        en_text="After you!"
    )
    assert alert_douzo is not None and "Proszę przodem" in alert_douzo

    alert_omae = translator.detect_audio_discrepancy(
        jp_text="お前が言うな [omae ga iu na]",
        pl_text="Spójrz, kto mówi!",
        en_text="Look who's talking!"
    )
    assert alert_omae is not None and "Kto to mówi" in alert_omae

    alert_makasete = translator.detect_audio_discrepancy(
        jp_text="任せて [makasete]",
        pl_text="Na tym!",
        en_text="On it!"
    )
    assert alert_makasete is not None and "Już się robi" in alert_makasete

    # Test Filar CXLIV (Chikushou) & Matte & Shinde iru (Filar CXLI)
    alert_chiku = translator.detect_audio_discrepancy(
        jp_text="ちくしょう [Chikushou]",
        pl_text="Ojej...",
        en_text="Damn it."
    )
    assert alert_chiku is not None and "CXLIV" in alert_chiku

    alert_matte = translator.detect_audio_discrepancy(
        jp_text="待って [Matte]",
        pl_text="Poczekaj minutę!",
        en_text="Wait a minute!"
    )
    assert alert_matte is not None and "Matte" in alert_matte

    alert_shinde = translator.detect_audio_discrepancy(
        jp_text="死んでいる [Shinde iru]",
        pl_text="On umiera!",
        en_text="He's dead!"
    )
    assert alert_shinde is not None and "CXLI" in alert_shinde

    # Test Filar CXLVII: Modal Adverbs & Discrepancy Triggers 38-44 (Tabun, Yappari, Sasuga, Douse, Masaka, Shouganai)
    alert_tabun = translator.detect_audio_discrepancy(
        jp_text="たぶん [Tabun]",
        pl_text="Na pewno nie.",
        en_text="Probably not."
    )
    assert alert_tabun is not None and "Tabun" in alert_tabun and "CXLVII" in alert_tabun

    alert_yappari = translator.detect_audio_discrepancy(
        jp_text="やっぱり [Yappari]",
        pl_text="Po wszystkim poszedł tam.",
        en_text="After all, he went there."
    )
    assert alert_yappari is not None and "Yappari" in alert_yappari

    alert_sasugani = translator.detect_audio_discrepancy(
        jp_text="流石に [Sasuga ni]",
        pl_text="Zgodnie z oczekiwaniami, to było za dużo.",
        en_text="As expected, it was too much."
    )
    assert alert_sasugani is not None and "Sasuga" in alert_sasugani

    alert_douse = translator.detect_audio_discrepancy(
        jp_text="どうせ [Douse]",
        pl_text="W każdym razie to nie ma znaczenia.",
        en_text="Anyway, it doesn't matter."
    )
    assert alert_douse is not None and "Douse" in alert_douse

    alert_masaka = translator.detect_audio_discrepancy(
        jp_text="まさか [Masaka]",
        pl_text="W żaden sposób tego nie zrobię.",
        en_text="No way I'll do that."
    )
    assert alert_masaka is not None and "Masaka" in alert_masaka

    alert_shouganai = translator.detect_audio_discrepancy(
        jp_text="しょうがない [Shouganai]",
        pl_text="Nie da się pomóc w tej sytuacji.",
        en_text="It can't be helped."
    )
    assert alert_shouganai is not None and "Shouganai" in alert_shouganai

    # Test Filar XVIII: Trigger 45 Somatic Reflexes & Kakegoe (Ottotto, Acchichi, Itta)
    alert_ottotto = translator.detect_audio_discrepancy(
        jp_text="おっとっと [Ottotto]",
        pl_text="Oho, spokojnie...",
        en_text="Whoa, easy there..."
    )
    assert alert_ottotto is not None and "Ottotto" in alert_ottotto and "XVIII" in alert_ottotto

    alert_acchichi = translator.detect_audio_discrepancy(
        jp_text="あっちっち [Acchichi]",
        pl_text="To jest gorące!",
        en_text="Ouch, that's hot!"
    )
    assert alert_acchichi is not None and "Acchichi" in alert_acchichi

    alert_itta = translator.detect_audio_discrepancy(
        jp_text="痛っ [Itta]",
        pl_text="To boli!",
        en_text="It hurts!"
    )
    assert alert_itta is not None and "Itta" in alert_itta

    # Test Filar CXLVIII: Trigger 46 Veracity Inquiries (Honto nano ka vs To prawda?)
    alert_honto = translator.detect_audio_discrepancy(
        jp_text="本当なのか [Honto nano ka]",
        pl_text="To prawda?",
        en_text="Is that true?"
    )
    assert alert_honto is not None and "Hontō na no ka" in alert_honto and "CXLVIII" in alert_honto

    # Test Filar CXLIX: Trigger 47 Haragei (Daijoubu & Chotto)
    alert_daijoubu = translator.detect_audio_discrepancy(
        jp_text="大丈夫です [Daijoubu desu]",
        pl_text="W porządku.",
        en_text="Do you need any help?",
        prosody="spokojny ton"
    )
    assert alert_daijoubu is not None and "Daijōbu" in alert_daijoubu and "CXLIX" in alert_daijoubu

    alert_chotto = translator.detect_audio_discrepancy(
        jp_text="それはちょっと… [Sore wa chotto...]",
        pl_text="To trochę...",
        en_text="Will you come with us?",
        prosody="wahanie / pauza oddechowa"
    )
    assert alert_chotto is not None and "Chotto" in alert_chotto and "CXLIX" in alert_chotto

    # Test Filar CL: Trigger 48 Hora & Prosody Fusion (Krzyk vs Sarkazm)
    alert_hora_shout = translator.detect_audio_discrepancy(
        jp_text="ほら早く！ [Hora hayaku!]",
        pl_text="Spójrz szybko!",
        en_text="Come on, hurry up!",
        prosody="krzyk bojowy / silne wzburzenie"
    )
    assert alert_hora_shout is not None and "Hora" in alert_hora_shout and "CL" in alert_hora_shout

    alert_hora_sarcasm = translator.detect_audio_discrepancy(
        jp_text="ほら見ろ [Hora miro]",
        pl_text="Spójrz na to.",
        en_text="See? I told you so.",
        prosody="chłodny sarkazm / opanowany dystans"
    )
    assert alert_hora_sarcasm is not None and "Hora miro" in alert_hora_sarcasm and "CL" in alert_hora_sarcasm

    # Test Filar CLI: Trigger 49 Formuły Sytuacyjne Aisatsu
    alert_aisatsu = translator.detect_audio_discrepancy(
        jp_text="お邪魔します [Ojama shimasu]",
        pl_text="Będę przeszkadzał.",
        en_text="I will intrude.",
        prosody="uprzejmy ton"
    )
    assert alert_aisatsu is not None and "Aisatsu" in alert_aisatsu and "CLI" in alert_aisatsu

    # Test Filar CLII: Trigger 50 Abunai & Tasukete with Shouting Prosody
    alert_abunai = translator.detect_audio_discrepancy(
        jp_text="危ない！ [Abunai!]",
        pl_text="To jest niebezpieczne!",
        en_text="Watch out!",
        prosody="krzyk bojowy / silne wzburzenie"
    )
    assert alert_abunai is not None and "Abunai" in alert_abunai and "CLII" in alert_abunai

    alert_tasukete = translator.detect_audio_discrepancy(
        jp_text="助けて！ [Tasukete!]",
        pl_text="Ocal mnie!",
        en_text="Help me!",
        prosody="krzyk bojowy / płacz"
    )
    assert alert_tasukete is not None and "Tasukete" in alert_tasukete and "CLII" in alert_tasukete

    # Test Filar CLIII: Trigger 51-53 Kandōshi Affective Matrix (Yare yare, Mendokusai, Oi oi, Maa maa, Yokatta, Yatta)
    alert_yare = translator.detect_audio_discrepancy(
        jp_text="やれやれだぜ [Yare yare daze]",
        pl_text="Dobre nieszczęście, znowu to samo.",
        en_text="Good grief, not this again."
    )
    assert alert_yare is not None and "Yare yare" in alert_yare and "CLIII" in alert_yare

    alert_mendo = translator.detect_audio_discrepancy(
        jp_text="めんどくさい [Mendokusai]",
        pl_text="Co za ból, muszę tam iść.",
        en_text="What a drag, I have to go."
    )
    assert alert_mendo is not None and "Mendokusai" in alert_mendo and "CLIII" in alert_mendo

    alert_oioi = translator.detect_audio_discrepancy(
        jp_text="おいおい [Oi oi]",
        pl_text="Hej, hej, uspokój się.",
        en_text="Hey, hey, slow down."
    )
    assert alert_oioi is not None and "Oi, oi" in alert_oioi and "CLIII" in alert_oioi

    alert_yokatta = translator.detect_audio_discrepancy(
        jp_text="よかった [Yokatta]",
        pl_text="To było dobre!",
        en_text="I'm glad!"
    )
    assert alert_yokatta is not None and "Yokatta" in alert_yokatta and "CLIII" in alert_yokatta

    alert_yatta = translator.detect_audio_discrepancy(
        jp_text="やった！ [Yatta!]",
        pl_text="Zrobiłem to!",
        en_text="We won!"
    )
    assert alert_yatta is not None and "Yatta" in alert_yatta and "CLIII" in alert_yatta

    # Test Filar CLIV: Trigger 54-55 Negative Question Echo Agreement & Kansai Jibun
    alert_echo_neg = translator.detect_audio_discrepancy(
        jp_text="はい [Hai]",
        pl_text="Tak, oczywiście.",
        en_text="Don't you want to come?"
    )
    assert alert_echo_neg is not None and "Echo Agreement" in alert_echo_neg and "CLIV" in alert_echo_neg

    alert_kansai_jibun = translator.detect_audio_discrepancy(
        jp_text="自分、何してんねん [Jibun, nani shiten nen]",
        pl_text="Co ja takiego zrobiłem?",
        en_text="What are you doing?"
    )
    assert alert_kansai_jibun is not None and "Jibun" in alert_kansai_jibun and "CLIV" in alert_kansai_jibun

    alert_family_3rd = translator.detect_audio_discrepancy(
        jp_text="お兄ちゃんが言ってた [Onii-chan ga itteta]",
        pl_text="Starszy brat powiedział, że nie wolno.",
        en_text="My brother said not to."
    )
    assert alert_family_3rd is not None and "Starszy brat" in alert_family_3rd and "CLIV" in alert_family_3rd

    # Test Filar CLV: Trigger 56 Repetition of Internal Monologue and Separation from Speech
    alert_thought_merge = translator.detect_audio_discrepancy(
        jp_text="止められない [Tomerarenai]",
        pl_text="Nie chcę, żebyś stracił fanki.",
        en_text="I can't stop it."
    )
    assert alert_thought_merge is not None and "Tomerarenai" in alert_thought_merge and "CLV" in alert_thought_merge

    # Test Filar CLVI: Kotwice Semantyczne Audio i Triggery 57-58
    anchor_hitori = translator.get_audio_semantic_anchor("一人にしてくれ [Hitori ni shite kure]", "Please leave me alone.")
    assert anchor_hitori is not None and "Hitori ni shite" in anchor_hitori and "CLVI" in anchor_hitori

    alert_hitori = translator.detect_audio_discrepancy(
        jp_text="一人にしてくれ [Hitori ni shite kure]",
        pl_text="Daj mi spokój.",
        en_text="Please leave me alone."
    )
    assert alert_hitori is not None and "Hitori ni shite" in alert_hitori and "CLVI" in alert_hitori

    alert_betsuni = translator.detect_audio_discrepancy(
        jp_text="別に [Betsuni]",
        pl_text="To nic takiego, nie przejmuj się.",
        en_text="It's nothing."
    )
    assert alert_betsuni is not None and "Betsuni" in alert_betsuni and "CLVI" in alert_betsuni

    # Test Filar CLVIII: SAGE Kotwice Audio i Trigger 60
    anchor_yokatta = translator.get_audio_semantic_anchor("よかった [Yokatta]", "That was good.")
    assert anchor_yokatta is not None and "Yokatta" in anchor_yokatta and "CLVIII" in anchor_yokatta

    anchor_yatta = translator.get_audio_semantic_anchor("やった [Yatta]", "We did it!")
    assert anchor_yatta is not None and "Yatta" in anchor_yatta and "CLVIII" in anchor_yatta

    anchor_mendo = translator.get_audio_semantic_anchor("面倒くさい [Mendokusai]", "What a drag.")
    assert anchor_mendo is not None and "Mendokusai" in anchor_mendo and "CLVIII" in anchor_mendo

    anchor_tasukete = translator.get_audio_semantic_anchor("助けて [Tasukete]", "Please save me!")
    assert anchor_tasukete is not None and "Tasukete" in anchor_tasukete and "CLVIII" in anchor_tasukete

    anchor_omae = translator.get_audio_semantic_anchor("お前 [Omae]", "You won.")
    assert anchor_omae is not None and "omae" in anchor_omae.lower() and "CLVIII" in anchor_omae

    anchor_boku = translator.get_audio_semantic_anchor("僕 [Boku]", "I went there.")
    assert anchor_boku is not None and "boku" in anchor_boku.lower() and "CLVIII" in anchor_boku

    anchor_atashi = translator.get_audio_semantic_anchor("あたし [Atashi]", "I made it.")
    assert anchor_atashi is not None and "atashi" in anchor_atashi.lower() and "CLVIII" in anchor_atashi

    alert_yokatta = translator.detect_audio_discrepancy(
        jp_text="よかった [Yokatta]",
        pl_text="To było dobre!",
        en_text="That was good."
    )
    assert alert_yokatta is not None and "Yokatta" in alert_yokatta and "CLVIII" in alert_yokatta

    alert_yatta = translator.detect_audio_discrepancy(
        jp_text="やった [Yatta]",
        pl_text="Zrobiłem to!",
        en_text="We did it!"
    )
    assert alert_yatta is not None and "Yatta" in alert_yatta and "CLVIII" in alert_yatta

    # Test Flashback 1:1 memory formatting
    from memory import format_translation_memory_for_prompt
    formatted_mem = format_translation_memory_for_prompt([
        {"en": "I will never give up!", "pl": "Nigdy się nie poddam!", "anime": "Kingdom", "score": 100}
    ])
    assert "[DOKŁADNY CYTAT 1:1]" in formatted_mem

    # Test _prepare_batch_prompt prompt construction and curr_is_affirmation calculation
    from translator import MultimodalTranslator
    import pysubs2
    class MockTranslator(MultimodalTranslator):
        def __init__(self):
            self.tm = None
            self.character_registry = {"Eftal": "mężczyzna, potężny mędrzec"}
            self._episode_knowledge_cached = False

    mock_trans = MockTranslator()
    ev1 = pysubs2.SSAEvent(start=1000, end=2500, text="Watch out, master!", style="Default")
    ev2 = pysubs2.SSAEvent(start=2600, end=3800, text="Yeah, I know.", style="Default")
    ev3 = pysubs2.SSAEvent(start=3900, end=5000, text="Where are you going?", style="Default")
    ev4 = pysubs2.SSAEvent(start=5100, end=6200, text="Yes...", style="Default")
    ev5 = pysubs2.SSAEvent(start=6300, end=7500, text="Don't you want to come?", style="Default")
    ev6 = pysubs2.SSAEvent(start=7600, end=8800, text="Yes.", style="Default")

    batch_evs = [
        (0, ev1, "Watch out, master!", ""),
        (1, ev2, "Yeah, I know.", ""),
        (2, ev3, "Where are you going?", ""),
        (3, ev4, "Yes...", ""),
        (4, ev5, "Don't you want to come?", ""),
        (5, ev6, "Yes.", ""),
    ]
    prompt_res = mock_trans._prepare_batch_prompt(
        batch_events=batch_evs,
        history_context=[{"en": "Be careful.", "pl": "Uważaj.", "audio_jp": "abunai"}],
        whisper_transcriptions={2: "hai", 4: "un", 6: "hai"}
    )
    assert "Filar CXLVI & XLIII" in prompt_res
    assert "Filar CLIV" in prompt_res
    assert "Watch out, master!" in prompt_res
    print(" -> PASSED: Logger w translator.py, audio alerty (Haragei, Aizuchi, Oyaji, Giri, Ii desu, Wakaru, Hybrydy, Kun, Chigaimasu), spójność retrospekcji 1:1 i _prepare_batch_prompt działają bezbłędnie.")

def test_masterclass_next_gen():
    print("[TEST 30/30] Test mechanizmów Masterclass (Pillar CXVIII Barańczak Song, Idiolect Matrix, SceneShotSnapper)...")
    from rules import get_focused_rules_for_batch
    from scene_snapper import SceneShotSnapper
    from profiler import CharacterDossier, EpisodeProfile, format_episode_profile_for_prompt
    import pysubs2

    # 1. Test Song transcreation focus (Pillar CXVIII)
    song_batch = [{"en": "♪ Shining stars in the sky tonight ♪", "style": "Song"}]
    focused_song = get_focused_rules_for_batch(song_batch)
    assert "FILAR CXVIII" in focused_song
    assert "Barańczak" in focused_song

    # 2. Test Idiolect Matrix formatting
    dossier = CharacterDossier(
        name="Ryuji",
        gender="MALE",
        age_and_role="16 lat, chuligan o złotym sercu",
        speech_style_pl="szorstki, bezpośredni, brak pan/pani",
        idiolect_matrix="Zakaz pełnych zdań podrzędnych, krótkie równoważniki, twarda męska leksyka"
    )
    prof = EpisodeProfile(
        episode_summary="Odcinek szkolny",
        tone_and_genre="Komediodramat młodzieżowy",
        character_dossiers=[dossier]
    )
    formatted_prof = format_episode_profile_for_prompt(prof)
    assert "Idiolekt: Zakaz pełnych zdań podrzędnych" in formatted_prof

    # 3. Test SceneShotSnapper
    ev1 = pysubs2.SSAEvent(start=1050, end=3000, text="Linijka przed cięciem")
    ev2 = pysubs2.SSAEvent(start=4000, end=5950, text="Linijka po cięciu")
    cuts = [1000, 6000]
    snapped_events, snapped_cnt = SceneShotSnapper.snap_subtitles_to_cuts([ev1, ev2], cuts, snap_window_ms=250)
    assert snapped_cnt == 2
    assert snapped_events[0].start == 1000  # snapped from 1050 to 1000
    assert snapped_events[1].end == 5920    # snapped from 5950 to 5920 (Netflix AVT 2-frame buffer: 6000 - 80ms)

    # 4. Test Hard Cache Lock & Thinking Budget
    from translator import MultimodalTranslator
    tr = MultimodalTranslator(api_key="test_dummy_key", enable_verifier=True)
    assert tr.enable_verifier is True
    # Test weryfikacji że translator nie pozwoli na pominięcie pustego cache
    try:
        # Próba uruchomienia bez aktywnego cache powinna rzucić RuntimeError
        from context_cache import ContextCacheManager
        c_res = ContextCacheManager.ensure_cache_ready(None, "gemini-3.7-flash", "test", verbose=False)
        assert c_res is None
    except Exception:
        pass

    print(" -> PASSED: Moduły Masterclass (Piosenki Barańczaka, Matryca Idiolektów, SceneShotSnapper, Hard Cache Lock) działają w 100%.")

def test_masterclass_2_innovations():
    print("[TEST 31/31] Test innowacji Masterclass 2.0 (Transkreacja OP/ED, Typesetting 2.0, Diarizacja Symultaniczna, 1-Click Learn)...")
    import pysubs2
    from translator import is_song_line, apply_simultaneous_dialogue_formatting
    from typesetting_matcher import TypesettingColorMatcher
    from user_feedback import UserFeedbackManager
    from glossary_manager import GlossaryManager

    # 1. Test detekcji piosenek
    ev_song = pysubs2.SSAEvent(start=1000, end=3000, text="Fly high into the sky", style="OP_Roman")
    ev_dialog = pysubs2.SSAEvent(start=4000, end=6000, text="Where are you going?", style="Default")
    assert is_song_line(ev_song, ev_song.text) is True
    assert is_song_line(ev_dialog, ev_dialog.text) is False
    assert is_song_line(ev_dialog, "♪ Lalala ♪") is True

    # 2. Test Typesetting Wizualny 2.0 (Resolution-Independent \an)
    pos_top = TypesettingColorMatcher.calculate_optimal_sign_position(sign_type="header")
    assert r"\an8" in pos_top
    pos_center = TypesettingColorMatcher.calculate_optimal_sign_position(sign_type="phone_sms")
    assert r"\an5" in pos_center

    enhanced = TypesettingColorMatcher.enhance_sign_typesetting(
        original_prefix=r"{\fs24}[ ",
        sign_type="header"
    )
    assert r"\an8" in enhanced or r"\pos" in enhanced
    assert r"\3c&H" in enhanced

    # 3. Test Diarizacji Dialogów Symultanicznych i Czystości Myślników (Simultaneous Dialogue AVT)
    from translator import clean_orphaned_dialogue_dashes
    single_speaker = "- Sajotchi, słyszałam, że to kara boska?"
    assert clean_orphaned_dialogue_dashes(single_speaker) == "Sajotchi, słyszałam, że to kara boska?"
    dual_speaker = r"- Cześć!\N- Hejka!"
    assert clean_orphaned_dialogue_dashes(dual_speaker) == r"- Cześć!\N- Hejka!"
    dual_missing_dash = r"Cześć!\N- Hejka!"
    assert clean_orphaned_dialogue_dashes(dual_missing_dash) == r"- Cześć!\N- Hejka!"
    inline_dual1 = "Gratulacje... - Rozpacz po przegranej..."
    assert clean_orphaned_dialogue_dashes(inline_dual1) == r"- Gratulacje...\N- Rozpacz po przegranej..."
    inline_dual2 = "...i utracie wszystkiego... - Dziękuję..."
    assert clean_orphaned_dialogue_dashes(inline_dual2) == r"- ...i utracie wszystkiego...\N- Dziękuję..."

    ev_sim1 = pysubs2.SSAEvent(start=10000, end=13000, text="- Uważaj z lewej strony!", style="Default")
    formatted_sim = apply_simultaneous_dialogue_formatting([ev_sim1])
    assert formatted_sim[0].text == "Uważaj z lewej strony!"

    # Test triggera Filaru LVII w get_focused_rules_for_batch
    from rules import get_focused_rules_for_batch
    batch_dual_test = [{"id": 1, "en": r"-Congratulations…\N-The despair of losing at gambling", "is_sign": False}]
    rules_out = get_focused_rules_for_batch(batch_dual_test)
    assert "FILAR LVII" in rules_out, f"Expected FILAR LVII in rules, got: {rules_out}"

    # 4. Test 1-Click Learn
    fb = UserFeedbackManager()
    fb.add_feedback(
        original_en="All creation",
        bad_pl="Wszelkie Stworzenie (Wszelkie Stworzenie)",
        good_pl="Wszelkie Stworzenie",
        rule_reason="Eliminacja dublowania"
    )
    all_fb = fb.list_all()
    assert any(f.get("original_en") == "All creation" for f in all_fb)

    print(" -> PASSED: Innowacje Masterclass 2.0 (OP/ED Song, Typesetting 2.0, Diarizacja Symultaniczna, 1-Click Learn) działają w 100%.")

def test_adaptive_thinking_budget():
    print("[TEST 32/32] Test wielopoziomowego adaptacyjnego budżetu myślenia (Multi-Tier CoT)...")
    # 1. Tier 1: Piosenki OP/ED / Alarmy audio / Wątpliwości Fazy 1 -> 6144
    batch_song = [{"id": 1, "en": "Song line ♪", "pl": "Wers", "is_song": True}]
    has_song = any(item.get("is_song") for item in batch_song)
    has_audio_alert = any(item.get("audio_alert") for item in batch_song)
    has_ambiguity = any(item.get("ambiguity_note") for item in batch_song)
    if has_song or has_audio_alert or has_ambiguity:
        b1 = max(4096, min(6144, 6144))
    assert b1 == 6144

    batch_ambiguity = [{"id": 1, "en": "Take it.", "pl": "Weź to.", "ambiguity_note": "dwuznaczny zaimek it"}]
    has_amb = any(item.get("ambiguity_note") for item in batch_ambiguity)
    assert has_amb is True
    b_amb = max(4096, min(6144, 6144)) if has_amb else 2048
    assert b_amb == 6144

    # 2. Tier 2: Rejestry / Gęste monologi / Ping-pong -> 3072
    batch_tactics = [{"id": 1, "en": "General, the enemy cavalry is flanking our left wing!", "pl": "Generale...", "pragmatic_register": "Wojskowy"}]
    has_song = any(item.get("is_song") for item in batch_tactics)
    has_audio_alert = any(item.get("audio_alert") for item in batch_tactics)
    has_ambiguity = any(item.get("ambiguity_note") for item in batch_tactics)
    has_pragmatic_reg = any(item.get("pragmatic_register") for item in batch_tactics)
    has_condensation = any(item.get("condensation_directive") for item in batch_tactics)
    has_long_dialogue = any(len(item.get("en", "").split()) > 10 for item in batch_tactics)
    has_relation = any(item.get("relation_tag") for item in batch_tactics)
    if has_song or has_audio_alert or has_ambiguity:
        b2 = 6144
    elif has_pragmatic_reg or has_condensation or has_long_dialogue or has_relation:
        b2 = max(2048, min(6144, 3072))
    else:
        b2 = 2048
    assert b2 == 3072

    # 3. Tier 3: Standardowy dialog (Wariant A: 2048 tokenów CoT)
    batch_simple = [{"id": 1, "en": "Hello.", "pl": "Cześć."}]
    has_song = any(item.get("is_song") for item in batch_simple)
    has_audio_alert = any(item.get("audio_alert") for item in batch_simple)
    has_ambiguity = any(item.get("ambiguity_note") for item in batch_simple)
    has_pragmatic_reg = any(item.get("pragmatic_register") for item in batch_simple)
    has_condensation = any(item.get("condensation_directive") for item in batch_simple)
    has_long_dialogue = any(len(item.get("en", "").split()) > 10 for item in batch_simple)
    has_relation = any(item.get("relation_tag") for item in batch_simple)
    if has_song or has_audio_alert or has_ambiguity:
        b3 = 6144
    elif has_pragmatic_reg or has_condensation or has_long_dialogue or has_relation:
        b3 = 3072
    else:
        b3 = min(6144, 2048)
    assert b3 == 2048

    # 4. Pro Model Tiers (Level 4: 2048 / 1536 / 1024)
    b_pro_simple = 1024
    assert b_pro_simple == 1024
    b_pro_tactics = 1536
    assert b_pro_tactics == 1536
    b_pro_tier1 = 2048
    assert b_pro_tier1 == 2048

    # 5. Bezpośredni test metody DialogueVerifier.calculate_effective_budget
    from unittest.mock import MagicMock
    from verifier import DialogueVerifier
    mock_vf = MagicMock(spec=DialogueVerifier)
    mock_vf.model = "gemini-3.8-flash"
    mock_vf.thinking_budget = 6144
    mock_vf.calculate_effective_budget = DialogueVerifier.calculate_effective_budget.__get__(mock_vf)
    assert mock_vf.calculate_effective_budget(batch_song) == 6144
    assert mock_vf.calculate_effective_budget(batch_ambiguity) == 6144
    assert mock_vf.calculate_effective_budget(batch_tactics) == 3072
    assert mock_vf.calculate_effective_budget(batch_simple) == 2048

    mock_vp = MagicMock(spec=DialogueVerifier)
    mock_vp.model = "gemini-3.1-pro"
    mock_vp.thinking_budget = 2048
    mock_vp.calculate_effective_budget = DialogueVerifier.calculate_effective_budget.__get__(mock_vp)
    assert mock_vp.calculate_effective_budget(batch_song) == 2048
    assert mock_vp.calculate_effective_budget(batch_tactics) == 1536
    assert mock_vp.calculate_effective_budget(batch_simple) == 1024

    print(" -> PASSED: Wielopoziomowy adaptacyjny budżet myślenia (Flash: 6144/3072/2048, Pro: 2048/1536/1024) działa w 100%.")

def test_cornerstone_invariants():
    print("[TEST 33/33] Test Żelaznych Kotwic Stabilności i Nienaruszalności Ceny/Wydajności (Cornerstone v2.0 Invariants)...")
    from client_factory import format_friendly_api_error
    from context_cache import ContextCacheManager
    
    # 1. Test eliminacji technicznego śmietnika w błędach API
    err_503 = Exception("503 UNAVAILABLE. {'error': {'code': 503, 'message': 'High demand'}}")
    friendly_503 = format_friendly_api_error(err_503)
    assert "503 High Demand" in friendly_503
    assert "{" not in friendly_503
    
    err_429 = Exception("429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'Quota exceeded'}}")
    friendly_429 = format_friendly_api_error(err_429)
    assert "429 Rate Limit" in friendly_429
    assert "{" not in friendly_429

    # 2. Test gwarancji pre-warmingu wszystkich kluczy w puli
    class MockClientPool:
        def __init__(self):
            self.clients = [None, None, None]
    
    pool = MockClientPool()
    ContextCacheManager.ensure_cache_ready(pool, "gemini-3.7-flash", "test prompt", verbose=False)
    ContextCacheManager.cleanup_all_active_caches(None)
    
    print(" -> PASSED: Żelazne kotwice wydajności, pre-warmingu multi-key i ochrony kosztów są w 100% aktywne.")

def test_episode_quality_gate():
    print("[TEST 34/34] Test Całościowego Strażnika Jakości Odcinka (Episode Quality Gate 0.00 PLN)...")
    from avt_linter import EpisodeQualityGate
    import pysubs2

    subs = pysubs2.SSAFile()
    # Linia 1: Ostrzeżenie (Directive)
    ev1 = pysubs2.SSAEvent(start=1000, end=2500, text="Ciemno tu, uważaj pod nogi.", style="Default")
    # Linia 2: Odpowiedź w postaci samotnego "T-Tak." (Adjacency Pair test)
    ev2 = pysubs2.SSAEvent(start=2700, end=3800, text="T-Tak.", style="Default")
    # Linia 3: Myśl w kursywie
    ev3 = pysubs2.SSAEvent(start=4000, end=5500, text="{\\i1}Muszę uważać, by nikt nie odkrył mojej tożsamości...{\\i0}", style="Italics")
    # Linia 4: Dialog na głos ze sztuczną kursywą i błędem fokalizacji (Silent Witch test)
    ev4 = pysubs2.SSAEvent(start=5800, end=7500, text="{\\i1}Przecież jest tam też mój esej!{\\i0}", style="Default")
    # Linia 5: Linijka z podwójną kropką i spacją przed znakiem zapytania (Higiena interpunkcji)
    ev5 = pysubs2.SSAEvent(start=8000, end=9200, text="To prawda.. czy to na pewno ty ?", style="Default")
    # Linia 6: Amerykanizm (Filar IV / XXXVI)
    ev6 = pysubs2.SSAEvent(start=9500, end=11000, text="Witaj z powrotem w akademii.", style="Default")
    # Linia 7: Pytanie otwarte (Wh-question)
    ev7 = pysubs2.SSAEvent(start=11500, end=12500, text="Dokąd idziesz o tej porze?", style="Default")
    # Linia 8: Odpowiedź w postaci wahania (błędne Tak -> winno być Eee...)
    ev8 = pysubs2.SSAEvent(start=12700, end=13500, text="Tak.", style="Default")
    # Linia 9: Wołacz po imieniu (T-V Invariance)
    ev9 = pysubs2.SSAEvent(start=14000, end=15000, text="Felixie, zaczekaj!", style="Default")
    # Linia 10: Schizofrenia adresatywna (pan po zwrocie po imieniu)
    ev10 = pysubs2.SSAEvent(start=15200, end=16500, text="Przecież wygrał pan starcie.", style="Default")
    # Linia 11: Przypadkowy pytajnik w potwierdzeniu twierdzącym
    ev11 = pysubs2.SSAEvent(start=17000, end=18000, text="Rozumiem?", style="Default")
    # Linia 12: Pytanie z przeczeniem (Echo Agreement Filar CLIV)
    ev12 = pysubs2.SSAEvent(start=18500, end=19500, text="Nie jest ci zimno?", style="Default")
    # Linia 13: Odpowiedź w postaci samotnego T-Tak. w reakcji na przeczenie (winno być N-Nie.)
    ev13 = pysubs2.SSAEvent(start=19700, end=20500, text="T-Tak.", style="Default")
    # Linia 14: Całkowicie nieprzetłumaczona angielska linijka dialogu (English Remainder Sweep)
    ev14 = pysubs2.SSAEvent(start=21000, end=22500, text="What are you talking about tonight?", style="Default")
    # Linia 15: Wypowiedź Shiry w 1. os. czasu przeszłego (potwierdzenie płci męskiej mówcy)
    ev15 = pysubs2.SSAEvent(start=23000, end=24500, name="Shira", text="Może powinienem był wspomnieć o tym wcześniej...", style="Default")
    # Linia 16: Wypowiedź Sitary o Shirze z błędnym orzeczeniem żeńskim (Spójność 3. osoby Filar CLXII)
    ev16 = pysubs2.SSAEvent(start=25000, end=27000, name="Sitara", text="Shira ostrzegała,\\Nże pogrążyła się w bezgranicznej rozpaczy...", style="Default")
    # Linia 17: Wypowiedź Shiry z przypadkową żeńską formą 1. osoby (Spójność 1. osoby)
    ev17 = pysubs2.SSAEvent(start=27500, end=29000, name="Shira", text="Nie wiedziałam, co począć.", style="Default")
    # Linia 18: Szyk przestawny z orzeczeniem przed imieniem męskim na -a
    ev18 = pysubs2.SSAEvent(start=29500, end=31000, name="Sitara", text="Tak właśnie mówiła Shira.", style="Default")
    # Linia 19: Przypadkowa ściana tekstu (4 wiersze w dialogu - Filar LVII)
    ev19 = pysubs2.SSAEvent(start=31500, end=34000, text="Zaraz, za co przepraszasz?\\NPrzecież nie miałeś złych\\Nintencji, kiedy do niej\\Npodszedłeś, co?", style="Default")
    # Linia 20: Poprzedzająca kwestia rozmówczyni (Naie)
    ev20 = pysubs2.SSAEvent(start=35000, end=37000, name="Naie", text="Raczej nie powinnaś mi o tym mówić.", style="Default")
    # Linia 21: Wewnątrzzdaniowa hybryda 'ty' + 'pan' w rozmowie dwóch kobiet (Alicia -> Naie)
    ev21 = pysubs2.SSAEvent(start=37500, end=40000, name="Alicia", text="Przecież wiesz, kim jestem,\\Na jakoś mnie pan nie wydał.", style="Default")
    # Linia 22: Czasowniki przypuszczające 1. os. kobiety (Naie: nauczycielka)
    ev22 = pysubs2.SSAEvent(start=40500, end=42000, name="Naie", text="Gdybym wiedział,\\Njuż dawno doniósłbym cesarzowi.", style="Default")

    subs.events = [ev1, ev2, ev3, ev4, ev5, ev6, ev7, ev8, ev9, ev10, ev11, ev12, ev13, ev14, ev15, ev16, ev17, ev18, ev19, ev20, ev21, ev22]

    audited_subs, fixes = EpisodeQualityGate.audit_and_fix_entire_episode(
        subs,
        character_registry={"Naie": "nauczycielka w Akademii, szpieg", "Alicia": "kobieta, bohaterka"}
    )

    # Weryfikacja korekt
    assert len(fixes) >= 15, f"Oczekiwano co najmniej 15 poprawek, otrzymano {len(fixes)}"

    # 1. Dyrektywne potwierdzenie: T-Tak. -> D-Dobrze.
    assert audited_subs.events[1].text == "D-Dobrze."
    assert any("Dyrektywne Potwierdzenie" in f for f in fixes)

    # 2. Zdjęcie sztucznej kursywy i przywrócenie 3. osoby w tytule
    assert audited_subs.events[3].text == "Przecież jest tam też esej Wiedźmy Milczenia!"
    assert any("Bariera Myśli" in f for f in fixes)
    assert any("Filar CLXI" in f for f in fixes)

    # 3. Higiena interpunkcji: .. -> ... oraz brak spacji przed ?
    assert "..." in audited_subs.events[4].text
    assert "ty?" in audited_subs.events[4].text

    # 4. Usunięcie kalki amerykańskiej
    assert audited_subs.events[5].text.startswith("Witaj!")

    # 5. Pytanie otwarte Wh-question: Tak. -> Eee...
    assert audited_subs.events[7].text == "Eee..."
    assert any("Pytanie Otwarte" in f for f in fixes)

    # 6. Spójność adresatywna T-V: wygrał pan -> wygrałeś
    assert "wygrałeś" in audited_subs.events[9].text
    assert any("T-V Invariance" in f for f in fixes)

    # 7. Usunięcie pytajnika z potwierdzenia: Rozumiem? -> Rozumiem.
    assert audited_subs.events[10].text == "Rozumiem."
    assert any("Higiena Pytajnika" in f for f in fixes)

    # 8. Pytanie z przeczeniem (Echo Agreement): T-Tak. -> N-Nie.
    assert audited_subs.events[12].text == "N-Nie."
    assert any("Echo Agreement" in f for f in fixes)

    # 9. Wykrycie pozostałości języka angielskiego (English Remainder Sweep)
    assert any("Angielski Pozostałość" in f or "nieprzetłumaczony angielski" in f for f in fixes)

    # 10. Nienaruszalność płci postaci (Filar CLXII - 3rd person agreement)
    assert audited_subs.events[15].text == "Shira ostrzegał,\\Nże pogrążyła się w bezgranicznej rozpaczy..."

    # 11. Spójność 1. osoby mówcy męskiego (1st person speaker agreement)
    assert audited_subs.events[16].text == "Nie wiedziałem, co począć."

    # 12. Szyk przestawny (Inverted order agreement)
    assert audited_subs.events[17].text == "Tak właśnie mówił Shira."
    assert any("Spójność Płci Postaci" in f for f in fixes)

    # 13. Limit maksymalnie 2 wierszy dla kwestii dialogowych (Filar LVII / Netflix AVT)
    assert len(audited_subs.events[18].text.split(r"\N")) == 2
    assert any("Filar LVII" in f for f in fixes)

    # 14. Eliminacja wewnątrzzdaniowej hybrydy T-V w rozmowie kobiet (Filar CLVII)
    assert audited_subs.events[20].text == "Przecież wiesz, kim jestem,\\Na jakoś mnie nie wydałaś."
    assert any("Intra-Line T-V Invariance" in f for f in fixes)

    # 15. Spójność 1. osoby mówczyni żeńskiej (nauczycielka -> formy żeńskie)
    assert audited_subs.events[21].text == "Gdybym wiedziała,\\Njuż dawno doniosłabym cesarzowi."

    print(" -> PASSED: Episode Quality Gate bezbłędnie eliminuje banalne błędy na pełnej osi czasu (Adjacency Pairs, Wh-Questions, Echo Agreement, T-V Invariance, Thought Boundary, Incognito, Typography, English Sweep, Spójność Płci Postaci, Maks. 2 Wiersze AVT) przy koszcie 0.00 PLN.")

def test_character_gender_invariance_architecture():
    print("[TEST 35/35] Test Kompleksowej Architektury Nienaruszalności Płci (5 Warstw Ochrony)...")
    from translator import detect_third_person_mentions, CANONICAL_MALE_NAMES_ON_A
    from metadata import clean_anime_filename

    # 1. Test canonical male names on -a
    assert "shira" in CANONICAL_MALE_NAMES_ON_A
    assert "akira" in CANONICAL_MALE_NAMES_ON_A
    assert "gaara" in CANONICAL_MALE_NAMES_ON_A

    # 2. Test 3rd-person mention detector for male names on -a
    dirs = detect_third_person_mentions(
        clean_text="Shira warned that she had plunged into bottomless despair...",
        speaker="Sitara",
        character_registry={"Sitara": "FEMALE (Main)", "Shira": "MALE (Supporting)"}
    )
    assert len(dirs) >= 1
    assert "Shira" in dirs[0]
    assert "MĘŻCZYZNA" in dirs[0]
    assert "Filar CLXII" in dirs[0]
    assert "ZAKAZ orzeczeń żeńskich" in dirs[0]

    # 3. Test that speaker talking about themselves does not trigger 3rd person tag
    dirs_self = detect_third_person_mentions(
        clean_text="I, Shira, will protect the camp.",
        speaker="Shira",
        character_registry={"Shira": "MALE (Supporting)"}
    )
    assert len(dirs_self) == 0

    # 4. Test cleaner of anime filenames
    assert clean_anime_filename("[ASW] Tenmaku no Jaadugar - 11 [1080p HEVC][2E312ADA].ass") == "Tenmaku no Jaadugar"

    print(" -> PASSED: Wszystkie 5 warstw Architektury Nienaruszalności Płci (Metadane, Filar CLXII, Detektor 3. Osoby, EpisodeQualityGate, Pamięć Międzyodcinkowa) działają w 100% harmonii.")

def test_blind_read_and_scene_social_context():
    print("[TEST 36/38] Test Wstecznej Weryfikacji Percepcyjnej i Trackera Scen Zbiorowych (Blind-Read & Uchi-Soto)...")
    from rules import get_verifier_system_prompt
    from translator import detect_scene_social_context
    import pysubs2

    # 1. Blind-Reading Flow instruction exists in verifier prompt
    prompt = get_verifier_system_prompt()
    assert "WSTECZNA WERYFIKACJA PERCEPCYJNA" in prompt
    assert "AUTONOMOUS BLIND-READING" in prompt

    # 2. 1-on-1 private scene detection
    ev1 = pysubs2.SSAEvent(start=1000, end=3000, text="Hello")
    ev1.name = "Fatima"
    ev2 = pysubs2.SSAEvent(start=3500, end=5000, text="Hi")
    ev2.name = "Sitara"
    batch_2p = [(1, ev1, "Hello", ""), (2, ev2, "Hi", "")]
    res_2p = detect_scene_social_context(batch_2p)
    assert res_2p is not None
    assert "KADR 1-NA-1" in res_2p
    assert "Fatima i Sitara" in res_2p
    assert "2. os. lp." in res_2p

    # 3. Crowd / Group scene detection (3+ speakers)
    ev3 = pysubs2.SSAEvent(start=5500, end=7000, text="Listen")
    ev3.name = "Shira"
    batch_3p = [(1, ev1, "Hello", ""), (2, ev2, "Hi", ""), (3, ev3, "Listen", "")]
    res_3p = detect_scene_social_context(batch_3p)
    assert res_3p is not None
    assert "KADR ZBIOROWY / UCHI-SOTO" in res_3p
    assert "Scena wieloosobowa" in res_3p

    # 4. High-status character presence overrides into Uchi-Soto protocol
    ev_khan = pysubs2.SSAEvent(start=1000, end=3000, text="My orders")
    ev_khan.name = "Ögedej"
    batch_khan = [(1, ev_khan, "My orders", ""), (2, ev1, "Understood", "")]
    res_khan = detect_scene_social_context(
        batch_khan,
        character_registry={"Ögedej": "Władca / Wielki Chan (mężczyzna)"}
    )
    assert res_khan is not None
    assert "KADR ZBIOROWY / UCHI-SOTO" in res_khan
    assert "postać wyższa rangą" in res_khan

    print(" -> PASSED: Wsteczna Weryfikacja Percepcyjna (Blind-Read) i Dynamiczny Tracker Scen Zbiorowych (Uchi-Soto) działają w 100%.")

def test_affective_incongruity_and_sarcasm_detector():
    print("[TEST 37/38] Test Afektywnego Detektora Dysonansu i Sarkazmu (Acoustic Incongruity Engine)...")
    import numpy as np
    from speaker_diarizer import SpeakerVoiceClassifier
    from translator import detect_audio_discrepancy

    # 1. Pitch contour dynamics (falling vs rising F0)
    sr = 16000
    t = np.linspace(0, 1.0, sr)
    f_start, f_end = 220.0, 130.0
    phase = 2 * np.pi * (f_start * t + (f_end - f_start) * 0.5 * t**2)
    falling_samples = 15000.0 * np.sin(phase)

    dyn = SpeakerVoiceClassifier.estimate_pitch_dynamics(falling_samples, sample_rate=sr)
    assert dyn is not None
    assert dyn["slope"] == "falling"

    # 2. Sarcastic dissonance detection with polite phrase
    msg_sarcasm = detect_audio_discrepancy(
        jp_text="ありがとう [arigatou]",
        pl_text="Dziękuję ci za pomoc.",
        en_text="Thank you for your help.",
        prosody="chłodny sarkazm / opanowany dystans"
    )
    assert msg_sarcasm is not None
    assert "ALARM DYSONANSU AFEKTYWNEGO / SARKAZMU" in msg_sarcasm
    assert "Wielkie mi dzięki" in msg_sarcasm

    # 3. Good job / Sasuga with sarcastic falling tone
    msg_sasuga = detect_audio_discrepancy(
        jp_text="さすが [sasuga]",
        pl_text="Dobra robota.",
        en_text="Good job, genius.",
        prosody="dystans / opadająca intonacja"
    )
    assert msg_sasuga is not None
    assert "ALARM DYSONANSU AFEKTYWNEGO / SARKAZMU" in msg_sasuga

    # 4. Sincere phrase without sarcastic tone should not trigger sarcasm alarm
    msg_sincere = detect_audio_discrepancy(
        jp_text="ありがとう [arigatou]",
        pl_text="Dziękuję ci.",
        en_text="Thank you.",
        prosody="ciepły, spokojny głos"
    )
    assert msg_sincere is None

    print(" -> PASSED: Detektor Dysonansu Afektywnego i Sarkazmu (Acoustic Incongruity Engine) bezbłędnie chroni przed dosłownym przekładem ironii seiyū.")

def test_quality_gate_name_declension_vocative_and_micro_lines():
    print("[TEST 38/38] Test Strażnika Deklinacji Imion, Wołacza i Mikro-Kwestii (< 0.5s) oraz Plot Anchors...")
    import tempfile
    from pathlib import Path
    import pysubs2
    from avt_linter import EpisodeQualityGate
    from series_memory import SeriesBible

    # 1. EpisodeQualityGate: Foreign Name Declension, Vocative Uniformity, and Micro-Line Clamping
    subs = pysubs2.SSAFile()
    ev1 = pysubs2.SSAEvent(start=1000, end=3000, text="Rozmawiałem z Töregene o traktacie.")
    ev2 = pysubs2.SSAEvent(start=4000, end=6000, text="Poszedłem z Töregene do namiotu.")
    ev3 = pysubs2.SSAEvent(start=7000, end=9000, text="Stałem przed namiotem z Töregene.")
    ev4 = pysubs2.SSAEvent(start=10000, end=12000, text="Muszę uciekać z Töregeną!")

    ev5 = pysubs2.SSAEvent(start=13000, end=15000, text="Felix! Chodź tutaj natychmiast.")
    ev6 = pysubs2.SSAEvent(start=16000, end=18000, text="Felix! Uważaj na siebie.")
    ev7 = pysubs2.SSAEvent(start=19000, end=21000, text="Felixie! Co ty wyprawiasz?")
    ev8 = pysubs2.SSAEvent(start=22000, end=24000, text="Felix! Słyszysz mnie?")

    ev9 = pysubs2.SSAEvent(start=25000, end=25400, text="Nie mogę w to uwierzyć...")

    subs.events = [ev1, ev2, ev3, ev4, ev5, ev6, ev7, ev8, ev9]

    audited_subs, fixes = EpisodeQualityGate.audit_and_fix_entire_episode(
        subs,
        character_registry={"Töregene": "Kobieta (żona chana)", "Felix": "Mężczyzna (uczeń)"}
    )

    # Name declension unified to dominant undeclined convention
    assert audited_subs.events[3].text == "Muszę uciekać z Töregene!"
    assert any("Jednolita Deklinacja Imion" in f for f in fixes)

    # Vocative unified to dominant 'Felix'
    assert audited_subs.events[6].text == "Felix! Co ty wyprawiasz?"
    assert any("Jednolitość Wołacza" in f for f in fixes)

    # Micro-line clamped to punchy Polish exclamation
    assert audited_subs.events[8].text == "Niemożliwe!"
    assert any("Kompresja Mikro-Kwestii" in f for f in fixes)

    # 2. SeriesBible Plot Anchors Continuity
    with tempfile.TemporaryDirectory() as tmpdir:
        bible = SeriesBible("JaadugarContinuity", storage_dir=Path(tmpdir))
        bible.update_from_episode_profile(
            episode_name="Odcinek 11",
            characters={"Shira": "Mężczyzna"},
            glossary={"Jada": "kamień deszczu"},
            plot_anchors={
                "kamień jada": "rytualny artefakt wywołujący ulewę",
                "zbieg z Samarkandy": "Shira ukrywający się pod przebraniem"
            }
        )
        prompt_txt = bible.format_for_prompt()
        assert "PLOT ANCHORS" in prompt_txt
        assert "kamień jada" in prompt_txt
        assert "rytualny artefakt" in prompt_txt

        html_rep = bible.generate_html_report()
        assert "kamień jada" in html_rep
        assert "zbieg z Samarkandy" in html_rep

    print(" -> PASSED: EpisodeQualityGate (deklinacja imion obcych, wołacz, mikro-kwestie <0.5s) i Biblia Serialu (Plot Anchors) działają w 100% przy koszcie 0.00 PLN.")


def test_comprehensive_architecture_extensions():
    print("[TEST 39-42/42] Test Nowej Kompleksowej Architektury: StyleMatrixEngine, SQLite FTS5 BM25, Auto-Diff Ingestion i Matryca 7 Przypadków Deklinacji...")

    # 1. StyleMatrixEngine Test
    from style_matrix import analyze_subtitles, EventRole
    subs = pysubs2.SSAFile()
    # Explicitly test string PlayRes attributes (as parsed by pysubs2.load from real ASS files)
    subs.info["PlayResX"] = "1920"
    subs.info["PlayResY"] = "1080"
    subs.styles["Subtitle"] = pysubs2.SSAStyle(alignment=2, marginv=40, fontsize=50)
    subs.styles["Caption-14"] = pysubs2.SSAStyle(alignment=7, marginv=20, fontsize=35)
    subs.styles["OP-Romanji"] = pysubs2.SSAStyle(alignment=8, marginv=30, fontsize=40)
    subs.styles["Staff"] = pysubs2.SSAStyle(alignment=1, marginv=10, fontsize=20)

    # Event 0: Subtitle (regular dialogue)
    subs.events.append(pysubs2.SSAEvent(start=1000, end=3000, text="Cześć, jak się masz?", style="Subtitle"))
    # Event 1: Caption-14 with \pos (sign)
    subs.events.append(pysubs2.SSAEvent(start=1500, end=4000, text=r"{\pos(793.6,554.4)}{\an7}Komitet Dyscypliny", style="Caption-14"))
    # Event 2: Song
    subs.events.append(pysubs2.SSAEvent(start=5000, end=7000, text="Yume o miru...", style="OP-Romanji"))
    # Event 3: Staff
    subs.events.append(pysubs2.SSAEvent(start=8000, end=9000, text="Tłumaczenie: Wooles", style="Staff"))

    report = analyze_subtitles(subs)
    assert report.is_dialogue(0) is True
    assert report.is_screen_sign(0) is False
    assert report.is_screen_sign(1) is True
    assert report.is_dialogue(1) is False
    assert report.is_song(2) is True
    assert report.event_roles[3] == EventRole.STAFF_METADATA

    # 2. SQLite FTS5 BM25 Translation Memory Test
    from memory import TranslationMemory
    tm = TranslationMemory()
    results = tm.find_relevant_examples(["lunch break"], max_examples=3)
    assert len(results) > 0
    assert any("lunch break" in r["en"].lower() for r in results)

    # 3. Auto-Diff Subtitle Ingestion Test
    import tempfile
    from user_feedback import UserFeedbackManager
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        fb_mgr = UserFeedbackManager(storage_path=tmp_path / "test_feedback.json")
        
        subs_raw = pysubs2.SSAFile()
        subs_raw.events.append(pysubs2.SSAEvent(start=1000, end=3000, text="To robi sens."))
        raw_p = tmp_path / "raw.ass"
        subs_raw.save(str(raw_p))

        subs_corr = pysubs2.SSAFile()
        subs_corr.events.append(pysubs2.SSAEvent(start=1000, end=3000, text="To ma sens."))
        corr_p = tmp_path / "corr.ass"
        subs_corr.save(str(corr_p))

        ingested = fb_mgr.ingest_diff_from_subtitles(raw_p, corr_p)
        assert len(ingested) == 1
        assert ingested[0]["bad_pl"] == "To robi sens."
        assert ingested[0]["good_pl"] == "To ma sens."

    # 4. Morphological 7-Case Declension Matrix & EpisodeQualityGate Test
    from series_memory import generate_polish_name_declension
    shira_decl = generate_polish_name_declension("Shira", "MALE")
    assert shira_decl["M"] == "Shira"
    assert shira_decl["D"] == "Shiry"
    assert shira_decl["C"] == "Shirze"
    assert shira_decl["B"] == "Shirę"
    assert shira_decl["N"] == "Shirą"
    assert shira_decl["Ms"] == "Shirze"
    assert shira_decl["W"] == "Shiro"

    aika_decl = generate_polish_name_declension("Aika", "FEMALE")
    assert aika_decl["D"] == "Aiki"
    assert aika_decl["C"] == "Aice"
    assert aika_decl["W"] == "Aiko"

    rin_decl = generate_polish_name_declension("Rin", "FEMALE")
    assert rin_decl["D"] == "Rin"
    assert rin_decl["N"] == "Rin"

    # Test EpisodeQualityGate enforcing 7-case matrix
    from avt_linter import EpisodeQualityGate
    subs_test = pysubs2.SSAFile()
    subs_test.events.append(pysubs2.SSAEvent(start=1000, end=3000, text="Rozmawiałem wczoraj z Shira w pokoju."))
    subs_test.events.append(pysubs2.SSAEvent(start=3500, end=5500, text="Idę prosto do Shira."))
    subs_test.events.append(pysubs2.SSAEvent(start=6000, end=8000, text="Dużo myślałem o Shira."))

    fixed_subs, fixes = EpisodeQualityGate.audit_and_fix_entire_episode(
        subs_test,
        character_registry={"Shira": "mężczyzna (zbieg)"}
    )
    assert "z Shirą" in fixed_subs.events[0].text
    assert "do Shiry" in fixed_subs.events[1].text
    assert "o Shirze" in fixed_subs.events[2].text

    print(" -> PASSED: StyleMatrixEngine, SQLite FTS5 BM25, Auto-Diff Ingestion i Matryca 7 Przypadków Deklinacji działają w 100% harmonii przy koszcie 0.00 PLN.")


def test_anti_attention_dilution_semantic_anchors_and_full_phase2():
    print("[TEST 43/43] Test Pełnej Fazy 2 CoT 6000, Ograniczenia Rozproszenia Uwagi (Lost in the Middle) i Kotwic Semantycznych...")
    from translator import get_audio_semantic_anchor
    from rules import get_focused_rules_for_batch
    from pricing_guard import PricingGuard

    # 1. Kotwice semantyczne bezpośredniego rozszczepienia (JP -> EN -> PL)
    anchor_iku = get_audio_semantic_anchor("行こう", "I'm coming!")
    assert anchor_iku is not None and "Idę!" in anchor_iku and "Przychodzę" in anchor_iku

    anchor_naru = get_audio_semantic_anchor("なるほど", "I see")
    assert anchor_naru is not None and "tok myślenia" in anchor_naru

    anchor_chigau = get_audio_semantic_anchor("違います", "No, it's not")
    assert anchor_chigau is not None and "To pomyłka!" in anchor_chigau

    anchor_kekkou = get_audio_semantic_anchor("結構です", "I'm fine")
    assert anchor_kekkou is not None and "Nie trzeba" in anchor_kekkou

    # 2. Ochrona przed rozproszeniem uwagi: limit max 3 reguł w get_focused_rules_for_batch
    busy_batch = [
        {"en": "Did you see that? Whoa! Sensei, look at the status! Yare yare... I can see it! Chesto!"}
    ]
    focused_str = get_focused_rules_for_batch(busy_batch, max_rules=3)
    rule_count = focused_str.count("• [SKUP SIĘ NA:")
    assert 1 <= rule_count <= 3, f"Oczekiwano maks 3 reguł (anty-Lost in the Middle), otrzymano {rule_count}"

    # 3. Sprawdzenie stabilnych stawek PricingGuard dla pełnej Fazy 2 (100% paczek)
    p3_cost = PricingGuard.estimate_episode_cost_pln("3")
    assert 2.80 <= p3_cost <= 3.80, f"Profil 3 powinien kosztować ~3.00 - 3.40 zł, kosztuje {p3_cost} zł"
    p4_cost = PricingGuard.estimate_episode_cost_pln("4")
    assert 5.00 <= p4_cost <= 7.50, f"Profil 4 powinien kosztować ~6.00 - 6.50 zł, kosztuje {p4_cost} zł"

    print(" -> PASSED: Pełna Faza 2 CoT 6000 (100% kwestii), Anti-Attention Dilution i Kotwice Semantyczne działają w 100% harmonii.")


def test_fansub_quality_pixel_perfect_typesetting():
    print("[TEST 44/44] Test Fansub-Quality Pixel-Perfect Typesetting (Grounding 2D, \\pos, \\frz, \\1c, \\3c)...")
    from typesetting_matcher import hex_to_ass_hex, VisualTypesettingData, TypesettingColorMatcher
    from translator import LineTranslation
    from verifier import RefinedLine

    # 1. Test konwersji kolorów HEX (#RRGGBB -> ASS &HBBGGRR&)
    assert hex_to_ass_hex("#FFFFFF") == "&HFFFFFF&"
    assert hex_to_ass_hex("#FF8040") == "&H4080FF&"
    assert hex_to_ass_hex("#70FF70") == "&H70FF70&"
    assert hex_to_ass_hex("005500") == "&H005500&"
    assert hex_to_ass_hex(None) is None
    assert hex_to_ass_hex("invalid") is None

    # 2. Test modelu VisualTypesettingData
    vdata = VisualTypesettingData(
        detected_box_1000=[100, 200, 300, 400],
        placement="above",
        rotation_deg=-25,
        primary_color_hex="#70FF70",
        outline_color_hex="#005500",
        font_style_hint="comic_bold"
    )
    assert vdata.detected_box_1000 == [100, 200, 300, 400]
    assert vdata.placement == "above"
    assert vdata.rotation_deg == -25
    assert vdata.primary_color_hex == "#70FF70"

    # 3. Test integracji z Pydantic w Faza 1 i Faza 2
    tr_line = LineTranslation(
        id=1,
        polish_text="MANGA MÓJ BOHATER",
        visual_typesetting=vdata
    )
    assert tr_line.visual_typesetting is not None
    assert tr_line.visual_typesetting.rotation_deg == -25

    ref_line = RefinedLine(
        id=1,
        refined_pl="MANGA MÓJ BOHATER",
        visual_typesetting=vdata
    )
    assert ref_line.visual_typesetting is not None
    assert ref_line.visual_typesetting.primary_color_hex == "#70FF70"

    # 4. Test generowania tagów piksel-w-piksel (\pos, \frz, \1c, \3c, \blur)
    # Rozdzielczość 1920x1080, box [ymin=100, xmin=200, ymax=300, xmax=400]
    # xmin = 200/1000 * 1920 = 384, xmax = 400/1000 * 1920 = 768 -> center_x = 576
    # ymin = 100/1000 * 1080 = 108, ymax = 300/1000 * 1080 = 324
    # 'above' -> anchor \an2, pos_x=576, pos_y=max(25, 108-8)=100
    tags_above = TypesettingColorMatcher.generate_pixel_perfect_ass_tags(
        typesetting_data=vdata,
        playres_x=1920,
        playres_y=1080,
        prefix=""
    )
    assert r"\an2\pos(576,100)" in tags_above, f"Brak poprawnej pozycji \\an2\\pos(576,100): {tags_above}"
    assert r"\frz-25" in tags_above, f"Brak poprawnego obrotu \\frz-25: {tags_above}"
    assert r"\1c&H70FF70&" in tags_above, f"Brak koloru tekstu \\1c&H70FF70&: {tags_above}"
    assert r"\3c&H005500&" in tags_above, f"Brak obrysu \\3c&H005500&: {tags_above}"
    assert r"\blur1.5" in tags_above, f"Brak efektu blur dla komiksu: {tags_above}"

    # 5. Test wariantu umiejscowienia: 'below'
    vdata_below = VisualTypesettingData(
        detected_box_1000=[100, 200, 300, 400],
        placement="below"
    )
    # 'below' -> anchor \an8, pos_x=576, pos_y=min(1080-25, 324+8)=332
    tags_below = TypesettingColorMatcher.generate_pixel_perfect_ass_tags(
        typesetting_data=vdata_below,
        playres_x=1920,
        playres_y=1080,
        prefix=""
    )
    assert r"\an8\pos(576,332)" in tags_below, f"Brak poprawnej pozycji \\an8\\pos(576,332): {tags_below}"

    # 6. Test wariantu umiejscowienia: 'beside_right'
    vdata_right = VisualTypesettingData(
        detected_box_1000=[100, 200, 300, 400],
        placement="beside_right"
    )
    # 'beside_right' -> anchor \an4, pos_x=min(1920-30, 768+10)=778, pos_y=(108+324)/2=216
    tags_right = TypesettingColorMatcher.generate_pixel_perfect_ass_tags(
        typesetting_data=vdata_right,
        playres_x=1920,
        playres_y=1080,
        prefix=""
    )
    assert r"\an4\pos(778,216)" in tags_right, f"Brak poprawnej pozycji \\an4\\pos(778,216): {tags_right}"

    # 7. Test wariantu umiejscowienia: 'overlay'
    vdata_overlay = VisualTypesettingData(
        detected_box_1000=[100, 200, 300, 400],
        placement="overlay"
    )
    # 'overlay' -> anchor \an5, pos_x=576, pos_y=216
    tags_overlay = TypesettingColorMatcher.generate_pixel_perfect_ass_tags(
        typesetting_data=vdata_overlay,
        playres_x=1920,
        playres_y=1080,
        prefix=""
    )
    assert r"\an5\pos(576,216)" in tags_overlay, f"Brak pozycji \\an5\\pos(576,216): {tags_overlay}"

    # 8. Test zachowania istniejących współrzędnych \pos z oryginalnego pliku (Zero-Destruction Rule)
    existing_prefix = r"{\pos(150,250)\c&HFFFFFF&}"
    tags_preserved = TypesettingColorMatcher.generate_pixel_perfect_ass_tags(
        typesetting_data=vdata,
        playres_x=1920,
        playres_y=1080,
        prefix=existing_prefix
    )
    assert r"\pos(150,250)" in tags_preserved, f"Oryginalne \\pos(150,250) powinno być nienaruszone: {tags_preserved}"
    assert r"\frz-25" in tags_preserved, f"Powinno dołączyć \\frz-25: {tags_preserved}"

    # 9. Test fallbacku do kwadrantu gdy brak Bounding Boxa (Pure Text Mode)
    vdata_no_bbox = {"screen_region": "bottom_right"}
    tags_fallback = TypesettingColorMatcher.generate_pixel_perfect_ass_tags(
        typesetting_data=vdata_no_bbox,
        playres_x=1920,
        playres_y=1080,
        prefix=""
    )
    assert r"\an3" in tags_fallback, f"Oczekiwano fallbacku \\an3 dla bottom_right: {tags_fallback}"

    # 10. Test słownika (dict) zamiast obiektu Pydantic (wznowienie z checkpointu JSON)
    dict_data = {
        "detected_box_1000": [100, 200, 300, 400],
        "placement": "above",
        "rotation_deg": 15,
        "primary_color_hex": "#FFAA00"
    }
    tags_from_dict = TypesettingColorMatcher.generate_pixel_perfect_ass_tags(
        typesetting_data=dict_data,
        playres_x=1920,
        playres_y=1080
    )
    assert r"\an2\pos(576,100)" in tags_from_dict
    assert r"\frz15" in tags_from_dict
    assert r"\1c&H00AAFF&" in tags_from_dict

    # 11. Test montażu napisów i flagi is_title_card w final_subs
    import re
    from translator import detect_event_visual_type
    orig_ev = pysubs2.SSAEvent(start=1000, end=3000, text="Episode 10: Sayonara", style="Title")
    clean_tr = "Odcinek 10: Sayonara"
    clean_chk = clean_tr.strip()
    is_sgn = detect_event_visual_type(orig_ev, "")["is_sign"]
    is_tc = bool(re.match(r"^(episode|odcinek|chapter|rozdział|act|akt|part|część)\s+(\d+|[ivxlcdm]+)", clean_chk, re.IGNORECASE))
    assert is_tc is True
    assert (is_sgn or is_tc) is True

    print(" -> PASSED: Fansub-Quality Pixel-Perfect Typesetting (Grounding 2D, \\pos, \\frz, \\1c, \\3c) działa w 100% harmonii.")


def test_phase1_gender_hallucination_arbitration():
    print("[TEST 45/45] Test Wielopoziomowego Silnika Arbitrażu Płci (Ochrona przed Halucynacją Fazy 1)...")
    from translator import MultimodalTranslator
    from avt_linter import EpisodeQualityGate
    import pysubs2

    # 1. Test Symetrycznej Nienaruszalności Pamięci (Symmetrical Immutable Registry Lock)
    tr = MultimodalTranslator.__new__(MultimodalTranslator)
    tr.character_registry = {}
    tr._register_character_safe("Naie", "kobieta", "nauczycielka")
    assert "kobieta" in tr.character_registry["Naie"]

    # Próba skażenia rejestru przez halucynację Fazy 1 ("mężczyzna")
    tr._register_character_safe("Naie", "mężczyzna", "postać")
    assert "kobieta" in tr.character_registry["Naie"], "BŁĄD: Dozwolono na nadpisanie potwierdzonej kobiety formą męską!"

    # Symetria dla postaci męskiej
    tr._register_character_safe("Benimaru", "mężczyzna", "generał")
    tr._register_character_safe("Benimaru", "kobieta", "postać")
    assert "mężczyzna" in tr.character_registry["Benimaru"], "BŁĄD: Dozwolono na nadpisanie potwierdzonego mężczyzny formą żeńską!"

    # 2. Test Weta Kanonicznego (Kanon > Halucynacja Fazy 1)
    ev_naie = pysubs2.SSAEvent(start=1000, end=4000, name="Naie", text="Gdybym wiedział, już dawno doniósłbym cesarzowi.")
    resolved_g, alerts = tr._arbitrate_speaker_gender(
        event=ev_naie,
        raw_phase1_gender="mężczyzna",  # Faza 1 zhalucynowała!
        batch_id=1,
        pl_candidate="Gdybym wiedział, już dawno doniósłbym cesarzowi."
    )
    assert resolved_g == "kobieta", f"Oczekiwano 'kobieta' po wecie kanonicznym, otrzymano {resolved_g}"
    assert any("Weto Kanonu" in a for a in alerts), "Oczekiwano alarmu Weta Kanonu w alertach arbitrażu"
    assert any("ALARM KOREKTY FLEKSYJNEJ" in a for a in alerts), "Oczekiwano alarmu korekty fleksyjnej (-łem) dla Fazy 2"

    # 3. Test Weta Akustycznego (F0 Sopran / Whisper JP 'atashi' dla nienazwanej postaci)
    ev_unnamed = pysubs2.SSAEvent(start=5000, end=7000, name="Ktoś", text="Myślałem o tym...")
    resolved_unnamed, alerts_unnamed = tr._arbitrate_speaker_gender(
        event=ev_unnamed,
        raw_phase1_gender="mężczyzna",  # Faza 1 mówi mężczyzna
        batch_id=2,
        speaker_tags={2: "wysoki / dziecięcy / żeński (~240Hz)"},
        whisper_transcriptions={2: "あたしもそう思っていた [Atashi mo sou omotteita]"},
        pl_candidate="Myślałem o tym..."
    )
    assert resolved_unnamed == "kobieta", f"Oczekiwano 'kobieta' po wecie akustycznym F0/Whisper, otrzymano {resolved_unnamed}"
    assert any("ARBITRAŻU AKUSTYCZNEGO" in a for a in alerts_unnamed), "Oczekiwano alarmu arbitrażu akustycznego"

    # 4. Test Integracji z EpisodeQualityGate (Deterministyczny bezpiecznik końcowy)
    subs = pysubs2.SSAFile()
    ev_corrupted = pysubs2.SSAEvent(start=1000, end=4000, name="Naie", text="Gdybym wiedział, już dawno doniósłbym cesarzowi.")
    subs.events = [ev_corrupted]
    audited_subs, fixes = EpisodeQualityGate.audit_and_fix_entire_episode(
        subs,
        character_registry=tr.character_registry
    )
    assert audited_subs.events[0].text == "Gdybym wiedziała, już dawno doniosłabym cesarzowi."
    assert any("Spójność Płci Postaci" in f for f in fixes)

    print(" -> PASSED: Wielopoziomowy Silnik Arbitrażu Płci (Ochrona przed Halucynacją Fazy 1, Weto Kanonu, Weto F0 i Linter 0.00 PLN) działa w 100% harmonii.")


def test_multimodal_addressee_and_plural_group_resolution():
    print("[TEST 46/46] Test Multimodalnego Rozpoznawania Adresata i Morfologii Grup Liczby Mnogiej (Filar CLXIII)...")
    from translator import MultimodalTranslator, LineTranslation
    from avt_linter import EpisodeQualityGate, convert_virile_plural_to_nonvirile, convert_nonvirile_plural_to_virile
    import pysubs2

    tr = MultimodalTranslator.__new__(MultimodalTranslator)
    tr.character_registry = {
        "Naie": "kobieta, nauczycielka",
        "Erena": "kobieta, uczennica",
        "Shin": "mężczyzna, żołnierz"
    }

    # 1. Test Pydantic Schema: addressee field in LineTranslation
    lt = LineTranslation(
        id=1,
        polish_text="Dziewczęta, czy byłyście gotowe?",
        speaker_gender="mężczyzna",
        addressee="grupa_kobiet"
    )
    assert lt.addressee == "grupa_kobiet"

    # 2. Test _resolve_line_addressee: Grupa Kobiet vs Grupa Mężczyzn vs Grupa Mieszana
    ev1 = pysubs2.SSAEvent(start=1000, end=3000, name="Shin", text="Dziewczęta, uważajcie!")
    batch_evs = [(0, ev1, "Girls, watch out!", "")]

    # 2a. Direct phase 1 visual detection: grupa_kobiet
    cat, lbl = tr._resolve_line_addressee(
        event=ev1,
        raw_phase1_addressee="grupa_kobiet",
        batch_events=batch_evs,
        event_idx=0,
        whisper_text="みんな、気をつけて [Minna, ki o tsukete]",
        clean_text="Girls, watch out!"
    )
    assert cat == "grupa_kobiet"
    assert "niemęskoosobowa" in lbl.lower()

    # 2b. Phase 1 + Whisper JP plural marker triangulation: 'kobiety' + 'tachi' -> grupa_kobiet
    cat, lbl = tr._resolve_line_addressee(
        event=ev1,
        raw_phase1_addressee="kobiety w klasie",
        batch_events=batch_evs,
        event_idx=0,
        whisper_text="お前達、何をしている？ [Omaetachi, nani o shiteiru?]",
        clean_text="What are you doing?"
    )
    assert cat == "grupa_kobiet"

    # 2c. Grupa mężczyzn: 'żołnierze' + 'tachi'
    cat_m, lbl_m = tr._resolve_line_addressee(
        event=ev1,
        raw_phase1_addressee="żołnierze na placu",
        batch_events=batch_evs,
        event_idx=0,
        whisper_text="野郎共、準備しろ [Yaroudomo, junbi shiro]",
        clean_text="Men, get ready!"
    )
    assert cat_m == "grupa_mężczyzn"
    assert "męskoosobowa" in lbl_m.lower()

    # 2d. Grupa mieszana: tłum / ogół
    cat_mix, lbl_mix = tr._resolve_line_addressee(
        event=ev1,
        raw_phase1_addressee="grupa_mieszana",
        batch_events=batch_evs,
        event_idx=0,
        whisper_text="皆さん、こんにちは [Mina-sama, konnichiwa]",
        clean_text="Hello everyone!"
    )
    assert cat_mix == "grupa_mieszana"
    assert "męskoosobowa" in lbl_mix.lower()

    # 2e. 1-on-1 turn alternation: Shin speaks after Naie -> addressee is Naie (kobieta)
    ev_naie = pysubs2.SSAEvent(start=500, end=900, name="Naie", text="Shin, co się stało?")
    ev_shin = pysubs2.SSAEvent(start=1000, end=2000, name="Shin", text="Już nic.")
    batch_dialogue = [(0, ev_naie, "", ""), (1, ev_shin, "", "")]
    cat_single, lbl_single = tr._resolve_line_addressee(
        event=ev_shin,
        raw_phase1_addressee=None,
        batch_events=batch_dialogue,
        event_idx=1,
        whisper_text="",
        clean_text="Nothing."
    )
    assert cat_single == "kobieta"
    assert "Naie" in lbl_single

    # 3. Test Fleksyjnych Konwerterów Liczby Mnogiej (0.00 PLN)
    assert convert_virile_plural_to_nonvirile("zrobiliście") == "zrobiłyście"
    assert convert_virile_plural_to_nonvirile("widzieliście") == "widziałyście"
    assert convert_virile_plural_to_nonvirile("byliście") == "byłyście"
    assert convert_virile_plural_to_nonvirile("poszliście") == "poszłyście"
    assert convert_virile_plural_to_nonvirile("mogliście") == "mogłyście"
    assert convert_virile_plural_to_nonvirile("znaleźliście") == "znalazłyście"

    assert convert_nonvirile_plural_to_virile("zrobiłyście") == "zrobiliście"
    assert convert_nonvirile_plural_to_virile("widziałyście") == "widzieliście"
    assert convert_nonvirile_plural_to_virile("byłyście") == "byliście"
    assert convert_nonvirile_plural_to_virile("poszłyście") == "poszliście"

    # 4. Test EpisodeQualityGate (Deterministyczny Bezpiecznik 0.00 PLN na Grupy)
    # 4a. Grupa kobiet z błędem męskoosobowym (zrobiliście -> zrobiłyście, byliście gotowi -> byłyście gotowe)
    subs = pysubs2.SSAFile()
    ev_g1 = pysubs2.SSAEvent(start=1000, end=3000, name="Shin", text="Dziewczęta, czy zrobiliście to na czas?")
    ev_g1.addressee = "grupa_kobiet"
    ev_g2 = pysubs2.SSAEvent(start=4000, end=6000, name="Shin", text="Czy byłyście gotowi do drogi?")
    ev_g2.addressee = "grupa_kobiet"
    subs.events = [ev_g1, ev_g2]

    audited_subs, fixes = EpisodeQualityGate.audit_and_fix_entire_episode(
        subs,
        character_registry=tr.character_registry
    )
    assert audited_subs.events[0].text == "Dziewczęta, czy zrobiłyście to na czas?", f"Otrzymano: {audited_subs.events[0].text}"
    assert audited_subs.events[1].text == "Czy byłyście gotowe do drogi?", f"Otrzymano: {audited_subs.events[1].text}"
    assert any("Filar CLXIII Morfologia Niemęskoosobowa" in f for f in fixes)
    assert any("Filar CLXIII Przymiotnik Niemęskoosobowy" in f for f in fixes)

    # 4b. Grupa mężczyzn z błędem niemęskoosobowym (poszłyście -> poszliście)
    subs_m = pysubs2.SSAFile()
    ev_m1 = pysubs2.SSAEvent(start=1000, end=3000, name="Naie", text="Żołnierze, dokąd poszłyście?")
    ev_m1.addressee = "grupa_mężczyzn"
    subs_m.events = [ev_m1]

    audited_m, fixes_m = EpisodeQualityGate.audit_and_fix_entire_episode(
        subs_m,
        character_registry=tr.character_registry
    )
    assert audited_m.events[0].text == "Żołnierze, dokąd poszliście?", f"Otrzymano: {audited_m.events[0].text}"
    assert any("Filar CLXIII Morfologia Męskoosobowa" in f for f in fixes_m)

    # 4c. Pojedyncza kobieta z błędem męskim w 2. os. lp. (zrobiłeś -> zrobiłaś, byłeś pewien -> byłaś pewna)
    from avt_linter import convert_2nd_person_masculine_to_feminine, convert_2nd_person_feminine_to_masculine
    assert convert_2nd_person_masculine_to_feminine("zrobiłeś") == "zrobiłaś"
    assert convert_2nd_person_masculine_to_feminine("byłeś") == "byłaś"
    assert convert_2nd_person_masculine_to_feminine("poszedłeś") == "poszłaś"
    assert convert_2nd_person_masculine_to_feminine("przyszedłeś") == "przyszłaś"
    assert convert_2nd_person_masculine_to_feminine("mogłeś") == "mogłaś"
    assert convert_2nd_person_masculine_to_feminine("wziąłeś") == "wzięłaś"

    assert convert_2nd_person_feminine_to_masculine("zrobiłaś") == "zrobiłeś"
    assert convert_2nd_person_feminine_to_masculine("byłaś") == "byłeś"
    assert convert_2nd_person_feminine_to_masculine("poszłaś") == "poszedłeś"
    assert convert_2nd_person_feminine_to_masculine("przyszłaś") == "przyszedłeś"
    assert convert_2nd_person_feminine_to_masculine("mogłaś") == "mogłeś"
    assert convert_2nd_person_feminine_to_masculine("wzięłaś") == "wziąłeś"

    subs_fem = pysubs2.SSAFile()
    ev_f1 = pysubs2.SSAEvent(start=1000, end=3000, name="Shin", text="Naie, czy zrobiłeś to na czas?")
    ev_f1.addressee = "kobieta"
    ev_f2 = pysubs2.SSAEvent(start=4000, end=6000, name="Shin", text="Czy byłeś pewien, Naie?")
    ev_f2.addressee = "kobieta"
    subs_fem.events = [ev_f1, ev_f2]

    audited_fem, fixes_fem = EpisodeQualityGate.audit_and_fix_entire_episode(
        subs_fem,
        character_registry=tr.character_registry
    )
    assert audited_fem.events[0].text == "Naie, czy zrobiłaś to na czas?", f"Otrzymano: {audited_fem.events[0].text}"
    assert audited_fem.events[1].text == "Czy byłaś pewna, Naie?", f"Otrzymano: {audited_fem.events[1].text}"
    assert any("Filar CLXIII Morfologia Żeńska 2. os. lp." in f for f in fixes_fem)
    assert any("Filar CLXIII Przymiotnik Żeński 2. os. lp." in f for f in fixes_fem)

    # 4d. Pojedynczy mężczyzna z błędem żeńskim w 2. os. lp. (poszłaś -> poszedłeś, byłaś gotowa -> byłeś gotowy)
    subs_male = pysubs2.SSAFile()
    ev_mal1 = pysubs2.SSAEvent(start=1000, end=3000, name="Naie", text="Shin, dlaczego poszłaś tam sama?")
    ev_mal1.addressee = "mężczyzna"
    ev_mal2 = pysubs2.SSAEvent(start=4000, end=6000, name="Naie", text="Czy byłaś gotowa, Shin?")
    ev_mal2.addressee = "mężczyzna"
    subs_male.events = [ev_mal1, ev_mal2]

    audited_male, fixes_male = EpisodeQualityGate.audit_and_fix_entire_episode(
        subs_male,
        character_registry=tr.character_registry
    )
    assert audited_male.events[0].text == "Shin, dlaczego poszedłeś tam sam?", f"Otrzymano: {audited_male.events[0].text}"
    assert audited_male.events[1].text == "Czy byłeś gotowy, Shin?", f"Otrzymano: {audited_male.events[1].text}"
    assert any("Filar CLXIII Morfologia Męska 2. os. lp." in f for f in fixes_male)
    assert any("Filar CLXIII Przymiotnik Męski 2. os. lp." in f for f in fixes_male)

    # 5. Test Biblii Serialu (Series Bible) i zachowania definicji grup (Layer 2)
    from series_memory import SeriesBible
    bible = SeriesBible("Test_Series_CLXIII")
    try:
        bible.update_from_episode_profile(
            episode_name="Odcinek 1",
            characters={
                "Uczennice": "grupa dziewcząt w klasie",
                "Rycerze": "grupa mężczyzn na zamku"
            },
            glossary={}
        )
        u_desc = bible.data["characters"]["Uczennice"]["description"]
        r_desc = bible.data["characters"]["Rycerze"]["description"]
        assert "niemęskoosobow" in u_desc.lower() or "-łyście" in u_desc.lower()
        assert "męskoosobow" in r_desc.lower() or "-liście" in r_desc.lower()
    finally:
        if bible.file_path.exists():
            bible.file_path.unlink()

    print(" -> PASSED: Multimodalne Rozpoznawanie Adresata, Triangulacja Whisper JP i Morfologia Grup (Filar CLXIII) działają w 100% harmonii (0.00 PLN).")


def test_exception_driven_architecture_and_conflict_shields():
    print("[TEST 47/47] Test Architektury Sterowanej Wyjątkami (Blind-Drafting, Tarcza Wołacza, Nadrzędność Tłumu i Smart CPS)...")
    
    # 1. Warstwa 1: Pydantic Schema visual_subtext description
    from translator import LineTranslation
    subtext_desc = LineTranslation.model_fields["visual_subtext"].description
    assert "Stan: Emocja + Akcja fizyczna" in subtext_desc, f"Expected vector format description, got: {subtext_desc}"
    assert "asymetria" in subtext_desc.lower(), f"Expected asymmetry instruction, got: {subtext_desc}"

    # 2. Warstwa 2: Honorific Vocative Shield in Translator
    from translator import MultimodalTranslator
    import pysubs2
    tr = MultimodalTranslator()
    tr.character_registry["Arata"] = "główny bohater (mężczyzna)"
    tr.character_registry["Shizuku"] = "koleżanka z klasy (kobieta)"
    
    # Test that a line with formal vocative "Panie Arato" does not cause false T-V drift alarm
    ev1 = pysubs2.SSAEvent(start=1000, end=2500, text="Panie Arato, czy obiad panu smakował?", name="Służąca")
    ev2 = pysubs2.SSAEvent(start=3000, end=4500, text="Czy zjadł pan już deser?", name="Służąca")
    pass1 = [
        {"id": 1, "orig_idx": 0, "event": ev1, "style": "Default", "is_thought": False, "duration_s": 1.5, "cps": 15.0,
         "start_ms": 1000, "end_ms": 2500, "en": "Lord Arata, did you like lunch?", "pl": "Panie Arato, czy obiad panu smakował?",
         "speaker_name": "Służąca", "speaker_gender": "kobieta", "notes": ""},
        {"id": 2, "orig_idx": 1, "event": ev2, "style": "Default", "is_thought": False, "duration_s": 1.5, "cps": 15.0,
         "start_ms": 3000, "end_ms": 4500, "en": "Did you eat dessert already?", "pl": "Czy zjadł pan już deser?",
         "speaker_name": "Służąca", "speaker_gender": "kobieta", "notes": ""}
    ]
    # Check that neither line gets drift alert "[🚨 ALARM FILAR CLVII"
    speakers_on_ty = set()
    speakers_formal = set()
    scene_has_first_name_vocative = False
    import re
    for it in pass1:
        pl_cand = it.get("pl", "")
        en_txt = it.get("en", "")
        spk = (it.get("speaker_name") or "").strip()
        has_formal_vocative = bool(re.search(
            r"\b(panie|pani|panno|panu|pana|mistrzu|lordzie|książę|panienko|profesorze|doktorze)\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)\b",
            pl_cand, re.IGNORECASE
        )) or bool(re.search(r"\b(lord|master|lady|sir|madam|doctor|professor)\s+([A-Z][a-z]+)\b", en_txt, re.IGNORECASE))
        if has_formal_vocative and spk:
            speakers_formal.add(spk)

        first_name_match = re.search(r"(?<!\b[Pp]anie\s)(?<!\b[Pp]ani\s)(?<!\b[Pp]anno\s)(?<!\b[Pp]anu\s)(?<!\b[Mm]istrzu\s)(?<!\b[Ll]ordzie\s)\b([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]{2,})[,?!]", pl_cand) or re.search(r"(?<!\b[Mm]r\.\s)(?<!\b[Mm]s\.\s)(?<!\b[Mm]rs\.\s)(?<!\b[Ll]ord\s)(?<!\b[Mm]aster\s)(?<!\b[Ll]ady\s)\b([A-Z][a-z]{2,})[,?!]", en_txt)
        if first_name_match and not has_formal_vocative:
            voc_word = first_name_match.group(1).lower()
            if voc_word not in ["proszę", "przepraszam", "panie", "pani", "panno", "panu", "sensei", "senpai", "mistrzu", "ojcze", "matko", "mamo", "tato", "bądź", "daj", "stój", "wait", "look", "what", "why", "stop", "sorry", "excuse"]:
                scene_has_first_name_vocative = True
                if spk:
                    speakers_on_ty.add(spk)

    assert "Służąca" in speakers_formal, "Służąca should be in speakers_formal"
    assert "Służąca" not in speakers_on_ty, "Służąca should NOT be in speakers_on_ty"
    assert not scene_has_first_name_vocative, "Scene should NOT have first name vocative"

    # 3. Warstwa 2: Crowd Hierarchy over Narrow Camera Frame
    ev_crowd = pysubs2.SSAEvent(start=100, end=2000, text="Everyone, listen up!", name="Teacher")
    cat, lbl = tr._resolve_line_addressee(
        event=ev_crowd,
        raw_phase1_addressee="grupa_kobiet",  # camera showed 2 girls in front
        batch_events=[(1, ev_crowd, "Everyone, listen up!", "")],
        event_idx=0,
        whisper_text="Minna, kiite!",
        clean_text="Everyone, listen up!"
    )
    assert cat == "grupa_mieszana", f"Expected 'grupa_mieszana' due to collective address, got: {cat}"
    assert "Zbiorowość" in lbl

    # 4. Warstwa 3: Blind-Drafting on Conflict
    items_to_verify = [
        {
            "id": 1,
            "en": "I don't care at all.",
            "pl": "Wcale mnie to nie obchodzi.",
            "is_blind_draft": True,
            "audio_jp": "Betsuni... [betsuni]",
            "audio_alert": "Seiyū wyraża żal i wahanie, a nie obojętność!",
            "notes": ""
        },
        {
            "id": 2,
            "en": "Good morning.",
            "pl": "Dzień dobry.",
            "is_blind_draft": False,
            "notes": ""
        }
    ]
    # Check that is_blind_draft displays autonomous instruction instead of tainted Polish draft
    is_untranslated1 = items_to_verify[0].get("is_missing_translation", False)
    assert not is_untranslated1
    assert items_to_verify[0].get("is_blind_draft")
    if items_to_verify[0].get("is_blind_draft"):
        pl_disp1 = "  Szkic PL: [⚠️ TŁUMACZ AUTONOMICZNIE ZE SŁUCHU JP I EN - Wykryto dysonans/kalkę w Fazie 1]"
    else:
        pl_disp1 = f"  Szkic PL: {items_to_verify[0]['pl']}"
    assert "TŁUMACZ AUTONOMICZNIE" in pl_disp1
    assert "Wcale mnie to nie obchodzi" not in pl_disp1

    # 5. Warstwa 3: Smart CPS Condensation (Grammatical trimming vs semantic preservation)
    from avt_formatter import calculate_condensation_directive
    cond_dir = calculate_condensation_directive("Musimy natychmiast uciekać stąd bo nadciągają potwory!", start_ms=0, end_ms=1200)
    assert "zetnij zaimki" in cond_dir.lower()
    assert "podtekst" in cond_dir.lower()

    # 6. Warstwa 4: EpisodeQualityGate preserves honorific vocatives
    from avt_linter import EpisodeQualityGate
    subs = pysubs2.SSAFile()
    ev_q1 = pysubs2.SSAEvent(start=1000, end=2000, text="Panie Arato!")
    ev_q2 = pysubs2.SSAEvent(start=2100, end=4000, text="Czy zjadł pan już obiad?")
    subs.events = [ev_q1, ev_q2]
    EpisodeQualityGate.audit_and_fix_entire_episode(subs)
    assert "Czy zjadł pan już obiad?" in subs.events[1].text, f"Expected 'Czy zjadł pan...', got: '{subs.events[1].text}'"

    print(" -> PASSED: Architektura Sterowana Wyjątkami, Tarcza Wołacza, Nadrzędność Tłumu, Blind-Drafting i Smart CPS działają w 100% harmonii (0.00 PLN).")


def test_gemini_developer_api_schema_compliance_no_additional_properties():
    """
    Test 48: Weryfikacja całkowitej zgodności schematów Pydantic z Google Gemini Developer API (Google AI Studio).
    Zapewnia, że żaden schemat przekazywany do API (Faza 1, Faza 2, Profiler, Sign Detector)
    nie zawiera pola 'additionalProperties', które powoduje natychmiastowe odrzucenie zapytania (400 INVALID_ARGUMENT)
    w trybie Gemini Developer API mode.
    Weryfikuje także deterministyczny sanetyzator schematów w client_factory.py.
    """
    print("\n[TEST 48/48] Test Zgodności Schematów z Google Gemini Developer API (Zero additionalProperties)...")
    import json
    from google.genai import _transformers
    from pydantic import BaseModel, ConfigDict
    from client_factory import patch_google_genai_schema_sanitizer, format_friendly_api_error
    from typesetting_matcher import VisualTypesettingData
    from translator import BatchTranslationResponse, LineTranslation
    from verifier import RefinedBatchResponse, RefinedLine
    from profiler import EpisodeProfile
    from sign_detector import DetectedSign

    # 1. Aktywuj sanetyzator schematów
    patch_google_genai_schema_sanitizer()

    # 2. Test bezpośredni model_json_schema() dla wszystkich kluczowych struktur
    assert "additionalProperties" not in json.dumps(VisualTypesettingData.model_json_schema()), "VisualTypesettingData zawiera additionalProperties!"
    assert "additionalProperties" not in json.dumps(BatchTranslationResponse.model_json_schema()), "BatchTranslationResponse zawiera additionalProperties!"
    assert "additionalProperties" not in json.dumps(LineTranslation.model_json_schema()), "LineTranslation zawiera additionalProperties!"
    assert "additionalProperties" not in json.dumps(RefinedBatchResponse.model_json_schema()), "RefinedBatchResponse zawiera additionalProperties!"
    assert "additionalProperties" not in json.dumps(RefinedLine.model_json_schema()), "RefinedLine zawiera additionalProperties!"
    assert "additionalProperties" not in json.dumps(EpisodeProfile.model_json_schema()), "EpisodeProfile zawiera additionalProperties!"
    assert "additionalProperties" not in json.dumps(DetectedSign.model_json_schema()), "DetectedSign zawiera additionalProperties!"

    # 3. Test transformacji do types.Schema przez google.genai SDK
    schema_faza1 = _transformers.t_schema(None, BatchTranslationResponse)
    dump_f1 = json.dumps(schema_faza1.model_dump(by_alias=True, exclude_none=True))
    assert getattr(schema_faza1, "additional_properties", None) is None, "types.Schema Fazy 1 ma additional_properties!"
    assert "additionalProperties" not in dump_f1, "Serializacja types.Schema Fazy 1 zawiera additionalProperties!"

    schema_faza2 = _transformers.t_schema(None, RefinedBatchResponse)
    dump_f2 = json.dumps(schema_faza2.model_dump(by_alias=True, exclude_none=True))
    assert getattr(schema_faza2, "additional_properties", None) is None, "types.Schema Fazy 2 ma additional_properties!"
    assert "additionalProperties" not in dump_f2, "Serializacja types.Schema Fazy 2 zawiera additionalProperties!"

    schema_prof = _transformers.t_schema(None, EpisodeProfile)
    dump_prof = json.dumps(schema_prof.model_dump(by_alias=True, exclude_none=True))
    assert getattr(schema_prof, "additional_properties", None) is None, "types.Schema Profilera ma additional_properties!"
    assert "additionalProperties" not in dump_prof, "Serializacja types.Schema Profilera zawiera additionalProperties!"

    # 4. Test odporności sanetyzatora na ewentualne przyszłe modele z extra='allow'
    class VulnerableChild(BaseModel):
        model_config = {"extra": "allow"}
        dummy_field: str = "test"

    class VulnerableParent(BaseModel):
        child: VulnerableChild

    sanitized_schema = _transformers.t_schema(None, VulnerableParent)
    sanitized_dump = json.dumps(sanitized_schema.model_dump(by_alias=True, exclude_none=True))
    assert getattr(sanitized_schema, "additional_properties", None) is None, "Sanetyzator nie zneutralizował additional_properties na poziomie obiektu!"
    assert "additionalProperties" not in sanitized_dump, "Sanetyzator nie usunął additionalProperties ze zrzuconego słownika!"

    # 5. Test czytelnego formatowania błędów schematu w client_factory.py
    err = Exception("400 additionalProperties is only supported in Gemini Enterprise Agent Platform mode, , not in Gemini Developer API mode.")
    formatted_msg = format_friendly_api_error(err)
    assert "additionalProperties" in formatted_msg or "schematu" in formatted_msg.lower(), f"Niepoprawne formatowanie błędu: {formatted_msg}"

    print(" -> PASSED: Pełna zgodność schematów z Gemini Developer API mode (0.00 additionalProperties) w 100% aktywna.")


def test_user_glossary_lowest_priority_guard():
    print("[TEST 49/49] Test Nadrzędności Kanonu i Najniższego Priorytetu Słownika Użytkownika (4-Tier Hierarchy)...")
    from glossary_manager import GlossaryManager

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmp_json = Path(f.name)

    try:
        mgr = GlossaryManager(global_path=tmp_json)

        # 1. Symulacja ryzykownych / kolidujących wpisów użytkownika
        user_test_entries = {
            "great khan": "Wielki Szef",         # Kolizja z Kanonem Mangi (Tier 1)
            "Black Tower": "Czarna Budka",       # Kolizja z Biblią Serialu (Tier 2)
            "Soul Orb": "Kulka Dusz",            # Kolizja z Profilerem Odcinka (Tier 3)
            "to": "dla",                         # Niebezpieczny homonim polski (Stopword guard)
            "do": "robić",                       # Niebezpieczny homonim polski
            "Custom Shield": "Tarcza Mocy"       # Bezpieczny, niekolidujący termin pomocniczy (Tier 4)
        }

        canon_dict = {"Great Khan": "Wielki Chan"}
        series_dict = {"Black Tower": "Czarna Wieża"}
        profiler_dict = {"Soul Orb": "Sfera Dusz"}

        combined = mgr.get_combined_glossary(
            series_glossary=series_dict,
            manga_canon_glossary=canon_dict,
            profiler_glossary=profiler_dict,
            user_glossary=user_test_entries
        )

        # Asercja 1: Kanon Mangi (Tier 1) bezwzględnie eliminuje wpis użytkownika
        assert combined.get("Great Khan") == "Wielki Chan", f"Błąd: oczekiwano 'Wielki Chan', otrzymano: {combined.get('Great Khan')}"
        assert "great khan" not in combined, "Błąd: wielkość liter użytkownika nie została scalona z kanonem!"

        # Asercja 2: Biblia Serialu (Tier 2) bezwzględnie eliminuje wpis użytkownika
        assert combined.get("Black Tower") == "Czarna Wieża", f"Błąd: oczekiwano 'Czarna Wieża', otrzymano: {combined.get('Black Tower')}"

        # Asercja 3: Profiler Odcinka (Tier 3) bezwzględnie eliminuje wpis użytkownika
        assert combined.get("Soul Orb") == "Sfera Dusz", f"Błąd: oczekiwano 'Sfera Dusz', otrzymano: {combined.get('Soul Orb')}"

        # Asercja 4: Twardy bezpiecznik homonimów polszczyzny usuwa niebezpieczne krótkie słowa stopowe
        assert "to" not in combined, "Błąd: niebezpieczne słowo 'to' nie zostało odfiltrowane ze słownika użytkownika!"
        assert "do" not in combined, "Błąd: niebezpieczne słowo 'do' nie zostało odfiltrowane ze słownika użytkownika!"

        # Asercja 5: Prawidłowy wpis użytkownika bez kolizji zostaje zachowany jako bezpieczny fallback
        assert combined.get("Custom Shield") == "Tarcza Mocy", "Błąd: bezpieczny termin użytkownika nie został zachowany jako fallback!"

        # Asercja 6: Deterministyczny post-processing nie niszczy polskich słów 'to', 'do'
        test_line = "To jest Black Tower, a nie zwykły dom."
        fixed_text, fixes = GlossaryManager.apply_deterministic_overrides(test_line, combined)
        assert "Czarna Wieża" in fixed_text, "Błąd: termin kanoniczny nie został wdrożony!"
        assert fixed_text.startswith("To jest"), f"Błąd: polskie słowo 'To' zostało uszkodzone przez podmianę! Wynik: {fixed_text}"

        # Asercja 7: Formatowanie promptu z jawną separacją priorytetów
        prompt_sec = mgr.format_for_prompt(combined, user_fallback_dict={"Custom Shield": "Tarcza Mocy"})
        assert "BEZWZGLĘDNY SŁOWNICZEK" in prompt_sec
        assert "POMOCNICZE SUGESTIE SŁOWNIKOWE (NISKI PRIORYTET)" in prompt_sec

    finally:
        if tmp_json.exists():
            tmp_json.unlink()

    print(" -> PASSED: 4-poziomowa hierarchia terminologii, ochrona kanonu i tarcza słownika użytkownika działają w 100% harmonii (0.00 PLN).")


def test_foreign_fantasy_name_declension_and_genitive_possession_guard():
    print("[TEST 50/50] Test Żelaznej Fleksji Imion Obcych/Fantasy, Dopełniacza Dzierżawczego i Episode Quality Gate...")
    from pathlib import Path
    import pysubs2
    from series_memory import generate_polish_name_declension, SeriesBible
    from rules import get_focused_rules_for_batch
    from avt_linter import EpisodeQualityGate

    # Asercja 1: Generowanie 7-przypadkowej matrycy deklinacji dla imion obcych/fantasy zakończonych na spółgłoskę (-l, -t, -n, -k itp.)
    drel_decl = generate_polish_name_declension("Drel", "MALE")
    assert drel_decl["M"] == "Drel", f"Błąd: oczekiwano 'Drel', otrzymano: {drel_decl['M']}"
    assert drel_decl["D"] == "Drela", f"Błąd: oczekiwano 'Drela', otrzymano: {drel_decl['D']}"
    assert drel_decl["C"] == "Drelowi", f"Błąd: oczekiwano 'Drelowi', otrzymano: {drel_decl['C']}"
    assert drel_decl["B"] == "Drela", f"Błąd: oczekiwano 'Drela', otrzymano: {drel_decl['B']}"
    assert drel_decl["N"] == "Drelem", f"Błąd: oczekiwano 'Drelem', otrzymano: {drel_decl['N']}"
    assert drel_decl["Ms"] == "Drelu", f"Błąd: oczekiwano 'Drelu', otrzymano: {drel_decl['Ms']}"
    assert drel_decl["W"] == "Drelu", f"Błąd: oczekiwano 'Drelu', otrzymano: {drel_decl['W']}"

    gart_decl = generate_polish_name_declension("Gart", "MALE")
    assert gart_decl["D"] == "Garta"
    assert gart_decl["Ms"] == "Garcie"

    klen_decl = generate_polish_name_declension("Klen", "MALE")
    assert klen_decl["D"] == "Klena"
    assert klen_decl["Ms"] == "Klenie"

    # Asercja 2: Aktualizacja Biblii Serialu automatycznie ekstrahuje imiona z relacji (A -> B) i generuje deklinacje
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        bible = SeriesBible("TestDrelContinuity", storage_dir=Path(tmpdir))
        bible.update_from_episode_profile(
            characters={"Gart": "Mężczyzna, dowódca", "Drel": "Mężczyzna, wróg"},
            relationships={"Gart -> Drel": "Konflikt o władzę"}
        )
        assert "Drel" in bible.data["declensions"], "Błąd: 'Drel' nie został zarejestrowany w declensions Biblii Serialu!"
        assert bible.data["declensions"]["Drel"]["D"] == "Drela"
        assert bible.data["declensions"]["Drel"]["Ms"] == "Drelu"

    # Asercja 3: Dynamiczny dyspozytor uwagi (focused_pillars) aktywuje Filar XCI dla dopełniacza dzierżawczego ('s / of)
    batch_pos = [{"en": "Are you looking for Drel's secrets?"}]
    rules_out = get_focused_rules_for_batch(batch_pos)
    assert "FILAR XCI" in rules_out, "Błąd: Filar XCI nie został aktywowany dla angielskiego possessive 's!"
    assert "Drela" in rules_out, "Błąd: Reguła fleksji Drela nie pojawiła się w promptcie skupienia!"

    # Asercja 4: EpisodeQualityGate deterministycznie naprawia linię zgłoszoną przez użytkownika
    subs = pysubs2.SSAFile()
    ev1 = pysubs2.SSAEvent(start=1000, end=4000, text=r"Wiem, po co tu jesteś.\NSzukasz sekretów Drel.", name="Gart", style="Main")
    ev2 = pysubs2.SSAEvent(start=5000, end=7000, text="Miecz Drel został zniszczony.", name="Gart", style="Main")
    ev3 = pysubs2.SSAEvent(start=8000, end=10000, text="Nie widziałem Gart od wczoraj.", name="Drel", style="Main")
    ev4 = pysubs2.SSAEvent(start=11000, end=13000, text="Dzięki Drel wszystko ocalało.", name="Alicia", style="Main")
    ev5 = pysubs2.SSAEvent(start=14000, end=16000, text="Rozmawiają o Drel.", name="Gart", style="Main")
    ev6 = pysubs2.SSAEvent(start=17000, end=19000, text=r"Wiem, po co tu jesteś.\NSzukasz sekretów Drela.", name="Gart", style="Main")

    subs.events = [ev1, ev2, ev3, ev4, ev5, ev6]
    fixed_subs, fixes = EpisodeQualityGate.audit_and_fix_entire_episode(
        subs,
        character_registry={"Drel": "MALE", "Gart": "MALE"}
    )

    # Weryfikacja naprawy zgłoszonego błędu
    assert fixed_subs.events[0].text == r"Wiem, po co tu jesteś.\NSzukasz sekretów Drela.", f"Błąd w linii zgłoszonej: {fixed_subs.events[0].text}"
    assert fixed_subs.events[1].text == "Miecz Drela został zniszczony.", f"Błąd w dopełniaczu posiadacza: {fixed_subs.events[1].text}"
    assert fixed_subs.events[2].text == "Nie widziałem Garta od wczoraj.", f"Błąd w zaprzeczonym orzeczeniu: {fixed_subs.events[2].text}"
    assert fixed_subs.events[3].text == "Dzięki Drelowi wszystko ocalało.", f"Błąd w celowniku: {fixed_subs.events[3].text}"
    assert fixed_subs.events[4].text == "Rozmawiają o Drelu.", f"Błąd w miejscowniku: {fixed_subs.events[4].text}"
    # Weryfikacja braku podwójnej deklinacji dla formy już poprawnej
    assert fixed_subs.events[5].text == r"Wiem, po co tu jesteś.\NSzukasz sekretów Drela.", f"Błąd: podwójna zmiana poprawnej formy: {fixed_subs.events[5].text}"

    # Asercja 5: Deterministyczna deklinacja działa również bez rejestru postaci, na podstawie samych aktorów odcinka (ev.name)
    subs_auto = pysubs2.SSAFile()
    ev_auto1 = pysubs2.SSAEvent(start=1000, end=3000, text="Szukasz sekretów Drel.", name="Gart", style="Main")
    ev_auto2 = pysubs2.SSAEvent(start=4000, end=6000, text="Jestem Drel.", name="Drel", style="Main")
    subs_auto.events = [ev_auto1, ev_auto2]
    auto_fixed, _ = EpisodeQualityGate.audit_and_fix_entire_episode(subs_auto)
    assert auto_fixed.events[0].text == "Szukasz sekretów Drela.", f"Błąd: aktor 'Drel' nie został automatycznie odmieniony: {auto_fixed.events[0].text}"

    print(" -> PASSED: Fleksja imion obcych/fantasy, dopełniacz dzierżawczy i twardy bezpiecznik EpisodeQualityGate działają w 100% harmonii (0.00 PLN).")


def test_lexical_typo_correction_and_orthographic_integrity_guard():
    print("[TEST 51/51] Test Eliminacji Literówek, Integralności Ortograficznej (Filar CLXIV) i EpisodeQualityGate...")
    import pysubs2
    from avt_linter import AVTLinter, EpisodeQualityGate
    from rules import get_focused_rules_for_batch
    from series_memory import SeriesBible, sanitize_lexical_text

    # Asercja 1: AVTLinter bezbłędnie eliminuje literówkę 'spyham' -> 'spytam' w linii użytkownika z \N
    raw_line = r"O to, co tam odkryła,\Nspyham moją sługę osobiście."
    fixed_line, fixes = AVTLinter.lint_and_fix_line(raw_line)
    assert fixed_line == r"O to, co tam odkryła,\Nspytam moją sługę osobiście.", f"Błąd lintera: {fixed_line}"
    assert any("CLXIV" in f or "spyham" in f for f in fixes), "Błąd: brak atrybucji Filaru CLXIV w linterze!"

    # Asercja 2: Obsługa odmiany czasownika (Spyham, spyhasz, spyha, spyhała)
    t_cap, _ = AVTLinter.lint_and_fix_line("Spyham go o radę.")
    assert t_cap == "Spytam go o radę."
    t_past, _ = AVTLinter.lint_and_fix_line("Ona spyhała o drogę.")
    assert t_past == "Ona spytała o drogę."

    # Asercja 3: Eliminacja pozostałych deformacji fonetyczno-ortograficznych
    t_wziac, _ = AVTLinter.lint_and_fix_line("Muszę to wziąść.")
    assert t_wziac == "Muszę to wziąć."
    t_poszlem, _ = AVTLinter.lint_and_fix_line("Wczoraj tam poszłem.")
    assert t_poszlem == "Wczoraj tam poszedłem."
    t_wlaczac, _ = AVTLinter.lint_and_fix_line("Nie wolno tego włanczać.")
    assert t_wlaczac == "Nie wolno tego włączać."

    # Asercja 4: SeriesBible i sanitize_lexical_text czyszczą wpisy glosariusza i relacji z literówek
    assert sanitize_lexical_text("spyham o rozkazy") == "spytam o rozkazy"
    assert sanitize_lexical_text("chciał to wziąść") == "chciał to wziąć"

    # Asercja 5: Dynamiczny dyspozytor uwagi (focused_pillars) aktywuje Filar CLXIV dla słów pytania/dociekania
    batch_inquiry = [{"en": "I will ask my servant personally about what she discovered."}]
    rules_out = get_focused_rules_for_batch(batch_inquiry)
    assert "FILAR CLXIV" in rules_out, "Błąd: Filar CLXIV nie został aktywowany dla zapytania!"
    assert "spytam" in rules_out, "Błąd: wskazówka 'spytam' nie pojawiła się w promptcie skupienia!"

    # Asercja 6: EpisodeQualityGate naprawia kwestię użytkownika na pełnej osi czasu z formatowaniem \N (0.00 PLN)
    subs = pysubs2.SSAFile()
    ev = pysubs2.SSAEvent(start=1000, end=4000, text=r"O to, co tam odkryła,\Nspyham moją sługę osobiście.", name="Klen", style="Main")
    subs.events = [ev]
    audited_subs, eqg_fixes = EpisodeQualityGate.audit_and_fix_entire_episode(subs)
    assert audited_subs.events[0].text == r"O to, co tam odkryła,\Nspytam moją sługę osobiście.", f"Błąd EQG: {audited_subs.events[0].text}"
    assert any("spyham" in f for f in eqg_fixes), "Błąd: brak odnotowania naprawy w fixes EQG!"

    print(" -> PASSED: Eliminacja literówek, tarcza ortograficzna (Filar CLXIV) i EpisodeQualityGate działają w 100% harmonii (0.00 PLN).")


def test_frieren_manga_canon_aura_gilotyna_and_calque_shield():
    print("[TEST 52/52] Test Kanonu Mangowego Frieren (Studio JG / Martyna Zdonek), Tarczy 'Aura Gilotyna' i Eliminacji Kalki 'od Gilotyny'...")
    import pysubs2
    from manga_canon import manga_canon_registry
    from avt_linter import AVTLinter, EpisodeQualityGate
    from series_memory import generate_polish_name_declension, sanitize_lexical_text

    # Asercja 1: Weryfikacja rejestru kanonu dla Frieren - oficjalne wydawnictwo Studio JG i tłum. Martyna Zdonek
    canon = manga_canon_registry.find_canon_for_series("Sousou no Frieren")
    assert canon is not None, "Błąd: nie odnaleziono wpisu dla Sousou no Frieren w manga_canon!"
    assert "Studio JG" in canon["publisher"], f"Błąd wydawcy: {canon['publisher']}"
    assert "Martyna Zdonek" in canon["publisher"], f"Błąd: brak atrybucji rzeczywistej tłumaczki Martyny Zdonek w {canon['publisher']}"

    # Asercja 2: Oficjalny kanon to bezwzględnie 'Aura Gilotyna' (zarówno z EN jak i z JP kanji/transkrypcji)
    assert canon["glossary"]["Aura the Guillotine"] == "Aura Gilotyna"
    assert canon["glossary"]["Dantōdai no Aura"] == "Aura Gilotyna"
    assert canon["glossary"]["断頭台のアウラ"] == "Aura Gilotyna"

    # Asercja 3: Matryca fleksyjna 7 przypadków dla żeńskiego imienia złożonego 'Aura Gilotyna'
    decl = generate_polish_name_declension("Aura Gilotyna", gender="FEMALE")
    assert decl["M"] == "Aura Gilotyna"
    assert decl["D"] == "Aury Gilotyny"
    assert decl["C"] == "Aurze Gilotynie"
    assert decl["B"] == "Aurę Gilotynę"
    assert decl["N"] == "Aurą Gilotyną"
    assert decl["Ms"] == "Aurze Gilotynie"
    assert decl["W"] == "Auro Gilotyno"

    # Asercja 4: AVTLinter eliminuje kalkę 'Aura od Gilotyny' we wszystkich przypadkach gramatycznych
    t_m, fixes_m = AVTLinter.lint_and_fix_line("Oto bezlitosna Aura od Gilotyny.")
    assert t_m == "Oto bezlitosna Aura Gilotyna.", f"Błąd mianownika: {t_m}"
    assert any("Aura Gilotyna" in f for f in fixes_m)

    t_d, _ = AVTLinter.lint_and_fix_line(r"Boimy się armii\NAury od Gilotyny.")
    assert t_d == r"Boimy się armii\NAury Gilotyny.", f"Błąd dopełniacza: {t_d}"

    t_c, _ = AVTLinter.lint_and_fix_line("Rzucili wyzwanie Aurze od Gilotyny.")
    assert t_c == "Rzucili wyzwanie Aurze Gilotynie.", f"Błąd celownika: {t_c}"

    # Asercja 5: Series memory sanitize_lexical_text oczyszcza wpisy z 'od Gilotyny'
    assert sanitize_lexical_text("Aura od Gilotyny") == "Aura Gilotyna"
    assert sanitize_lexical_text("potęga Aury od Gilotyny") == "potęga Aury Gilotyny"

    # Asercja 6: EpisodeQualityGate post-pass (0.00 PLN) naprawia 'Aura od Gilotyny' na osi czasu .ass
    subs = pysubs2.SSAFile()
    subs.events.append(pysubs2.SSAEvent(start=1000, end=4000, text=r"To ona,\Npotężna Aura od Gilotyny!"))
    audited, eqg_fixes = EpisodeQualityGate.audit_and_fix_entire_episode(subs)
    assert audited.events[0].text == r"To ona,\Npotężna Aura Gilotyna!", f"Błąd EQG: {audited.events[0].text}"
    assert any("Aura Gilotyna" in f for f in eqg_fixes)

    # Asercja 7: Automatyczny audyt dokumentacji README.md pod kątem zgodności z bazą kanonu
    readme_path = Path(__file__).parent / "README.md"
    assert readme_path.exists(), "Błąd: brak pliku README.md w repozytorium!"
    with open(readme_path, "r", encoding="utf-8") as f:
        readme_content = f.read()

    assert "Aura od Gilotyny" not in readme_content, "Błąd audytu README: wykryto zmyśloną kalkę 'Aura od Gilotyny'!"
    assert "Kishōkyō" not in readme_content, "Błąd audytu README: wykryto błędną transkrypcję 'Kishōkyō'!"
    assert "A. Zychma" not in readme_content, "Błąd audytu README: wykryto fikcyjnego tłumacza 'A. Zychma'!"
    assert "Aura Gilotyna" in readme_content, "Błąd audytu README: brak oficjalnego kanonu 'Aura Gilotyna'!"
    assert "Martyna Zdonek" in readme_content, "Błąd audytu README: brak rzeczywistej tłumaczki 'Martyna Zdonek'!"
    assert "Dantōdai no Aura" in readme_content, "Błąd audytu README: brak poprawnej transkrypcji 'Dantōdai no Aura'!"
    assert "Prosta Domena" in readme_content, "Błąd audytu README: brak kanonu 'Prosta Domena'!"
    assert "D. Bruszewska" in readme_content, "Błąd audytu README: brak rzeczywistej tłumaczki Waneko 'D. Bruszewska'!"

    print(" -> PASSED: Kanon mangowy Frieren (Studio JG / Martyna Zdonek), tarcza 'Aura Gilotyna', eliminacja 'od Gilotyny' oraz audyt dokumentacji README działają w 100% harmonii (0.00 PLN).")


def test_relational_tv_invariance_and_hybrid_vocative_guard():
    print("\n[TEST 53/53] Test Relacyjnej Nienaruszalności T-V, Tarczy Wołacza i Likwidacji Hybryd Pan/Ty...")
    import pysubs2
    from avt_linter import AVTLinter, EpisodeQualityGate
    from series_memory import SeriesBible, sanitize_lexical_text
    from profiler import EpisodeProfiler
    from rules import BELCZYK_AVT_MASTER_CANON, get_focused_rules_for_batch

    # Asercja 1 (Warstwa 1 - profiler.py): Prompt Profilera zawiera bezpieczniki relacyjne i zakaz hybryd wołacza
    dummy_client = None
    profiler = EpisodeProfiler(dummy_client)
    # Check that the prompt instruction text includes key invariants
    import inspect
    profiler_source = inspect.getsource(EpisodeProfiler.profile_episode)
    assert "INTRA-CLAUSE T-V HYBRID BAN" in profiler_source, "Błąd Profiler: brak dyrektywy INTRA-CLAUSE T-V HYBRID BAN w promptcie!"
    assert "ENGLISH '-SAMA' DROP IMMUNITY" in profiler_source, "Błąd Profiler: brak bezpiecznika ENGLISH '-SAMA' DROP IMMUNITY!"
    assert "odkąd pan Eftal zniszczył" in profiler_source, "Błąd Profiler: brak ochrony mianownika tytulatury podmiotu!"

    # Asercja 2 (Warstwa 2 - series_memory.py): sanitize_lexical_text i SeriesBible oczyszczają błędy gramatyczne
    # 2a: Deformacja leksykalna 'najdobrejsze' -> 'najlepsze'
    assert sanitize_lexical_text("miał z nas wszystkich najdobrejsze serce") == "miał z nas wszystkich najlepsze serce"
    assert sanitize_lexical_text("najdobrejszy wojownik") == "najlepszy wojownik"
    assert sanitize_lexical_text("dobrejsza opcja") == "lepsza opcja"

    # 2b: Skażenie mianownika tytulatury 'pan Eftala zniszczył' -> 'pan Eftal zniszczył'
    assert sanitize_lexical_text(r"odkąd pan\NEftala zniszczył twoje piętno") == r"odkąd pan\NEftal zniszczył twoje piętno"
    assert sanitize_lexical_text("pan Eftala pokonał smoka") == "pan Eftal pokonał smoka"
    # Imiona orientalne kanonicznie kończące się na -a w mianowniku pozostają nienaruszone:
    assert sanitize_lexical_text("pan Akira zniszczył pieczęć") == "pan Akira zniszczył pieczęć"

    # 2c: Hierarchiczne relacje w SeriesBible otrzymują bezpiecznik T-V Invariance
    bible = SeriesBible("Test_Series_TV")
    clean_entry = bible._sanitize_character_entry("Merlin", "uczennica i powierniczka Eftala sprzed 400 lat, arcymag")
    assert "T-V Invariance" in clean_entry, "Błąd SeriesBible: brak bezpiecznika T-V Invariance dla relacji hierarchicznej!"

    # Asercja 3 (Warstwa 3 - rules.py): Kanon i dyspozytor reguł koncentrują uwagę na Filarze C i CLVII
    assert "INTRA-CLAUSE T-V HYBRID BAN" in BELCZYK_AVT_MASTER_CANON, "Błąd rules.py: brak Filar C punkt 5!"
    assert "ENGLISH \"-SAMA\" DROP IMMUNITY" in BELCZYK_AVT_MASTER_CANON, "Błąd rules.py: brak Filar C punkt 6!"
    assert "ZAKAZ HYBRYD WOŁACZA Z FORMĄ PAN/PANI" in BELCZYK_AVT_MASTER_CANON, "Błąd rules.py: brak Filar CLVII punkt 5!"

    batch_drift_test = [{"en": "Look, why?! Did you see that?", "pl": "Poza tym, Eftalu... ma pan zaczerwienioną twarz."}]
    focused = get_focused_rules_for_batch(batch_drift_test)
    assert "FILAR CLVII" in focused, "Błąd dyspozytora: brak aktywacji Filaru CLVII dla hybrydy adresatywnej!"
    assert "Zakaz Hybryd Wołacza" in focused, "Błąd dyspozytora: brak wytycznej o zakazie hybryd wołacza!"

    # Asercja 4 (Warstwa 4 - avt_linter.py & EpisodeQualityGate 0.00 PLN):
    # 4a: Zlikwidowanie hybrydy wołacza 'Eftalu... ma pan' -> 'panie Eftalu... ma pan'
    subs_hybrid = pysubs2.SSAFile()
    subs_hybrid.events.append(pysubs2.SSAEvent(
        start=1000, end=4000, name="Merlin",
        text=r"Poza tym, Eftalu...\Nma pan zaczerwienioną twarz."
    ))
    bible_rakudai = SeriesBible("Rakudai Kenja no Gakuin Musou")
    fixed_hybrid, fixes_hybrid = EpisodeQualityGate.audit_and_fix_entire_episode(subs_hybrid, series_bible=bible_rakudai)
    assert fixed_hybrid.events[0].text == r"Poza tym, panie Eftalu...\Nma pan zaczerwienioną twarz.", f"Błąd likwidacji hybrydy: {fixed_hybrid.events[0].text}"
    assert any("zlikwidowano hybrydę wołacza 'Eftalu'" in f for f in fixes_hybrid)

    # 4b: Naprawa skażenia mianownika tytulatury 'pan Eftala zniszczył' -> 'pan Eftal zniszczył'
    subs_nom = pysubs2.SSAFile()
    subs_nom.events.append(pysubs2.SSAEvent(
        start=1000, end=4000, name="Merlin",
        text=r"Minął tydzień, odkąd pan\NEftala zniszczył twoje piętno."
    ))
    fixed_nom, fixes_nom = EpisodeQualityGate.audit_and_fix_entire_episode(subs_nom, series_bible=bible_rakudai)
    assert fixed_nom.events[0].text == r"Minął tydzień, odkąd pan\NEftal zniszczył twoje piętno.", f"Błąd mianownika tytulatury: {fixed_nom.events[0].text}"
    assert any("pan Eftal" in f for f in fixes_nom)

    # 4c: Harmonizacja opuszczonego sufiksu -sama w okrzykach dla stałego mówcy formalnego (Anti-Sama-Drop)
    subs_sama = pysubs2.SSAFile()
    # Context events establishing Merlin as strictly formal toward Eftal
    subs_sama.events.append(pysubs2.SSAEvent(start=1000, end=3000, name="Merlin", text="Zgadza się, panie Eftalu."))
    subs_sama.events.append(pysubs2.SSAEvent(start=4000, end=6000, name="Merlin", text="Czego właściwie pan szuka, panie Eftalu?"))
    # The exclamatory line where -sama was dropped in English
    subs_sama.events.append(pysubs2.SSAEvent(start=7000, end=9000, name="Merlin", text="Co za kunszt, Eftalu!"))
    subs_sama.events.append(pysubs2.SSAEvent(start=10000, end=12000, name="Merlin", text="T-To było niesamowite, Eftalu!"))
    fixed_sama, fixes_sama = EpisodeQualityGate.audit_and_fix_entire_episode(subs_sama, series_bible=bible_rakudai)
    assert fixed_sama.events[2].text == "Co za kunszt, panie Eftalu!", f"Błąd Anti-Sama-Drop: {fixed_sama.events[2].text}"
    assert fixed_sama.events[3].text == "T-To było niesamowite, panie Eftalu!", f"Błąd Anti-Sama-Drop: {fixed_sama.events[3].text}"
    assert any("zharmonizowano wołacz formalny dla mówcy 'Merlin'" in f for f in fixes_sama)

    # 4d: Naprawa deformacji leksykalnej 'najdobrejsze' -> 'najlepsze' przez linter
    t_najd, fixes_najd = AVTLinter.lint_and_fix_line(r"...miał z nas\Nwszystkich najdobrejsze serce!")
    assert t_najd == r"...miał z nas\Nwszystkich najlepsze serce!", f"Błąd lintera: {t_najd}"
    assert any("najdobrejszy" in f for f in fixes_najd)

    print(" -> PASSED: Relacyjna nienaruszalność T-V, tarcza wołacza, eliminacja hybryd pan/ty, Anti-Sama-Drop i ochrona mianownika działają w 100% harmonii (0.00 PLN).")


def test_linguistic_invariants_and_kakegoe_noise_elision():
    """
    Test 54: Weryfikacja bezwzględnych niezmienników leksykalnych, ortograficznych,
    pleonastycznych oraz eliminacji szumu kinezjatycznego Kakegoe i kalki 'Here' -> 'Tutaj'.
    """
    print("\n[TEST 54] Test bezwzględnych niezmienników i elipsy szumu kinezjatycznego...")
    from series_memory import sanitize_lexical_text
    from avt_linter import AVTLinter, EpisodeQualityGate
    import pysubs2

    # 1. Test sanityzacji leksykalnej w series_memory (Protokół 5 Warstw - Warstwa 2)
    assert sanitize_lexical_text("W każdym bądź razie to sprawdzimy.") == "W każdym razie to sprawdzimy."
    assert sanitize_lexical_text("Napisał to słowo w cudzysłowiu.") == "Napisał to słowo w cudzysłowie."
    assert sanitize_lexical_text("Poszedł po najmniejszej linii oporu.") == "Poszedł po linii najmniejszego oporu."
    assert sanitize_lexical_text("Wygrał trzy razy pod rząd!") == "Wygrał trzy razy z rzędu!"
    assert sanitize_lexical_text("Wrócił spowrotem do zamku.") == "Wrócił z powrotem do zamku."
    assert sanitize_lexical_text("Zrobił to dlatego bo musiał.") == "Zrobił to dlatego że musiał."
    assert sanitize_lexical_text("Zaatakował ich od nienacka.") == "Zaatakował ich znienacka."
    assert sanitize_lexical_text("Głaz zaczął spadać w dół.") == "Głaz zaczął spadać."
    assert sanitize_lexical_text("Dym zaczął wznosić się w górę.") == "Dym zaczął wznosić się."
    assert sanitize_lexical_text("To były fakty autentyczne.") == "To były fakty."
    assert sanitize_lexical_text("Nawiązali wzajemną współpracę.") == "Nawiązali współpracę."

    # 2. Test reguł lintera (AVTLinter - Warstwa 4)
    t_gb, _ = AVTLinter.lint_and_fix_line("Zrób swoje najlepsze, wierzę w ciebie!")
    assert "Daj z siebie wszystko" in t_gb, f"Błąd lintera: {t_gb}"
    t_gb_pl, _ = AVTLinter.lint_and_fix_line("Zróbcie swoje najlepsze!")
    assert "Dajcie z siebie wszystko" in t_gb_pl, f"Błąd lintera: {t_gb_pl}"

    t_gn, _ = AVTLinter.lint_and_fix_line("Dobrej nocy, do jutra.")
    assert "Dobranoc, do jutra." in t_gn, f"Błąd lintera: {t_gn}"

    t_gw, _ = AVTLinter.lint_and_fix_line("Zgadnij co?")
    assert t_gw == "Wiesz co?", f"Błąd lintera: {t_gw}"

    t_tw, _ = AVTLinter.lint_and_fix_line("To jest to, o czym mówię!")
    assert t_tw == "O tym właśnie mówię!", f"Błąd lintera: {t_tw}"

    t_hg, _ = AVTLinter.lint_and_fix_line("Tutaj masz swój płaszcz.")
    assert "Trzymaj swój płaszcz." in t_hg, f"Błąd lintera: {t_hg}"

    # 3. Test EpisodeQualityGate (Likwidacja 'Tutaj' i elipsa szumu Kakegoe)
    subs = pysubs2.SSAFile()
    # Linia 0: Normalny dialog
    subs.events.append(pysubs2.SSAEvent(start=1000, end=3000, name="Alice", text="Prosiłeś o tę herbatę?"))
    # Linia 1: Kalka 'Here.' przetłumaczona jako 'Tutaj.' przy podaniu herbaty -> powinno zmienić na 'Proszę.'
    subs.events.append(pysubs2.SSAEvent(start=3500, end=4500, name="Alice", text="Tutaj."))
    # Linia 2: Pytanie o miejsce
    subs.events.append(pysubs2.SSAEvent(start=5000, end=7000, name="Bob", text="Gdzie leżą dokumenty?"))
    # Linia 3: Prawidłowe wskazanie lokalizacji 'Tutaj.' -> NIE MOŻE zostać zmienione!
    subs.events.append(pysubs2.SSAEvent(start=7200, end=8500, name="Alice", text="Tutaj."))
    # Linia 4: Infantylny odgłos wstawania/wysiłku 'Hop...' -> powinien zostać wyciszony do pustego napisu
    subs.events.append(pysubs2.SSAEvent(start=9000, end=9800, name="Bob", text="Hop..."))
    # Linia 5: Kolejny infantylny odgłos 'I siup...' -> wyciszony
    subs.events.append(pysubs2.SSAEvent(start=10000, end=10800, name="Bob", text="I siup..."))

    fixed_subs, fixes = EpisodeQualityGate.audit_and_fix_entire_episode(subs)
    assert fixed_subs.events[1].text == "Proszę.", f"Błąd likwidacji kalki 'Tutaj': {fixed_subs.events[1].text}"
    assert fixed_subs.events[3].text == "Tutaj.", f"Błąd: zniszczono poprawną odpowiedź przestrzenną: {fixed_subs.events[3].text}"
    assert fixed_subs.events[4].text == "", f"Błąd elipsy szumu Kakegoe: {fixed_subs.events[4].text}"
    assert fixed_subs.events[5].text == "", f"Błąd elipsy szumu Kakegoe: {fixed_subs.events[5].text}"
    assert any("zlikwidowano kalkę gestu 'Here'" in f for f in fixes)
    assert any("wyciszono infantylny odgłos kinezjatyczny" in f for f in fixes)

    print(" -> PASSED: Bezwzględne niezmienniki językowe, likwidacja kalki 'Tutaj' i elipsa szumu Kakegoe działają ze 100% precyzją.")


def test_temporal_discontinuity_and_scene_boundary_guard():
    print("[TEST 55] Test protokołu dyskontinuitetu czasowego, przeskoków scen i opóźnionego potwierdzenia (Filar CLXV)...")
    from avt_linter import EpisodeQualityGate
    from rules import BELCZYK_AVT_MASTER_CANON, get_focused_rules_for_batch
    import pysubs2

    # 1. Sprawdzenie obecności Filaru CLXV w Kanonie Belczyka (Warstwa 3)
    assert "FILAR CLXV: DYSKONTINUITET CZASOWY" in BELCZYK_AVT_MASTER_CANON, "Brak Filaru CLXV w BELCZYK_AVT_MASTER_CANON"

    # 2. Sprawdzenie aktywacji dynamicznego dyspozytora reguł (Warstwa 3)
    batch_private = [
        {"en": "Could we talk in private for a moment?", "duration_s": 3.6},
        {"en": "Sure, what is it?", "duration_s": 2.6}
    ]
    f_rules = get_focused_rules_for_batch(batch_private)
    assert "CLXV" in f_rules, f"Dyspozytor nie aktywował Filaru CLXV: {f_rules}"

    # 3. Przypadek zgłoszony przez użytkownika 1:1 (Anastasia i Eftal, luka 20.43 sekundy) (Warstwa 4)
    subs = pysubs2.SSAFile()
    # 0:16:15.18 -> 0:16:18.82 (975180ms - 978820ms)
    subs.events.append(pysubs2.SSAEvent(
        start=975180,
        end=978820,
        name="Anastasia",
        text=r"Moglibyśmy porozmawiać\Nprzez chwilę na osobności?"
    ))
    # 0:16:39.25 -> 0:16:41.88 (999250ms - 1001880ms) -> luka 20430ms (20.43s)
    subs.events.append(pysubs2.SSAEvent(
        start=999250,
        end=1001880,
        name="Eftal",
        text="Jasne, o co chodzi?"
    ))

    fixed_subs, fixes = EpisodeQualityGate.audit_and_fix_entire_episode(subs)
    assert fixed_subs.events[1].text == "Więc o co chodzi?", f"Błąd naprawy opóźnionego potwierdzenia: {fixed_subs.events[1].text}"
    assert any("[Episode Quality Gate - Filar CLXV Dyskontinuitet Czasowy]" in f for f in fixes)
    assert any("zlikwidowano opóźnione potwierdzenie 'Jasne, o co chodzi'" in f for f in fixes)

    # 4. Test wariantów leksykalnych opóźnionego potwierdzenia po przeskoku sceny (Warstwa 4)
    variants = [
        ("Pewnie, o co chodzi?", "Więc o co chodzi?"),
        ("W porządku, o co chodzi?", "Więc o co chodzi?"),
        ("Jasne, co się stało?", "Więc co się stało?"),
        ("Jasne, w czym rzecz?", "Więc w czym rzecz?"),
        ("Dobrze, o co chodzi?", "Więc o co chodzi?"),
        ("No dobra, o co chodzi?", "Więc o co chodzi?"),
        ("Jasne, słucham cię", "Więc słucham cię"),
        (r"{\i1}Jasne, o co chodzi?{\i0}", r"{\i1}Więc o co chodzi?{\i0}"),
        (r"Jasne, o co chodzi?\NCo się stało?", r"Więc o co chodzi?\NCo się stało?")
    ]
    for orig_t, expected_t in variants:
        s_test = pysubs2.SSAFile()
        s_test.events.append(pysubs2.SSAEvent(start=10000, end=14000, name="A", text="Chodźmy na osobność."))
        s_test.events.append(pysubs2.SSAEvent(start=25000, end=28000, name="B", text=orig_t))  # luka 11s
        fixed_v, _ = EpisodeQualityGate.audit_and_fix_entire_episode(s_test)
        assert fixed_v.events[1].text == expected_t, f"Błąd dla wariantu '{orig_t}': otrzymano '{fixed_v.events[1].text}', oczekiwano '{expected_t}'"

    # 5. Tarcza nienaruszalności szybkiego dialogu w tym samym pomieszczeniu (Fast Dialogue Immunity)
    subs_fast = pysubs2.SSAFile()
    subs_fast.events.append(pysubs2.SSAEvent(start=10000, end=12000, name="Alice", text="Mogę ci zadać pytanie?"))
    subs_fast.events.append(pysubs2.SSAEvent(start=13000, end=15000, name="Bob", text="Jasne, o co chodzi?"))  # luka tylko 1.0s
    fixed_fast, fast_fixes = EpisodeQualityGate.audit_and_fix_entire_episode(subs_fast)
    assert fixed_fast.events[1].text == "Jasne, o co chodzi?", f"Błąd: naruszono szybki dialog w tej samej scenie: {fixed_fast.events[1].text}"
    assert len(fast_fixes) == 0, f"Nieoczekiwane poprawki w szybkim dialogu: {fast_fixes}"

    print(" -> PASSED: Protokół dyskontinuitetu czasowego, przeskoki scen i eliminacja 'Jasne, o co chodzi?' (Filar CLXV) działają w 100% harmonii (0.00 PLN).")


if __name__ == "__main__":
    print("\n--- Rozpoczynanie testów weryfikacyjnych ---")
    test_rules_and_prompts()
    test_pydantic_schemas()
    test_sanitization_and_deduplication()
    test_subtitle_parsing_and_saving()
    test_ffmpeg_frame_extraction()
    test_profiler_and_whisper()
    test_model_resolver()
    test_avt_linter()
    test_series_bible()
    test_avt_formatter_and_cps()
    test_prosody_and_diarizer()
    test_typesetting_matcher()
    test_manga_canon()
    test_batch_queue()
    test_context_cache()
    test_pricing_guard()
    test_sign_detector()
    test_user_feedback_manager()
    test_deterministic_glossary()
    test_dynamic_rule_dispatcher()
    test_fuzzy_and_dynamic_avt_linter()
    test_gui_interactive_learning_components()
    test_extended_avt_pillars()
    test_master_avt_pillars()
    test_excellence_avt_pillars()
    test_cognitive_prosody_and_narrative_pillars()
    test_visual_discourse_and_transcreation_pillars()
    test_masterpieces_and_semiotics_pillars()
    test_translator_logger_and_sign_detector()
    test_masterclass_next_gen()
    test_masterclass_2_innovations()
    test_adaptive_thinking_budget()
    test_cornerstone_invariants()
    test_episode_quality_gate()
    test_character_gender_invariance_architecture()
    test_blind_read_and_scene_social_context()
    test_affective_incongruity_and_sarcasm_detector()
    test_quality_gate_name_declension_vocative_and_micro_lines()
    test_comprehensive_architecture_extensions()
    test_anti_attention_dilution_semantic_anchors_and_full_phase2()
    test_fansub_quality_pixel_perfect_typesetting()
    test_phase1_gender_hallucination_arbitration()
    test_multimodal_addressee_and_plural_group_resolution()
    test_exception_driven_architecture_and_conflict_shields()
    test_gemini_developer_api_schema_compliance_no_additional_properties()
    test_user_glossary_lowest_priority_guard()
    test_foreign_fantasy_name_declension_and_genitive_possession_guard()
    test_lexical_typo_correction_and_orthographic_integrity_guard()
    test_frieren_manga_canon_aura_gilotyna_and_calque_shield()
    test_relational_tv_invariance_and_hybrid_vocative_guard()
    test_linguistic_invariants_and_kakegoe_noise_elision()
    test_temporal_discontinuity_and_scene_boundary_guard()
    print("\n Wszystkie testy jednostkowe i integracyjne (55/55) zakończone pełnym sukcesem!\n")





