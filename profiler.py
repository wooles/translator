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


class CharacterRelationship(BaseModel):
    speaker: str = Field(description="Imię postaci mówiącej")
    listener: str = Field(description="Imię postaci słuchającej / adresata")
    address_form: str = Field(description="Polska forma zwrotu (np. 'pani Teshima', 'panie profesorze', 'na ty / po imieniu: Minami')")
    relationship_type: str = Field(description="Typ relacji (np. 'uczeń -> nauczycielka', 'koleżanki z klasy', 'rodzeństwo')")


class GlossaryTerm(BaseModel):
    term_en: str = Field(description="Termin w języku angielskim lub japońskim")
    translation_pl: str = Field(description="Ustalony, spójny polski odpowiednik")
    explanation: str = Field(description="Wyjaśnienie kontekstu / znaczenia w anime")


class EpisodeProfile(BaseModel):
    episode_summary: str = Field(description="Krótkie 2-3 zdaniowe streszczenie fabuły i tonu odcinka")
    setting_and_era: str = Field(default="", description="Epoka historyczna, czas i miejsce akcji (np. 'XIII wiek, Imperium Mongolskie', 'Współczesne Tokio')")
    domain_expertise: str = Field(default="", description="Specjalistyczna dziedzina wiedzy i profesjonalna terminologia branżowa (np. 'Enologia / Sommelierstwo: terminologia winiarska, szczepy, apelacje', 'Szachy / Shogi')")
    dialogue_stylization: str = Field(default="", description="Wytyczne stylizacji rejestru języka i zakazy/nakazy słownictwa dla tej epoki")
    manga_canon_source: Optional[str] = Field(default="", description="Oficjalne polskie wydawnictwo mangi (np. Waneko, J.P.Fantastica, Studio JG, Hanami), jeśli seria była wydana w Polsce")
    tone_and_genre: str = Field(description="Rejestr i ton dialogów (np. 'szlachetny epos historyczny', 'profesjonalny dramat sommeliera', 'lekkie młodzieżowe anime')")
    characters: List[CharacterRelationship] = Field(default_factory=list, description="Macierz relacji i form grzecznościowych między bohaterami")
    glossary: List[GlossaryTerm] = Field(default_factory=list, description="Słowniczek kluczowych pojęć, tytułów, nazw własnych i terminów specjalistycznych")
    key_conventions: List[str] = Field(default_factory=list, description="Kluczowe wytyczne stylistyczne dla tego konkretnego odcinka")


def format_episode_profile_for_prompt(profile: Optional[EpisodeProfile]) -> str:
    """Formatuje profil odcinka do postaci zwięzłego bloku promptu systemowego."""
    if not profile:
        return ""

    lines = ["=== SŁOWNICZEK, REALIA ŚWIATA, DZIEDZINA I MACIERZ RELACJI (PROFILER ODCINKA) ==="]
    if profile.manga_canon_source:
        lines.append(f"📖 Oficjalny polski kanon mangowy: {profile.manga_canon_source}")
    if profile.setting_and_era:
        lines.append(f"🏛️ Epoka i realia świata: {profile.setting_and_era}")
    if profile.domain_expertise:
        lines.append(f"🍷 Dziedzina specjalistyczna: {profile.domain_expertise}")
    if profile.dialogue_stylization:
        lines.append(f"📜 Stylizacja językowa i rejestr: {profile.dialogue_stylization}")
    if profile.episode_summary:
        lines.append(f"Fabuła odcinka: {profile.episode_summary}")
    if profile.tone_and_genre:
        lines.append(f"Ton dialogów: {profile.tone_and_genre}")

    if profile.characters:
        lines.append("\nRELACJE SPOŁECZNE I FORMY ZWROTU (BEZWZGLĘDNIE PRZESTRZEGAJ):")
        for rel in profile.characters:
            lines.append(f"- {rel.speaker} -> {rel.listener}: {rel.address_form} ({rel.relationship_type})")

    if profile.glossary:
        lines.append("\nUSTALONY SŁOWNICZEK POJĘĆ I TERMINOLOGII BRANŻOWEJ:")
        for g in profile.glossary:
            lines.append(f"- '{g.term_en}' = '{g.translation_pl}' ({g.explanation})")

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
        Generuje lub wczytuje z cache profil odcinka (Pre-pass).
        """
        if cache_path and os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    logger.info(f"Wczytano profil odcinka z cache: {cache_path}")
                    return EpisodeProfile.model_validate(data)
            except Exception as e:
                logger.warning(f"Błąd odczytu cache profilu ({e}), generowanie na nowo...")

        prompt = f"""Jesteś Głównym Reżyserem i Konsultantem Merytorycznym Lokalizacji Anime.
Twoim zadaniem jest wstępna analiza całego odcinka na podstawie poniższych dialogów i metadanych, aby stworzyć kompletny PROFIL ODCINKA, ustalić REALIA ŚWIATA, SPECJALISTYCZNĄ DZIEDZINĘ WIEDZY (np. winiarstwo/enologia, medycyna, muzyka klasyczna, shogi, kulinaria), OFICJALNY KANON POLSKIEGO WYDANIA MANGI (jeśli seria wyszła w Polsce) ORAZ REJESTR STYLIZACJI DIALOGÓW.

METADANE Z BAZY ANILIST:
{anime_metadata_str}

PRÓBKA KWESTII DIALOGOWYCH Z ODCINKA:
{subs_text_sample[:12000]}

ZADANIE:
1. Zidentyfikuj EPOKĘ HISTORYCZNĄ ORAZ MIEJSCE AKCJI (np. "XIII wiek, Imperium Mongolskie / dwór chanów", "Okres Edo w feudalnej Japonii", "Współczesna szkoła w Tokio", "Średniowieczny świat fantasy").
2. Zidentyfikuj NISZOWĄ DZIEDZINĘ WIEDZY / TEMATYKĘ SPECJALISTYCZNĄ (np. "Enologia i Sommelierstwo (Wino / Winiarstwo) - terminologia: szczepy, apelacje, roczniki, taniny, kupaż", "Medycyna", "Muzyka klasyczna", "Shogi").
3. OFICJALNY POLSKI KANON MANGOWY: Jeśli to anime posiada oficjalny polski przekład mangowy (np. z wydawnictw Waneko, J.P.Fantastica, Studio JG, Hanami, Kotori, Dango, Egmont), zidentyfikuj wydawnictwo w 'manga_canon_source' oraz bezwzględnie włącz do słowniczka oficjalne polskie nazwy technik, magii, krain, formacji bojowych, organizacji i rang z polskich tomików papierowych.
4. Ustal WYTYCZNE STYLIZACJI JĘZYKOWEJ dla tej epoki i dziedziny (np. dla wina: używanie fachowych polskich pojęć enologicznych, dla epoki dawnej: ZAKAZ współczesnego slangu).
5. Zidentyfikuj kluczowe postacie, ich role oraz ustal, jak powinny się do siebie zwracać po polsku (kto per 'pan/pani', kto 'Wasza Dostojność / Chanie', kto po imieniu).
6. Wyodrębnij specyficzne pojęcia epokowe, branżowe terminy specjalistyczne, tytuły dzieł, nazwy win/potraw/miejsc i ustal dla nich bezbłędne, polskie tłumaczenie.
7. Określ ton i rejestr językowy dialogów.

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
                        temperature=0.2
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
                    print("  ❌ [BŁĄD KONTA GOOGLE AI STUDIO / PŁATNOŚCI]:")
                    print("  Wyczerpały się środki przedpłacone (Prepayment Credits / Limit wydatków)!")
                    print("  Komunikat Google: 'Your prepayment credits are depleted.'")
                    print("  👉 Wejdź na https://aistudio.google.com/ i doładuj środki, aby kontynuować.")
                    print("!" * 75 + "\n")
                    raise RuntimeError("Wyczerpane środki na koncie Google AI Studio (Prepayment Credits Depleted).")

                is_unavailable = "503" in err_str or "unavailable" in err_str or "high demand" in err_str
                is_rate_limit = "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str
                
                # Jeśli po 2 próbach dany model ma 503 na serwerach Google, przełączamy na bezpośredni model równoległy z tej samej generacji
                if is_unavailable and len(candidate_models) > 1 and attempt >= 2:
                    next_idx = (current_model_idx + 1) % len(candidate_models)
                    if next_idx != current_model_idx:
                        print(f"\n[Profiler Odcinka]: Model {current_model} jest przeciążony u Google (503).")
                        print(f"  ⚡ Płynne przełączenie na bezpośredni model flagowy {candidate_models[next_idx]} (100% jakość bez czekania)...")
                        current_model_idx = next_idx
                        time.sleep(1)
                        continue

                if is_unavailable or is_rate_limit:
                    wait_sec = min(4 + attempt * 2, 20)
                    print(f"\n[Profiler Odcinka]: Chwilowe przeciążenie serwerów Google (503/429 na {current_model}).")
                    print(f"  ⏳ Utrzymuję najwyższą jakość profilu. Czekam {wait_sec}s na zwolnienie zasobów (próba #{attempt})...")
                    time.sleep(wait_sec)
                else:
                    wait_sec = min(4 + attempt * 2, 20)
                    print(f"\n[Profiler Odcinka]: Ponawianie próby #{attempt} za {wait_sec}s ({e})...")
                    time.sleep(wait_sec)
