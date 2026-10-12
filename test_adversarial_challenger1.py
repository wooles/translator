# -*- coding: utf-8 -*-
"""
Adversarial Stress Test Suite — Challenger 1 (INC-AVT-004)
Testing Requirements:
R1: Toponym Sanitization & Entity Protection (sanitize_toponymic_origin_and_companionship)
R2: Plural Addressee Guard & Pronoun Harmonization (whisper_disambiguator & avt_linter)
"""

import sys
import os
import re
import pysubs2

from series_memory import (
    SeriesBible,
    KNOWN_FANTASY_TOPONYMS,
    sanitize_toponymic_origin_and_companionship,
    sanitize_closed_idioms_and_prepositions,
)
from avt_linter import (
    EpisodeQualityGate,
    AVTLinter,
    has_2nd_person_plural_verb,
    harmonize_2nd_person_singular_to_plural_pronouns,
    PLURAL_2ND_PERSON_VERB_PAT,
    EXCLUDED_NOUNS_CIE,
)
from whisper_disambiguator import WhisperDisambiguator


def run_tests():
    passed = 0
    failed = 0
    findings = []

    def check(name, condition, details=""):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  [PASS] {name}")
        else:
            failed += 1
            print(f"  [FAIL] {name}: {details}")
            findings.append((name, details))

    print("\n========================================================")
    print(" SUITE 1: REQUIREMENT R1 — TOPONYMS & SERIES BIBLE PROTECTION")
    print("========================================================")

    bible = SeriesBible("Tensei Kizoku, Kantei Skill de Nariagaru")

    # 1.1 Known fantasy toponym constants
    check("R1.1.1: 'seitz' in KNOWN_FANTASY_TOPONYMS", "seitz" in KNOWN_FANTASY_TOPONYMS)
    check("R1.1.2: 'canarre' in KNOWN_FANTASY_TOPONYMS", "canarre" in KNOWN_FANTASY_TOPONYMS)
    check("R1.1.3: 'lamberg' in KNOWN_FANTASY_TOPONYMS", "lamberg" in KNOWN_FANTASY_TOPONYMS)

    # 1.2 Non-character entity classification in SeriesBible
    check("R1.2.1: Seitz is non-character entity", bible.is_non_character_entity("Seitz") is True)
    check("R1.2.2: Canarre is non-character entity", bible.is_non_character_entity("Canarre") is True)
    check("R1.2.3: Lamberg is non-character entity", bible.is_non_character_entity("Lamberg") is True)
    check("R1.2.4: Braham is NOT non-character entity", bible.is_non_character_entity("Braham") is False)
    check("R1.2.5: Rietz is NOT non-character entity", bible.is_non_character_entity("Rietz") is False)

    # 1.3 Baseline Instrumental Companionship Sanity
    t1 = sanitize_toponymic_origin_and_companionship("Wojna z Seitzem wybuchnie lada dzień.")
    check("R1.3.1: z Seitzem -> z Seitz", "z Seitz wybuchnie" in t1, f"Got: {t1}")

    t2 = sanitize_toponymic_origin_and_companionship("Podpiszemy pokój z Canarrem.")
    check("R1.3.2: z Canarrem -> z Canarre", "z Canarre" in t2, f"Got: {t2}")

    t3 = sanitize_toponymic_origin_and_companionship("Sojusz z Lambergem trwa.")
    check("R1.3.3: z Lambergem -> z Lamberg", "z Lamberg trwa" in t3, f"Got: {t3}")

    t4 = sanitize_toponymic_origin_and_companionship("Czy ci ze Seitzu są gotowi?")
    check("R1.3.4: ci ze Seitzu -> ci z Seitz", "ci z Seitz" in t4, f"Got: {t4}")

    # 1.4 Adversarial ASS Tags & Line Breaks on Toponyms
    t_ass_prefix = sanitize_toponymic_origin_and_companionship(r"{\an8}Z Seitzem nie ma żartów.")
    check("R1.4.1: ASS prefix {\\an8}Z Seitzem -> {\\an8}Z Seitz", r"{\an8}Z Seitz" in t_ass_prefix, f"Got: {t_ass_prefix}")

    t_nl_z_seitz = sanitize_toponymic_origin_and_companionship(r"Uważaj!\Nz Seitzem nie ma żartów.")
    check("R1.4.2: Newline \\Nz Seitzem -> \\Nz Seitz", r"\Nz Seitz" in t_nl_z_seitz, f"Got: {t_nl_z_seitz}")

    t_nl_Z_seitz = sanitize_toponymic_origin_and_companionship(r"Uważaj!\NZ Seitzem nie ma żartów.")
    check("R1.4.3: Newline \\NZ Seitzem -> \\NZ Seitz", r"\NZ Seitz" in t_nl_Z_seitz, f"Got: {t_nl_Z_seitz}")

    t_nl_z_canarre = sanitize_toponymic_origin_and_companionship(r"Uważaj!\Nz Canarrem nie wygramy.")
    check("R1.4.4: Newline \\Nz Canarrem -> \\Nz Canarre", r"\Nz Canarre" in t_nl_z_canarre, f"Got: {t_nl_z_canarre}")

    t_nl_z_lamberg = sanitize_toponymic_origin_and_companionship(r"Uważaj!\Nz Lambergem nie ma sojuszu.")
    check("R1.4.5: Newline \\Nz Lambergem -> \\Nz Lamberg", r"\Nz Lamberg" in t_nl_z_lamberg, f"Got: {t_nl_z_lamberg}")

    t_nl_ci_seitz = sanitize_toponymic_origin_and_companionship(r"Co tam?\Nci ze Seitzu nie mają szans.")
    check("R1.4.6: Newline \\Nci ze Seitzu -> \\Nci z Seitz", r"\Nci z Seitz" in t_nl_ci_seitz, f"Got: {t_nl_ci_seitz}")

    t_nl_between_ci_ze = sanitize_toponymic_origin_and_companionship(r"Czy ci\Nze Seitzu są gotowi?")
    check("R1.4.7: Newline ci\\Nze Seitzu -> ci\\Nz Seitz", r"ci\Nz Seitz" in t_nl_between_ci_ze, f"Got: {t_nl_between_ci_ze}")

    t_nl_between_z_name = sanitize_toponymic_origin_and_companionship(r"Wojna z\NSeitzem wybuchnie.")
    check("R1.4.8: Newline z\\NSeitzem -> z\\NSeitz", r"z\NSeitz" in t_nl_between_z_name, f"Got: {t_nl_between_z_name}")

    t_ze_seitz = sanitize_toponymic_origin_and_companionship("Wojna ze Seitzem wybuchnie lada dzień.")
    check("R1.4.9: ze Seitzem without 'ci' -> z Seitz", "z Seitz" in t_ze_seitz, f"Got: {t_ze_seitz}")

    t_ze_canarre = sanitize_toponymic_origin_and_companionship("Pokój ze Canarrem to błąd.")
    check("R1.4.10: ze Canarrem without 'ci' -> z Canarre", "z Canarre" in t_ze_canarre, f"Got: {t_ze_canarre}")

    t_ze_lamberg = sanitize_toponymic_origin_and_companionship("Sojusz ze Lambergem trwa.")
    check("R1.4.11: ze Lambergem without 'ci' -> z Lamberg", "z Lamberg" in t_ze_lamberg, f"Got: {t_ze_lamberg}")

    t_ass_inline = sanitize_toponymic_origin_and_companionship(r"Walczymy z {\i1}Seitzem{\i0}.")
    check("R1.4.12: Inline ASS tag z {\\i1}Seitzem{\\i0} -> z {\\i1}Seitz{\\i0}", r"z {\i1}Seitz{\i0}" in t_ass_inline, f"Got: {t_ass_inline}")

    # 1.5 Negative Controls on Real People (Instrumental Companionship Invariance)
    real_people = [
        ("Brahamem", "Rozmawiałem z Brahamem wczoraj."),
        ("Klenem", "Rozmawiałem z Klenem wczoraj."),
        ("Rietzem", "Spotkałem się z Rietzem na placu."),
        ("Arsem", "Przyszedłem z Arsem do zamku."),
        ("Ravenem", "Wyruszyłem z Ravenem na polowanie."),
        ("Jeanem", "Walczyłem z Jeanem ramię w ramię."),
        ("Meną", "Rozmawiałem z Meną o sprawach domowych."),
        ("Charlotte", "Wyszedłem z Charlotte do ogrodu."),
    ]
    for p_name, p_text in real_people:
        res_p = sanitize_toponymic_origin_and_companionship(p_text)
        check(f"R1.5: Real person '{p_name}' untouched in companionship", res_p == p_text, f"Mutated: {p_text} -> {res_p}")

    print("\n========================================================")
    print(" SUITE 2: REQUIREMENT R2 — PLURAL ADDRESSEE GUARD & VERBS")
    print("========================================================")

    # 2.1 WhisperDisambiguator markers
    w_pl1 = WhisperDisambiguator.disambiguate_line(clean_en="", jp_audio="temee-ra nani shiteru")
    check("R2.1.1: WhisperDisambiguator temee-ra -> PLURAL", w_pl1.addressee_is_group is True)

    w_pl2 = WhisperDisambiguator.disambiguate_line(clean_en="", jp_audio="anta-tachi hayaku")
    check("R2.1.2: WhisperDisambiguator anta-tachi -> PLURAL", w_pl2.addressee_is_group is True)

    w_pl3 = WhisperDisambiguator.disambiguate_line(clean_en="Soldiers, prepare yourselves!", jp_audio="")
    check("R2.1.3: WhisperDisambiguator 'Soldiers' -> PLURAL", w_pl3.addressee_is_group is True)

    w_pl4 = WhisperDisambiguator.disambiguate_line(clean_en="You guys are awesome", jp_audio="")
    check("R2.1.4: WhisperDisambiguator 'You guys' -> PLURAL", w_pl4.addressee_is_group is True)

    # 2.2 Verbs mandated by prompt
    check("R2.2.1: 'Tęsknicie' detected as 2nd person plural verb", has_2nd_person_plural_verb("Tęsknicie za mamusiami?!") is True)
    check("R2.2.2: 'Poddajcie się' detected as 2nd person plural verb", has_2nd_person_plural_verb("Poddajcie się!") is True)
    check("R2.2.3: 'Słuchajcie' detected as 2nd person plural verb", has_2nd_person_plural_verb("Słuchajcie uważnie!") is True)

    # 2.3 Extended imperative verbs coverage
    extended_imperatives = [
        ("Walczcie", "Walczcie dzielnie!"),
        ("Przestańcie", "Przestańcie natychmiast!"),
        ("Pomóżcie", "Pomóżcie mi!"),
        ("Zgińcie", "Zgińcie, przeklęci!"),
        ("Stańcie", "Stańcie w szeregu!"),
        ("Pokażcie", "Pokażcie mi drogę!"),
        ("Otwórzcie", "Otwórzcie bramę!"),
        ("Bierzcie", "Bierzcie, co chcecie!"),
        ("Prowadźcie", "Prowadźcie nas!"),
        ("Wyjdźcie", "Wyjdźcie stąd!"),
        ("Zostańcie", "Zostańcie ze mną!"),
        ("Milczcie", "Milczcie obaj!"),
        ("Brońcie", "Brońcie murów!"),
    ]
    for v_name, v_text in extended_imperatives:
        is_det = has_2nd_person_plural_verb(v_text)
        check(f"R2.3: Imperative '{v_name}' detected", is_det is True, f"Failed to detect: {v_text}")

    # 2.4 Pronoun Harmonization under Plural Addressee
    pronoun_tests = [
        ("do ciebie -> do was (Tęsknicie)", r"Mam do ciebie pytanie!\NTęsknicie za mamusiami?!", r"Mam do was pytanie!\NTęsknicie za mamusiami?!"),
        ("dla ciebie -> dla was (Poddajcie)", "Poddajcie się! Mam dla ciebie propozycję!", "Poddajcie się! Mam dla was propozycję!"),
        ("do ciebie -> do was (Słuchajcie)", "Słuchajcie uważnie! Mówię do ciebie!", "Słuchajcie uważnie! Mówię do was!"),
        ("od ciebie -> od was", "Słuchajcie, wymagam tego od ciebie!", "Słuchajcie, wymagam tego od was!"),
        ("na ciebie -> na was", "Poddajcie się, czekamy na ciebie!", "Poddajcie się, czekamy na was!"),
        ("przez ciebie -> przez was", "Słuchajcie, to wszystko przez ciebie!", "Słuchajcie, to wszystko przez was!"),
        ("o tobie -> o was", "Tęsknicie? Myślimy o tobie!", "Tęsknicie? Myślimy o was!"),
        ("u ciebie -> u was", "Zróbcie porządek, jak u ciebie!", "Zróbcie porządek, jak u was!"),
        ("dzięki tobie -> dzięki wam", "Słuchajcie, dzięki tobie wygramy!", "Słuchajcie, dzięki wam wygramy!"),
        ("z tobą -> z wami", "Słuchajcie, nie idę z tobą!", "Słuchajcie, nie idę z wami!"),
        ("ze tobą -> z wami", "Poddajcie się, nie wygram ze tobą!", "Poddajcie się, nie wygram z wami!"),
        ("Cię -> Was (standalone)", "Widzicie to? Szukałem Cię wszędzie!", "Widzicie to? Szukałem Was wszędzie!"),
        ("cię -> was (standalone)", "Widzicie to? Szukałem cię wszędzie!", "Widzicie to? Szukałem was wszędzie!"),
        ("Tobie -> Wam (standalone)", "Tęsknicie? Tobie to zawdzięczamy!", "Tęsknicie? Wam to zawdzięczamy!"),
        ("tobie -> wam (standalone)", "Tęsknicie? Mówiłem tobie o tym!", "Tęsknicie? Mówiłem wam o tym!"),
        ("Ciebie -> Was (standalone)", "Słuchajcie, Ciebie ostrzegam!", "Słuchajcie, Was ostrzegam!"),
        ("ciebie -> was (standalone)", "Słuchajcie, ciebie ostrzegam!", "Słuchajcie, was ostrzegam!"),
        ("Tobą -> Wami (standalone)", "Słuchajcie, Tobą gardzę!", "Słuchajcie, Wami gardzę!"),
        ("tobą -> wami (standalone)", "Słuchajcie, tobą gardzę!", "Słuchajcie, wami gardzę!"),
    ]
    for p_label, p_in, p_exp in pronoun_tests:
        p_out, p_fixes = AVTLinter.lint_and_fix_line(p_in)
        check(f"R2.4: Pronoun harmonization: {p_label}", p_out == p_exp, f"Expected: {p_exp} | Got: {p_out}")

    # 2.5 Pronoun Harmonization under missing imperative verbs
    check("R2.5.1: Harmonization with 'Pomóżcie'",
          AVTLinter.lint_and_fix_line("Pomóżcie mi! Mam do ciebie prośbę!")[0] == "Pomóżcie mi! Mam do was prośbę!",
          f"Got: {AVTLinter.lint_and_fix_line('Pomóżcie mi! Mam do ciebie prośbę!')[0]}")

    check("R2.5.2: Harmonization with 'Walczcie'",
          AVTLinter.lint_and_fix_line("Walczcie dzielnie! Wierzę w ciebie!")[0] == "Walczcie dzielnie! Wierzę w was!",
          f"Got: {AVTLinter.lint_and_fix_line('Walczcie dzielnie! Wierzę w ciebie!')[0]}")

    print("\n========================================================")
    print(r" SUITE 3: EDGE CASES, ASS TAGS & LINE BREAKS (\N)")
    print("========================================================")

    # 3.1 Line breaks in plural pronoun constructions
    nl_cases = [
        ("Newline between do and ciebie", r"Mam do\Nciebie pytanie!\NTęsknicie?", r"Mam do\Nwas pytanie!\NTęsknicie?"),
        ("Newline between dla and ciebie", r"Mam dla\Nciebie propozycję!\NSłuchajcie!", r"Mam dla\Nwas propozycję!\NSłuchajcie!"),
        ("Newline between z and tobą", r"Rozmawiam z\Ntobą!\NPoddajcie się!", r"Rozmawiam z\Nwami!\NPoddajcie się!"),
        ("Newline before standalone ciebie", r"Słuchajcie!\Nciebie nie pytam!", r"Słuchajcie!\Nwas nie pytam!"),
        ("Newline before preposition do ciebie", r"Tęsknicie?\Ndo ciebie mówię!", r"Tęsknicie?\Ndo was mówię!"),
        ("Double newline before preposition", r"Słuchajcie!\N\NMam do ciebie pytanie!", r"Słuchajcie!\N\NMam do was pytanie!"),
        ("Multiple newlines in sentence", r"Mam\Ndo\Nciebie\Npytanie!\NTęsknicie?", r"Mam\Ndo\Nwas\Npytanie!\NTęsknicie?"),
    ]
    for nl_label, nl_in, nl_exp in nl_cases:
        nl_out, _ = AVTLinter.lint_and_fix_line(nl_in)
        check(f"R3.1: {nl_label}", nl_out == nl_exp, f"Expected: {nl_exp} | Got: {nl_out}")

    # 3.2 ASS Tags in plural pronoun constructions
    ass_cases = [
        ("ASS tag prefix {\\an8}", r"{\an8}Mam do ciebie pytanie!\NTęsknicie?", r"{\an8}Mam do was pytanie!\NTęsknicie?"),
        ("Inline ASS tag around preposition", r"Mam {\i1}do ciebie{\i0} pytanie!\NTęsknicie?", r"Mam {\i1}do was{\i0} pytanie!\NTęsknicie?"),
        ("Inline ASS tag inside preposition", r"Mam do {\i1}ciebie{\i0} pytanie!\NTęsknicie?", r"Mam do {\i1}was{\i0} pytanie!\NTęsknicie?"),
        ("ASS tag around plural verb", r"Mam do ciebie pytanie!\N{\b1}Tęsknicie?{\b0}", r"Mam do was pytanie!\N{\b1}Tęsknicie?{\b0}"),
        ("Complex position tag {\\pos(100,200)}", r"{\pos(100,200)}Poddajcie się!{\r} Mam dla ciebie propozycję!", r"{\pos(100,200)}Poddajcie się!{\r} Mam dla was propozycję!"),
    ]
    for ass_label, ass_in, ass_exp in ass_cases:
        ass_out, _ = AVTLinter.lint_and_fix_line(ass_in)
        check(f"R3.2: {ass_label}", ass_out == ass_exp, f"Expected: {ass_exp} | Got: {ass_out}")

    print("\n========================================================")
    print(" SUITE 4: NEGATIVE CONTROLS (DEMONSTRATIVE 'CI' & NOUNS ON -CIE)")
    print("========================================================")

    # 4.1 Demonstrative pronoun 'ci' must NEVER be mutated to 'wam'
    ci_cases = [
        ("ci rycerze", "Słuchajcie, ci rycerze nadchodzą!"),
        ("ci z Seitz", "Co zrobicie, gdy ci z Seitz zaatakują?"),
        ("ci ludzie", "Widzicie? Ci ludzie wam pomogą!"),
        ("ci z Canarre", "Słuchajcie, ci z Canarre uciekają!"),
        ("ci strażnicy", "Poddajcie się, ci strażnicy was otoczyli!"),
        ("ci dwaj", "Ci dwaj, powiedzcie mi prawdę!"),
        ("ci z Lamberg", "Mówię wam, ci z Lamberg nie mają szans, więc zróbcie to!"),
    ]
    for ci_label, ci_text in ci_cases:
        ci_res, _ = AVTLinter.lint_and_fix_line(ci_text)
        check(f"R4.1: Demonstrative '{ci_label}' untouched (no 'wam')",
              "wam rycerze" not in ci_res and "wam z Seitz" not in ci_res and "wam ludzie" not in ci_res and "wam strażnicy" not in ci_res and "wam dwaj" not in ci_res and "wam z Canarre" not in ci_res and "wam z Lamberg" not in ci_res,
              f"Mutated to wam: {ci_res}")
        check(f"R4.1: Line completely invariant: '{ci_label}'", ci_res == ci_text, f"Mutated: {ci_text} -> {ci_res}")

    # 4.2 Nouns ending in '-cie' must NOT cause false plural transition
    nouns_on_cie = [
        ("życie", "Mam do ciebie prośbę o życie."),
        ("mieście", "W tym mieście mam do ciebie pytanie."),
        ("świecie", "Na całym świecie szukałem ciebie."),
        ("błocie", "W tym błocie czekam na ciebie."),
        ("złocie", "W tym złocie widzę ciebie."),
        ("bracie", "Mój bracie, mam do ciebie prośbę."),
        ("powiecie (locative)", "W całym powiecie mówią o tobie."),
        ("powrocie", "Po powrocie porozmawiam z tobą."),
        ("namiocie", "W namiocie czekam na ciebie."),
        ("picie", "Mam dla ciebie picie."),
        ("okrycie", "Mam dla ciebie okrycie."),
        ("przeżycie", "To było dla ciebie ciężkie przeżycie."),
        ("kwiecie", "W tym kwiecie widzę ciebie."),
        ("locie", "W locie spojrzałem na ciebie."),
        ("aucie", "W aucie mam coś dla ciebie."),
        ("kocie", "O tym kocie mówiłem tobie."),
        ("pocie", "W pocie czoła pracowałem dla ciebie."),
        ("bicie", "To bicie serca jest dla ciebie."),
        ("mycie", "Mam dla ciebie wodę na mycie."),
        ("odkrycie", "To wielkie odkrycie dla ciebie."),
        ("obrocie", "W tym obrocie spraw liczę na ciebie."),
        ("płocie", "Na tym płocie powiesiłem list do ciebie."),
    ]
    for n_label, n_text in nouns_on_cie:
        n_verb = has_2nd_person_plural_verb(n_text)
        check(f"R4.2: Noun '{n_label}' not falsely detected as plural verb", n_verb is False, f"Falsely detected as verb: {n_text}")
        n_out, _ = AVTLinter.lint_and_fix_line(n_text)
        check(f"R4.2: Sentence with noun '{n_label}' preserved (no false pluralization)", n_out == n_text, f"Mutated: {n_text} -> {n_out}")

    # 4.3 Legitimate verb 'powiecie' check
    verb_powiecie = "Co mi na to powiecie?"
    check("R4.3: Legitimate verb 'powiecie' recognized as plural verb",
          has_2nd_person_plural_verb(verb_powiecie) is True,
          f"Failed: {verb_powiecie} was falsely excluded")

    print("\n========================================================")
    print(f" TOTAL TESTS RUN: {passed + failed}")
    print(f" PASSED: {passed}")
    print(f" FAILED: {failed}")
    print("========================================================")

    if findings:
        print("\nSUMMARY OF EMPIRICAL FAILURES:")
        for name, details in findings:
            print(f"  * {name}: {details}")

    return passed, failed, findings


if __name__ == "__main__":
    p, f, errs = run_tests()
    sys.exit(0 if f == 0 else 1)
