"""
Whisper Deterministic Disambiguator (WDD) — Bezkosztowe (0.00 PLN) Rozstrzyganie Niejednoznaczności Angielskiego Pivotu.
Automatycznie wydobywa twarde cechy z japońskiego audio seiyū (Whisper) i skryptu EN:
- K1: Płeć i bliskość adresata 2. osoby ('you')
- K2: Liczba gramatyczna adresata 2. osoby ('you' -> lp. vs lm.)
- K3: Płeć autoreferencyjna mówcy 1. osoby ('I / me / my')
- K4: Hierarchia pokrewieństwa i role społeczne (starszy/młodszy brat/siostra, szef yakuzy/armii)
- K5: Wektory przysługi i beneficjent działań (kureru vs ageru vs morau)
- K6: Odwrócona biegunowość pytań negatywnych (Echo Agreement: Hai/Un po pytaniu z przeczeniem -> 'Nie / Zgadza się')
- K7: Rejestr społeczny i dystans T-V (Keigo vs Kudaketa -> Pan/Pani vs per Ty)
- K8: Trójstopniowa deiksa przestrzenna (Ko-So-A-Do: kore vs sore vs are)

Moduł ten odciąża modele Gemini (AGENTS.md §0), eliminując wielolinijkowe mikro-zakazy w promptach
na rzecz ultrazwięzłej metadanej SSOT oraz zapewniając deterministyczny bezpiecznik w EpisodeQualityGate (0.00 PLN).
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple
import re


@dataclass
class DisambiguationTag:
    speaker_gender: Optional[str] = None       # "MALE" | "FEMALE"
    addressee_gender: Optional[str] = None     # "MALE" | "FEMALE" | "MIXED"
    addressee_number: Optional[str] = None     # "SINGULAR" | "PLURAL"
    social_register: Optional[str] = None      # "INFORMAL_TY" | "FORMAL_PAN"
    polar_response: Optional[str] = None       # "NEGATIVE_CONFIRM" (Hai/Un po pytaniu negatywnym -> 'Nie')
    kinship_role: Optional[str] = None         # "STARSZY_BRAT" | "MLODSZY_BRAT" | "STARSZA_SIOSTRA" | "MLODSZA_SIOSTRA" | "SZEF"
    benefactive: Optional[str] = None          # "FOR_ME" | "FOR_THEM"
    spatial_deictic: Optional[str] = None      # "to tutaj (blisko mówcy)" | "to tam (blisko rozmówcy)" | "tamto (daleko)"
    is_phantom_audio: bool = False             # no_speech_prob > 0.85
    low_acoustic_confidence: bool = False     # avg_logprob < -1.0
    is_hallucination_loop: bool = False       # compression_ratio > 2.4 or repetitive n-gram
    detected_markers: Optional[List[str]] = None

    @property
    def kinship_term(self) -> Optional[str]:
        if not self.kinship_role:
            return None
        mapping = {
            "STARSZY_BRAT": "starszy brat",
            "STARSZY_BRAT_LUB_SZEF": "starszy brat",
            "MLODSZY_BRAT": "młodszy brat",
            "STARSZA_SIOSTRA": "starsza siostra",
            "MLODSZA_SIOSTRA": "młodsza siostra",
        }
        return mapping.get(self.kinship_role, self.kinship_role)

    @property
    def benefactive_direction(self) -> Optional[str]:
        if self.benefactive == "FOR_ME":
            return "dla mnie / mnie"
        elif self.benefactive == "FOR_THEM":
            return "dla niego / kogoś"
        return self.benefactive

    @property
    def polar_agreement(self) -> bool:
        return self.polar_response == "NEGATIVE_CONFIRM"

    @property
    def honorific_register(self) -> Optional[str]:
        if self.social_register == "FORMAL_PAN":
            return "Pan/Pani/Uprzejmy"
        elif self.social_register == "INFORMAL_TY":
            return "Ty/Swobodny"
        return self.social_register

    def is_empty(self) -> bool:
        return not any([
            self.speaker_gender, self.addressee_gender, self.addressee_number,
            self.social_register, self.polar_response, self.kinship_role,
            self.benefactive, self.spatial_deictic
        ])


class WhisperDisambiguator:
    """
    Wysokowydajny silnik analizy leksykalno-akustycznej Whisper (0.00 PLN).
    Mapuje wykładniki języka japońskiego na jednoznaczne dyskryminatory fleksyjno-semantyczne.
    """

    # --- K1: Zaimki 2. osoby (Adresat) ---
    MASC_INFORMAL_2ND_PERSON = [
        "omae", "お前", "temee", "手前", "kisama", "貴様", "anta", "あんた"
    ]
    EQUAL_JUNIOR_2ND_PERSON = ["kimi", "君"]
    FEMALE_HONORIFIC_VOCATIVES = ["-chan", "chan", "ちゃん"]
    MALE_HONORIFIC_VOCATIVES = ["-kun", "kun", "君"]

    # --- K2: Liczba mnoga adresata (Plural markers) ---
    PLURAL_MARKERS = [
        "tachi", "たち", "達", "omae-ra", "お前ら", "kisama-ra", "貴様ら",
        "minna", "みんな", "皆", "shokun", "諸君", "zen'in", "全員",
        "mina-sama", "皆様", "domo", "ども", "共"
    ]

    # --- K3: Zaimki 1. osoby (Mówca) & Cząstki płciowe ---
    MALE_1ST_PERSON = [
        "ore", "俺", "boku", "僕", "oira", "おいら", "washi", "わし",
        "sessha", "拙者", "ware", "我", "wagahai", "吾輩", "jibun", "自分"
    ]
    FEMALE_1ST_PERSON = [
        "atashi", "あたし", "atai", "あたい", "atakushi",
        "warawa", "妾", "uchi", "うち"
    ]
    FEMALE_SENTENCE_PARTICLES = [
        "kashira", "かしら", "wa yo", "わよ", "none", "のね",
        "no yo", "のよ", "te yo", "てよ", "koto", "こと"
    ]
    MALE_SENTENCE_PARTICLES = [
        "da zo", "だぞ", "da ze", "だぜ", "zo", "ぜ", "ぞ", "kai", "かい"
    ]

    # --- K4: Pokrewieństwo i hierarchia wieku ---
    OLDER_BROTHER_MARKERS = ["onii-san", "onii-chan", "nii-san", "nii-chan", "aniki", "aniue", "兄", "兄貴", "兄上"]
    YOUNGER_BROTHER_MARKERS = ["otouto", "弟"]
    OLDER_SISTER_MARKERS = ["onee-san", "onee-chan", "nee-san", "nee-chan", "aneue", "姉", "姉貴", "姉上"]
    YOUNGER_SISTER_MARKERS = ["imouto", "妹"]

    # --- K5: Wektory przysługi (Benefactives) ---
    BENEFACTIVE_FOR_ME = ["kureru", "kureta", "kure", "kudasaru", "kudasatta", "kudasai", "くれる", "くれた", "くださる", "ください"]
    BENEFACTIVE_FOR_THEM = ["ageru", "ageta", "yaru", "yatta", "あげる", "あげた", "やる", "やった"]

    # --- K6: Odpowiedzi na pytania negatywne ---
    AFFIRMATIVE_JP_TOKENS = ["hai", "はい", "ee", "ええ", "un", "うん", "sou da", "そうだ", "sou desu", "そうです"]

    # --- K7: Rejestr społeczny T-V ---
    KEIGO_FORMAL_MARKERS = [
        "desu", "masu", "mashita", "masen", "gozaimasu", "gozaimashita",
        "irasshai", "zonjimasu", "itashimasu", "o-kudasai", "kudasaimase",
        "です", "ます", "ました", "ません", "ございます", "いらっしゃる", "存じます"
    ]
    KUDAKETA_INFORMAL_MARKERS = [
        "da yo", "da na", "daro", "darou", "kure", "shiro", "koiyo", "janai",
        "だよ", "だな", "だろう", "くれ", "しろ", "じゃない"
    ]

    # --- K8: Deiksa przestrzenna ---
    DEICTIC_KO = ["kore", "kono", "koko", "kotchi", "これ", "この", "ここ", "こっち"]
    DEICTIC_SO = ["sore", "sono", "soko", "sotchi", "それ", "その", "そこ", "そっち"]
    DEICTIC_A = ["are", "ano", "asoko", "atchi", "あれ", "あの", "あそこ", "あっち"]

    @classmethod
    def disambiguate_line(
        cls,
        whisper_text: str = "",
        source_en: str = "",
        prev_whisper_text: str = "",
        prev_source_en: str = "",
        prev_pl: str = "",
        time_gap_ms: int = 0,
        is_sign: bool = False,
        clean_en: str = "",
        jp_audio: str = "",
        speaker: str = "",
        character_registry: Optional[Dict[str, str]] = None,
        series_bible: Optional[Any] = None,
        prev_clean_en: str = "",
        prev_clean_pl: str = "",
        **kwargs
    ) -> DisambiguationTag:
        """
        Główna metoda deterministycznego rozstrzygania cech wypowiedzi (0.00 PLN).
        """
        whisper_text = whisper_text or jp_audio or ""
        source_en = source_en or clean_en or ""
        prev_source_en = prev_source_en or prev_clean_en or ""
        prev_pl = prev_pl or prev_clean_pl or ""

        tag = DisambiguationTag(detected_markers=[])
        if is_sign or not whisper_text:
            return tag

        jp_lower = whisper_text.lower()
        en_lower = (source_en or "").lower()
        prev_en_lower = (prev_source_en or "").lower()
        prev_jp_lower = (prev_whisper_text or "").lower()

        # -------------------------------------------------------------
        # K3: Płeć autoreferencyjna mówcy 1. osoby (I / me / my)
        # -------------------------------------------------------------
        has_male_1st = any(re.search(rf"\b{re.escape(m)}\b", jp_lower) for m in cls.MALE_1ST_PERSON)
        has_female_1st = any(re.search(rf"\b{re.escape(m)}\b", jp_lower) for m in cls.FEMALE_1ST_PERSON)
        has_female_particles = any(m in jp_lower for m in cls.FEMALE_SENTENCE_PARTICLES)
        has_male_particles = any(m in jp_lower for m in cls.MALE_SENTENCE_PARTICLES)

        if has_male_1st or (has_male_particles and not has_female_1st):
            tag.speaker_gender = "MALE"
            tag.detected_markers.append("K3:Mówca_M")
        elif has_female_1st or has_female_particles:
            tag.speaker_gender = "FEMALE"
            tag.detected_markers.append("K3:Mówca_K")

        # -------------------------------------------------------------
        # K2: Liczba gramatyczna adresata 2. osoby ('you' -> lp. vs lm.)
        # -------------------------------------------------------------
        has_jp_plural = any(re.search(rf"\b{re.escape(m)}\b", jp_lower) or m in jp_lower for m in cls.PLURAL_MARKERS)
        has_collective_vocative = bool(re.search(
            r"^(?:everyone|everybody|guys|team|class|all of you|ladies and gentlemen|people)[,!\?]|"
            r"\b(?:attention everyone|listen up,?\s*(?:everyone|guys|team|all of you)?)\b|"
            r"\b(?:to all of you|for all of you)\b",
            en_lower
        ))
        if has_jp_plural or has_collective_vocative:
            tag.addressee_number = "PLURAL"
            tag.detected_markers.append("K2:Adresat_LM")
        else:
            # Prymat relacji diadycznej (Singular Dyadic Primacy)
            tag.addressee_number = "SINGULAR"

        # -------------------------------------------------------------
        # K1: Płeć i rejestr adresata 2. osoby ('you')
        # -------------------------------------------------------------
        has_masc_2nd = any(re.search(rf"\b{re.escape(m)}\b", jp_lower) for m in cls.MASC_INFORMAL_2ND_PERSON)
        has_chan = any(m in jp_lower for m in cls.FEMALE_HONORIFIC_VOCATIVES)
        has_kun = any(m in jp_lower for m in cls.MALE_HONORIFIC_VOCATIVES)

        if tag.addressee_number == "SINGULAR":
            if has_kun or any(m in jp_lower for m in ["temee", "手前", "kisama", "貴様"]):
                tag.addressee_gender = "MALE"
                tag.detected_markers.append("K1:Adresat_M")
            elif has_chan or "anta" in jp_lower or "あんた" in jp_lower:
                tag.addressee_gender = "FEMALE"
                tag.detected_markers.append("K1:Adresat_K")
            elif any(m in jp_lower for m in ["omae", "お前"]):
                tag.addressee_gender = "MALE"
                tag.detected_markers.append("K1:Adresat_M (omae)")

        # -------------------------------------------------------------
        # K4: Hierarchia pokrewieństwa i role społeczne
        # -------------------------------------------------------------
        has_older_bro = any(m in jp_lower for m in cls.OLDER_BROTHER_MARKERS)
        has_younger_bro = any(m in jp_lower for m in cls.YOUNGER_BROTHER_MARKERS)
        has_older_sis = any(m in jp_lower for m in cls.OLDER_SISTER_MARKERS)
        has_younger_sis = any(m in jp_lower for m in cls.YOUNGER_SISTER_MARKERS)

        if "aniki" in jp_lower or "兄貴" in jp_lower:
            # Sprawdź czy to relacja podwładny-szef czy rodzina
            if any(w in en_lower for w in ["boss", "bro", "brother", "big bro", "chief"]):
                tag.kinship_role = "STARSZY_BRAT_LUB_SZEF"
                tag.detected_markers.append("K4:Aniki")
        elif has_older_bro:
            tag.kinship_role = "STARSZY_BRAT"
            tag.detected_markers.append("K4:StarszyBrat")
        elif has_younger_bro:
            tag.kinship_role = "MLODSZY_BRAT"
            tag.detected_markers.append("K4:MłodszyBrat")
        elif has_older_sis:
            tag.kinship_role = "STARSZA_SIOSTRA"
            tag.detected_markers.append("K4:StarszaSiostra")
        elif has_younger_sis:
            tag.kinship_role = "MLODSZA_SIOSTRA"
            tag.detected_markers.append("K4:MłodszaSiostra")

        # -------------------------------------------------------------
        # K5: Wektory przysługi i kierunkowość działań
        # -------------------------------------------------------------
        has_kureru = any(m in jp_lower for m in cls.BENEFACTIVE_FOR_ME)
        has_ageru = any(m in jp_lower for m in cls.BENEFACTIVE_FOR_THEM)
        if has_kureru and not has_ageru:
            tag.benefactive = "FOR_ME"
            tag.detected_markers.append("K5:DlaMnie (kureru)")
        elif has_ageru and not has_kureru:
            tag.benefactive = "FOR_THEM"
            tag.detected_markers.append("K5:DlaCiebie (ageru)")

        # -------------------------------------------------------------
        # K6: Odwrócona biegunowość pytań negatywnych (Echo Agreement)
        # -------------------------------------------------------------
        is_prev_neg_q = (prev_en_lower.endswith("?") or prev_jp_lower.endswith("?") or "？" in prev_jp_lower) and (
            any(re.search(rf"\b{re.escape(w)}\b", prev_en_lower) for w in [
                "not", "don't", "aren't", "didn't", "can't", "won't", "haven't", "isn't", "couldn't", "shouldn't", "never"
            ]) or any(m in prev_jp_lower for m in [
                "nai", "ない", "masen", "ません", "nakatta", "なかった", "janai", "じゃない"
            ]) or bool(re.search(r"\bnie\s+[a-ząćęłńóśźż]+", prev_pl, re.IGNORECASE))
        )
        curr_is_affirmative_jp = any(re.search(rf"\b{re.escape(t)}\b", jp_lower) or t in jp_lower for t in cls.AFFIRMATIVE_JP_TOKENS)

        if time_gap_ms < 6000 and is_prev_neg_q and curr_is_affirmative_jp:
            tag.polar_response = "NEGATIVE_CONFIRM"
            tag.detected_markers.append("K6:EchoAgreement (Hai -> Nie)")

        # -------------------------------------------------------------
        # K7: Rejestr społeczny T-V
        # -------------------------------------------------------------
        has_keigo = any(m in jp_lower for m in cls.KEIGO_FORMAL_MARKERS)
        has_kudaketa = any(m in jp_lower for m in cls.KUDAKETA_INFORMAL_MARKERS) or has_masc_2nd
        if has_keigo and not has_kudaketa:
            tag.social_register = "FORMAL_PAN"
            tag.detected_markers.append("K7:Formalny (Keigo)")
        elif has_kudaketa and not has_keigo:
            tag.social_register = "INFORMAL_TY"
            tag.detected_markers.append("K7:Nieformalny (Ty)")

        # -------------------------------------------------------------
        # K8: Deiksa przestrzenna (Ko-So-A-Do)
        # -------------------------------------------------------------
        if any(re.search(rf"\b{re.escape(m)}\b", jp_lower) for m in cls.DEICTIC_KO):
            tag.spatial_deictic = "to tutaj (blisko mówcy)"
        elif any(re.search(rf"\b{re.escape(m)}\b", jp_lower) for m in cls.DEICTIC_SO):
            tag.spatial_deictic = "to tam (blisko rozmówcy)"
        elif any(re.search(rf"\b{re.escape(m)}\b", jp_lower) for m in cls.DEICTIC_A):
            tag.spatial_deictic = "tamto (daleko od obu)"

        return tag

    @classmethod
    def format_compact_ssot_tag(cls, tag: DisambiguationTag) -> str:
        """
        Formatuje maksymalnie zwięzłą, jednolinijkową metadaną SSOT do promptu Fazy 2.
        Zero zbędnego szumu, zero wielolinijkowych mikro-nakazów (zgodnie z AGENTS.md §0).
        """
        if not tag or tag.is_empty():
            return ""

        parts = []
        if tag.speaker_gender == "MALE":
            parts.append("Mówca: Męski (-łem)")
        elif tag.speaker_gender == "FEMALE":
            parts.append("Mówca: Żeński (-łam)")

        if tag.addressee_number == "SINGULAR":
            if tag.addressee_gender == "MALE":
                parts.append("Odbiorca: Mężczyzna (-łeś/ci)")
            elif tag.addressee_gender == "FEMALE":
                parts.append("Odbiorca: Kobieta (-łaś/ci)")
            else:
                parts.append("Odbiorca: 1 osoba (l. poj.: ci/tobie)")
        elif tag.addressee_number == "PLURAL":
            if tag.addressee_gender == "FEMALE":
                parts.append("Odbiorca: Grupa Kobiet (-łyście/wam)")
            else:
                parts.append("Odbiorca: Zbiorowość/Grupa (-liście/wam)")

        if tag.polar_response == "NEGATIVE_CONFIRM":
            parts.append("Odpowiedź na przeczenie: 'Nie' / 'Zgadza się'")

        if tag.kinship_role == "STARSZY_BRAT_LUB_SZEF":
            parts.append("Relacja: Aniki (Starszy brat lub szef)")
        elif tag.kinship_role == "STARSZY_BRAT":
            parts.append("Relacja: Starszy brat")
        elif tag.kinship_role == "MLODSZY_BRAT":
            parts.append("Relacja: Młodszy brat")
        elif tag.kinship_role == "STARSZA_SIOSTRA":
            parts.append("Relacja: Starsza siostra")
        elif tag.kinship_role == "MLODSZA_SIOSTRA":
            parts.append("Relacja: Młodsza siostra")

        if tag.benefactive == "FOR_ME":
            parts.append("Kierunek: Dla mnie (kureru)")
        elif tag.benefactive == "FOR_THEM":
            parts.append("Kierunek: Dla kogoś (ageru)")

        if tag.social_register == "FORMAL_PAN":
            parts.append("Dystans: Formalny (Pan/Pani)")
        elif tag.social_register == "INFORMAL_TY":
            parts.append("Dystans: Bezpośredni (Ty)")

        if tag.is_phantom_audio:
            parts.append("Dźwięk: Muzyka/Tło/Brak mowy")
        if tag.low_acoustic_confidence:
            parts.append("Akustyka: Niska pewność/Krzyk")
        if tag.is_hallucination_loop:
            parts.append("Filtr: Artefakt pętli zneutralizowany")

        if not parts:
            return ""

        return f" [AUDIO JP: {' | '.join(parts)}]"

    @classmethod
    def detect_hallucination_loop(
        cls,
        whisper_segment: Any,
        compression_ratio_threshold: float = 2.4,
        repetition_threshold: int = 4
    ) -> bool:
        """
        Detects Whisper repetition/hallucination loops (e.g. repeated tokens on long silence or background music).
        Returns True if the segment is a hallucinated loop and should be discarded.
        """
        if not whisper_segment:
            return False

        # 1. Check native compression_ratio if available from Whisper
        if isinstance(whisper_segment, dict):
            comp_ratio = whisper_segment.get("compression_ratio")
            if comp_ratio is not None and float(comp_ratio) > compression_ratio_threshold:
                return True
            text = str(whisper_segment.get("text", "")).strip()
        else:
            text = str(whisper_segment).strip()

        if not text:
            return False

        # 2. Check repetitive consecutive words or phrases
        words = text.split()
        if len(words) >= repetition_threshold:
            for i in range(len(words) - repetition_threshold + 1):
                window = words[i:i+repetition_threshold]
                if len(set(window)) == 1:
                    return True

        # 3. Check for repeated phrases in Japanese without spaces
        rep_patterns = [
            r"(.{2,10}?)\1{3,}",   # Same 2-10 char pattern repeated 4+ times
        ]
        for pat in rep_patterns:
            if re.search(pat, text):
                return True

        return False

    @classmethod
    def filter_voice_activity(
        cls,
        whisper_segment: Any,
        no_speech_threshold: float = 0.85
    ) -> bool:
        """
        Evaluates Voice Activity Detection (VAD) metadata from Whisper.
        Returns True if the segment is non-speech (music, noise, or silence).
        """
        if isinstance(whisper_segment, dict):
            no_speech = whisper_segment.get("no_speech_prob")
            if no_speech is not None and float(no_speech) >= no_speech_threshold:
                return True
        return False

    @classmethod
    def assess_acoustic_confidence(
        cls,
        whisper_segment: Any,
        low_confidence_threshold: float = -1.0
    ) -> str:
        """
        Assesses the acoustic confidence of the Whisper transcription based on avg_logprob.
        Returns: "HIGH", "NORMAL", or "LOW".
        """
        if isinstance(whisper_segment, dict):
            logprob = whisper_segment.get("avg_logprob")
            if logprob is not None:
                lp = float(logprob)
                if lp < low_confidence_threshold:
                    return "LOW"
                elif lp > -0.3:
                    return "HIGH"
        return "NORMAL"
