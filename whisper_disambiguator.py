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
from typing import Optional, Dict, Any, List, Tuple, Set
import re


@dataclass
class DisambiguationTag:
    speaker_gender: Optional[str] = None       # "MALE" | "FEMALE"
    speaker_age_class: Optional[str] = None    # "CHILD_MALE" | "CHILD_FEMALE" | "ADULT_MALE" | "ADULT_FEMALE" | "ELDERLY_MALE" | "ELDERLY_FEMALE" | "UNKNOWN"
    addressee_gender: Optional[str] = None     # "MALE" | "FEMALE" | "MIXED"
    addressee_age_class: Optional[str] = None  # "CHILD" | "ADULT" | "ELDERLY"
    addressee_number: Optional[str] = None     # "SINGULAR" | "DUAL" | "PLURAL"
    social_register: Optional[str] = None      # "INFORMAL_TY" | "FORMAL_PAN"
    pragmatic_attitude: Optional[str] = None   # "HOSTILE" | None (Kisama / Temee)
    polar_response: Optional[str] = None       # "NEGATIVE_CONFIRM" (Hai/Un po pytaniu negatywnym -> 'Nie')
    kinship_role: Optional[str] = None         # "STARSZY_BRAT" | "MLODSZY_BRAT" | "STARSZA_SIOSTRA" | "MLODSZA_SIOSTRA" | "SZEF"
    benefactive: Optional[str] = None          # "FOR_ME" | "FOR_THEM"
    spatial_deictic: Optional[str] = None      # "to tutaj (blisko mówcy)" | "to tam (blisko rozmówcy)" | "tamto (daleko)"
    is_phantom_audio: bool = False             # no_speech_prob > 0.85
    low_acoustic_confidence: bool = False     # avg_logprob < -1.0
    is_hallucination_loop: bool = False       # compression_ratio > 2.4 or repetitive n-gram
    is_shock_drop: bool = False               # Filar CLXXVIII: sudden drop >= 12 dBFS / shout -> whisper
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

    @property
    def addressee_is_group(self) -> bool:
        return self.addressee_number in ("PLURAL", "DUAL")

    @property
    def addressee_register(self) -> Optional[str]:
        return self.social_register

    @addressee_register.setter
    def addressee_register(self, value: Optional[str]):
        self.social_register = value

    def is_empty(self) -> bool:
        return not any([
            self.speaker_gender, self.addressee_gender, self.addressee_number,
            self.social_register, getattr(self, "pragmatic_attitude", None),
            self.polar_response, self.kinship_role,
            self.benefactive, self.spatial_deictic, self.is_shock_drop
        ])


class WhisperDisambiguator:
    """
    Wysokowydajny silnik analizy leksykalno-akustycznej Whisper (0.00 PLN).
    Mapuje wykładniki języka japońskiego na jednoznaczne dyskryminatory fleksyjno-semantyczne.
    """

    # --- Kanji Pronoun Anchors chroniące przed sufiksem -kun i złożeniami jukugo (Dyrektywy 4 i 5) ---
    KANJI_PRONOUN_PATTERNS = {
        "私": r"私(?=[はがのもにをと、,\s]|$)",
        "君": r"(?<![\u4e00-\u9fff\u3040-\u30ff])君(?=[はがのもにをと、,\s]|$)",
        "手前": r"手前(?=[はがも！!…\s、,]|$)"
    }

    @classmethod
    def _match_jp_token(cls, m: str, text: str) -> bool:
        if m in cls.KANJI_PRONOUN_PATTERNS:
            return bool(re.search(cls.KANJI_PRONOUN_PATTERNS[m], text))
        if any('\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9fff' for c in m):
            return m in text
        return bool(re.search(rf"\b{re.escape(m)}\b", text))

    # --- K1: Zaimki 2. osoby (Adresat) ---
    HOSTILE_2ND_PERSON = ["temee", "手前", "てめえ", "テメエ", "kisama", "貴様", "きさま", "キサマ"]
    MASC_INFORMAL_2ND_PERSON = [
        "omae", "お前", "おまえ", "オマエ", "temee", "手前", "てめえ", "テメエ", "kisama", "貴様", "きさま", "キサマ", "anta", "あんた", "アンタ"
    ]
    EQUAL_JUNIOR_2ND_PERSON = ["kimi", "君", "きみ", "キミ"]
    FEMALE_HONORIFIC_VOCATIVES = ["-chan", "chan", "ちゃん", "チャン"]
    MALE_HONORIFIC_VOCATIVES = ["-kun", "kun", "君", "くん", "クン"]

    # --- K2: Liczba mnoga i podwójna adresata (Plural & Dual markers) ---
    DUAL_MARKERS = [
        "futari", "ふたり", "二人", "futari-tomo", "二人とも", "ryouhou", "両方", "docchi", "どっち"
    ]
    PLURAL_MARKERS = [
        "tachi", "たち", "達", "omae-ra", "お前ら", "kisama-ra", "貴様ら",
        "temee-ra", "てめえら", "テメエら", "anta-tachi", "あんたら", "あんたたち",
        "kimi-tachi", "君たち", "anata-tachi", "あなたたち", "koitsura", "aitsura", "こいつら", "あいつら",
        "minna", "みんな", "皆", "shokun", "諸君", "zen'in", "全員",
        "mina-sama", "皆様", "domo", "ども", "共"
    ]

    # --- K3: Zaimki 1. osoby (Mówca), Cząstki płciowe & Rodzajowe imperatywy ---
    FEMALE_IMPERATIVES = [
        "nasai", "なさい", "choudai", "ちょうだい"
    ]
    MALE_IMPERATIVES = [
        "tamae", "たまえ", "kure", "くれ", "shiro", "しろ", "koi", "来い", "koiyo", "miro", "見ろ", "yare", "やれ"
    ]
    YOUNG_BOY_JP_MARKERS = [
        "boku", "僕", "oira", "おいら", "bozu", "坊主", "bocchan", "坊ちゃん",
        "kozo", "小僧", "shounen", "少年", "otouto", "弟", "musuko", "息子"
    ]
    YOUNG_BOY_EN_MARKERS = [
        "boy", "lad", "kiddo", "son", "brother", "little guy", "young master",
        "schoolboy", "young man"
    ]
    YOUNG_GIRL_JP_MARKERS = [
        "ojousan", "ojou-san", "ojou-chan", "jou-chan", "onnanoko", "shoujo", "musume", "imouto",
        "女の子", "少女", "嬢ちゃん", "お嬢さん", "お嬢ちゃん", "妹", "娘"
    ]
    YOUNG_GIRL_EN_MARKERS = [
        "little girl", "girl", "lass", "missy", "young lady", "daughter", "little lady",
        "schoolgirl"
    ]
    MALE_1ST_PERSON = [
        "ore", "俺", "おれ", "オレ", "boku", "僕", "ぼく", "ボク", "oira", "おいら", "オイラ", "washi", "わし",
        "sessha", "拙者", "ware", "我", "wagahai", "吾輩", "jibun", "自分"
    ]
    FEMALE_1ST_PERSON = [
        "atashi", "あたし", "アタシ", "atai", "あtai", "アタイ", "atakushi",
        "warawa", "妾", "uchi", "うち"
    ]
    FEMALE_SENTENCE_PARTICLES = [
        "kashira", "かしら", "wa yo", "わよ", "none", "のね",
        "no yo", "のよ", "te yo", "てよ", "koto", "こと", "wa", "わ", "mono", "もの"
    ]
    MALE_SENTENCE_PARTICLES = [
        "da zo", "だぞ", "da ze", "だぜ", "zo", "ぜ", "ぞ", "kai", "かい"
    ]

    # --- K4: Pokrewieństwo i hierarchia wieku ---
    OLDER_BROTHER_MARKERS = ["onii-san", "onii-chan", "nii-san", "nii-chan", "aniki", "aniue", "兄", "兄貴", "兄上"]
    YOUNGER_BROTHER_MARKERS = ["otouto", "弟"]
    OLDER_SISTER_MARKERS = ["onee-san", "onee-chan", "nee-san", "nee-chan", "aneue", "姉", "姉貴", "姉上"]
    YOUNGER_SISTER_MARKERS = ["imouto", "妹"]
    FATHER_MARKERS = ["otou-san", "tou-san", "chichi", "chichioya", "oyaji", "chichiue", "父", "父親", "親父", "父上", "お父さん"]
    MOTHER_MARKERS = ["okaa-san", "kaa-san", "haha", "hahaoya", "ofukuro", "hahaue", "母", "母親", "お袋", "母上", "お母さん"]
    GRANDFATHER_MARKERS = ["ojii-san", "jii-san", "jiji", "sofu", "祖父", "おじいさん", "爺", "じいさん"]
    GRANDMOTHER_MARKERS = ["obaa-san", "baa-san", "baba", "sobo", "祖母", "おばあさん", "婆", "ばあさん"]
    UNCLE_MARKERS = ["oji-san", "ojisan", "叔父", "伯父", "おじさん"]
    AUNT_MARKERS = ["oba-san", "obasan", "叔母", "伯母", "おばさん"]

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
        whisper_text = whisper_text or jp_audio or kwargs.get("jp_text", "") or kwargs.get("jp", "") or ""
        source_en = source_en or clean_en or kwargs.get("en_text", "") or kwargs.get("en", "") or ""
        prev_source_en = prev_source_en or prev_clean_en or kwargs.get("prev_en", "") or ""
        prev_pl = prev_pl or prev_clean_pl or kwargs.get("prev_pl", "") or ""

        tag = DisambiguationTag(detected_markers=[])
        if is_sign or (not whisper_text and not source_en):
            return tag

        jp_lower = whisper_text.lower()
        en_lower = (source_en or "").lower()
        prev_en_lower = (prev_source_en or "").lower()
        prev_jp_lower = (prev_whisper_text or "").lower()

        # -------------------------------------------------------------
        # K3: Płeć autoreferencyjna mówcy 1. osoby (I / me / my)
        # K3: Płeć autoreferencyjna mówcy 1. osoby ('I / me / my')
        # -------------------------------------------------------------
        has_male_1st = any(cls._match_jp_token(m, jp_lower) for m in cls.MALE_1ST_PERSON)
        has_female_1st = any(cls._match_jp_token(m, jp_lower) for m in cls.FEMALE_1ST_PERSON)
        has_female_particles = any(m in jp_lower for m in cls.FEMALE_SENTENCE_PARTICLES)
        has_male_particles = any(m in jp_lower for m in cls.MALE_SENTENCE_PARTICLES)

        has_young_boy_jp = any(re.search(rf"\b{re.escape(m)}\b", jp_lower) or m in jp_lower for m in cls.YOUNG_BOY_JP_MARKERS)
        has_young_boy_en = any(re.search(rf"\b{re.escape(m)}\b", en_lower) for m in cls.YOUNG_BOY_EN_MARKERS)
        has_young_girl_jp = any(re.search(rf"\b{re.escape(m)}\b", jp_lower) or m in jp_lower for m in cls.YOUNG_GIRL_JP_MARKERS)
        has_young_girl_en = any(re.search(rf"\b{re.escape(m)}\b", en_lower) for m in cls.YOUNG_GIRL_EN_MARKERS)
        has_female_imperatives = any(re.search(rf"\b{re.escape(m)}\b", jp_lower) or m in jp_lower for m in cls.FEMALE_IMPERATIVES)
        has_male_imperatives = any(re.search(rf"\b{re.escape(m)}\b", jp_lower) or m in jp_lower for m in cls.MALE_IMPERATIVES)

        spk_is_boy_role = False
        spk_is_girl_role = False
        spk_is_elderly_female = False
        spk_is_elderly_male = False
        if speaker and (character_registry or series_bible):
            clean_spk = re.sub(r"\s*\(.*?\)", "", speaker).strip().lower()
            spk_desc = ""
            if character_registry and clean_spk in character_registry:
                c_val = character_registry[clean_spk]
                spk_desc = (c_val.get("description", "") if isinstance(c_val, dict) else str(c_val)).lower()
            elif series_bible and hasattr(series_bible, "data") and "characters" in series_bible.data:
                b_val = series_bible.data["characters"].get(clean_spk, {})
                spk_desc = (b_val.get("description", "") if isinstance(b_val, dict) else str(b_val)).lower()
            if any(k in spk_desc for k in ["chłopiec", "chłopak", "boy", "syn", "młodzieniec", "książę", "dziecko płci męskiej", "uczeń", "schoolboy", "lad"]):
                spk_is_boy_role = True
            if any(k in spk_desc for k in ["dziewczynka", "girl", "córka", "panienka", "mała dziewczynka", "uczennica", "schoolgirl", "lass"]):
                spk_is_girl_role = True
            if any(k in spk_desc for k in ["staruszka", "babcia", "stara kobieta", "elderly female", "grandmother", "old woman"]):
                spk_is_elderly_female = True
            if any(k in spk_desc for k in ["starzec", "dziadek", "stary mężczyzna", "elderly male", "grandfather", "old man"]):
                spk_is_elderly_male = True

        if has_young_boy_jp or has_young_boy_en or spk_is_boy_role:
            tag.speaker_gender = "MALE"
            tag.speaker_age_class = "CHILD_MALE"
            tag.detected_markers.append("K3:Chłopiec_M (Seiyū)")
        elif has_young_girl_jp or has_young_girl_en or spk_is_girl_role:
            tag.speaker_gender = "FEMALE"
            tag.speaker_age_class = "CHILD_FEMALE"
            tag.detected_markers.append("K3:Dziewczynka_K (Seiyū)")
        elif spk_is_elderly_female:
            tag.speaker_gender = "FEMALE"
            tag.speaker_age_class = "ELDERLY_FEMALE"
            tag.detected_markers.append("K3:Seniorka_K")
        elif spk_is_elderly_male:
            tag.speaker_gender = "MALE"
            tag.speaker_age_class = "ELDERLY_MALE"
            tag.detected_markers.append("K3:Senior_M")
        elif has_male_1st or (has_male_particles and not has_female_1st):
            tag.speaker_gender = "MALE"
            tag.speaker_age_class = "ADULT_MALE"
            tag.detected_markers.append("K3:Mówca_M")
        elif has_female_1st or has_female_particles:
            tag.speaker_gender = "FEMALE"
            tag.speaker_age_class = "ADULT_FEMALE"
            tag.detected_markers.append("K3:Mówca_K")
        elif has_female_imperatives and not has_male_1st:
            tag.speaker_gender = "FEMALE"
            tag.speaker_age_class = "ADULT_FEMALE"
            tag.detected_markers.append("K3:Mówca_K (Imperatyw)")
        elif has_male_imperatives and not has_female_1st:
            tag.speaker_gender = "MALE"
            tag.speaker_age_class = "ADULT_MALE"
            tag.detected_markers.append("K3:Mówca_M (Imperatyw)")

        # -------------------------------------------------------------
        # K2: Liczba gramatyczna adresata 2. osoby ('you' -> lp. vs lm. vs dual)
        # -------------------------------------------------------------
        has_dual_jp = any(re.search(rf"\b{re.escape(m)}\b", jp_lower) or m in jp_lower for m in cls.DUAL_MARKERS)
        has_dual_en = bool(re.search(r"\b(?:both\s+of\s+you|you\s+two|two\s+of\s+you|the\s+two\s+of\s+you)\b", en_lower))
        has_jp_plural = any(re.search(rf"\b{re.escape(m)}\b", jp_lower) or m in jp_lower for m in cls.PLURAL_MARKERS)
        has_collective_vocative = bool(re.search(
            r"^(?:everyone|everybody|guys|team|class|all of you|ladies and gentlemen|people|soldiers|warriors|troops|men|you guys|you all)[,!\?]|"
            r"\b(?:you\s+guys|you\s+all)\b|"
            r"\b(?:attention everyone|listen up,?\s*(?:everyone|guys|team|all of you|soldiers|men)?)\b|"
            r"\b(?:to all of you|for all of you)\b",
            en_lower
        ))

        # Adresatywne znaczniki tytularne i wiekowe
        has_chan = any(m in jp_lower for m in cls.FEMALE_HONORIFIC_VOCATIVES)
        has_kun = any(m in jp_lower for m in cls.MALE_HONORIFIC_VOCATIVES)
        has_boy_addr_jp = any(re.search(rf"\b{re.escape(m)}\b", jp_lower) or m in jp_lower for m in ["bocchan", "坊ちゃん", "bozu", "坊主", "kozo", "小僧", "shounen", "少年", "otouto", "弟"])
        has_boy_addr_en = any(re.search(rf"\b{re.escape(m)}\b", en_lower) for m in ["boy", "lad", "kiddo", "son", "young master"])
        has_girl_addr_jp = any(re.search(rf"\b{re.escape(m)}\b", jp_lower) or m in jp_lower for m in cls.YOUNG_GIRL_JP_MARKERS)
        has_girl_addr_en = any(re.search(rf"\b{re.escape(m)}\b", en_lower) for m in cls.YOUNG_GIRL_EN_MARKERS)

        if has_dual_jp or has_dual_en:
            tag.addressee_number = "DUAL"
            tag.detected_markers.append("K2:Adresat_DUAL")
        elif has_jp_plural or has_collective_vocative:
            tag.addressee_number = "PLURAL"
            tag.detected_markers.append("K2:Adresat_LM")
        else:
            # Doktryna Twardych Dowodów (Epistemic Proof Chain):
            # Liczbę pojedynczą adresata przypisujemy wyłącznie przy twardym dowodzie obecności zaimka 2. os.,
            # wołacza lub tytulatury adresatywnej. W przeciwnym razie liczba adresata pozostaje None (Zero-Evidence Invariance Gate).
            has_2nd_person = any(cls._match_jp_token(m, jp_lower) for m in cls.MASC_INFORMAL_2ND_PERSON + cls.EQUAL_JUNIOR_2ND_PERSON + ["anata", "あなた"]) or bool(re.search(r"\b(?:you|your|yours|yourself)\b", en_lower))
            if has_2nd_person or has_boy_addr_jp or has_boy_addr_en or has_girl_addr_jp or has_girl_addr_en:
                tag.addressee_number = "SINGULAR"
            else:
                tag.addressee_number = None

        # -------------------------------------------------------------
        # K1: Płeć i wiek adresata 2. osoby ('you') - Twarde Dowody Onomastyczne i Tytularne
        # -------------------------------------------------------------

        if tag.addressee_number == "SINGULAR":
            if has_girl_addr_jp or has_girl_addr_en:
                tag.addressee_gender = "FEMALE"
                tag.addressee_age_class = "CHILD"
                tag.detected_markers.append("K1:Adresat_K (Dziewczynka)")
            elif has_boy_addr_jp or has_boy_addr_en:
                tag.addressee_gender = "MALE"
                tag.addressee_age_class = "CHILD"
                tag.detected_markers.append("K1:Adresat_M (Chłopiec)")
            elif has_chan:
                tag.addressee_gender = "FEMALE"
                tag.addressee_age_class = "ADULT"
                tag.detected_markers.append("K1:Adresat_K (-chan)")
            elif has_kun:
                tag.addressee_gender = "MALE"
                tag.addressee_age_class = "ADULT"
                tag.detected_markers.append("K1:Adresat_M (-kun)")
            # Zaimki omae, anta, temee, kisama celowo NIE definiują płci (przeniesione do K7 jako rejestr nieformalny)
        elif tag.addressee_number == "DUAL":
            if has_chan or any(w in en_lower for w in ["girls", "ladies", "women"]):
                tag.addressee_gender = "FEMALE"
            elif has_kun or any(w in en_lower for w in ["boys", "men"]):
                tag.addressee_gender = "MALE"
            else:
                tag.addressee_gender = "MIXED"
        elif tag.addressee_number == "PLURAL":
            if has_chan or any(w in en_lower for w in ["girls", "ladies", "women", "dziewczęta", "kobiety"]):
                tag.addressee_gender = "FEMALE"

        # -------------------------------------------------------------
        # K4: Hierarchia pokrewieństwa i role społeczne
        # -------------------------------------------------------------
        has_older_bro = any(m in jp_lower for m in cls.OLDER_BROTHER_MARKERS)
        has_younger_bro = any(m in jp_lower for m in cls.YOUNGER_BROTHER_MARKERS)
        has_older_sis = any(m in jp_lower for m in cls.OLDER_SISTER_MARKERS)
        has_younger_sis = any(m in jp_lower for m in cls.YOUNGER_SISTER_MARKERS)
        has_father = any(m in jp_lower for m in cls.FATHER_MARKERS)
        has_mother = any(m in jp_lower for m in cls.MOTHER_MARKERS)
        has_grandfather = any(m in jp_lower for m in cls.GRANDFATHER_MARKERS)
        has_grandmother = any(m in jp_lower for m in cls.GRANDMOTHER_MARKERS)
        has_uncle = any(m in jp_lower for m in cls.UNCLE_MARKERS)
        has_aunt = any(m in jp_lower for m in cls.AUNT_MARKERS)

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
        elif has_father:
            tag.kinship_role = "OJCIEC"
            tag.detected_markers.append("K4:Ojciec")
        elif has_mother:
            tag.kinship_role = "MATKA"
            tag.detected_markers.append("K4:Matka")
        elif has_grandfather:
            tag.kinship_role = "DZIADEK"
            tag.detected_markers.append("K4:Dziadek")
        elif has_grandmother:
            tag.kinship_role = "BABCIA"
            tag.detected_markers.append("K4:Babcia")
        elif has_uncle:
            tag.kinship_role = "WUJ"
            tag.detected_markers.append("K4:Wuj")
        elif has_aunt:
            tag.kinship_role = "CIOTKA"
            tag.detected_markers.append("K4:Ciotka")

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
        has_hostile = any(cls._match_jp_token(m, jp_lower) for m in cls.HOSTILE_2ND_PERSON)
        has_2nd_informal = any(cls._match_jp_token(m, jp_lower) for m in cls.MASC_INFORMAL_2ND_PERSON + cls.EQUAL_JUNIOR_2ND_PERSON)
        has_kudaketa = any(m in jp_lower for m in cls.KUDAKETA_INFORMAL_MARKERS) or has_2nd_informal or has_hostile

        if has_hostile:
            tag.pragmatic_attitude = "HOSTILE"
            tag.social_register = "INFORMAL_TY"
            tag.detected_markers.append("K7:Wrogi (Kisama/Temee)")
        elif has_keigo and not has_kudaketa:
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
        if tag.speaker_age_class == "CHILD_FEMALE":
            parts.append("Mówca: Mała Dziewczynka (Głos Seiyū / Formy Żeńskie: -łam / Prosty rejestr)")
        elif tag.speaker_age_class == "CHILD_MALE":
            parts.append("Mówca: Młody Chłopiec (Głos Seiyū / Formy Męskie: -łem)")
        elif tag.speaker_age_class == "ELDERLY_FEMALE":
            parts.append("Mówca: Starsza Kobieta (Głos Seiyū / Formy Żeńskie: -łam)")
        elif tag.speaker_age_class == "ELDERLY_MALE":
            parts.append("Mówca: Starszy Mężczyzna (Głos Seiyū / Formy Męskie: -łem)")
        elif tag.speaker_gender == "MALE":
            parts.append("Mówca: Męski (-łem)")
        elif tag.speaker_gender == "FEMALE":
            parts.append("Mówca: Żeński (-łam)")

        if tag.addressee_number == "SINGULAR":
            if tag.addressee_age_class == "CHILD":
                if tag.addressee_gender == "FEMALE":
                    parts.append("Odbiorca: Mała Dziewczynka (Rejestr: Ty, opiekuńczy)")
                else:
                    parts.append("Odbiorca: Mały Chłopiec (Rejestr: Ty, opiekuńczy)")
            elif tag.addressee_gender == "MALE":
                parts.append("Odbiorca: Mężczyzna (-łeś/ci)")
            elif tag.addressee_gender == "FEMALE":
                parts.append("Odbiorca: Kobieta (-łaś/ci)")
            else:
                parts.append("Odbiorca: 1 osoba (l. poj.: ci/tobie)")
        elif tag.addressee_number == "DUAL":
            if tag.addressee_gender == "FEMALE":
                parts.append("Odbiorca: Dwie Kobiety (L. podwójna: Obie / -łyście)")
            elif tag.addressee_gender == "MALE":
                parts.append("Odbiorca: Dwóch Mężczyzn (L. podwójna: Obaj / -liście)")
            else:
                parts.append("Odbiorca: Para Mieszana (L. podwójna: Oboje / -liście)")
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

        if getattr(tag, "pragmatic_attitude", None) == "HOSTILE":
            parts.append("Dystans: Skrajnie wrogi/Konfrontacyjny (Kisama/Temee)")
        elif tag.social_register == "FORMAL_PAN":
            parts.append("Dystans: Formalny (Pan/Pani)")
        elif tag.social_register == "INFORMAL_TY":
            parts.append("Dystans: Bezpośredni (Ty)")

        if tag.is_phantom_audio:
            parts.append("Dźwięk: Muzyka/Tło/Brak mowy")
        if tag.low_acoustic_confidence:
            parts.append("Akustyka: Niska pewność/Krzyk")
        if tag.is_hallucination_loop:
            parts.append("Filtr: Artefakt pętli zneutralizowany")
        if getattr(tag, "is_shock_drop", False):
            parts.append("Afekt: Załamanie/Szok (Ac=SHOCK_DROP)")

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

    @classmethod
    def detect_batch_discourse_categories(cls, combined_en: str, combined_jp: str) -> Set[str]:
        """
        N-05: Ekstrahuje kategorie dyskursu z tekstu japońskiego (i mieszanego)
        dla modułu reguł dynamicznych rules.py bez naruszania Z1/Z4 w rules.py.
        Zwraca neutralne znaczniki kategorii:
        - "DIALECT_JP"
        - "ARCHAIC_JP"
        - "AGE_GENDER_JP"
        - "FEMALE_GROUP_JP"
        - "HONORIFIC_JP"
        - "AFFECT_JP"
        - "LYRICAL_HIGH_JP"
        - "LYRICAL_SUPPORT_JP"
        - "LYRICAL_JP"
        - "CULTURE_JP"
        - "AISATSU_JP"
        - "SEIYU_SOVEREIGNTY_JP"
        - "CODE_SWITCH_EN"
        """
        categories: Set[str] = set()
        en_lower = (combined_en or "").lower()
        jp_lower = (combined_jp or "").lower()
        full_text = f"{en_lower} {jp_lower}"

        # 1. DIALECT_JP (Dialekty, gwary, sociolekty, yakuwarigo)
        jp_dialect_pat = re.compile(
            r"\b(?:ya|yan|yade|yaro|nen|seya|akan|honma|dappe|dabe|washi|atai|wai|wagahai|jaken|koraa|suitoo|nankurunaisa|haisai|namara|shibareru|だべ|じゃけん|やん|やde|yaro|ねん|せや|あかん|ほんま|わし|あたい|わい|吾輩|desu\s*wa|masu\s*wa|desu\s*koto|arimasen\s*koto|masu\s*no\s*yo|naissu|ssu\s*kedo|ssu\s*ne|ssu\s*yo|ttanano|danano|kuretamae)\b",
            re.IGNORECASE
        )
        character_suffix_pat = re.compile(
            r"(?:^|[\s\-])(?:dechu|nyan|pyon|zura|gero|dabe)\b",
            re.IGNORECASE
        )
        jp_anchored_dialect_re = re.compile(
            r"(?:(?:いく|行(?:く)?|すっ|やる|だ)べ(?:[！？!?。、\s]|$)|(?:^|[、。\s])おら(?:は|が|の|に|を|も|たち|っち)|(?:てる|でる|はず|だけ|こと|いい|ない|な)ある(?:よ|ね|か|な)*(?:[！？!?。、\s]|$)|(?:いい|ない|な|何)やる(?:か|ね|よ)*(?:[！？!?。、\s]|$))"
        )
        jp_dialect_tokens = [
            "だべ", "じゃけん", "やん", "やde", "やろ", "ねん", "せや", "あかん", "ほんま",
            "わし", "あたい", "わい", "吾輩", "ですわ", "ますわ", "ですこと", "ありませんこと",
            "ますのよ", "ないっす", "っすけど", "っすね", "っすよ", "ったなの", "だなの", "くれたまえ"
        ]
        if (
            jp_dialect_pat.search(jp_lower)
            or jp_dialect_pat.search(en_lower)
            or any(tok in jp_lower for tok in jp_dialect_tokens)
            or character_suffix_pat.search(jp_lower)
            or character_suffix_pat.search(en_lower)
            or jp_anchored_dialect_re.search(jp_lower)
        ):
            categories.add("DIALECT_JP")

        # 2. ARCHAIC_JP (Archaizacja, etykieta dworska)
        jp_archaic_pat = re.compile(
            r"\b(?:sessha|ojou|chichi-ue|haha-ue|gozaimasu|de gozaru)\b",
            re.IGNORECASE
        )
        jp_archaic_tokens = ["拙者", "お嬢", "父上", "母上", "ござる", "ございます"]
        if (
            jp_archaic_pat.search(jp_lower)
            or jp_archaic_pat.search(en_lower)
            or any(tok in jp_lower for tok in jp_archaic_tokens)
        ):
            categories.add("ARCHAIC_JP")

        # 3. AGE_GENDER_JP & FEMALE_GROUP_JP
        jp_age_gender_pat = re.compile(
            r"\b(?:kanojo-tachi|kanojotachi|onnatachi|shonen|baba|bba)\b",
            re.IGNORECASE
        )
        jp_age_gender_tokens = ["彼女たち", "彼女達", "女たち", "女達", "少年", "ばばあ", "ババア"]
        if (
            jp_age_gender_pat.search(jp_lower)
            or jp_age_gender_pat.search(en_lower)
            or any(tok in jp_lower for tok in jp_age_gender_tokens)
        ):
            categories.add("AGE_GENDER_JP")
            if any(k in full_text for k in ["kanojo-tachi", "kanojotachi", "onnatachi", "彼女たち", "彼女達", "女たち", "女達"]):
                categories.add("FEMALE_GROUP_JP")

        # 4. HONORIFIC_JP (Tytulatura i honoryfikatory)
        jp_honorifics_pat = re.compile(
            r"(?:-san|-kun|-chan|-sama|-sensei|-dono|先生|先輩|様|殿|師匠)",
            re.IGNORECASE
        )
        if jp_honorifics_pat.search(jp_lower) or jp_honorifics_pat.search(en_lower):
            categories.add("HONORIFIC_JP")

        # 5. AFFECT_JP (Kakegoe, ekspresja afektywna)
        if "kakegoe" in full_text:
            categories.add("AFFECT_JP")

        # 6. LYRICAL_JP (Liryka emocjonalna, melancholia)
        dyn9_high_pat = re.compile(
            r"\b(?:namida|sayonara|sabishii|kanashii)\b",
            re.IGNORECASE
        )
        dyn9_support_pat = re.compile(
            r"\b(?:natsukashii|itoshii)\b",
            re.IGNORECASE
        )
        if dyn9_high_pat.search(full_text) or any(tok in jp_lower for tok in ["涙", "さようなら", "さよなら", "寂しい", "悲しい"]):
            categories.add("LYRICAL_HIGH_JP")
            categories.add("LYRICAL_JP")
        if dyn9_support_pat.search(full_text) or any(tok in jp_lower for tok in ["懐かしい", "愛しい"]):
            categories.add("LYRICAL_SUPPORT_JP")
            categories.add("LYRICAL_JP")

        # 7. CULTURE_JP (Realia kulturowe, humor, kalambury)
        jp_culture_pat = re.compile(
            r"\b(?:tsukkomi|boke|neta|gyagu|dajare|bento|onigiri|ramen|udon|soba|tempura|sushi|sake|mochi|takoyaki|okonomiyaki|kotatsu|yukata|kimono|giongo|gitaigo)\b",
            re.IGNORECASE
        )
        jp_culture_tokens = ["ツッコミ", "ボケ", "ネタ", "ギャグ", "駄洒落", "弁当", "おにぎり", "ラーメン", "うどん", "そば", "天ぷら", "寿司", "酒", "餅", "たこ焼き", "お好み焼き", "こたつ", "浴衣", "着物"]
        if jp_culture_pat.search(full_text) or any(tok in jp_lower for tok in jp_culture_tokens):
            categories.add("CULTURE_JP")

        # 8. AISATSU_JP
        if "tadaima" in full_text or "ただいま" in jp_lower:
            categories.add("AISATSU_JP")

        # 9. SEIYU_SOVEREIGNTY_JP
        jp_seiyu_pat = re.compile(
            r"\b(?:urusai|urusee|ussee|damare|tadaima)\b",
            re.IGNORECASE
        )
        jp_seiyu_tokens = ["うるさい", "うるせえ", "うっせえ", "黙れ", "ただいま"]
        if jp_seiyu_pat.search(full_text) or any(tok in jp_lower for tok in jp_seiyu_tokens):
            categories.add("SEIYU_SOVEREIGNTY_JP")

        # 10. CODE_SWITCH_EN (Code-switching JA+EN w dialogu japońskim)
        jp_codeswitch_pat = re.compile(
            r"(?:[ァ-ヶー]{4,}(?:します|した|して|する)|オーケーオッケ|オッケーオッケ|テンション上げ|\b(?:rifurekuto\s*shimasu|tenshon\s*age|ookee\s*okkee|ookeeokke)\b)",
            re.IGNORECASE
        )
        excluded_loanwords = ("クリア", "装備", "ガード", "チェック", "スタート", "セーブ", "ロード", "スキップ")
        if jp_codeswitch_pat.search(jp_lower) or jp_codeswitch_pat.search(en_lower):
            matched_str = ""
            m_jp = jp_codeswitch_pat.search(jp_lower)
            if m_jp:
                matched_str = m_jp.group(0)
            else:
                m_en = jp_codeswitch_pat.search(en_lower)
                if m_en:
                    matched_str = m_en.group(0)
            if not any(excl in matched_str for excl in excluded_loanwords):
                categories.add("CODE_SWITCH_EN")

        return categories
