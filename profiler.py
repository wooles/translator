# -*- coding: utf-8 -*-
"""
Pre-pass Episode Profiler & Glossary Engine Module.
Analyzes the entire episode script prior to translation, mapping character relationships
(honorific vs. informal address forms) and compiling a specialized terminology glossary,
ensuring consistent dialogue continuity across the whole episode.
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from client_factory import format_friendly_api_error

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


class RelationshipPivot(BaseModel):
    approx_time: str = Field(description="Przybliżony czas zmiany w odcinku (np. '00:14:20')")
    characters_involved: str = Field(description="Postacie, których dotyczy zmiana (np. 'Shin i Kyoukai', 'Nauczyciel i Arata')")
    nature_of_shift: str = Field(description="Przyczyna i charakter zmiany relacji (np. 'Przejście ze sztywnego dystansu na poufałość po wyznaniu prawdy')")
    strict_direction_pl: str = Field(description="Ścisła dyrektywa formy zwrotu (np. 'Od tej minuty ZAKAZ formy per pani, przejście na bezpośrednie ty / po imieniu: Kyoukai')")


class CharacterCatchphrase(BaseModel):
    character_name: str = Field(description="Imię postaci")
    original_phrase: str = Field(description="Oryginalna fraza lub motyw w EN/JP (np. 'Yare yare daze', 'Dattebayo', 'Good grief')")
    canonical_pl: str = Field(description="Ustalony, kultowy i jednolity polski odpowiednik (np. 'Dajcie mi święty spokój...', 'I to jak!')")
    context_notes: str = Field(description="Zasada stosowania we wszystkich scenach odcinka")


class SongTranscreationPlan(BaseModel):
    song_type: str = Field(description="Typ utworu: 'Opening (OP)', 'Ending (ED)' lub 'Insert Song / Piosenka w tle'")
    time_range: str = Field(description="Przedział czasowy piosenki (np. '00:01:30 - 00:03:00')")
    metre_and_syllables: str = Field(description="Plan sylabiczny i metrum (np. '8 sylab w wersie (8/8/8/8), rymy parzyste AABB')")
    poetic_theme: str = Field(description="Główny motyw poetycki i rejestr emocjonalny (np. 'Młodość, tęsknota i walka z przeznaczeniem')")


class PunWordplayPlan(BaseModel):
    approx_time: str = Field(description="Przybliżony czas kalamburu (np. '00:08:45')")
    original_joke_or_pun: str = Field(description="Oryginalny żart słowny lub homofon (np. 'Dajare Kami [bóg] vs Kami [papier]')")
    polish_transcreation: str = Field(description="Autonomiczny, zabawny polski ekwiwalent fonetyczny (ZAKAZ przypisów [Przyp. tłum.]!)")


class ContinuityBridgeAlert(BaseModel):
    term_or_event: str = Field(description="Kluczowy termin, nazwa rekwizytu lub wydarzenie z przeszłości")
    canon_source_episode: str = Field(description="Źródło kanonu (np. 'Ustalenie z Odcinka 2 / Biblia Serialu')")
    continuity_directive: str = Field(description="Ścisły wymóg spójności dla tłumacza w tym odcinku")


class CharacterDossier(BaseModel):
    name: str = Field(description="Imię postaci")
    gender: str = Field(description="'MALE', 'FEMALE' lub 'UNKNOWN'")
    age_and_role: str = Field(description="Wiek, status społeczny i rola (np. '7 lat, młody arystokrata/kapłan, syn Yorishige')")
    speech_style_pl: str = Field(description="Unikalny polski rejestr mowy (np. 'Chłodny, dumny, krótki, arystokratyczny bez poufałości')")
    first_person_pronoun: Optional[str] = Field(default=None, description="Japoński zaimek 'ja' (Ore, Boku, Watashi, Atashi) i profil ego")
    declension: Optional[str] = Field(default=None, description="Polska odmiana przez przypadki (np. 'Yoritsugu -> D. Yoritsugu, C. Yoritsugu, B. Yoritsugu')")
    dialect_category: Optional[str] = Field(default="", description="Dialekt regionalny postaci jeśli występuje: 'Satsuma-ben', 'Kansai-ben', 'Kyoto-ben', 'Tohoku-ben', 'Hiroshima-ben', 'Hakata-ben', 'Nagoya-ben', 'Okinawa-ben', 'Hokkaido-ben' lub brak (Filar CXXXV)")
    idiolect_matrix: Optional[str] = Field(default="", description="Matryca idiolektu: specyficzne nawyki leksykalne, zakazane/preferowane zwroty i rytm wypowiedzi dla tej postaci")


class EpisodeProfile(BaseModel):
    episode_summary: str = Field(default="", description="Krótkie 2-3 zdaniowe streszczenie fabuły i tonu odcinka")
    setting_and_era: str = Field(default="", description="Epoka historyczna, czas i miejsce akcji (np. 'XIII wiek, Imperium Mongolskie', 'Współczesne Tokio')")
    domain_expertise: str = Field(default="", description="Specjalistyczna dziedzina wiedzy i profesjonalna terminologia branżowa (np. 'Enologia / Sommelierstwo: terminologia winiarska, szczepy, apelacje', 'Szachy / Shogi')")
    dialogue_stylization: str = Field(default="", description="Wytyczne stylizacji rejestru języka i zakazy/nakazy słownictwa dla tej epoki")
    manga_canon_source: Optional[str] = Field(default="", description="Oficjalne polskie wydawnictwo mangi (np. Waneko, J.P.Fantastica, Studio JG, Hanami), jeśli seria była wydana w Polsce")
    tone_and_genre: str = Field(default="", description="Gatunek i dominujący ton emocjonalny (np. 'Komediodramat młodzieżowy, ciepły z elementami absurdu')")
    danger_lines_prescan: List[DangerLinePreScan] = Field(default_factory=list, description="Lista wyłapanych przed tłumaczeniem niebezpiecznych pułapek kontekstowych i wieloznaczności w całym odcinku")
    relationship_pivots: List[RelationshipPivot] = Field(default_factory=list, description="Punkty zwrotne i dynamiczne zmiany w relacjach/formach zwrotu w trakcie odcinka")
    character_catchphrases: List[CharacterCatchphrase] = Field(default_factory=list, description="Zamrożone kanoniczne polskie odpowiedniki dla powracających powiedzonek postaci")
    song_transcreation_plans: List[SongTranscreationPlan] = Field(default_factory=list, description="Precyzyjny plan metryczny i rymotwórczy dla piosenek (Barańczak)")
    puns_and_wordplays: List[PunWordplayPlan] = Field(default_factory=list, description="Strategie adaptacji japońskich gier słownych (Dajare) i homofonów na autonomiczne polskie dowcipy")
    continuity_bridge_alerts: List[ContinuityBridgeAlert] = Field(default_factory=list, description="Ostrzeżenia i mosty ciągłości terminologicznej względem poprzednich odcinków")
    dramatic_sequences: List[DramaticSequence] = Field(default_factory=list, description="Podział odcinka na główne akty/sekwencje dramaturgiczne")
    character_dossiers: List[CharacterDossier] = Field(default_factory=list, description="Dokładne dossier i stylizacja mowy głównych bohaterów")
    name_declensions: List[NameDeclension] = Field(default_factory=list, description="Precyzyjna odmiana imion bohaterów przez wszystkie przypadki w języku polskim")
    characters: List[CharacterRelationship] = Field(default_factory=list, description="Relacje między postaciami i ustalone polskie formy zwrotu")
    glossary: List[GlossaryTerm] = Field(default_factory=list, description="Słowniczek kluczowych terminów, nazw własnych, ataków i realiów świata")
    yojijukugo_and_idioms: List[GlossaryTerm] = Field(default_factory=list, description="Wykryte 4-znakowe idiomy (Yojijukugo), przysłowia i metafory z naturalnymi polskimi ekwiwalentami")
    key_conventions: List[str] = Field(default_factory=list, description="Kluczowe wytyczne stylistyczne dla tego konkretnego odcinka")


def format_episode_profile_for_prompt(profile: Optional[EpisodeProfile]) -> str:
    """Formats episode profile into a concise system prompt block (Profiler 4.0)."""
    if not profile:
        return ""

    lines = ["=== SŁOWNICZEK, KANON MANGI, REALIA ŚWIATA I PROFIL ODCINKA (PROFILER 4.0) ==="]
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

    if profile.relationship_pivots:
        lines.append("\n🔄 PUNKTY ZWROTNE I ZMIANY RELACJI W TRAKCIE ODCINKA (RELATIONSHIP PIVOTS):")
        for rp in profile.relationship_pivots:
            lines.append(f"• [{rp.approx_time}] {rp.characters_involved}: {rp.nature_of_shift} => NAKAZ: {rp.strict_direction_pl}")

    if profile.character_catchphrases:
        lines.append("\n💬 ZAMROŻONE POWIEDZONKA I KWESTIE-WIZYTÓWKI (CATCHPHRASES):")
        for cp in profile.character_catchphrases:
            lines.append(f"• {cp.character_name}: '{cp.original_phrase}' = '{cp.canonical_pl}' ({cp.context_notes})")

    if profile.song_transcreation_plans:
        lines.append("\n🎵 MATRYCA RYMOTWÓRCZA DLA PIOSENEK OP/ED (FILAR CXVIII - BARAŃCZAK):")
        for song in profile.song_transcreation_plans:
            lines.append(f"• [{song.time_range}] {song.song_type}: Rytm: {song.metre_and_syllables} | Motyw: {song.poetic_theme}")

    if profile.puns_and_wordplays:
        lines.append("\n🃏 ADAPTACJA JAPOŃSKICH GIER SŁOWNYCH I KALAMBURÓW (PUNS & DAJARE):")
        for pun in profile.puns_and_wordplays:
            lines.append(f"• [{pun.approx_time}] {pun.original_joke_or_pun} => POLSKA ADAPTACJA: {pun.polish_transcreation}")

    if profile.continuity_bridge_alerts:
        lines.append("\n🌉 MOSTY CIĄGŁOŚCI MIĘDZYODCINKOWEJ (CONTINUITY ALERTS):")
        for ca in profile.continuity_bridge_alerts:
            lines.append(f"• [{ca.canon_source_episode}] {ca.term_or_event} => DYREKTYWA: {ca.continuity_directive}")

    if profile.dramatic_sequences:
        lines.append("\n🗺️ MAPA SEKWENCJI DRAMATURGICZNYCH ODCINKA:")
        for seq in profile.dramatic_sequences:
            lines.append(f"• [{seq.time_range}] {seq.sequence_name}: {seq.dramatic_summary} (Ton: {seq.dominant_tone})")

    if profile.character_dossiers:
        lines.append("\n🎭 KARTOTEKA OBSADY I MATRYCA IDIOLEKTÓW (CHARACTER DOSSIERS & IDIOLECT MATRIX):")
        for cd in profile.character_dossiers:
            pron = f" [Zaimek: {cd.first_person_pronoun}]" if cd.first_person_pronoun else ""
            decl = f" [Odmiana: {cd.declension}]" if cd.declension else ""
            dial = f" [Dialekt: {cd.dialect_category}]" if cd.dialect_category else ""
            idio = f" [Idiolekt: {cd.idiolect_matrix}]" if cd.idiolect_matrix else ""
            lines.append(f"• {cd.name} ({cd.gender}, {cd.age_and_role}){pron}{decl}{dial} -> Styl: {cd.speech_style_pl}{idio}")

    if profile.name_declensions:
        lines.append("\nŻELAZNA TABELA ODMIANY IMION PRZEZ PRZYPADKI (FILAR XCI - BEZWZGLĘDNIE STOSUJ):")
        for decl in profile.name_declensions:
            lines.append(f"- {decl.character_name} ({decl.gender}): {decl.declension_summary}")

    if profile.characters:
        lines.append("\nRELACJE SPOŁECZNE I FORMY ZWROTU (BEZWZGLĘDNIE PRZESTRZEGAJ):")
        for rel in profile.characters:
            lines.append(f"- {rel.speaker} -> {rel.listener}: {rel.address_form} ({rel.relationship_type})")

    if profile.glossary:
        lines.append("\nUSTALONY SŁOWNICZEK POJĘĆ I TERMINOLOGII BRANŻOWEJ (BAZA KANONICZNA W MIANOWNIKU):")
        for g in profile.glossary:
            lines.append(f"- '{g.term_en}' = '{g.translation_pl}' [Kontekst: {g.explanation} -> W zdaniu BEZWZGLĘDNIE ODMIENIAJ PRZEZ PRZYPADKI (np. 'w {g.translation_pl.lower()}'); wklejaj czystą polską nazwę bez dopisków w nawiasach!]")

    if profile.yojijukugo_and_idioms:
        lines.append("\nEKWIWALENTY JAPOŃSKICH PRZYSŁÓW I IDIOMÓW (FILAR XCV):")
        for idi in profile.yojijukugo_and_idioms:
            lines.append(f"- '{idi.term_en}' = '{idi.translation_pl}' [Kontekst: {idi.explanation} -> W zdaniu dopasuj gramatycznie i fleksyjnie do kontekstu; bez dopisków w nawiasach!]")

    if profile.key_conventions:
        lines.append("\nWYTYCZNE SPECYFICZNE DLA TEGO ODCINKA:")
        for conv in profile.key_conventions:
            lines.append(f"- {conv}")

    lines.append("=================================================================================\n")
    return "\n".join(lines)


class EpisodeProfiler:
    def __init__(self, client: Any, model: str = "gemini-3.5-flash-lite"):
        self.client = client
        if hasattr(client, "clients") and hasattr(client, "get_client"):
            self.client_pool = client
        else:
            from client_factory import MultiKeyClientPool
            timeout_sec = float(os.getenv("GEMINI_HTTP_TIMEOUT_SEC", "90.0"))
            self.client_pool = MultiKeyClientPool(raw_keys=os.getenv("GEMINI_API_KEY"), timeout_sec=timeout_sec)
        self.model = model

    def profile_episode(
        self,
        subs_text_sample: str,
        anime_metadata_str: str = "",
        cache_path: Optional[str] = None
    ) -> EpisodeProfile:
        """
        Generates or loads episode profile from cache (Profiler 4.0 Pre-pass).
        """
        if cache_path and os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    logger.info(f"Loaded episode profile from cache: {cache_path}")
                    return EpisodeProfile.model_validate(data)
            except Exception as e:
                logger.warning(f"Error reading profile cache ({e}), regenerating...")

        prompt = f"""Jesteś Głównym Reżyserem, Konsultantem Merytorycznym i Script Doctorem Lokalizacji Anime (Profiler 4.0).
Twoim zadaniem jest dogłębna, wszechstronna analiza 100% skryptu całego odcinka, aby przygotować dla zespołu tłumaczy i redaktorów kompletny PROFIL ODCINKA 4.0:

1. OFICJALNY KANON POLSKIEGO WYDANIA MANGI (Filar XXIII & XCIV): Zidentyfikuj wydawnictwo (Waneko, J.P.Fantastica, Studio JG, Kotori, Hanami, Dango, Egmont) i podaj oficjalne nazwy z tomików papierowych.
2. SKANER MIN JĘZYKOWYCH, PUŁAPEK ŚRODOWISKOWYCH I WIELOZNACZNOŚCI (danger_lines_prescan): Przeskanuj cały odcinek i wskaż zdradliwe kwestie angielskie (np. 'I\'m fine' jako odmowa 'Ja podziękuję' zamiast 'Nic mi nie jest', 'Bless you', 'That bombed', 'Kikanaide', 'Sumimasen', 'Kanojo-tachi') ORAZ pułapki fizyczności sceny (Filar CXXXVIII: np. 'underwater' w browarze z piwem/kadzi wina/bagnie -> ostrzeż przed słowem 'woda'; 'get down' w kosmosie -> ostrzeż przed 'padnij na ziemię').
3. PUNKTY ZWROTNE I ZMIANY RELACJI (relationship_pivots): Wskaż momenty w odcinku, w których następuje przełom i zmiana formy zwracania się do siebie (np. przejście z 'pani' na 'ty').
4. POWIEDZONKA I KWESTIE-WIZYTÓWKI (character_catchphrases): Ustal jedno, kanoniczne polskie tłumaczenie dla powtarzających się motywów/zawołań postaci.
5. MATRYCA METRYCZNA DLA PIOSENEK OP/ED (song_transcreation_plans): Rozpoznaj piosenki i ustal plan sylabiczny (np. 8 sylab) i rymy Barańczaka (AABB/ABAB).
6. KALAMBURY I GRY SŁOWNE (puns_and_wordplays): Przekształć japońskie Dajare i Goroawase na autonomiczne polskie gry słowne wg zasad Stanisława Barańczaka (bez przypisów [Przyp. tłum.]!).
7. MOSTY CIĄGŁOŚCI (continuity_bridge_alerts): Wskaż terminy i wątki wymagające żelaznej spójności z całą serią.
8. CHRONOLOGICZNA MAPA SEKWENCJI DRAMATURGICZNYCH (dramatic_sequences): Podziel odcinek na 3-4 akty/sekwencje czasowe z opisem napięcia i tonu.
9. KARTOTEKA OBSADY I IDIOLEKTY YAKUWARIGO (character_dossiers): Określ wiek, status, japońskie zaimki (Ore/Boku/Watashi/Washi/Sessha), dialekt (Kansai-ben) i unikalny polski rejestr mowy (Ojou-sama salonowy, Starzec staroświecki, Samuraj rycerski, Yankii szorstki, Kansai gawędziarski).
10. TABELA ODMIANY IMION PRZEZ PRZYPADKI (name_declensions) & MATRYCA RELACJI I TYTULATURY (characters).
11. SŁOWNICZEK POJĘĆ BRANŻOWYCH (glossary) ORAZ JAPOŃSKICH PRZYSŁÓW/IDIOMÓW (yojijukugo_and_idioms): Podawaj wyłącznie CZYSTE, DOCELOWE polskie nazwy własne i terminy bez żadnych dopisków w nawiasach.
12. EPOKA, REALIA ŚWIATA I DZIEDZINA SPECJALISTYCZNA.

METADANE Z BAZY ANILIST:
{anime_metadata_str}

PEŁNY SKRYPT DIALOGOWY CAŁEGO ODCINKA (100% TREŚCI):
{subs_text_sample[:100000]}

Zwróć wynik w formacie JSON zgodnym ze schematem EpisodeProfile."""

        import time
        attempt = 0

        while True:
            attempt += 1
            try:
                gen_config_kwargs = {
                    "response_mime_type": "application/json",
                    "response_schema": EpisodeProfile,
                    "temperature": 0.2,
                }
                if "3.7" in self.model.lower() or "3.1-pro" in self.model.lower():
                    gen_config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)

                active_client = self.client_pool.get_client() if self.client_pool else self.client
                response = active_client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(**gen_config_kwargs)
                )
                profile_data = json.loads(response.text)
                profile = EpisodeProfile.model_validate(profile_data)

                if cache_path:
                    try:
                        with open(cache_path, "w", encoding="utf-8") as f:
                            json.dump(profile.model_dump(), f, ensure_ascii=False, indent=2)
                    except Exception:
                        pass

                if attempt > 1:
                    print(f"  └─ [OK / Profiler]: Połączenie z Google API przywrócone.")
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

                import random
                # Zero-Wait Multi-Key Hopping (200ms between keys; micro-pause after full key round)
                num_keys = len(self.client_pool.clients) if hasattr(self, "client_pool") and self.client_pool and hasattr(self.client_pool, "clients") else 1
                if attempt % max(1, num_keys) != 0:
                    wait_sec = 0.2 + random.uniform(0.05, 0.15)
                else:
                    cycle = attempt // max(1, num_keys)
                    wait_sec = min(3.0, 0.6 + 0.4 * min(cycle, 4) + random.uniform(0.1, 0.3))

                is_timeout = "504" in err_str or "deadline" in err_str or "timeout" in err_str or "timed out" in err_str
                is_unavailable = "503" in err_str or "unavailable" in err_str or "high demand" in err_str
                is_rate_limit = "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str
                
                friendly_msg = format_friendly_api_error(e)
                if attempt == 1:
                    print(f"\n[Profiler Odcinka]: {friendly_msg} -> oczekiwanie na serwery Google i automatyczna rotacja kluczy...")
                time.sleep(wait_sec)
