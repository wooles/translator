# Project: Core Engine Parallel Architecture Squad (Standard 3.0)

## Architecture
The AVT Pipeline core architecture enhancement operates across 5 defensive layers and 4 pillars:
- **Pillar 1 / Warstwa 1 (Acoustic & NLP Triangulation / `profiler.py` & `pipeline/character_profiler.py`)**:
  - Elimination of acoustic dead zone ($F_0 > 135\text{ Hz}$ gets weight 0.0).
  - Dependency tree isolation in `SpaCyAnaphoraDiscourseAnalyzer` (proper noun subject tracking).
  - Relational label resolving (`[Owner]'s [Relation]`).
- **Pillar 1 & 4 / Warstwa 2 (Ontology & Morphophonology / `series_memory.py`)**:
  - `EntityCategory` classification (`ANTHROPONYM`, `TOPONYM`, `CHREMATONYM`).
  - `DeclensionParadigm` expansion for Japanese CV-mora open `-e` (blocking false apostrophe) and masculine vocative/locative `-u` for stems on `-tz, -c, -dz, -cz, -sz, -rz, -ż, -sh, -ch, -k, -g, -j, -y, -l`.
  - Canonical prefix inheritance (`Young/Child/Old/etc.`).
  - Decoupling `EP_RUPTURE` from acoustic pitch.
- **Pillar 2 & 3 / Warstwa 2 & 3 (Discourse Topology & Monologue / `scene_discourse.py`)**:
  - Two-tier `is_internal_monologue()`: explicit thought brackets `( )` / `（ ）` / style override vs. italic safety gate `{\i1}`.
  - Dyadic Turn-Taking with masculine/feminine Vocative-Predicate Lock across speech turns ($\Delta t < 2.5\text{ s}$).
  - `SpeakerTurn` grouping and addressee plural detection (`addressee_number = "PLURAL"`).
- **Pillar 3 & 4 / Warstwa 3 & 4 (Egress Contract & Morphosyntactic Repair / `translator.py` & `avt_linter.py`)**:
  - Pre-generation contract injection (speaker_gender, target_gender, addressee_number, EntityCategory, DeclensionParadigm).
  - Post-generation deterministic repair of 1st and 2nd person verbal/predicate forms (`-łam -> -łem`, `nie bądź naiwna -> nie bądź naiwny`, role noun pairs `uczennicą -> uczniem`).
  - Turn-level bidirectional plural pronoun & verb harmonizer (`do ciebie -> do was`).
  - Ablative `z` protection against false instrumental `-em` on toponyms and collective groups.
- **Pillar 5 / Warstwa 5 (QA & Isomorphic Test Family / `test_system.py`)**:
  - Atomic Tests 161–166 with positive & negative double-sided assertions.

## Feature Inventory
| # | Feature | Description | Milestone | Stream / Owner |
|---|---------|-------------|-----------|----------------|
| 1 | F0 Deadzone Removal | $F_0 > 135\text{ Hz}$ receives acoustic weight 0.0 in `EpistemicAudioTriangulator` | M1 | Stream 1 (AGENT-1) |
| 2 | spaCy Dep Isolation | Anaphora resolution follows syntactic dependency tree `nsubj` preventing cross-sentence pronoun bleed | M1 | Stream 1 (AGENT-1) |
| 3 | Relational Label Resolving | `[Owner]'s [Relation]` gender inference with flashback protection against default feminization | M1 | Stream 1 (AGENT-1) |
| 4 | EntityCategory Classification | Classification into `ANTHROPONYM`, `TOPONYM`, `CHREMATONYM`; toponyms uninflected after `z` | M1 | Stream 2 (AGENT-2) |
| 5 | DeclensionParadigm CV-Mora & Vocative -u | Japanese CV-mora open `-e` blocks apostrophe; affricate/soft/hard stems receive `-u` in vocative/locative | M1 | Stream 2 (AGENT-2) |
| 6 | Age/Status Prefix Inheritance | Strip `Young/Child/Old/etc.` and inherit canon `true_gender` from base entity | M1 | Stream 2 (AGENT-2) |
| 7 | Anaphora EP_RUPTURE Decoupling | Decouple identity rupture from pitch; trigger on EN score phase transition | M1 | Stream 2 (AGENT-2) |
| 8 | Two-Tier Internal Monologue | Explicit thought brackets `( )`/`（ ）`/style override vs. strict italic `{\i1}` safety gate | M1 | Stream 3 (AGENT-3) |
| 9 | Dyadic Turn-Taking & Vocative Lock | Turn-taking addressee resolution and Vocative-Predicate Lock (`target_gender`) across turn lines | M1 | Stream 3 (AGENT-3) |
| 10 | SpeakerTurn Plural Detection | Detect `PLURAL` addressee from EN/JA/PL markers across continuous speaker turns | M1 | Stream 3 (AGENT-3) |
| 11 | Pre-Generation Contract Injection | Inject discourse and memory constraints into translation prompts | M1 | Stream 4 (AGENT-4) |
| 12 | Post-Gen 1st/2nd Person Repair | Deterministic repair for 1st & 2nd person verbs, adjectives, and predicate nouns | M1 | Stream 4 (AGENT-4) |
| 13 | Turn-Level Plural Harmonizer | Bidirectional turn-level harmonization of singular pronouns to plural (`do ciebie -> do was`) | M1 | Stream 4 (AGENT-4) |
| 14 | Ablative 'z' Protection & Toponym Polish | Prevent false `-em` on toponyms/groups after `z`; fix vocative `-tzie -> -tzu`; masculine orthography `ciency` | M1 | Stream 4 (AGENT-4) |
| 15 | Atomic Tests 161–166 | Universal test suites in `test_system.py` verifying all 6 isomorphic phenomenon families | M1 | Stream 5 (AGENT-5) |
| 16 | Adversarial & Forensic Verification | Independent adversarial review & forensic audit confirming zero regressions and clean architecture | M1 | Gate & Auditor |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Parallel Implementation Wave | Execution of Streams 1–5 by 5 parallel workers with strict file exclusivity | none | IN_PROGRESS |
| 2 | Targeted Integration Testing | Fast targeted tests (`pytest -k`) verifying Tests 161–166 (< 2s) | M1 | PLANNED |
| 3 | Adversarial Quality Gate | Dual Reviewers & Dual Challengers stress-testing against 18 AVT dimensions | M2 | PLANNED |
| 4 | Forensic Audit & Full CI/CD | Forensic AST and integrity audit + full 166/166 CI/CD run by Victory Auditor | M3 | PLANNED |

## Interface Contracts
### `profiler.py` ↔ `translator.py` / `series_memory.py`
- `EpistemicAudioTriangulator.triangulate_epistemic_gender(median_f0, ...)`: Returns acoustic weight 0.0 when $F_0 > 135\text{ Hz}$.
- `SpaCyAnaphoraDiscourseAnalyzer.resolve_pronoun_reference(...)`: Respects dependency tree `nsubj` boundary.
- `resolve_relational_actor(actor_name)`: Returns `(base_name, relation_type, inferred_gender, confidence)`.

### `series_memory.py` ↔ `scene_discourse.py` / `translator.py`
- `EntityCategory`: Enum with `ANTHROPONYM`, `TOPONYM`, `CHREMATONYM`.
- `CharacterIdentity`: Maintains `entity_category`, `declension_paradigm`, inherited `true_gender`.
- `DeclensionParadigm.get_vocative(name)`: Produces `-u` for stems on `-tz`, `-c`, `-dz`, `-cz`, `-sz`, `-rz`, `-ż`, `-sh`, `-ch`, `-k`, `-g`, `-j`, `-y`, `-l`; no apostrophe on Japanese CV-mora open `-e`.

### `scene_discourse.py` ↔ `translator.py` / `avt_linter.py`
- `is_internal_monologue(line, target_speaker, style)`: Two-tier evaluation returning boolean.
- `SpeakerTurn`: Container for continuous speaker lines ($\Delta t < 2.5\text{ s}$) with `addressee_number: "SINGULAR" | "PLURAL" | "DUAL"`, `target_speaker`, `target_gender`.
- `resolve_turn_addressee(turn, previous_turn)`: Dyadic turn-taking and vocative-predicate lock.

### `translator.py` / `avt_linter.py`
- Pre-generation prompt injection: passes `speaker_gender`, `target_gender`, `addressee_number`, `EntityCategory`.
- Post-generation repair: deterministic single-token and predicate transformation functions.

## Code Layout (Strict File Exclusivity)
- Stream 1 (AGENT-1): `profiler.py`, `pipeline/character_profiler.py` (exclusive write).
- Stream 2 (AGENT-2): `series_memory.py` (exclusive write).
- Stream 3 (AGENT-3): `scene_discourse.py` (exclusive write).
- Stream 4 (AGENT-4): `translator.py`, `avt_linter.py` (exclusive write).
- Stream 5 (AGENT-5): `test_system.py` (exclusive write).
- Quality Gate (Reviewers / Challengers / Auditor): Read-only on source files, writes to their respective `.agents/teamwork/` metadata directories.
