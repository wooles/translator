# -*- coding: utf-8 -*-
"""
Moduł Profilowania Odcinka (Pre-pass Episode Profiler & Glossary Engine).
Przed rozpoczęciem tłumaczenia analizuje cały odcinek, mapuje relacje między postaciami
(kto do kogo mówi na 'ty', kto per 'pan/pani') oraz tworzy słowniczek specyficznych pojęć,
gwarantując idealną spójność dialogów w całym odcinku.
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

logger = logging.getLogger("profiler")


class NameDeclension(BaseModel):
    character_name: str = Field(description="Imię postaci w mianowniku (np. 'Issei', 'Tomine', 'Shizuku')")
    gender: str = Field(description="'MALE' lub 'FEMALE'")
    declension_summary: str = Field(description="Polska odmiana imienia/nazwiska przez przypadki (np. 'Issei -> D. Isseia, C. Isseiowi, B. Isseia, N. z Isseiem, Msc. o Isseiu' lub 'Shizuku -> nieodmienne (z Shizuku, o Shizuku)')")


class FirstPersonPronoun(BaseModel):
    character_name: str = Field(description="Imię postaci")
    japanese_pronoun: str = Field(description="Zaimki 1. osoby używane w dialogach: 'Ore', 'Boku', 'Watashi', 'Atashi', 'Sessha', 'Waga'")
    psychological_profile: str = Field(description="Profil psychologiczny i rejestr (np. 'Ore -> pewny siebie, szorstki, bezkompromisowy', 'Boku -> skromny, uprzejmy, chłopięcy', 'Watashi -> formalny/neutralny')")


class CharacterRelationship(BaseModel):
    speaker: str = Field(description="Imię postaci mówiącej")
    listener: str = Field(description="Imię postaci słuchającej / adresata")
    address_form: str = Field(description="Polska forma zwrotu (np. 'pani Teshima', 'panie profesorze', 'na ty / po imieniu: Minami')")
    relationship_type: str = Field(description="Typ relacji (np. 'uczeń -> nauczycielka', 'koleżanki z klasy', 'rodzeństwo')")


class GlossaryTerm(BaseModel):
    term_en: str = Field(description="Termin w języku angielskim lub japońskim")
    translation_pl: str = Field(description="Ustalony, spójny polski odpowiednik")
    explanation: str = Field(description="Wyjaśnienie kontekstu / znaczenia w anime")


class DangerLinePreScan(BaseModel):
    approx_time: str = Field(description="Przybliżony czas kwestii w odcinku (np. '00:06:12')")
    english_phrase: str = Field(description="Wieloznaczna lub zdradliwa fraza angielska (np. 'I\\'m… fine.', 'Bless you', 'That bombed')")
    speaker: Optional[str] = Field(default=None, description="Mówca kwestii")
    contextual_trap: str = Field(description="Wyjaśnienie pułapki kontekstowej / japońskiego audio (np. 'Odmowa udziału w powitaniu [boku wa ii desu], a NIE stan zdrowia/rany!')")
    mandatory_direction: str = Field(description="Ścisła dyrektywa przekładu dla tłumacza (np. 'Tłumacz jako: Ja... podziękuję / Nie mam ochoty. KATEGORYCZNY ZAKAZ: Nic mi nie jest.')")


class DramaticSequence(BaseModel):
    sequence_name: str = Field(description="Nazwa sekwencji (np. 'Sekwencja 1: Ucieczka z Kamakury', 'Sekwencja 2: Świątynia Suwa i zazdrość')")
    time_range: str = Field(description="Przedział czasowy (np. '00:00 - 05:30')")
    dramatic_summary: str = Field(description="Opis dynamiki, napięcia i relacji władzy w tej części odcinka")
    dominant_tone: str = Field(description="Dominujący rejestr i ton (np. 'panika i tempo bojowe', 'dworska etykieta i tłumiona zazdrość', 'patos rycerski')")


class CharacterDossier(BaseModel):
    name: str = Field(description="Imię postaci")
    gender: str = Field(description="'MALE', 'FEMALE' lub 'UNKNOWN'")
    age_and_role: str = Field(description="Wiek, status społeczny i rola (np. '7 lat, młody arystokrata/kapłan, syn Yorishige')")
    speech_style_pl: str = Field(description="Unikalny polski rejestr mowy (np. 'Chłodny, dumny, krótki, arystokratyczny bez poufałości')")
    first_person_pronoun: Optional[str] = Field(default=None, description="Japoński zaimek 'ja' (Ore, Boku, Watashi, Atashi) i profil ego")
    declension: Optional[str] = Field(default=None, description="Polska odmiana przez przypadki (np. 'Yoritsugu -> D. Yoritsugu, C. Yoritsugu, B. Yoritsugu')")
    idiolect_matrix: Optional[str] = Field(default="", description="Matryca idiolektu: specyficzne nawyki leksykalne, zakazane/preferowane zwroty i rytm wypowiedzi dla tej postaci")


class EpisodeProfile(BaseModel):
    episode_summary: str = Field(description="Krótkie 2-3 zdaniowe streszczenie fabuły i tonu odcinka")
    setting_and_era: str = Field(default="", description="Epoka historyczna, czas i miejsce akcji (np. 'XIII wiek, Imperium Mongolskie', 'Współczesne Tokio')")
    domain_expertise: str = Field(default="", description="Specjalistyczna dziedzina wiedzy i profesjonalna terminologia branżowa (np. 'Enologia / Sommelierstwo: terminologia winiarska, szczepy, apelacje', 'Szachy / Shogi')")
    dialogue_stylization: str = Field(default="", description="Wytyczne stylizacji rejestru języka i zakazy/nakazy słownictwa dla tej epoki")
    manga_canon_source: Optional[str] = Field(default="", description="Oficjalne polskie wydawnictwo mangi (np. Waneko, J.P.Fantastica, Studio JG, Hanami), jeśli seria była wydana w Polsce")
    tone_and_genre: str = Field(description="Gatunek i dominujący ton emocjonalny (np. 'Komediodramat młodzieżowy, ciepły z elementami absurdu')")
    danger_lines_prescan: List[DangerLinePreScan] = Field(default_factory=list, description="Lista wyłapanych przed tłumaczeniem niebezpiecznych pułapek kontekstowych i wieloznaczności w całym odcinku")
    dramatic_sequences: List[DramaticSequence] = Field(default_factory=list, description="Podział odcinka na główne akty/sekwencje dramaturgiczne")
    character_dossiers: List[CharacterDossier] = Field(default_factory=list, description="Dokładne dossier i stylizacja mowy głównych bohaterów")
    name_declensions: List[NameDeclension] = Field(default_factory=list, description="Precyzyjna odmiana imion bohaterów przez wszystkie przypadki w języku polskim")
    characters: List[CharacterRelationship] = Field(default_factory=list, description="Relacje między postaciami i ustalone polskie formy zwrotu")
    glossary: List[GlossaryTerm] = Field(default_factory=list, description="Słowniczek kluczowych terminów, nazw własnych, ataków i realiów świata")
    yojijukugo_and_idioms: List[GlossaryTerm] = Field(default_factory=list, description="Wykryte 4-znakowe idiomy (Yojijukugo), przysłowia i metafory z naturalnymi polskimi ekwiwalentami")
    key_conventions: List[str] = Field(default_factory=list, description="Kluczowe wytyczne stylistyczne dla tego konkretnego odcinka")


def format_episode_profile_for_prompt(profile: Optional[EpisodeProfile]) -> str:
    """Formatuje profil odcinka do postaci zwięzłego bloku promptu systemowego (Profiler 3.0)."""
    if not profile:
        return ""

    lines = ["=== SŁOWNICZEK, KANON MANGI, REALIA ŚWIATA I PROFIL ODCINKA (PROFILER 3.0) ==="]
    if profile.manga_canon_source:
        lines.append(f"[Oficjalny Kanon Mangi / Wydawnictwo]: {profile.manga_canon_source} (TERMINOLOGIA ZABLOKOWANA)")
    if profile.setting_and_era:
        lines.append(f"[Realia świata / Epoka]: {profile.setting_and_era}")
    if profile.domain_expertise:
        lines.append(f"[Dziedzina specjalistyczna]: {profile.domain_expertise}")
    if profile.dialogue_stylization:
        lines.append(f"[Stylizacja językowa]: {profile.dialogue_stylization}")
    if profile.episode_summary:
        lines.append(f"Fabuła odcinka: {profile.episode_summary}")
    if profile.tone_and_genre:
        lines.append(f"Ton dialogów: {profile.tone_and_genre}")

    if profile.danger_lines_prescan:
        lines.append("\n🚨 SKANER MIN JĘZYKOWYCH I PUŁAPEK WIELOZNACZNOŚCI (DANGER-LINES PRE-SCAN):")
        for dl in profile.danger_lines_prescan:
            spk = f" ({dl.speaker})" if dl.speaker else ""
            lines.append(f"• [{dl.approx_time}]{spk} '{dl.english_phrase}' -> PUŁAPKA: {dl.contextual_trap} => DYREKTYWA: {dl.mandatory_direction}")

    if profile.dramatic_sequences:
        lines.append("\n🗺️ MAPA SEKWENCJI DRAMATURGICZNYCH ODCINKA:")
        for seq in profile.dramatic_sequences:
            lines.append(f"• [{seq.time_range}] {seq.sequence_name}: {seq.dramatic_summary} (Ton: {seq.dominant_tone})")

    if profile.character_dossiers:
        lines.append("\n🎭 KARTOTEKA OBSADY I MATRYCA IDIOLEKTÓW (CHARACTER DOSSIERS & IDIOLECT MATRIX):")
        for cd in profile.character_dossiers:
            pron = f" [Zaimek: {cd.first_person_pronoun}]" if cd.first_person_pronoun else ""
            decl = f" [Odmiana: {cd.declension}]" if cd.declension else ""
            idio = f" [Idiolekt: {cd.idiolect_matrix}]" if cd.idiolect_matrix else ""
            lines.append(f"• {cd.name} ({cd.gender}, {cd.age_and_role}){pron}{decl} -> Styl: {cd.speech_style_pl}{idio}")

    if profile.name_declensions:
        lines.append("\nŻELAZNA TABELA ODMIANY IMION PRZEZ PRZYPADKI (FILAR XCI - BEZWZGLĘDNIE STOSUJ):")
        for decl in profile.name_declensions:
            lines.append(f"- {decl.character_name} ({decl.gender}): {decl.declension_summary}")

    if profile.characters:
        lines.append("\nRELACJE SPOŁECZNE I FORMY ZWROTU (BEZWZGLĘDNIE PRZESTRZEGAJ):")
        for rel in profile.characters:
            lines.append(f"- {rel.speaker} -> {rel.listener}: {rel.address_form} ({rel.relationship_type})")

    if profile.glossary:
        lines.append("\nUSTALONY SŁOWNICZEK POJĘĆ I TERMINOLOGII BRANŻOWEJ:")
        for g in profile.glossary:
            lines.append(f"- '{g.term_en}' = '{g.translation_pl}' ({g.explanation})")

    if profile.yojijukugo_and_idioms:
        lines.append("\nEKWIWALENTY JAPOŃSKICH PRZYSŁÓW I IDIOMÓW (FILAR XCV):")
        for idi in profile.yojijukugo_and_idioms:
            lines.append(f"- '{idi.term_en}' = '{idi.translation_pl}' ({idi.explanation})")

    if profile.key_conventions:
        lines.append("\nWYTYCZNE SPECYFICZNE DLA TEGO ODCINKA:")
        for conv in profile.key_conventions:
            lines.append(f"- {conv}")

    lines.append("=================================================================================\n")
    return "\n".join(lines)


class EpisodeProfiler:
    def __init__(self, client: genai.Client, model: str = "gemini-3.5-flash-lite"):
        self.client = client
        self.model = model

    def profile_episode(
        self,
        subs_text_sample: str,
        anime_metadata_str: str = "",
        cache_path: Optional[str] = None
    ) -> EpisodeProfile:
        """
        Generuje lub wczytuje z cache profil odcinka (Profiler 3.0 Pre-pass).
        """
        if cache_path and os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    logger.info(f"Wczytano profil odcinka z cache: {cache_path}")
                    return EpisodeProfile.model_validate(data)
            except Exception as e:
                logger.warning(f"Błąd odczytu cache profilu ({e}), generowanie na nowo...")

        prompt = f"""Jesteś Głównym Reżyserem, Konsultantem Merytorycznym i Script Doctorem Lokalizacji Anime (Profiler 3.0).
Twoim zadaniem jest dogłębna, wszechstronna analiza 100% skryptu całego odcinka, aby przygotować dla zespołu tłumaczy i redaktorów kompletny PROFIL ODCINKA 3.0:

1. OFICJALNY KANON POLSKIEGO WYDANIA MANGI (Filar XXIII & XCIV): Zidentyfikuj wydawnictwo (Waneko, J.P.Fantastica, Studio JG, Kotori, Hanami, Dango, Egmont) i podaj oficjalne nazwy z tomików papierowych.
2. SKANER MIN JĘZYKOWYCH I PUŁAPEK WIELOZNACZNOŚCI (danger_lines_prescan): Przeskanuj cały odcinek i wskaż zdradliwe kwestie angielskie (np. 'I\\'m fine' jako odmowa 'Ja podziękuję' zamiast 'Nic mi nie jest', 'Bless you', 'That bombed', 'Kikanaide', 'Sumimasen', 'Kanojo-tachi').
3. CHRONOLOGICZNA MAPA SEKWENCJI DRAMATURGICZNYCH (dramatic_sequences): Podziel odcinek na 3-4 akty/sekwencje czasowe z opisem napięcia i tonu.
4. KARTOTEKA OBSADY I UNIKALNE IDIOLEKTY (character_dossiers): Określ wiek, status, japońskie zaimki 'ja' (Ore/Boku/Watashi) i unikalny polski rejestr mowy każdej postaci.
5. TABELA ODMIANY IMION PRZEZ PRZYPADKI (name_declensions) & MATRYCA RELACJI I TYTULATURY (characters).
6. SŁOWNICZEK POJĘĆ BRANŻOWYCH (glossary) ORAZ JAPOŃSKICH PRZYSŁÓW/IDIOMÓW (yojijukugo_and_idioms).
7. EPOKA, REALIA ŚWIATA I DZIEDZINA SPECJALISTYCZNA.

METADANE Z BAZY ANILIST:
{anime_metadata_str}

PEŁNY SKRYPT DIALOGOWY CAŁEGO ODCINKA (100% TREŚCI):
{subs_text_sample[:100000]}

Zwróć wynik w formacie JSON zgodnym ze schematem EpisodeProfile."""

        import time
        attempt = 0

        # Pula wyłącznie dwóch absolutnie najnowszych modeli flagowych (Gemini 3.7 i 3.6 Flash)
        candidate_models = [self.model]
        if "flash" in self.model.lower():
            for m in ["gemini-3.7-flash", "gemini-3.6-flash"]:
                if m not in candidate_models:
                    candidate_models.append(m)
        elif "pro" in self.model.lower():
            for m in ["gemini-3.1-pro-preview"]:
                if m not in candidate_models:
                    candidate_models.append(m)
        # Ograniczenie do maksymalnie 2 najnowszych modeli
        candidate_models = candidate_models[:2]

        current_model_idx = 0

        while True:
            attempt += 1
            current_model = candidate_models[current_model_idx]
            try:
                response = self.client.models.generate_content(
                    model=current_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=EpisodeProfile,
                        temperature=0.2,
                        thinking_config=types.ThinkingConfig(thinking_budget=0)
                    )
                )
                profile_data = json.loads(response.text)
                profile = EpisodeProfile.model_validate(profile_data)

                if cache_path:
                    try:
                        with open(cache_path, "w", encoding="utf-8") as f:
                            json.dump(profile.model_dump(), f, ensure_ascii=False, indent=2)
                    except Exception:
                        pass

                return profile
            except Exception as e:
                err_str = str(e).lower()
                is_billing_exhausted = "prepayment" in err_str or "depleted" in err_str or ("billing" in err_str and "credit" in err_str)
                if is_billing_exhausted:
                    print("\n" + "!" * 75)
                    print("  [!] [BŁĄD KONTA GOOGLE AI STUDIO / PŁATNOŚCI]:")
                    print("  Wyczerpały się środki przedpłacone (Prepayment Credits / Limit wydatków)!")
                    print("  Komunikat Google: 'Your prepayment credits are depleted.'")
                    print("  -> Wejdź na https://aistudio.google.com/ i doładuj środki, aby kontynuować.")
                    print("!" * 75 + "\n")
                    raise RuntimeError("Wyczerpane środki na koncie Google AI Studio (Prepayment Credits Depleted).")

                is_unavailable = "503" in err_str or "unavailable" in err_str or "high demand" in err_str
                is_rate_limit = "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str
                
                # Jeśli po 2 próbach dany model ma 503 na serwerach Google, przełączamy na bezpośredni model równoległy z tej samej generacji
                if is_unavailable and len(candidate_models) > 1 and attempt >= 2:
                    next_idx = (current_model_idx + 1) % len(candidate_models)
                    if next_idx != current_model_idx:
                        print(f"\n[Profiler Odcinka]: Model {current_model} jest przeciążony u Google (503).")
                        print(f"  [>>] Płynne przełączenie na bezpośredni model flagowy {candidate_models[next_idx]} (100% jakość bez czekania)...")
                        current_model_idx = next_idx
                        time.sleep(1)
                        continue

                if is_unavailable or is_rate_limit:
                    wait_sec = min(4 + attempt * 2, 20)
                    print(f"\n[Profiler Odcinka]: Chwilowe przeciążenie serwerów Google (503/429 na {current_model}).")
                    print(f"  [..] Utrzymuję najwyższą jakość profilu. Czekam {wait_sec}s na zwolnienie zasobów (próba #{attempt})...")
                    time.sleep(wait_sec)
                else:
                    wait_sec = min(4 + attempt * 2, 20)
                    print(f"\n[Profiler Odcinka]: Ponawianie próby #{attempt} za {wait_sec}s ({e})...")
                    time.sleep(wait_sec)
