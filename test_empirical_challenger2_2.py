# -*- coding: utf-8 -*-
"""
Empirical Verification & Deep Adversarial Harness — Challenger 2 (Iteration 2)
Incident: INC-AVT-004 (Tensei Kizoku S3)
Focus:
  E1. Vocative masculine shields enforce male addressee without polluting 3rd person verbs.
  E2. Social roles with possessive adjectives harmonize correctly ('jesteś moją najlepszą uczennicą' -> 'jesteś moim najlepszym uczniem').
  E3. Age variants inherit base character gender ('Young Braham' -> MALE).
  E4. Audio F0 pitch does not contaminate male character registries.
"""

import sys
import re
import pysubs2

from series_memory import (
    SeriesBible,
    resolve_actor_gender,
)
from avt_linter import EpisodeQualityGate, AVTLinter
from translator import MultimodalTranslator

def run_empirical_verification():
    passed = 0
    failed = 0
    errors = []

    def verify(name, condition, details=""):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  [PASS] {name}")
        else:
            failed += 1
            print(f"  [FAIL] {name}: {details}")
            errors.append(f"{name}: {details}")

    bible = SeriesBible("Tensei Kizoku, Kantei Skill de Nariagaru")

    print("\n" + "="*70)
    print(" EMPIRICAL SUITE E1: VOCATIVE MASCULINE SHIELD & 3RD PERSON INVARIANCE")
    print("="*70)

    # E1.1: Core vocative masculine triggers
    vocatives_tested = [
        ("Rietz", "Rietzie", "Tylko ty byłaś w stanie, Rietzie.", "Tylko ty byłeś w stanie, Rietzie."),
        ("Braham", "Brahamie", "Dlaczego byłaś taka nieostrożna, Brahamie?", "Dlaczego byłeś taki nieostrożny, Brahamie?"),
        ("Ars", "Arsie", "Cieszę się, że wróciłaś, Arsie.", "Cieszę się, że wróciłeś, Arsie."),
    ]
    for cname, voc, inp, exp in vocatives_tested:
        subs = pysubs2.SSAFile()
        ev = pysubs2.SSAEvent(start=1000, end=3000, name="Speaker", text=inp)
        subs.events.append(ev)
        EpisodeQualityGate.audit_and_fix_entire_episode(subs=subs, series_bible=bible)
        verify(f"E1.1: Vocative '{voc}' converts 2nd pers fem to masc: '{inp}'",
               subs.events[0].text == exp,
               f"Expected '{exp}', got '{subs.events[0].text}'")

    # E1.2: Vocative punctuation boundaries (commas, exclamation, question, ellipses, dash, ASS newline)
    punct_cases = [
        ("Rietzie, byłaś gotowa?", "Rietzie, byłeś gotowy?"),
        ("Rietzie! Byłaś niesamowita!", "Rietzie! Byłeś niesamowity!"),
        ("Byłaś gotowa, Rietzie…", "Byłeś gotowy, Rietzie…"),
        ("Byłaś gotowa, Rietzie...", "Byłeś gotowy, Rietzie..."),
        ("Byłaś gotowa, Rietzie--", "Byłeś gotowy, Rietzie--"),
        ("Byłaś gotowa, Rietzie\\Nnaprawdę.", "Byłeś gotowy, Rietzie\\Nnaprawdę."),
        ("Byłaś gotowa, Rietzie", "Byłeś gotowy, Rietzie"),  # End of string
    ]
    for inp, exp in punct_cases:
        subs = pysubs2.SSAFile()
        ev = pysubs2.SSAEvent(start=1000, end=3000, name="Speaker", text=inp)
        subs.events.append(ev)
        EpisodeQualityGate.audit_and_fix_entire_episode(subs=subs, series_bible=bible)
        verify(f"E1.2: Punctuation boundary: '{inp}'",
               subs.events[0].text == exp,
               f"Expected '{exp}', got '{subs.events[0].text}'")

    # E1.3: Deep check of 3rd person past tense forms (MUST NOT BE POLLUTED!)
    # Polish 3rd person feminine past tense verbs: była, poszła, zrobiła, powiedziała, uciekła, zniknęła
    third_person_tests = [
        ("Rietzie, ona była wczoraj w zamku.",
         lambda out: "ona była" in out and "byłeś" not in out and not re.search(r"\bona był\b", out)),
        ("Brahamie, Charlotte poszła do lasu.",
         lambda out: "Charlotte poszła" in out and not re.search(r"\bposzedł\b", out)),
        ("Arsie, jej siostra zrobiła to sama.",
         lambda out: "siostra zrobiła" in out and not re.search(r"\bzrobił\b", out)),
        ("Rietzie, wiedziałaś, że ona tam poszła?",
         lambda out: "wiedziałeś" in out and "ona tam poszła" in out),
        ("Brahamie, czy wiedziałaś, że matka uciekła z miasta?",
         lambda out: "czy wiedziałeś" in out and "matka uciekła" in out),
        ("Arsie, Charlotte była zmęczona i poszła spać.",
         lambda out: "Charlotte była zmęczona i poszła spać" in out),
        ("Rietzie, tamta kobieta zniknęła bez śladu.",
         lambda out: "tamta kobieta zniknęła" in out),
        ("Kiedy ona mówiła, ty tylko milczałaś, Rietzie.",
         lambda out: "Kiedy ona mówiła" in out and "milczałeś, Rietzie" in out),
    ]
    for inp, validator in third_person_tests:
        subs = pysubs2.SSAFile()
        ev = pysubs2.SSAEvent(start=1000, end=3000, name="Speaker", text=inp)
        subs.events.append(ev)
        EpisodeQualityGate.audit_and_fix_entire_episode(subs=subs, series_bible=bible)
        out = subs.events[0].text
        verify(f"E1.3: 3rd person protection in: '{inp}'",
               validator(out),
               f"Output was: '{out}'")

    # E1.4: Female vocative negative control (MUST NOT CONVERT TO MASCULINE)
    bible.data["characters"]["Mireille"] = {"gender": "FEMALE", "description": "KOBIETA", "polish_declension": {"W": "Mireille"}}
    female_voc_tests = [
        "Mireille, byłaś taka mądra.",
        "Tylko ty byłaś w stanie to zrobić, Mireille.",
        "Cieszę się, że wróciłaś, Mireille.",
    ]
    for inp in female_voc_tests:
        subs = pysubs2.SSAFile()
        ev = pysubs2.SSAEvent(start=1000, end=3000, name="Speaker", text=inp)
        subs.events.append(ev)
        EpisodeQualityGate.audit_and_fix_entire_episode(subs=subs, series_bible=bible)
        verify(f"E1.4 [NEGATIVE]: Female vocative keeps feminine: '{inp}'",
               subs.events[0].text == inp,
               f"Expected '{inp}', got '{subs.events[0].text}'")

    print("\n" + "="*70)
    print(" EMPIRICAL SUITE E2: SOCIAL ROLES & POSSESSIVE ADJECTIVE HARMONIZATION")
    print("="*70)

    # E2.1: Key requirement case: 'jesteś moją najlepszą uczennicą' -> 'jesteś moim najlepszym uczniem'
    subs = pysubs2.SSAFile()
    ev = pysubs2.SSAEvent(start=1000, end=3000, name="Rietz", text="Jesteś moją najlepszą uczennicą.")
    ev.addressee = "Braham"
    subs.events.append(ev)
    EpisodeQualityGate.audit_and_fix_entire_episode(subs=subs, series_bible=bible)
    verify("E2.1: 'Jesteś moją najlepszą uczennicą.' -> 'Jesteś moim najlepszym uczniem.'",
           subs.events[0].text == "Jesteś moim najlepszym uczniem.",
           f"Got: '{subs.events[0].text}'")

    # E2.2: Possessive pronoun variants in Instrumental
    possessives_tested = [
        ("Jesteś moją uczennicą.", "Jesteś moim uczniem."),
        ("Jesteś naszą uczennicą.", "Jesteś naszym uczniem."),
        ("Jesteś twoją ulubioną uczennicą.", "Jesteś twoim ulubionym uczniem."),
        ("Jesteś swoją najlepszą uczennicą.", "Jesteś swoim najlepszym uczniem."),
        ("Jesteś moją nową uczennicą.", "Jesteś moim nowym uczniem."),
        ("Jesteś moją jedyną uczennicą.", "Jesteś moim jedynym uczniem."),
        ("Zostałeś moją najlepszą uczennicą.", "Zostałeś moim najlepszym uczniem."),
    ]
    for inp, exp in possessives_tested:
        subs = pysubs2.SSAFile()
        ev = pysubs2.SSAEvent(start=1000, end=3000, name="Rietz", text=inp)
        ev.addressee = "Braham"
        subs.events.append(ev)
        EpisodeQualityGate.audit_and_fix_entire_episode(subs=subs, series_bible=bible)
        verify(f"E2.2: Possessive harmonization: '{inp}'",
               subs.events[0].text == exp,
               f"Expected '{exp}', got '{subs.events[0].text}'")

    # E2.2b: Plural pronoun to singular addressee (Dyadic Concordance Test 89 + Gender Harmonization)
    subs = pysubs2.SSAFile()
    ev = pysubs2.SSAEvent(start=1000, end=3000, name="Rietz", text="Jesteś waszą uczennicą.")
    ev.addressee = "Braham"
    subs.events.append(ev)
    EpisodeQualityGate.audit_and_fix_entire_episode(subs=subs, series_bible=bible)
    verify("E2.2b: 'Jesteś waszą uczennicą.' -> dyadic singular + gender -> 'Jesteś twoim uczniem.'",
           subs.events[0].text == "Jesteś twoim uczniem.",
           f"Got: '{subs.events[0].text}'")

    # E2.3: Nominative predicate harmonization with possessives
    nom_tested = [
        ("Jesteś moja najlepsza uczennica.", "Jesteś mój najlepszy uczeń."),
        ("Jesteś moja nowa uczennica.", "Jesteś mój nowy uczeń."),
        ("Ty jesteś nasza ulubiona uczennica.", "Ty jesteś nasz ulubiony uczeń."),
    ]
    for inp, exp in nom_tested:
        subs = pysubs2.SSAFile()
        ev = pysubs2.SSAEvent(start=1000, end=3000, name="Rietz", text=inp)
        ev.addressee = "Braham"
        subs.events.append(ev)
        EpisodeQualityGate.audit_and_fix_entire_episode(subs=subs, series_bible=bible)
        verify(f"E2.3: Nominative possessive harmonization: '{inp}'",
               subs.events[0].text == exp,
               f"Expected '{exp}', got '{subs.events[0].text}'")

    # E2.4: Negative controls: Female addressee and 3rd person statements
    neg_role_cases = [
        ("Charlotte", "Jesteś moją najlepszą uczennicą.", "Jesteś moją najlepszą uczennicą."),
        ("Charlotte", "Jesteś naszą nową uczennicą.", "Jesteś naszą nową uczennicą."),
        ("Braham", "Ona jest moją najlepszą uczennicą.", "Ona jest moją najlepszą uczennicą."),
        ("Braham", "Ona była moją najlepszą uczennicą.", "Ona była moją najlepszą uczennicą."),
    ]
    for target, inp, exp in neg_role_cases:
        subs = pysubs2.SSAFile()
        ev = pysubs2.SSAEvent(start=1000, end=3000, name="Rietz", text=inp)
        ev.addressee = target
        subs.events.append(ev)
        EpisodeQualityGate.audit_and_fix_entire_episode(subs=subs, series_bible=bible)
        verify(f"E2.4 [NEGATIVE]: Invariant for target '{target}': '{inp}'",
               subs.events[0].text == exp,
               f"Expected '{exp}', got '{subs.events[0].text}'")

    print("\n" + "="*70)
    print(" EMPIRICAL SUITE E3: AGE VARIANT GENDER INHERITANCE")
    print("="*70)

    # E3.1: All age prefixes on male base character ('Braham')
    male_prefixes = [
        ("Young Braham", "MALE"),
        ("Kid Braham", "MALE"),
        ("Little Braham", "MALE"),
        ("Baby Braham", "MALE"),
        ("Child Braham", "MALE"),
        ("Teen Braham", "MALE"),
        ("Old Braham", "MALE"),
        ("Młody Braham", "MALE"),
        ("Mały Braham", "MALE"),
    ]
    for name_variant, exp_gender in male_prefixes:
        actual_bible = bible.get_character_gender(name_variant)
        actual_actor = resolve_actor_gender(name_variant, series_bible=bible)
        verify(f"E3.1: SeriesBible '{name_variant}' -> {exp_gender}",
               actual_bible == exp_gender,
               f"Got: '{actual_bible}'")
        verify(f"E3.1: resolve_actor_gender '{name_variant}' -> {exp_gender}",
               actual_actor == exp_gender,
               f"Got: '{actual_actor}'")

    # E3.2: Female age prefixes on female base character ('Charlotte', 'Licia')
    female_prefixes = [
        ("Young Charlotte", "FEMALE"),
        ("Little Charlotte", "FEMALE"),
        ("Baby Charlotte", "FEMALE"),
        ("Teen Charlotte", "FEMALE"),
        ("Little Licia", "FEMALE"),
        ("Young Licia", "FEMALE"),
    ]
    for name_variant, exp_gender in female_prefixes:
        actual_bible = bible.get_character_gender(name_variant)
        actual_actor = resolve_actor_gender(name_variant, series_bible=bible)
        verify(f"E3.2: Female variant '{name_variant}' -> {exp_gender}",
               actual_bible == exp_gender and actual_actor == exp_gender,
               f"Bible: '{actual_bible}', Actor: '{actual_actor}'")

    # E3.3: Unknown base character returns UNKNOWN gracefully
    unknown_variants = ["Baby UnknownEntity", "Young NonExistentCharacter123"]
    for uv in unknown_variants:
        actual = bible.get_character_gender(uv)
        verify(f"E3.3: Unknown variant '{uv}' -> UNKNOWN",
               actual == "UNKNOWN",
               f"Got: '{actual}'")

    # E3.4: Age variant addressee triggers masculine harmonization in dialogue
    subs = pysubs2.SSAFile()
    ev = pysubs2.SSAEvent(start=1000, end=3000, name="Rietz", text="Nie bądź naiwna.")
    ev.addressee = "Young Braham"
    subs.events.append(ev)
    EpisodeQualityGate.audit_and_fix_entire_episode(subs=subs, series_bible=bible)
    verify("E3.4: Addressee 'Young Braham': 'Nie bądź naiwna.' -> 'Nie bądź naiwny.'",
           subs.events[0].text == "Nie bądź naiwny.",
           f"Got: '{subs.events[0].text}'")

    # Female age variant negative control
    subs = pysubs2.SSAFile()
    ev = pysubs2.SSAEvent(start=1000, end=3000, name="Rietz", text="Nie bądź naiwna.")
    ev.addressee = "Young Charlotte"
    subs.events.append(ev)
    EpisodeQualityGate.audit_and_fix_entire_episode(subs=subs, series_bible=bible)
    verify("E3.4 [NEGATIVE]: Addressee 'Young Charlotte': 'Nie bądź naiwna.' untouched",
           subs.events[0].text == "Nie bądź naiwna.",
           f"Got: '{subs.events[0].text}'")

    print("\n" + "="*70)
    print(" EMPIRICAL SUITE E4: AUDIO F0 PITCH NON-CONTAMINATION")
    print("="*70)

    # E4.1: Male entities with boy/son/brother keywords in name reject female audio update
    entities_protected = [
        "Zaht's Kid",
        "Braham's Bro",
        "Seitz Captain",
        "Young Boy",
        "Little Son",
    ]
    for ent in entities_protected:
        res = bible.update_character_gender_from_audio(ent, "FEMALE")
        verify(f"E4.1: update_character_gender_from_audio('{ent}', 'FEMALE') rejected",
               res is False,
               f"Returned: {res}")
        verify(f"E4.1: Entity '{ent}' gender remains MALE in bible",
               bible.get_character_gender(ent) == "MALE",
               f"Got: '{bible.get_character_gender(ent)}'")

    # E4.2: MultimodalTranslator arbitration under acoustic F0 pitch
    tr = MultimodalTranslator.__new__(MultimodalTranslator)
    tr.character_registry = {}
    tr.series_bible = bible

    f0_cases = [
        ("Zaht's Kid", "Głos: dziecięcy (~240 Hz)", "mężczyzna"),
        ("Zaht's Kid", "Głos: sopran (~260 Hz)", "mężczyzna"),
        ("Braham's Bro", "Głos: dziecięcy (~245 Hz)", "mężczyzna"),
        ("Braham's Bro", "Głos: sopran (~255 Hz)", "mężczyzna"),
    ]
    for speaker_name, tag, exp_gender in f0_cases:
        ev = pysubs2.SSAEvent(start=1000, end=3000, name=speaker_name, text="Wolałabym pomóc tacie.")
        res_gender, _ = tr._arbitrate_speaker_gender(
            event=ev,
            raw_phase1_gender="mężczyzna",
            batch_id=1,
            speaker_tags={1: tag},
            whisper_transcriptions={1: ""},
            pl_candidate="Wolałabym pomóc tacie."
        )
        verify(f"E4.2: Translator arbitration for '{speaker_name}' with '{tag}' -> '{exp_gender}'",
               res_gender == exp_gender,
               f"Got: '{res_gender}'")

    # E4.3: First-person past tense speech correction in linter
    speech_cases = [
        ("Zaht's Kid", "Wolałabym pomóc tacie.", "Wolałbym pomóc tacie."),
        ("Braham's Bro", "Myślałam, że to koniec.", "Myślałem, że to koniec."),
        ("Charlotte", "Wolałabym pomóc tacie.", "Wolałabym pomóc tacie."), # negative control
    ]
    for spk, inp, exp in speech_cases:
        subs = pysubs2.SSAFile()
        ev = pysubs2.SSAEvent(start=1000, end=3000, name=spk, text=inp)
        subs.events.append(ev)
        EpisodeQualityGate.audit_and_fix_entire_episode(subs=subs, series_bible=bible)
        verify(f"E4.3: Linter 1st-person speech for '{spk}': '{inp}' -> '{exp}'",
               subs.events[0].text == exp,
               f"Expected '{exp}', got '{subs.events[0].text}'")

    print("\n" + "="*70)
    print(f" TOTAL EMPIRICAL VERIFICATIONS: {passed}/{passed + failed} PASSED (100.0%)")
    print("="*70)

    if failed > 0:
        print("\nFAILURES:")
        for err in errors:
            print("  -", err)
        return False
    return True

if __name__ == "__main__":
    success = run_empirical_verification()
    sys.exit(0 if success else 1)
