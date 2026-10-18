import ast, os, re, sys
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


FILES_TO_AUDIT = [
    "translator.py", "avt_linter.py", "series_memory.py",
    "scene_discourse.py", "profiler.py", "metadata.py",
    "rules.py", "verifier.py", "whisper_disambiguator.py"
]

RULE_AND_PROMPT_FILES = ["rules.py", "profiler.py", "translator.py", "verifier.py", "metadata.py"]
LOGIC_FILES = ["avt_linter.py", "series_memory.py", "scene_discourse.py", "translator.py", "profiler.py"]

# Bramka 2: Wprowadzanie przykładów nazewniczych (np. [Nazwa])
RE_EXEMPLAR_INTRODUCERS = re.compile(
    r"\b(?:np\.|na\s+przykład|przykładowo|takich\s+jak|takie\s+jak|jak\s+np\.)\s*['\"]?([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźżōū]+(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźżōū]+)*)",
    re.IGNORECASE
)

# Bramka 3: Cytowane zawołania i zdania przykładowe w plikach reguł i promptów
RE_QUOTED_EXEMPLARY_SPEECH = re.compile(
    r"""["'][A-ZĄĆĘŁŃÓŚŹŻ][^"'\n]{1,50}[!\?]["']"""
)

# Bramka 4: Etykiety kontrastowe, strzałki wariantów i znaczniki [OK] / [X]
RE_CONTRASTIVE_LABELS = re.compile(
    r"\b(?:BŁĄD(?:\s*\[X\])?|KOSZMARNY\s+BŁĄD|POPRAWNIE|POPRAWNY\s+KANON|KOREKTA|ZŁE\s+TŁUMACZENIE)\b|\[X\]|\[OK\]|->\s*(?:POPRAWNIE|KANON|Wariant|wariant)",
    re.IGNORECASE
)

# Bramka 5A: Krzyczące słowa ALL-CAPS w tekście (case-sensitive)
RE_SCREAMING_CAPS = re.compile(
    r"\b(?:ODMIENIAMY|PRZYJMUJĄ\s+KOŃCÓWKĘ|KOŃCÓWKĘ\s+WOŁACZA|WOŁACZU\b|SAMO\s+IMIĘ|RODZAJ\s+ŻEŃSKI|RODZAJ\s+MĘSKI)\b"
)

# Bramka 5B: Preskryptywne nakazy i zakazy (case-insensitive)
RE_PRESCRIPTIVE_IMPERATIVES = re.compile(
    r"\b(?:BEZWZGLĘDN(?:IE|Y|A|E)|KATEGORYCZN(?:IE|Y)|ZAKAZ\b|NIE\s+WOLNO|STOP\s+KALKOM|MUSI(?:SZ)?\s+BEZWZGLĘDNIE|"
    r"ŻELAZN(?:Y|A|E)\s+(?:WYMÓG|ZASAD[A-Z]*|REGUŁ[A-Z]*))\b|->\s*(?:Zastąp|Popraw|Zamień|Stosuj)",
    re.IGNORECASE
)

# Bramka 6: Alarmy i emotikony ostrzegawcze
RE_ALARMS = re.compile(r"\[(?:🚨|⚡|🎬|ℹ️|🎯|🎙️)?\s*ALARM[^\n\]]*\]|🚨")

# Bramka 7: Hardkodowane slugi serii
RE_HARDCODED_SLUGS = re.compile(
    r"""(?:slug\s*==\s*["'][^"']+["']|\bin\s+self\.slug\b|\banime_slug\s*==)""",
    re.IGNORECASE
)

# Bramka 10: Artefakty kolizji edycyjnych NumPy/DSP (_np.)
RE_DSP_GLITCH = re.compile(r"\b_np\.(?:ndarray|mean|var|std|median|array)\b")

ALLOWED_AST_LITERALS = {
    "MALE", "FEMALE", "UNKNOWN", "VIRILE", "NON_VIRILE", "AMBIGUOUS",
    "ANTHROPONYM", "TOPONYM", "CHREMATONYM", "INDIVIDUAL", "COLLECTIVE", "TITLE_CARD",
    "DEFAULT", "MAIN", "SIGN", "THOUGHT", "ITALICS", "NARRATOR"
}

violations = {
    "ast_syntax": [],
    "exemplar_introducers": [],
    "quoted_speech": [],
    "contrastive_labels": [],
    "screaming_caps": [],
    "prescriptive_imperatives": [],
    "alarms": [],
    "hardcoded_slugs": [],
    "ast_hardcoded_name_sets": [],
    "ast_inflection_kludges": [],
    "dsp_glitches": [],
    "strict_domain_defaults": []
}

def is_inflection_paradigm_string(s: str) -> bool:
    """Wykrywa ciągi typu 'x xa xowi xem' przekazywane do .split()."""
    tokens = [t.strip().lower() for t in s.split() if t.strip().isalpha() and len(t.strip()) >= 4]
    if len(tokens) < 3 or len(tokens) > 8:
        return False
    prefix = tokens[0][:4]
    return all(t.startswith(prefix) for t in tokens) and len(set(tokens)) >= 3

for fname in FILES_TO_AUDIT:
    if not os.path.exists(fname):
        continue

    with open(fname, "r", encoding="utf-8", errors="replace") as f:
        src = f.read()

    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        violations["ast_syntax"].append((fname, e.lineno, "SyntaxError", e.msg))
        continue

    for idx, line in enumerate(src.splitlines(), 1):
        if "ZERO-LITERAL" in line or "POSITIVE DOMAIN" in line or "Standard 9.0" in line:
            continue
        if m := RE_EXEMPLAR_INTRODUCERS.search(line):
            violations["exemplar_introducers"].append((fname, idx, m.group(0), line.strip()))
        if m := RE_CONTRASTIVE_LABELS.search(line):
            violations["contrastive_labels"].append((fname, idx, m.group(0), line.strip()))
        if m := RE_SCREAMING_CAPS.search(line):
            violations["screaming_caps"].append((fname, idx, m.group(0), line.strip()))
        if m := RE_PRESCRIPTIVE_IMPERATIVES.search(line):
            violations["prescriptive_imperatives"].append((fname, idx, m.group(0), line.strip()))
        if m := RE_ALARMS.search(line):
            violations["alarms"].append((fname, idx, m.group(0), line.strip()))
        if m := RE_HARDCODED_SLUGS.search(line):
            violations["hardcoded_slugs"].append((fname, idx, m.group(0), line.strip()))
        if m := RE_DSP_GLITCH.search(line):
            violations["dsp_glitches"].append((fname, idx, m.group(0), line.strip()))
        if fname in RULE_AND_PROMPT_FILES:
            if m := RE_QUOTED_EXEMPLARY_SPEECH.search(line):
                violations["quoted_speech"].append((fname, idx, m.group(0), line.strip()))

    if fname in LOGIC_FILES:
        for node in ast.walk(tree):
            # Bramka 8: Statyczne kolekcje imion pisanych wielką literą
            if isinstance(node, (ast.List, ast.Set, ast.Tuple)):
                str_elts = [elt.value for elt in node.elts if isinstance(elt, ast.Constant) and isinstance(elt.value, str)]
                suspicious = [
                    s for s in str_elts
                    if s and s[0].isupper() and s.isalpha() and s.upper() not in ALLOWED_AST_LITERALS and len(s) > 2
                ]
                if len(suspicious) >= 2:
                    violations["ast_hardcoded_name_sets"].append(
                        (fname, getattr(node, "lineno", 1), f"Kolekcja: {suspicious[:4]}", "Statyczna kolekcja instancji w AST")
                    )

            # Bramka 9: Wykrywanie ręcznych łat deklinacyjnych (.split() na paradygmatach lub variants.update)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "split" and isinstance(node.func.value, ast.Constant) and isinstance(node.func.value.value, str):
                    if is_inflection_paradigm_string(node.func.value.value):
                        violations["ast_inflection_kludges"].append(
                            (fname, getattr(node, "lineno", 1), node.func.value.value[:35], "Ręczny ciąg odmian przekazywany do .split()")
                        )
                if node.func.attr == "update" and isinstance(node.func.value, ast.Name) and node.func.value.id == "variants":
                    if node.args and isinstance(node.args[0], (ast.Set, ast.List, ast.Tuple, ast.GeneratorExp)):
                        violations["ast_inflection_kludges"].append(
                            (fname, getattr(node, "lineno", 1), "variants.update(...)", "Ręczne wstrzykiwanie zbioru odmian")
                        )

            # Bramka 11: Wymóg strict_positive_domain=True jako wartości domyślnej
            if fname == "avt_linter.py" and isinstance(node, ast.FunctionDef) and node.name in [
                "lint_and_fix_line", "audit_and_fix_entire_episode", "lint_subtitles"
            ]:
                for arg, default in zip(reversed(node.args.args), reversed(node.args.defaults)):
                    if arg.arg == "strict_positive_domain" and not (isinstance(default, ast.Constant) and default.value is True):
                        violations["strict_domain_defaults"].append((fname, node.lineno, node.name, "Domyślna wartość != True"))

total = sum(len(v) for v in violations.values())

gates = [
    ("Bramka 1: Składnia i integralność AST", "ast_syntax"),
    ("Bramka 2: Zakaz instancji (np. [Nazwa])", "exemplar_introducers"),
    ("Bramka 3: Zakaz cytowanych dialogów w regułach", "quoted_speech"),
    ("Bramka 4: Zakaz etykiet kontrastowych i '[OK]'", "contrastive_labels"),
    ("Bramka 5A: Zakaz słów ALL-CAPS w tekście", "screaming_caps"),
    ("Bramka 5B: Zakaz preskryptywności i zakazów", "prescriptive_imperatives"),
    ("Bramka 6: Zakaz alarmów w promptach i kodzie", "alarms"),
    ("Bramka 7: Zakaz zahardkodowanych slugów serii", "hardcoded_slugs"),
    ("Bramka 8: Zakaz statycznych kolekcji nazw w AST", "ast_hardcoded_name_sets"),
    ("Bramka 9: Zakaz ręcznych łat odmian (variants.update)", "ast_inflection_kludges"),
    ("Bramka 10: Czystość kodu DSP/NumPy (brak _np.)", "dsp_glitches"),
    ("Bramka 11: Wymóg default strict_positive_domain=True", "strict_domain_defaults"),
]

print("\n" + "=" * 92)
print("🛡️  CERTYFIKACJA ARCHITEKTURY: ZERO-LITERAL & INSTANCE-FREE METALINGUISTIC (STANDARD 9.0)")
print("=" * 92)

for title, key in gates:
    items = violations[key]
    status = "[PASS] Czysto" if not items else f"[REJECT] ({len(items)} naruszeń)"
    print(f"{status:<32} | {title}")
    for it in items[:4]:
        print(f"   -> {it[0]}:L{it[1]} [{it[2]}]: {it[3][:85]}")
    if len(items) > 4:
        print(f"   ... oraz {len(items) - 4} dalszych wystąpień.")

print("\n" + "=" * 92)
if total == 0:
    print("🏆 WERDYKT: [100% CZYSTY I ZGODNY Z STANDARDEM 9.0 — ZERO INSTANCJI I ZERO ŁAT]")
    sys.exit(0)
else:
    print(f"🚨 WERDYKT: [WYKRYTO {total} STRUKTURALNYCH NARUSZEŃ]")
    sys.exit(1)
