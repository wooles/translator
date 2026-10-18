# -*- coding: utf-8 -*-
"""
Linguistic Verification & Polish Dialogue Polish/Refinement Module (Phase 2).
Eliminates translationese, mechanical calques, and refines dialogues for natural spoken Polish flow.
"""

import re
import json
from typing import List, Optional, Dict, Any, Tuple, Union
from pydantic import BaseModel, Field, ConfigDict
from google import genai
from google.genai import types
from rules import get_verifier_system_prompt, SceneDiagnosis
from client_factory import format_friendly_api_error, patch_google_genai_schema_sanitizer
from typesetting_matcher import VisualTypesettingData

patch_google_genai_schema_sanitizer()

class RefinedLine(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int = Field(description="ID kwestii dialogowej zgodne z wejściem")
    refined_pl: str = Field(description="Ostateczna, perfekcyjnie zredagowana kwestia w języku polskim, wolna od kalek")
    screen_region: Optional[str] = Field(default=None, description="Dla planszy/tytułu/napisu ekranowego: wskaż lub zachowaj wykryte na kadrze położenie japońskiego napisu: 'bottom_right' (prawy dolny róg), 'bottom_left' (lewy dolny róg), 'top_right' (prawy górny róg), 'top_left' (lewy górny róg), 'bottom_center' (dół), 'top_center' (góra), 'center' (środek) lub null dla zwykłych dialogów.")
    visual_typesetting: Optional[VisualTypesettingData] = Field(default=None, description="Zachowaj lub skoryguj obiekt pozycjonowania przestrzennego (VisualTypesettingData) dla napisów ekranowych")
    changes_made: Optional[str] = Field(default=None, description="Dokładne uzasadnienie i numer Filaru AVT dla poprawionej kwestii (np. '[Filar IV - Szyk Zdania] Usunięto kalkę'). Jeśli kwestia nie wymagała zmian, wpisz null.")

class RefinedBatchResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    scene_diagnosis: Optional[SceneDiagnosis] = Field(default=None, description="Diagnoza i weryfikacja intencji dramaturgicznych sceny")
    lines: List[RefinedLine] = Field(description="Lista zredagowanych i zweryfikowanych kwestii dialogowych")

import os
import threading

class DialogueVerifier:
    _STATUS_LOCK = threading.Lock()
    _STATUS_ACTIVE: bool = False
    _LAST_STATUS_TIME: float = 0.0

    def __init__(
        self,
        client: Optional[genai.Client] = None,
        model: str = "gemini-3.5-flash-lite",
        keep_honorifics: bool = True,
        thinking_budget: Optional[int] = None,
        lean: bool = True
    ):
        self.client = client
        if hasattr(client, "get_client") and hasattr(client, "clients"):
            self.client_pool = client
        else:
            from client_factory import MultiKeyClientPool
            timeout_sec = max(150.0, float(os.getenv("GEMINI_HTTP_TIMEOUT_SEC", "90.0")))
            self.client_pool = MultiKeyClientPool(raw_keys=os.getenv("GEMINI_API_KEY"), timeout_sec=timeout_sec)
        self.model = model
        self.keep_honorifics = keep_honorifics
        self.lean = lean
        self.system_prompt = get_verifier_system_prompt(keep_honorifics=keep_honorifics, lean=lean)
        self.current_episode_tokens: Dict[str, Any] = {"prompt": 0, "cached": 0, "output": 0, "model": self.model}
        import threading
        self.lock = threading.Lock()
        
        if thinking_budget is not None:
            self.thinking_budget = thinking_budget
        else:
            try:
                self.thinking_budget = int(os.getenv("PHASE2_THINKING_BUDGET", "6144"))
            except (ValueError, TypeError):
                self.thinking_budget = 6144

    def calculate_effective_budget(self, batch_items: List[Dict[str, Any]]) -> int:
        """
        Elastic Multi-Tier CoT Budget calculation:
        Scales thinking tokens dynamically based on the semiotic and linguistic complexity of the batch.
        - Pro: 2048 (complex) / 1536 (medium) / 1024 (simple)
        - Flash: 6144 (complex) / 3072 (medium) / 2048 (simple)
        """
        has_song = any(item.get("is_song") for item in batch_items)
        has_audio_alert = any(item.get("audio_alert") for item in batch_items)
        has_ambiguity = any(item.get("ambiguity_note") for item in batch_items)
        has_pragmatic_reg = any(item.get("pragmatic_register") for item in batch_items)
        has_condensation = any(item.get("condensation_directive") for item in batch_items)
        has_long_dialogue = any(len(item.get("en", "").split()) > 10 for item in batch_items)
        has_relation = any(item.get("relation_tag") for item in batch_items)

        # Separate adaptive CoT tiers for Pro Model ($12/1M output rate) vs Flash Model ($3.75/1M output rate)
        n_lines = len(batch_items)
        if "pro" in self.model.lower():
            # PRO MODEL DEDICATED TIERS (Level 4: High Literary Depth without token bloating)
            # Tier 1 (Pro): Piosenki OP/ED, gry słowne, zawiłe metafory, alarmy Whisper, wątpliwości Fazy 1
            if has_song or has_audio_alert or has_ambiguity:
                base = 2048
            # Tier 2 (Pro): Rejestry militarne, stylizacja feudalna, kompresja, narady, ping-pong
            elif has_pragmatic_reg or has_condensation or has_long_dialogue or has_relation:
                base = 1536
            # Tier 3 (Pro): Proste, krótkie dialogi i okrzyki bojowe (1024 tokeny CoT)
            else:
                base = 1024
            min_linear = n_lines * 90
            return max(base, min_linear)
        else:
            # FLASH MODEL TIERS (Level 3: Full Deep CoT up to 6144)
            # Tier 1: Piosenki OP/ED (Barańczak), kalambury fonetyczne, alarmy rozbieżności audio, wątpliwości F1
            if has_song or has_audio_alert or has_ambiguity:
                base = max(4096, min(self.thinking_budget, 6144))
            # Tier 2: Rejestry feudalne/dworskie, kompresja czasowa, długie narady militarne, ping-pong
            elif has_pragmatic_reg or has_condensation or has_long_dialogue or has_relation:
                base = max(2048, min(self.thinking_budget, 3072))
            # Tier 3: Standardowy, żywy dialog codzienny (2048 tokenów CoT dla pełnego audytu 156 Filarów)
            else:
                base = min(self.thinking_budget, 2048)
            min_linear = n_lines * 160
            return min(self.thinking_budget, max(base, min_linear))

    def _prepare_verification_prompt(
        self,
        batch_items: List[Dict[str, Any]],
        scene_summary: str = "",
        episode_profile_str: str = "",
        user_feedback_str: str = "",
        glossary_str: str = "",
        focused_rules_str: str = "",
        series_bible_str: str = "",
        manga_canon_str: str = "",
        history_context: Optional[List[Dict[str, Any]]] = None,
        lookahead_events: Optional[List[Tuple[int, Any, str, str]]] = None,
        character_registry: Optional[Dict[str, str]] = None,
        scene_diagnosis: Optional[Any] = None
    ) -> str:
        res = self.verify_batch(
            batch_items=batch_items,
            scene_summary=scene_summary,
            episode_profile_str=episode_profile_str,
            user_feedback_str=user_feedback_str,
            glossary_str=glossary_str,
            focused_rules_str=focused_rules_str,
            series_bible_str=series_bible_str,
            manga_canon_str=manga_canon_str,
            history_context=history_context,
            lookahead_events=lookahead_events,
            character_registry=character_registry,
            scene_diagnosis=scene_diagnosis,
            return_prompt=True
        )
        return str(res)

    def verify_batch(
        self,
        batch_items: List[Dict[str, Any]],
        scene_summary: str = "",
        episode_profile_str: str = "",
        user_feedback_str: str = "",
        glossary_str: str = "",
        focused_rules_str: str = "",
        series_bible_str: str = "",
        manga_canon_str: str = "",
        history_context: Optional[List[Dict[str, Any]]] = None,
        lookahead_events: Optional[List[Tuple[int, Any, str, str]]] = None,
        character_registry: Optional[Dict[str, str]] = None,
        scene_diagnosis: Optional[Any] = None,
        return_prompt: bool = False
    ) -> Union[List[RefinedLine], str]:
        """
        Executes editorial refinement and verification for a dialogue batch.
        batch_items contains elements:
        [{'id': int, 'en': str, 'pl': str, 'speaker_gender': str, 'notes': str}, ...]
        """
        if not batch_items:
            return [] if not return_prompt else ""

        prompt_lines = []
        prompt_lines.append("Zredaguj poniższe kwestie dialogowe. Koniecznie wyeliminuj dosłowne tłumaczenie 1 do 1, sztuczne konstrukcje i kalki.")
        prompt_lines.append("Zastąp drewniane sformułowania żywym, potoczystym językiem polskim mówionym (tak jak w profesjonalnym dubbingu / u polskich nastolatków):")
        prompt_lines.append(
            "WARSTWA 3 (GŁÓWNY MÓZG TŁUMACZENIA): Na Tobie opiera się główny ciężar przekładu. W oparciu o wszystkie potrzebne w danej chwili informacje (z nadrzędnego kanonu mangowego, profilera odcinka oraz wiedzy z Warstw 1 i 2), oddaj pełnię piękna języka polskiego.\n"
            "Twój proces myślenia ma symulować pracę polskiego tłumacza, który jest w pełni świadomy tego, co widzi i słyszy w danej chwili i jakie anime tłumaczy.\n"
            "ZASADA PRYMATU AFEKTU (DYNAMIC AFFECTIVE PRIMACY): Głos i emocjonalny afekt seiyū (drżenie, płacz, panika, szept, krzyk) ZAWSZE biją statyczny portret z Series Bible! Jeśli chłodna postać załamuje się i płacze, oddaj fizjologię rozpaczy (urwane słowa, chaos składniowy).\n"
            "WYKORZYSTAJ CZAS NA ZASTANOWIENIE (Thinking / CoT): Jako Główny Reżyser Dubbingu i Script Doctor, przed zatwierdzeniem każdej kwestii przeprowadź TRZYETAPOWY AUDYT POZNAWCZY (THE 3-STAGE EDITORIAL FUNNEL / DWUETAPOWY AUDYT POZNAWCZY KREACJI I TRIANGULACJI):\n"
            "   KROK 1: AUTONOMICZNA ŚLEPA LEKTURA I KREACJA DIALOGU (THE DUBBING & STAGE FLOW - FILAR CLXVI):\n"
            "     - KANON MANGOWY JAKO FUNDAMENT: Pojęcia z oficjalnych wydań polskich to formy syntetyczne bazowe — w zdaniu naturalnie odmieniaj je przez 7 polskich przypadków (np. 'z Demonem Krwi', 'o Czarnym Mieczniku', 'dla Oukiego').\n"
            "     - KONTRAKT POLSZCZYZNY BEZTERMINOWEJ (THE TIMELESS COLLOQUIAL CONTRACT):\n"
            "       * Twórz dialogi w estetyce polszczyzny bezterminowej: język żywy, organiczny, soczysty i miękki w ustach aktora, wolny od tymczasowych mód internetowych.\n"
            "       * Pisz tak, jak brzmią klasyki polskiego dubbingu kinowego: dialog ma brzmieć świeżo dzisiaj, naturalnie 30 lat temu i zrozumiale za 30 lat.\n"
            "       * Wprowadź wektory rzemiosła:\n"
            "         - Zasada Remy: kluczową informację i emocjonalny akcent logiczny stawiaj na końcu polskiego zdania.\n"
            "         - Reakcja na Intencję: odpowiadaj na intencję postaci (na ostrzeżenie gotowością: 'Zrozumiałem' / 'Uważam', na propozycję chęcią: 'Chętnie', na pytanie otwarte faktem).\n"
            "         - Etykieta Gestu: fizyczne podanie przedmiotu kwituj zwrotem grzecznościowym ('Proszę' / 'Trzymaj') lub elipsą.\n"
            "       * Współczesna, świeża polszczyzna bez sztucznego patosu i pretensjonalnych archaizmów (Filar CLXXII).\n"
            "       * Żywa, naturalna fraza bez pretensjonalnych zwrotów (np. 'to nie tak, że', 'mam na myśli', 'widzisz', 'tutaj, weź to').\n"
            "     - PROTOKÓŁ AUTONOMICZNEJ KREACJI (ACTIVE GENERATION FIRST - ANTY-KOTWICZENIE):\n"
            "       * Najpierw sformułuj w CoT własne, suwerenne polskie zdanie, które idealnie 'leży w ustach' polskiego aktora i pasuje do energii sceny.\n"
            "       * Dopiero potem spójrz na szkic roboczy PL z Fazy 1.\n"
            "       * Jeśli szkic z Fazy 1 powiela angielski szyk, zbędne zaimki osobowe ('ja', 'ty'), klisze lub potaknięcia ('Ta...', 'Więc...'), zdecydowanie go odrzuć na rzecz swojej autonomicznej kreacji!\n"
            "   KROK 2: MULTIMODALNA TRIANGULACJA I PRAWDA AKTORSKA (MULTIMODAL TRIANGULATION & ACTING CHECK):\n"
            "     - Skonfrontuj polszczyznę z japońskim audio seiyū i faktami ze skryptu EN (w tym wielkimi literami nazw własnych).\n"
            "     - Zbadaj ton, intonację F0 i ewentualną ironię seiyū (Filar CLVIII). Upewnij się, że nie pominięto kluczowych faktów ani liczb (Filar CLXXI).\n"
            "     - AUDYT ROZBIEŻNOŚCI PIVOTU (JP-to-EN Pivot Discrepancy Gate - Filar CLXX):\n"
            "       * Głos seiyū stanowi nadrzędny autorytet w warstwie intencji i afektu.\n"
            "       * Oddaj intencję seiyū: gdy mówi 'urusai / urusai na' (poirytowanie zrzędzeniem), zastosuj polski akt uciszania ('Ale marudzisz...', 'Daj mi spokój...', 'Nie truj...').\n"
            "       * Powitania domowe (aisatsu): po 'Wróciłem' postać wita naturalnie: 'Witaj w domu!', 'O, już jesteś?' lub 'Dobrze, że jesteś!'.\n"
            "       * Tytulatura i imiona: zachowaj poprawną odmianę i wielkie litery imion (np. 'Mistrz Tonden Minoru nie zdążył').\n"
            "     - Trzy soczewki weryfikacyjne:\n"
            "       * 👂 Ucho: oddech, CPS, dynamika ping-ponga (Filar CLIV).\n"
            "       * 🌍 Świat: relacje statusu, nienaruszalność formy Pan/Ty (Filar CLVII), perspektywa incognito (Filar CLXI).\n"
            "       * 🎬 Obraz i Audio: afekt seiyū, gesty, napisy ekranowe vs dialog.\n"
            "   KROK 3: PROAKTYWNY AUDYT NEGATYWNY REJESTRU, PŁCI I REKCJI (NEGATIVE REGISTER, GENDER & CALQUE GATE - FILAR X, CLXXXVII, CLXXXVIII):\n"
            "     - Zgodność płciowa i cytaty: Upewnij się, że końcówki 1. osoby mówczyń (-am, -ałam, -łabym) oraz formy 2. osoby do adresatek (-aś, -ałaś, jesteś pewna) i grup żeńskich (-yście, one) są w pełni poprawne. Cytaty („...”) w dialogach zachowują płeć oryginalnego autora.\n"
            "     - Ścisła rekcja zaprzeczona (Genitive of Negation): Każdy czasownik przechodni podlegający negacji w KAŻDYM czasie (teraźniejszym, przeszłym i przyszłym: nie mam/nie miałam, nie widziałem, nie czułam, nie będę miał) ściśle wymaga dopełniacza również przy wtrąceniach (nie miałem już czasu, nie widzę w tym sensu, nie czułam strachu).\n"
            "     - Prewencja mianownizacji kanonu i bariery AVT: Terminy kanoniczne odmieniaj swobodnie przez przypadki po przyimkach we wszystkich przypadkach zależnych (np. 'z Czarnym Rycerzem', 'przez Wielkiego Chana', 'o Królu Demonów'). Przestrzegaj twardych barier AVT: tempo czytania CPS <= 17 i długość wiersza CPL <= 38.\n"
            "     - Twarda eliminacja błędów fleksyjnych, literówek i kalek leksykalnych jest dodatkowo w 100% asekurowana przez deterministyczny silnik EpisodeQualityGate (0.00 PLN).\n"
            "     - W swoim myśleniu skup się na autentyczności, szlachetności i żywości dialogu w świecie przedstawionym.\n"
        )
        prompt_lines.append("W polu 'changes_made' dla KAŻDEJ poprawionej kwestii podaj DOKŁADNE uzasadnienie i numer Filaru AVT (np. '[Filar IV - Szyk Zdania] Usunięto kalkę angielską' lub '[Filar CLVII - Forma Adresatywna] Usunięto 'wygrał pan' -> 'wygrałeś''). Jeśli kwestia nie wymagała poprawek, wpisz null.")
        
        if focused_rules_str:
            prompt_lines.append(f"\n{focused_rules_str}\n")

        # Known Characters in episode for role and status continuity (Just-In-Time Scoped)
        if character_registry:
            batch_corpus = " ".join([
                (it.get("en", "") or "") + " " + (it.get("pl", "") or "") + " " + (it.get("speaker_name") or "")
                for it in batch_items
            ]).lower()
            if history_context:
                batch_corpus += " " + " ".join([(h.get("en", "") or "") + " " + (h.get("speaker") or "") for h in history_context[-3:]]).lower()
            if lookahead_events:
                batch_corpus += " " + " ".join([str(item[2] if len(item) > 2 else "") for item in lookahead_events[:2]]).lower()

            active_chars = {}
            for name, details in list(character_registry.items()):
                name_clean = name.strip()
                name_stem = name_clean[:max(3, len(name_clean) - 2)].lower()
                if len(character_registry) <= 4 or name_stem in batch_corpus:
                    active_chars[name] = details

            if active_chars:
                prompt_lines.append("--- ZNANE POSTACIE W SCENIE (spójność ról, płci i relacji władzy) ---")
                for name, details in active_chars.items():
                    prompt_lines.append(f"• {name}: {details}")
                prompt_lines.append("--------------------------------------------------------------------------\n")

        # Structured Scene Diagnosis from Phase 1 (Support both Pydantic model and dict)
        if scene_diagnosis:
            diag_dict = scene_diagnosis.dict() if hasattr(scene_diagnosis, "dict") else (scene_diagnosis if isinstance(scene_diagnosis, dict) else {})
            dram_ctx = diag_dict.get("dramatic_context") or getattr(scene_diagnosis, "dramatic_context", None)
            dial_flow = diag_dict.get("dialogue_flow") or getattr(scene_diagnosis, "dialogue_flow", None)
            aud_check = diag_dict.get("audio_intent_check") or getattr(scene_diagnosis, "audio_intent_check", None)
            dom_tone = diag_dict.get("dominant_tone") or getattr(scene_diagnosis, "dominant_tone", None)
            pow_dyn = diag_dict.get("power_dynamic") or getattr(scene_diagnosis, "power_dynamic", None)
            epis_asym = diag_dict.get("epistemic_asymmetry") or getattr(scene_diagnosis, "epistemic_asymmetry", None)
            tbl_read = diag_dict.get("table_read_mouth_feel") or getattr(scene_diagnosis, "table_read_mouth_feel", None)

            diag_lines = ["\n🎬 DIAGNOZA DRAMATURGICZNA I KOGNITYWNA SCENY:"]
            if dram_ctx and str(dram_ctx).strip():
                diag_lines.append(f"• Sytuacja i emocje: {str(dram_ctx).strip()}")
            if dial_flow and str(dial_flow).strip():
                diag_lines.append(f"• Dynamika dialogu (przyczyna-skutek): {str(dial_flow).strip()}")
            if aud_check and str(aud_check).strip():
                diag_lines.append(f"• Intencja ze słuchu (Whisper): {str(aud_check).strip()}")
            if dom_tone and str(dom_tone).strip():
                diag_lines.append(f"• Rejestr i ton: {str(dom_tone).strip()}")
            if pow_dyn and str(pow_dyn).strip():
                diag_lines.append(f"• Relacja władzy: {str(pow_dyn).strip()}")
            if epis_asym and str(epis_asym).strip():
                diag_lines.append(f"• Teoria Umysłu (asymetria wiedzy / ochrona tożsamości): {str(epis_asym).strip()}")
            if tbl_read and str(tbl_read).strip():
                diag_lines.append(f"• Próba Stolikowa (płynność w ustach aktora): {str(tbl_read).strip()}")
            if len(diag_lines) > 1:
                prompt_lines.append("\n".join(diag_lines) + "\n")
        elif scene_summary:
            prompt_lines.append(f"\n[Kontekst sceny]: {scene_summary}\n")

        # Dialogue History Context (Cross-Batch & Intra-Scene)
        if history_context:
            prompt_lines.append("--- POPRZEDNIE KWESTIE W SCENIE (kontekst przeszły / ciągłość dialogu) ---")
            for h in history_context[-4:]:
                spk_label = ""
                spk_name = (h.get("speaker") or h.get("speaker_name") or "").strip()
                spk_gen = (h.get("speaker_gender") or "").strip()
                if spk_name and spk_gen:
                    spk_label = f" (Mówca: {spk_name} | {spk_gen})"
                elif spk_name:
                    spk_label = f" (Mówca: {spk_name})"
                elif spk_gen:
                    spk_label = f" (Mówca: {spk_gen})"
                
                mode_label = " [💭 Myśl wewnętrzna]" if h.get("is_thought") else ""

                if h.get("pl"):
                    prompt_lines.append(f"[Poprzednio]{spk_label}{mode_label} EN: {h['en']} -> PL: {h['pl']}")
                else:
                    prompt_lines.append(f"[Poprzednio]{spk_label}{mode_label} EN: {h['en']}")
            prompt_lines.append("---------------------------------------------------------------------------\n")

        # Lookahead preview of upcoming dialogue
        if lookahead_events:
            prompt_lines.append("--- NADCHODZĄCE KWESTIE (kontekst przyszły / dokąd zmierza rozmowa) ---")
            for item in lookahead_events[:4]:
                fut_text = item[2] if len(item) > 2 else ""
                fut_ev = item[1] if len(item) > 1 else None
                fut_spk = f" (Mówca: {fut_ev.name})" if fut_ev and getattr(fut_ev, "name", None) else ""
                prompt_lines.append(f"[Wkrótce]{fut_spk} EN: {fut_text}")
            prompt_lines.append("--------------------------------------------------------------------------\n")

        # Static Episode Knowledge (Only appended if not already baked into Cached System Instructions)
        if not getattr(self, "_episode_knowledge_cached", False):
            if user_feedback_str:
                prompt_lines.append(f"\n{user_feedback_str}\n")
            if glossary_str:
                prompt_lines.append(f"\n{glossary_str}\n")
            if manga_canon_str:
                prompt_lines.append(f"\n{manga_canon_str}\n")
            if series_bible_str:
                prompt_lines.append(f"\n{series_bible_str}\n")
            if episode_profile_str:
                prompt_lines.append(f"\n{episode_profile_str}\n")

        for item in batch_items:
            type_tag = f" [[Napis] {item['visual_type']}]" if item.get("is_sign") else " [DIALOG]"
            semiotic_tag = f" [{item['semiotic_layer']}]" if item.get("semiotic_layer") else ""
            mode_tag = " [💭 Myśl]" if item.get("is_thought") else (" [🗣️ Mowa]" if not item.get("is_sign") else "")
            dur_s = item.get("duration_s")
            dur_info = f" (Czas: {dur_s:.1f}s)" if dur_s else ""
            speaker_name = (item.get('speaker_name') or '').strip()
            speaker_gender = (item.get('speaker_gender') or '').strip()
            if speaker_name and speaker_gender:
                char_info = f" (Postać: {speaker_name} | {speaker_gender})"
            elif speaker_name:
                char_info = f" (Postać: {speaker_name})"
            elif speaker_gender:
                char_info = f" (Mówca: {speaker_gender})"
            else:
                char_info = ""

            addressee_label = (item.get('addressee_label') or '').strip()
            if addressee_label:
                char_info = f"{char_info} -> [Adresat: {addressee_label}]"

            # Actor & Voice profile
            actor_cues = []
            if item.get('speaker_voice'):
                actor_cues.append(f"Głos: {item['speaker_voice']}")
            if item.get('prosody'):
                actor_cues.append(f"Ton: {item['prosody']}")
            if item.get('pragmatic_register'):
                actor_cues.append(f"Rejestr: {item['pragmatic_register']}")
            actor_line = f"  [Aktorstwo i Rejestr]: {', '.join(actor_cues)}\n" if actor_cues else ""

            # Multimodal audio/visual cues
            multimodal_lines = []
            if item.get("audio_jp"):
                multimodal_lines.append(f"    • JP (Audio seiyū): {item['audio_jp']}")
            if item.get('visual_subtext'):
                multimodal_lines.append(f"    • Obraz i mimika: {item['visual_subtext']}")
            if item.get('literal_meaning'):
                multimodal_lines.append(f"    • Dosłowny sens JP: {item['literal_meaning']}")
            if item.get('visual_details'):
                multimodal_lines.append(f"    • Typografia/Styl: {item['visual_details']}")
            if item.get('screen_region'):
                multimodal_lines.append(f"    • Kwadrant kadru: {item['screen_region']}")
            multimodal_block = "  [Kontekst Multimodalny]:\n" + "\n".join(multimodal_lines) + "\n" if multimodal_lines else ""

            # Directives, alarms, relational dynamics & traps
            directive_lines = []
            if item.get('time_gap_s') and item['time_gap_s'] >= 4.0:
                directive_lines.append(f"    • Oś czasu: Pauza {item['time_gap_s']:.1f}s od poprzedniej kwestii (DYSKONTINUITET CZASOWY / ZMIANA SCENY)")
            if item.get('relation_tag'):
                directive_lines.append(f"    • Dynamika: {item['relation_tag'].strip()}")
            if item.get('audio_alert'):
                directive_lines.append(f"    • Alarm audio: {item['audio_alert'].strip()}")
            if item.get('third_person_subject'):
                directive_lines.append(f"    • Płeć 3. osoby: {item['third_person_subject'].strip()}")
            if item.get('duration_s') and item['duration_s'] > 0:
                dur_s = float(item['duration_s'])
                max_pl_chars = min(76, int(max(0.5, dur_s) * 17.0))
                if max_pl_chars < 15:
                    max_pl_chars = 15
                directive_lines.append(f"    • BUDŻET ZNAKOWY AVT: Maksymalnie {max_pl_chars} znaków ze spacjami (tempo czytania 17.0 z/s, max 2 wiersze na ekranie) – NIE PRZEKRACZAJ!")
            if item.get('condensation_directive'):
                directive_lines.append(f"    • Kondensacja: {item['condensation_directive'].strip()}")
            elif item.get('cps_warning'):
                directive_lines.append(f"    • Tempo CPS: {item['cps_warning'].strip()}")
            if item.get('is_song'):
                directive_lines.append("    • PIOSENKA: Wymóg rymu i metrum sylabicznego (Filar CXVIII - Barańczak)!")
            if item.get('ambiguity_note'):
                directive_lines.append(f"    • Wątpliwość Fazy 1: {item['ambiguity_note'].strip()}")
            if item.get('addressee') == 'kobieta':
                directive_lines.append(f"    • Adresat: kobieta (2. os. lp. żeńska: -łaś, jesteś pewna - Filar CLXIII)")
            elif item.get('addressee') == 'mężczyzna':
                directive_lines.append(f"    • Adresat: mężczyzna (2. os. lp. męska: -łeś, jesteś pewien - Filar CLXIII)")
            elif item.get('addressee') == 'kobieta_dual':
                directive_lines.append(f"    • Adresat: dwie kobiety (liczba podwójna niemęskoosobowa: obie byłyście - Filar CLXIII)")
            elif item.get('addressee') == 'mężczyzna_dual':
                directive_lines.append(f"    • Adresat: dwóch mężczyzn (liczba podwójna męskoosobowa: obaj byliście - Filar CLXIII)")
            elif item.get('addressee') == 'para_mieszana_dual':
                directive_lines.append(f"    • Adresat: para mieszana (liczba podwójna męskoosobowa: oboje byliście - Filar CLXIII)")
            elif item.get('addressee') == 'grupa_kobiet':
                directive_lines.append("    • Adresat: grupa kobiet (liczba mnoga niemęskoosobowa: byłyście, zrobiłyście - Filar CLXIII)")
            elif item.get('addressee') in ['grupa_mężczyzn', 'grupa_mieszana']:
                directive_lines.append(f"    • Adresat: {'grupa mężczyzn' if item.get('addressee') == 'grupa_mężczyzn' else 'grupa mieszana'} (liczba mnoga męskoosobowa: byliście, zrobiliście - Filar CLXIII)")
            if item.get('canonical_glossary_term'):
                directive_lines.append(f"    • KANON MANGOWY (Nadrzędna baza): {item['canonical_glossary_term']} (forma syntetyczna bazowa – w dialogu odmieniaj przez przypadki!)")

            # SSOT Sanitizer: Clean notes from duplicates (remove third_person_subject and repeated alarm tags)
            raw_notes = (item.get('notes') or '').strip()
            if raw_notes:
                clean_notes = raw_notes
                if item.get('third_person_subject') and item['third_person_subject'] in clean_notes:
                    clean_notes = clean_notes.replace(item['third_person_subject'], '').strip()
                clean_notes = re.sub(r"\[(?:🎯|🚨|🎙️|⚠️)?\s*ALARM(?:\s+FILAR\s+[A-Z0-9]+|\s+[^\]]+)?\]", "", clean_notes).strip()
                clean_notes = re.sub(r"\s+", " ", clean_notes).strip()
                if clean_notes:
                    directive_lines.append(f"    • Wytyczne redakcyjne: {clean_notes}")

            directives_block = "  [TELEMETRIA: wytyczne_szlifu]:\n" + "\n".join(directive_lines) + "\n" if directive_lines else ""

            is_untranslated = item.get("is_missing_translation", False) or (
                item.get("pl", "").strip().lower() == item.get("en", "").strip().lower()
                and len(item.get("en", "").split()) >= 2
                and not item.get("is_sign")
            )
            if is_untranslated:
                pl_display = "  Szkic PL: [TELEMETRIA: brak_przekładu_faza_1: przetłumacz od zera z EN i audio JP]"
            elif item.get("is_blind_draft"):
                calque_sc = float(item.get("calque_score", 0.0) or 0.0)
                if calque_sc >= 0.65:
                    pl_display = (
                        f"  Szkic PL: [⚠️ UKRYTO: Wykryto mechaniczną kalkę angielską (Calque Score: {calque_sc:.2f}). "
                        f"WYMÓG AUTONOMICZNEJ KREACJI OD ZERA Z EN I AUDIO JP!]"
                    )
                else:
                    orig_pl = (item.get('pl') or '').strip()
                    ref_hint = f" (Szkic referencyjny: '{orig_pl}')" if orig_pl else ""
                    pl_display = (
                        f"  Szkic PL (KWESTIA KRYTYCZNA - ANTY-KOTWICZENIE): "
                        f"[⚠️ WYMÓG NIEZALEŻNEGO PRZEKŁADU! Przetłumacz autonomicznie z audio JP i dynamiki sceny, eliminując kalki i potaknięcia!{ref_hint}]"
                    )
            else:
                pl_display = f"  Szkic PL: {item['pl']}"

            prompt_lines.append(
                f"- [KWESTIA #{item['id']}]{type_tag}{semiotic_tag}{mode_tag}{char_info}{dur_info}\n"
                f"{actor_line}"
                f"{multimodal_block}"
                f"{directives_block}"
                f"  EN: {item['en']}\n"
                f"{pl_display}"
            )

        prompt_text = "\n".join(prompt_lines)
        self.last_prompt = prompt_text
        if return_prompt:
            return prompt_text

        if self.client is None and not getattr(self, "client_pool", None):
            return []

        import time
        attempt = 0

        # Determine adaptive CoT thinking budget based on batch complexity (Elastic Multi-Tier Budget)
        effective_budget = self.calculate_effective_budget(batch_items)

        while True:
            attempt += 1
            cached_name = None
            try:
                from context_cache import ContextCacheManager
                gen_config_kwargs = {
                    "response_mime_type": "application/json",
                    "response_schema": RefinedBatchResponse,
                }
                is_reasoning_capable = any(k in self.model.lower() for k in ["2.", "3.", "4.", "5.", "pro", "thinking", "reasoning"]) and "lite" not in self.model.lower()
                if is_reasoning_capable:
                    gen_config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=effective_budget)

                import concurrent.futures

                last_used_client = None
                def _single_generate():
                    nonlocal cached_name, last_used_client
                    from client_factory import global_rate_limiter
                    global_rate_limiter.acquire()
                    active_c = self.client_pool.get_client() if hasattr(self, "client_pool") and self.client_pool else self.client
                    last_used_client = active_c
                    cached_name = ContextCacheManager.get_or_create_cache(
                        client=active_c,
                        model=self.model,
                        system_instruction=self.system_prompt,
                        tag="verifier"
                    )
                    cfg_kwargs = dict(gen_config_kwargs)
                    if cached_name:
                        cfg_kwargs["cached_content"] = cached_name
                    else:
                        is_paid = ("flash" in self.model.lower() or "pro" in self.model.lower()) and "lite" not in self.model.lower()
                        if is_paid:
                            cached_name = ContextCacheManager.get_or_create_cache(
                                client=active_c,
                                model=self.model,
                                system_instruction=self.system_prompt,
                                tag="verifier"
                            )
                            if cached_name:
                                cfg_kwargs["cached_content"] = cached_name
                            else:
                                raise RuntimeError(
                                    f"KATEGORYCZNA BLOKADA FINANSOWA: Zablokowano próbę wysłania 33k tokenów bez aktywnego rabatu -90% dla {self.model}."
                                )
                        if "cached_content" not in cfg_kwargs:
                            cfg_kwargs["system_instruction"] = self.system_prompt
                    cfg = types.GenerateContentConfig(**cfg_kwargs)
                    return active_c.models.generate_content(
                        model=self.model,
                        contents=[prompt_text],
                        config=cfg
                    )

                # Direct generation using thread-safe multi-key rotation and token bucket pacing with hard 150s watchdog
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                    fut = ex.submit(_single_generate)
                    response = fut.result(timeout=150.0)

                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    um = response.usage_metadata
                    with self.lock:
                        self.current_episode_tokens["prompt"] += getattr(um, "prompt_token_count", 0) or 0
                        self.current_episode_tokens["cached"] += getattr(um, "cached_content_token_count", 0) or 0
                        cands = getattr(um, "candidates_token_count", 0) or 0
                        thoughts = getattr(um, "thoughts_token_count", 0) or 0
                        self.current_episode_tokens["output"] += (cands + thoughts)
                        self.current_episode_tokens["model"] = self.model

                # Retrieve parsed structured output
                result_lines: List[RefinedLine] = []
                if hasattr(response, "parsed") and response.parsed is not None:
                    parsed_obj: RefinedBatchResponse = response.parsed
                    result_lines = parsed_obj.lines
                else:
                    # Fallback to response.text if SDK returned raw string
                    data = json.loads(response.text)
                    batch_resp = RefinedBatchResponse.model_validate(data)
                    result_lines = batch_resp.lines

                # Zero-Drop Line Verifier Gate (0.00 PLN):
                # Verify that all line IDs from batch_items are present in result_lines.
                # If any line was omitted by the LLM, synthesize a fallback preserving the Phase 1 draft.
                returned_ids = {r.id for r in result_lines}
                missing_items = [it for it in batch_items if it.get("id") not in returned_ids]
                if missing_items:
                    for m_it in missing_items:
                        result_lines.append(RefinedLine(
                            id=m_it["id"],
                            refined_pl=m_it.get("pl", ""),
                            changes_made="Zweryfikowano (zachowano szkic Fazy 1)"
                        ))
                    result_lines.sort(key=lambda x: x.id)

                with DialogueVerifier._STATUS_LOCK:
                    if DialogueVerifier._STATUS_ACTIVE:
                        print(f"  └─ [OK / Faza 2]: Połączenie z Google API przywrócone.")
                        DialogueVerifier._STATUS_ACTIVE = False
                        DialogueVerifier._LAST_STATUS_TIME = 0.0
                return result_lines

            except Exception as e:
                err_str = str(e).lower()
                if hasattr(self, "client_pool") and self.client_pool and last_used_client:
                    self.client_pool.report_error(last_used_client, err_str)

                is_cache_err = "403" in err_str or "cachedcontent" in err_str or "permission" in err_str
                if is_cache_err and cached_name:
                    from context_cache import ContextCacheManager
                    ContextCacheManager.invalidate_cache(self.model, self.system_prompt, client=last_used_client, tag="verifier")
                    with DialogueVerifier._STATUS_LOCK:
                        print(f"\n[Context Cache]: Wykryto unieważniony cache serwerowy weryfikatora -> automatyczna regeneracja...")
                    cached_name = None
                    time.sleep(0.5)
                    continue

                is_billing_exhausted = "prepayment" in err_str or "depleted" in err_str or ("billing" in err_str and "credit" in err_str)
                if is_billing_exhausted:
                    print("\n" + "!" * 75)
                    print("  [!] [BŁĄD KONTA GOOGLE AI STUDIO / PŁATNOŚCI]:")
                    print("  Wyczerpały się środki przedpłacone (Prepayment Credits / Limit wydatków)!")
                    print("  Komunikat Google: 'Your prepayment credits are depleted.'")
                    print("  -> Wejdź na https://aistudio.google.com/ i doładuj środki, aby kontynuować.")
                    print("!" * 75 + "\n")
                    raise RuntimeError("Wyczerpane środki na koncie Google AI Studio (Prepayment Credits Depleted).")

                # Anti-Spin-Lock Circuit Breaker: Hard stop to protect quota and funds
                num_keys = len(self.client_pool.clients) if hasattr(self, "client_pool") and self.client_pool else 1
                max_allowed_attempts = max(25, num_keys * 8)
                if attempt >= max_allowed_attempts:
                    raise RuntimeError(
                        f"KATEGORYCZNA BLOKADA BEZPIECZEŃSTWA: Osiągnięto limit {attempt} prób dla partii w Fazie 2. "
                        f"Ostatni błąd: {e}. Proces wstrzymano w celu ochrony budżetu przed niekontrolowanymi zapytaniami."
                    )

                is_timeout = "504" in err_str or "deadline" in err_str or "timeout" in err_str or "timed out" in err_str
                is_unavailable = "503" in err_str or "unavailable" in err_str or "high demand" in err_str
                is_rate_limit = "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str

                import random
                import time as _time
                if is_unavailable or is_timeout:
                    cycle = attempt // max(1, num_keys)
                    wait_sec = min(4.0, 1.5 + 0.5 * min(cycle, 5) + random.uniform(0.1, 0.4))
                else:
                    if attempt % max(1, num_keys) != 0:
                        wait_sec = 0.2 + random.uniform(0.05, 0.15)
                    else:
                        cycle = attempt // max(1, num_keys)
                        wait_sec = min(3.0, 0.6 + 0.4 * min(cycle, 4) + random.uniform(0.1, 0.3))
                
                friendly_msg = format_friendly_api_error(e)
                with DialogueVerifier._STATUS_LOCK:
                    if not DialogueVerifier._STATUS_ACTIVE:
                        print(f"\n[Status / Faza 2]: {friendly_msg} -> oczekiwanie na serwery Google i automatyczna rotacja kluczy...")
                        DialogueVerifier._STATUS_ACTIVE = True

                time.sleep(wait_sec)
