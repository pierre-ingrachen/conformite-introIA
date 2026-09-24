"""Noyau (stdlib uniquement) : collecte du projet, appel OpenAI, moteur de décision AI Act / RGPD.

Principe : le LLM ne fait qu'EXTRAIRE des faits avec preuve (fichier cité). Les conclusions (statut AI Act,
obligations, constats RGPD, verdict) sont calculées ici, de façon déterministe, d'après le flowchart FLI et la grille CNIL.
"""
import io, json, os, re, subprocess, urllib.request, urllib.error, zipfile
from pathlib import Path

KB = Path(__file__).resolve().parent.parent / "kb"
TOTAL, MAX_OUT, MARGIN = 50_000, 3500, 0.05
FILE_CAP, TREE_CAP, MAX_FILE_BYTES, MAX_ZIP = 2500, 1200, 200_000, 30_000_000


# ───────────────────────── tokens (estimation pessimiste : ~3 car./token, tiktoken absent sur Vercel)
def count(s): return len(s) // 3 + 1
def cut(s, n): return s[: n * 3]


# ───────────────────────── schéma des faits extraits par le LLM
B = "bool"
ENUMS = {
    "roles": ["provider", "deployer", "distributor", "importer", "product_manufacturer"],
    "annex3": ["biometrics", "critical_infrastructure", "education", "employment", "essential_services",
               "law_enforcement", "migration_border", "justice_democracy"],
    "hr5": ["narrow_procedural", "improves_prior_human_result", "detects_patterns_no_influence", "preparatory_task"],
    "excl": ["military", "third_country_public_authority", "research_only", "open_source", "personal_use"],
    "prohib": ["subliminal_manipulation", "exploiting_vulnerabilities", "biometric_categorisation", "social_scoring",
               "predictive_policing", "facial_recognition_scraping", "emotion_recognition_work_school", "realtime_remote_biometric"],
    "transp": ["interacts_with_people", "synthetic_content", "emotion_or_biometric_categorisation", "deepfake_or_public_interest_text"],
    "pdata": ["identity_contact", "birth_age", "nationality_ethnic", "health", "biometric", "political_religious_union",
              "criminal", "location", "financial", "employment_cv", "children", "online_identifiers", "other"],
    "annex1": ["none", "section_a", "section_b"],
}
FACTS = {  # clé: (type, description courte FR — sert aussi de libellé « à vérifier »)
    "is_ai_system": (B, "Le projet est/contient un système d'IA (modèle ML, LLM, API d'IA appelée)"),
    "roles": ("roles", "Rôle(s) du porteur du projet. Produit commercialisé sous son nom, construit sur une API/modèle tiers => provider. Développer/assembler un système (même sur un modèle tiers) et le mettre en service sous son nom, y compris pour ses propres clients => provider (et deployer s'il l'utilise lui-même). Simple usage interne d'un outil IA acheté tel quel => deployer. Un éditeur qui vend son système à des clients est provider seulement : ses clients sont les deployers, ne les liste pas"),
    "repurposes_third_party_ai": (B, "Met son nom/sa marque sur une IA tierce, change sa destination ou la modifie substantiellement"),
    "annex1": ("annex1", "IA composant de sécurité d'un produit réglementé (annexe I : section_a machines/jouets/médical/radio…, section_b auto/aviation/rail/marine)"),
    "third_party_conformity": (B, "Le produit annexe I A exige une évaluation de conformité par un tiers"),
    "annex3": ("annex3", "Domaines d'usage haut risque de l'annexe III"),
    "profiling_of_persons": (B, "Profilage de personnes physiques (évaluation automatisée d'aspects personnels)"),
    "hr5_exceptions": ("hr5", "Exceptions art. 6(3) applicables (tâche procédurale étroite, amélioration d'un travail humain, détection de schémas sans influence, tâche préparatoire)"),
    "placed_on_eu_market": (B, "Le système est mis sur le marché/en service dans l'UE"),
    "established_in_eu": (B, "Le porteur est établi/situé dans l'UE"),
    "output_used_in_eu": (B, "Les sorties du système sont utilisées dans l'UE"),
    "gpai_model_provider": (B, "Le projet fournit un modèle d'IA à usage général (pas un simple usage d'une API)"),
    "gpai_systemic_risk": (B, "Ce modèle dépasse 10^25 FLOP ou est désigné à risque systémique"),
    "exclusions": ("excl", "Exclusions art. 2, UNIQUEMENT si le projet le déclare explicitement (jamais déduites d'un hébergement ou d'une API aux États-Unis)"),
    "prohibited_practices": ("prohib", "Pratiques interdites art. 5, seulement si la définition stricte est remplie : subliminal_manipulation=techniques subliminales/manipulatrices causant un préjudice ; exploiting_vulnerabilities=exploiter l'âge/handicap/situation sociale ; biometric_categorisation=déduire des attributs sensibles (origine, opinions, religion, orientation) à partir de données BIOMÉTRIQUES (visage, voix), pas à partir d'un CV ou d'un texte ; social_scoring=notation générale du comportement social menant à un traitement défavorable dans un autre contexte ; predictive_policing=prédire une infraction par le seul profilage ; facial_recognition_scraping=constituer des bases faciales par moissonnage ; emotion_recognition_work_school=inférer les émotions au travail/à l'école ; realtime_remote_biometric=identification biométrique à distance en temps réel dans l'espace public. Le tri de candidats ou le scoring de crédit est un HAUT RISQUE, pas une pratique interdite"),
    "transparency_triggers": ("transp", "Déclencheurs de transparence art. 50"),
    "public_body_or_public_service": (B, "Le déployeur est un organisme public ou une entité privée fournissant un service public"),
    "human_oversight_present": (B, "Contrôle/revue humaine prévu sur les sorties de l'IA"),
    "ai_risk_management_documented": (B, "Gestion des risques / documentation technique de l'IA"),
    "ai_logging_traceability": (B, "Journalisation/traçabilité des décisions de l'IA"),
    "users_informed_of_ai_use": (B, "Les utilisateurs/personnes sont informés qu'une IA est utilisée"),
    "personal_data_categories": ("pdata", "Catégories de données personnelles traitées ([] = aucune)"),
    "large_scale": (B, "Traitement à grande échelle"),
    "vulnerable_persons": (B, "Personnes vulnérables concernées (enfants, salariés, candidats, patients)"),
    "systematic_monitoring": (B, "Surveillance systématique de personnes"),
    "automated_decision_legal_effect": (B, "Décision automatisée à effet juridique ou significatif (ex. rejet automatique)"),
    "human_review_before_decision": (B, "Intervention humaine avant la décision finale"),
    "transfers_outside_eu": (B, "Données envoyées hors UE/EEE (ex. API hébergée aux États-Unis)"),
    "transfer_safeguards_documented": (B, "Garanties de transfert documentées (DPF, clauses types)"),
    "third_party_processors": (B, "Recours à des sous-traitants (hébergeur, API tierce)"),
    "processor_contracts_documented": (B, "Contrats de sous-traitance art. 28 / DPA documentés"),
    "training_data_personal": (B, "Des données personnelles servent à entraîner/affiner/évaluer le modèle"),
    "legal_basis_documented": (B, "Base légale documentée"),
    "privacy_notice_present": (B, "Information des personnes (mentions, politique de confidentialité)"),
    "rights_mechanism_present": (B, "Mécanisme d'exercice des droits (accès, effacement…)"),
    "retention_policy_documented": (B, "Durées de conservation définies"),
    "security_measures_present": (B, "Mesures de sécurité (contrôle d'accès, chiffrement, secrets protégés)"),
    "breach_procedure_documented": (B, "Procédure de gestion des violations de données"),
    "dpia_documented": (B, "AIPD réalisée/documentée"),
    "dpo_or_privacy_contact": (B, "DPO ou contact protection des données identifié"),
    "records_of_processing_documented": (B, "Registre des traitements"),
    "data_minimisation_concern": (B, "Collecte de données manifestement non nécessaires à la finalité"),
}
MATURITY = ["procedures", "gouvernance", "registre", "conformite", "formation", "droits", "securite", "violations"]
CORE = ["is_ai_system", "roles", "annex3", "profiling_of_persons", "prohibited_practices", "personal_data_categories",
        "legal_basis_documented", "privacy_notice_present", "security_measures_present", "transfers_outside_eu",
        "third_party_processors", "retention_policy_documented", "rights_mechanism_present", "human_oversight_present"]


def response_schema():
    def fact(t):
        v = {"type": ["boolean", "null"]} if t == B else \
            {"anyOf": [{"type": "array", "items": {"type": "string", "enum": ENUMS[t]}}, {"type": "null"}]}
        return {"type": "object", "properties": {"v": v, "e": {"type": ["string", "null"]}},
                "required": ["v", "e"], "additionalProperties": False}
    facts = {k: {**fact(t), "description": d} for k, (t, d) in FACTS.items()}
    mat = {k: {"type": "object", "properties": {"level": {"type": ["integer", "null"]}, "e": {"type": ["string", "null"]}},
               "required": ["level", "e"], "additionalProperties": False} for k in MATURITY}
    obj = lambda p: {"type": "object", "properties": p, "required": list(p), "additionalProperties": False}
    return obj({"facts": obj(facts), "maturity": obj(mat),
                "missing_info": {"type": "array", "items": {"type": "string"}}})


# ───────────────────────── base de connaissances (extraits envoyés au LLM)
AI_IDS = {"ai_act.definition", "ai_act.E1", "ai_act.HR2", "ai_act.HR4", "ai_act.HR5", "ai_act.R2", "ai_act.R3", "ai_act.R4"}


def kb_text():
    out = []
    for f in sorted(KB.glob("*.md")):
        text = re.sub(r"<!--.*?-->", "", f.read_text(encoding="utf-8"), flags=re.S)
        for part in re.split(r"^## ", text, flags=re.M)[1:]:
            head, _, body = part.partition("\n")
            cid = head.split("|")[0].strip()
            if f.stem == "ai_act" and cid not in AI_IDS: continue
            if cid == "rgpd.references": continue
            body = "\n".join(l for l in body.splitlines() if not l.startswith(("mots-clés:", "source:")))
            out.append(f"## {head.strip()}\n{body.strip()}")
    return "\n".join(out)


SYSTEM = """Tu es un extracteur de faits pour un audit de conformité AI Act / RGPD. Tu ne rends AUCUN avis juridique : \
les décisions sont calculées ailleurs. Remplis le schéma d'après UNIQUEMENT les fichiers du projet fournis ; la base de \
connaissances sert de définitions.
Règles :
- "e" (preuve) = "chemin/exact/du/fichier: extrait ou paraphrase ≤ 15 mots", avec le chemin EXACT d'un fichier fourni.
- v=true (ou liste non vide) exige une preuve positive dans un fichier. Sans preuve : v=null.
- v=false = absence constatée : seulement si le projet paraît assez couvert pour l'affirmer (ou s'il le dit explicitement), sinon null. e="absent" est accepté.
- Listes : [] = tu as examiné le projet et rien ne s'applique (aucune preuve requise) ; null = impossible à évaluer. Si le projet est décrit assez précisément pour trancher, réponds [] plutôt que null.
- Ne devine pas. Un modèle/une API appelée par le code (openai, transformers, sklearn…) prouve un système d'IA.
- Maturité CNIL : level 1 à 5 seulement si un fichier prouve la pratique (politique, procédure, registre…). Le code seul ne prouve pas une organisation : null. N'emploie jamais 0 : une absence de mention n'est pas une preuve d'absence.
- Pour les faits « hors champ » (is_ai_system=false, aucun lien UE), exige une déclaration explicite du projet, sinon null.
- missing_info : au plus 6 questions précises à poser au porteur pour lever les incertitudes décisives.
"""


# ───────────────────────── collecte du projet
SKIP_PARTS = {"node_modules", "vendor", "dist", "build", ".git", "__pycache__", ".venv", "venv", "test", "tests", "__tests__", "kb"}
SKIP_NAMES = re.compile(r"(^\.env|\.pem$|\.key$|id_rsa|lock\.json$|\.lock$|package-lock|\.min\.|secret|credential|\.svg$)", re.I)
TEXT_EXT = {".md", ".rst", ".txt", ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".kt", ".go", ".rs", ".rb", ".php", ".cs",
            ".sql", ".yml", ".yaml", ".toml", ".json", ".ini", ".cfg", ".html", ".prisma", ".proto", ".graphql", ".ipynb"}
SECRET = re.compile(r"(sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|(?i:(password|passwd|secret|token|api[_-]?key)\s*[=:]\s*)['\"][^'\"\n]{6,}['\"])")


def priority(path):
    p = Path(path); n, s = p.name.lower(), path.lower()
    if re.search(r"(privacy|confidential|rgpd|gdpr|dpia|aipd|dpa|consent|security|compliance)", s): return 0
    if n.startswith("readme") or s.startswith("docs/") or p.suffix in {".md", ".rst"}: return 1
    if n in {"requirements.txt", "pyproject.toml", "package.json", "pom.xml", "go.mod", "cargo.toml", "dockerfile",
             "docker-compose.yml", "docker-compose.yaml"}: return 2
    if re.search(r"(model|schema|migration|openapi|swagger|config|settings|user|auth|data|score|predict|train|llm|ai)", s) \
            or p.suffix in {".sql", ".prisma", ".proto"}: return 3
    return 4


def load_local(root):
    root = Path(root).resolve()
    try:
        out = subprocess.run(["git", "-C", str(root), "ls-files"], capture_output=True, text=True, check=True).stdout
        names = out.splitlines()
    except Exception:
        names = [str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()]
    return root.name, [(n, (root / n).stat().st_size, (lambda n=n: (root / n).read_text(encoding="utf-8")))
                       for n in names if (root / n).is_file()]


def load_github(url):
    m = re.match(r"^https://github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?(?:/tree/([\w./-]+))?/?$", url.strip())
    if not m: raise ValueError("URL GitHub attendue : https://github.com/proprietaire/depot")
    o, r, br = m.groups()
    ref = f"refs/heads/{br}" if br else "HEAD"
    try:
        with urllib.request.urlopen(f"https://codeload.github.com/{o}/{r}/zip/{ref}", timeout=40) as resp:
            data = resp.read(MAX_ZIP + 1)
    except urllib.error.HTTPError as e:
        raise ValueError(f"Dépôt introuvable ou privé (HTTP {e.code}).")
    if len(data) > MAX_ZIP: raise ValueError(f"Dépôt trop volumineux (> {MAX_ZIP // 1_000_000} Mo).")
    z = zipfile.ZipFile(io.BytesIO(data))
    ents = []
    for i in z.infolist():
        if i.is_dir(): continue
        rel = i.filename.split("/", 1)[-1]
        ents.append((rel, i.file_size, (lambda i=i: z.read(i).decode("utf-8"))))
    return r, ents


def load_doc(text, name="documentation"):
    return name, [("doc", len(text), lambda: text)]


def collect(entries, budget):
    ok = lambda n: (n == "doc" or (not (set(Path(n).parts) & SKIP_PARTS) and not SKIP_NAMES.search(Path(n).name)
                    and (Path(n).suffix.lower() in TEXT_EXT or Path(n).name.lower() in {"dockerfile", "readme"})))
    ents = [e for e in entries if ok(e[0])]
    tree = cut("\n".join(sorted(e[0] for e in ents)), TREE_CAP)
    budget -= count(tree)
    parts, paths, skipped, trunc = [], [], 0, 0
    for n, size, read in sorted(ents, key=lambda e: (priority(e[0]), e[1])):
        if size > MAX_FILE_BYTES: skipped += 1; continue
        try: text = SECRET.sub("[REDACTED]", read())
        except Exception: skipped += 1; continue
        if not text.strip(): continue
        if count(text) > FILE_CAP: text = cut(text, FILE_CAP) + "\n[... tronqué ...]"; trunc += 1
        block = f"### {n}\n{text}\n"
        if count(block) > budget: skipped += 1; continue
        parts.append(block); paths.append(n); budget -= count(block)
    return {"tree": tree, "content": "".join(parts), "paths": paths, "total": len(ents), "skipped": skipped, "truncated": trunc}


# ───────────────────────── appel OpenAI
def call_openai(model, user, api_key):
    body = {"model": model, "max_completion_tokens": MAX_OUT,
            "response_format": {"type": "json_schema", "json_schema": {"name": "facts", "strict": True, "schema": response_schema()}},
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]}
    if model.startswith("gpt-4"): body["temperature"] = 0
    req = urllib.request.Request("https://api.openai.com/v1/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"})
    try:
        with urllib.request.urlopen(req, timeout=55) as r: resp = json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Erreur API OpenAI {e.code}: {e.read().decode()[:300]}")
    ch = resp["choices"][0]
    if ch["finish_reason"] != "stop": raise RuntimeError(f"Réponse incomplète ({ch['finish_reason']}).")
    return json.loads(ch["message"]["content"]), resp["usage"]


# ───────────────────────── validation des preuves (anti-hallucination)
def _has_path(e, paths):
    if not e: return False
    head = e.split(":", 1)[0]
    for p in re.split(r"[,;]", head):
        p = p.strip().lstrip("./")
        if len(p) > 1 and any(x == p or x.endswith("/" + p) for x in paths): return True
    return False


def validate(raw, paths):
    facts, unsupported = {}, []
    for k, (t, _) in FACTS.items():
        d = (raw.get("facts") or {}).get(k) or {}
        v, e = d.get("v"), d.get("e")
        positive = v is True or (isinstance(v, list) and len(v) > 0)
        if positive and not _has_path(e, paths):
            unsupported.append(k); v = None
        if isinstance(v, list): v = [x for x in v if x in ENUMS[t]]
        facts[k] = {"v": v, "e": e if v is not None else None}
    mat = {}
    for k in MATURITY:
        d = (raw.get("maturity") or {}).get(k) or {}
        lv, e = d.get("level"), d.get("e")
        if lv == 0: lv = None                      # « rien n'est fait » ne se prouve pas depuis un dépôt
        elif lv is not None and (not isinstance(lv, int) or not 1 <= lv <= 5 or not _has_path(e, paths)):
            unsupported.append("maturity." + k); lv = None
        mat[k] = {"level": lv, "e": e if lv is not None else None}
    return facts, mat, unsupported, [str(x) for x in (raw.get("missing_info") or [])][:6]


# ───────────────────────── moteur AI Act (flowchart FLI)
LABELS = {"prohibited": "Interdit (art. 5)", "excluded": "Hors AI Act (exclusion art. 2)", "out_of_scope": "Hors champ",
          "high_risk": "Haut risque", "high_risk_sectoral": "Haut risque – régime sectoriel (annexe I B)",
          "not_high_risk_registered": "Non haut risque (art. 6(3)) – à enregistrer", "minimal": "Risque minimal / limité",
          "undetermined": "Indéterminé"}
PROVIDER_HR = [("art. 16", "Obligations du fournisseur"), ("art. 9", "Système de gestion des risques"),
               ("art. 10", "Gouvernance des données d'entraînement/validation"), ("art. 11-12", "Documentation technique et journalisation"),
               ("art. 13-14", "Transparence envers les déployeurs et contrôle humain"), ("art. 15", "Exactitude, robustesse, cybersécurité"),
               ("art. 17", "Système de gestion de la qualité"), ("art. 43, 47-49", "Évaluation de conformité, déclaration UE, marquage CE, enregistrement UE"),
               ("art. 72-73", "Surveillance après commercialisation, signalement des incidents graves")]
DEPLOYER_HR = [("art. 26", "Usage conforme à la notice, contrôle humain par des personnes compétentes, surveillance, conservation des logs ≥ 6 mois, information des travailleurs et des personnes concernées"),
               ("art. 86", "Droit à une explication d'une décision individuelle")]
NOTES_TIMELINE = "Calendrier : pratiques interdites et AI Literacy applicables depuis le 2/02/2025, GPAI depuis le 2/08/2025 ; obligations haut risque annexe III prévues au 2/08/2026 (un report est en discussion : vérifier le texte en vigueur)."


def decide_ai(f):
    g = lambda k: f[k]["v"]
    path, unk, obl, notes = [], [], [], [NOTES_TIMELINE]
    step = lambda s, a, w="": path.append({"step": s, "answer": a, "why": w or ""})
    def res(status, roles=(), transparency=(), gpai=None):
        return {"status": status, "label": LABELS[status], "roles": sorted(roles), "path": path, "obligations": obl,
                "transparency": list(transparency), "gpai": gpai, "notes": notes, "unknowns": unk}
    ob = lambda ref, label: obl.append({"ref": ref, "label": label})

    ai = g("is_ai_system")
    if ai is False and f["is_ai_system"]["e"]: step("Définition", "Pas un système d'IA (art. 3(1))", f["is_ai_system"]["e"]); return res("out_of_scope")
    if ai is None or ai is False: unk.append(FACTS["is_ai_system"][1])
    else: step("Définition", "Système d'IA", f["is_ai_system"]["e"])

    nx = [g("placed_on_eu_market"), g("established_in_eu"), g("output_used_in_eu")]
    if any(x is True for x in nx): step("S1", "Dans le champ territorial (art. 2)")
    elif all(x is False for x in nx) and all(f[k]["e"] for k in ("placed_on_eu_market", "established_in_eu", "output_used_in_eu")):
        step("S1", "Aucun lien avec l'UE (déclaré)"); return res("out_of_scope")
    else: unk.append("Lien avec l'UE (marché, établissement du porteur ou usage des sorties dans l'UE)")

    ex = set(g("exclusions") or [])
    if ex & {"military", "third_country_public_authority", "research_only"}:   # jamais bloquant : une fausse exclusion serait pire qu'une fausse alerte
        notes.append("Exclusion invoquée (à confirmer par le porteur) : " + ", ".join(sorted(ex & {"military", "third_country_public_authority", "research_only"}))
                     + ". Si elle est confirmée, aucune obligation de l'AI Act ne s'applique.")

    roles = set(g("roles") or [])
    if g("repurposes_third_party_ai") is True:
        roles.add("provider"); step("E2", "Devient fournisseur (art. 25) : marque/destination/modification substantielle")
        notes.append("Le fournisseur d'origine doit vous transmettre informations et accès (handover, art. 25(2)).")
    if not roles: unk.append(FACTS["roles"][1])
    else: step("E1", "Rôle(s) : " + ", ".join(sorted(roles)), f["roles"]["e"])
    if ROLE_NOTE(roles): notes.append(ROLE_NOTE(roles))

    pr = g("prohibited_practices") or []
    if pr:
        step("R3", "Pratique(s) interdite(s) : " + ", ".join(pr), f["prohibited_practices"]["e"])
        ob("art. 5", "Système interdit : ne pas mettre sur le marché ni utiliser ; amendes jusqu'à 35 M€ ou 7 % du CA (art. 99)")
        return res("prohibited", roles)
    if g("prohibited_practices") is None: unk.append(FACTS["prohibited_practices"][1])

    # classification haut risque
    hr = None
    a1, a3 = g("annex1"), g("annex3") or []
    if a1 == "section_a":
        tp = g("third_party_conformity")
        if tp is True: hr = "high_risk"; step("HR2-HR3", "Haut risque (annexe I A + évaluation par tiers)")
        elif tp is None: unk.append(FACTS["third_party_conformity"][1])
        else: step("HR3", "Pas d'évaluation par tiers → poursuite vers HR4")
    elif a1 == "section_b":
        hr = "high_risk_sectoral"; step("HR1", "Annexe I section B")
        notes.append("Section B : régime sectoriel, seuls certains articles de l'AI Act s'appliquent (art. 2(2)) ; vérifier.")
    if hr is None and a3:
        prof = g("profiling_of_persons"); exs = g("hr5_exceptions") or []
        step("HR4", "Domaine annexe III : " + ", ".join(a3), f["annex3"]["e"])
        if prof is True: hr = "high_risk"; step("HR5", "Profilage : toujours haut risque (art. 6(3))", f["profiling_of_persons"]["e"])
        elif exs:
            if prof is None: unk.append(FACTS["profiling_of_persons"][1])
            hr = "not_high_risk_registered"; step("HR5", "Exception art. 6(3) : " + ", ".join(exs))
        else: hr = "high_risk"; step("HR5", "Aucune exception art. 6(3) démontrée → haut risque")
    if hr is None:
        if g("annex3") is None: unk.append(FACTS["annex3"][1])
        hr = "minimal"; step("HR", "Aucun cas haut risque identifié")

    prov, dep = "provider" in roles, "deployer" in roles
    if roles & {"provider", "deployer"}: ob("art. 4", "AI Literacy : former le personnel qui exploite ou utilise l'IA")
    if hr == "high_risk":
        if prov or not roles: [ob(*x) for x in PROVIDER_HR]
        if dep or not roles: [ob(*x) for x in DEPLOYER_HR]
        if "distributor" in roles: ob("art. 24", "Obligations du distributeur")
        if "importer" in roles: ob("art. 23", "Obligations de l'importateur")
        if "product_manufacturer" in roles: ob("cons. 47, 166", "Fabricant de produit (aussi fournisseur, art. 25)")
        if dep or not roles:
            if g("public_body_or_public_service") is True:
                ob("art. 27", "Analyse d'impact sur les droits fondamentaux (FRIA) avant déploiement")
            elif "essential_services" in a3:
                ob("art. 27", "FRIA à vérifier : s'applique aussi aux déployeurs de scoring de crédit / assurance (hors flowchart FLI)")
    elif hr == "not_high_risk_registered" and (prov or not roles):
        ob("art. 6(4), 49(2)", "Documenter l'évaluation « non haut risque » et enregistrer le système dans la base UE avant mise sur le marché")
    elif hr == "high_risk_sectoral": ob("art. 2(2), 102-109", "Exigences sectorielles ; vérifier la législation applicable")

    tr = list(g("transparency_triggers") or [])
    T = {"interacts_with_people": ("art. 50(1)", "Informer qu'on interagit avec une IA"),
         "synthetic_content": ("art. 50(2)", "Marquage lisible par machine des contenus synthétiques"),
         "emotion_or_biometric_categorisation": ("art. 50(3)", "Informer les personnes exposées à la reconnaissance d'émotions / catégorisation biométrique"),
         "deepfake_or_public_interest_text": ("art. 50(4)", "Signaler les deepfakes et textes d'information du public générés par IA")}
    for t in tr: ob(*T[t])
    if g("gpai_model_provider") is True:
        ob("art. 53", "Obligations des fournisseurs de modèles GPAI")
        if g("gpai_systemic_risk") is True: ob("art. 55", "Obligations GPAI à risque systémique")
    if "personal_use" in ex and not prov: notes.append("Usage personnel non professionnel : obligations du déployeur non applicables.")
    if "open_source" in ex and hr == "minimal" and not tr: notes.append("Composant open source hors champ tant qu'il n'est pas intégré à un système haut risque/interdit/GPAI/transparence.")
    status = "undetermined" if (hr == "minimal" and ai is None) else hr
    if hr == "minimal" and g("annex3") is None: notes.append("Classement « risque limité » PROVISOIRE : l'appartenance à l'annexe III n'a pas pu être établie.")
    return res(status, roles, tr, "systemic" if g("gpai_systemic_risk") else ("gpai" if g("gpai_model_provider") else None))


def ROLE_NOTE(roles):
    if roles == {"provider"}: return "Fournisseur du système : le modèle tiers (ex. OpenAI) relève du fournisseur GPAI, pas de vous."
    return ""


# ───────────────────────── moteur RGPD + verdict
SENSITIVE = {"health", "biometric", "political_religious_union", "criminal", "nationality_ethnic"}


def decide_rgpd(f, ai):
    g = lambda k: f[k]["v"]
    cats = g("personal_data_categories")
    findings, verify = [], []
    def add(sev, text, ref, k=None): findings.append({"severity": sev, "text": text, "ref": ref, "evidence": f[k]["e"] if k else None})
    def need(k): verify.append(FACTS[k][1])
    if cats is None: need("personal_data_categories"); applicable = None
    else: applicable = len(cats) > 0
    if applicable is False:
        return {"applicable": False, "findings": [], "criteria": [], "aipd_required": False, "special_categories": []}, []
    sens = sorted(set(cats or []) & SENSITIVE)
    hr_ai = ai["status"] == "high_risk"
    crit = [c for c, on in [("profilage/scoring", g("profiling_of_persons")), ("décision automatisée", g("automated_decision_legal_effect")),
                            ("surveillance systématique", g("systematic_monitoring")), ("données sensibles", bool(sens) or None),
                            ("grande échelle", g("large_scale")), ("personnes vulnérables", g("vulnerable_persons")),
                            ("technologie innovante (IA)", g("is_ai_system"))] if on is True]
    aipd = len(crit) >= 2
    if aipd and g("dpia_documented") is not True:
        add("majeur", f"AIPD probablement requise ({len(crit)} critères : {', '.join(crit)}) et non documentée.", "RGPD art. 35", "dpia_documented")
    if g("automated_decision_legal_effect") is True and g("human_review_before_decision") is not True:
        add("critique", "Décision automatisée à effet significatif sans intervention humaine démontrée.", "RGPD art. 22", "automated_decision_legal_effect")
    if sens: add("majeur", f"Catégories sensibles/proxys traitées ({', '.join(sens)}) : base légale et garanties renforcées (art. 9) ; risque de discrimination.", "RGPD art. 9",
                 "personal_data_categories")
    if g("data_minimisation_concern") is True: add("majeur", "Collecte de données non nécessaires à la finalité.", "RGPD art. 5(1)(c)", "data_minimisation_concern")
    if g("transfers_outside_eu") is True and g("transfer_safeguards_documented") is not True:
        add("majeur", "Transfert hors UE sans garanties documentées (DPF, clauses types).", "RGPD art. 44-46", "transfers_outside_eu")
    if g("third_party_processors") is True and g("processor_contracts_documented") is not True:
        add("majeur", "Sous-traitants sans contrat art. 28 documenté.", "RGPD art. 28", "third_party_processors")
    if g("legal_basis_documented") is False: add("majeur", "Aucune base légale documentée.", "RGPD art. 6")
    if g("privacy_notice_present") is False: add("majeur", "Pas d'information des personnes.", "RGPD art. 13-14")
    if g("security_measures_present") is False: add("majeur", "Aucune mesure de sécurité identifiée.", "RGPD art. 32")
    if g("rights_mechanism_present") is False: add("mineur", "Pas de mécanisme d'exercice des droits.", "RGPD art. 15-22")
    if g("retention_policy_documented") is False: add("mineur", "Durées de conservation non définies.", "RGPD art. 5(1)(e)")
    if g("records_of_processing_documented") is False: add("mineur", "Pas de registre des traitements.", "RGPD art. 30")
    if g("breach_procedure_documented") is False: add("mineur", "Pas de procédure de violation (notification 72 h).", "RGPD art. 33-34")
    if g("training_data_personal") is True and g("legal_basis_documented") is not True:
        add("majeur", "Données personnelles utilisées pour l'IA sans base légale documentée.", "RGPD art. 6", "training_data_personal")
    if aipd and ("grande échelle" in crit or sens) and g("dpo_or_privacy_contact") is False:
        add("mineur", "Aucun DPO/contact protection des données alors que le traitement est à risque.", "RGPD art. 37-38")
    # AI Act (constats liés)
    if hr_ai:
        if g("human_oversight_present") is False: add("majeur", "Contrôle humain absent sur un système à haut risque.", "AI Act art. 14, 26", "human_oversight_present")
        if g("ai_risk_management_documented") is False: add("majeur", "Gestion des risques / documentation technique absente.", "AI Act art. 9, 11")
        if g("ai_logging_traceability") is False: add("majeur", "Pas de journalisation des décisions de l'IA.", "AI Act art. 12, 26(6)")
    if ai["transparency"] and g("users_informed_of_ai_use") is False:
        add("majeur", "Utilisateurs non informés de l'usage d'une IA.", "AI Act art. 50")
    for k in ["legal_basis_documented", "privacy_notice_present", "security_measures_present", "transfers_outside_eu",
              "third_party_processors", "retention_policy_documented", "rights_mechanism_present"]:
        if g(k) is None: need(k)
    if hr_ai and g("human_oversight_present") is None: need("human_oversight_present")
    return {"applicable": applicable, "findings": findings, "criteria": crit, "aipd_required": aipd, "special_categories": sens}, verify


VERDICTS = {"interdit": "Système interdit", "non_conforme_probable": "Non conforme (probable)", "a_corriger": "À corriger",
            "plutot_conforme": "Plutôt conforme (sous réserve)", "indetermine": "Indéterminé : informations insuffisantes"}


def verdict(ai, rgpd, facts):
    if ai["status"] == "prohibited": return "interdit"
    sev = {x["severity"] for x in rgpd["findings"]}
    if "critique" in sev: return "non_conforme_probable"
    known = sum(facts[k]["v"] is not None for k in CORE)
    if known / len(CORE) < 0.5 or ai["status"] == "undetermined": return "indetermine"
    if "majeur" in sev: return "a_corriger"
    return "plutot_conforme" if facts["annex3"]["v"] is not None else "indetermine"


# ───────────────────────── orchestration
def analyze(name, entries, model="gpt-4.1-mini", api_key=None, total=TOTAL, dry_run=False):
    kb = kb_text()
    fixed = count(SYSTEM) + count(kb) + count(json.dumps(response_schema())) + 200
    budget = total - MAX_OUT - int(total * MARGIN) - fixed
    if budget < 2000: raise RuntimeError(f"Budget insuffisant pour le projet ({budget} tokens).")
    c = collect(entries, budget)
    user = f"# BASE DE CONNAISSANCES\n{kb}\n\n# PROJET : {name}\n## Arborescence\n{c['tree']}\n\n## Fichiers\n{c['content']}"
    est = count(SYSTEM) + count(json.dumps(response_schema())) + count(user)
    meta = {"model": model, "estimated_input": est, "max_output": MAX_OUT, "budget": total, "files_included": len(c["paths"]),
            "files_total": c["total"], "files_skipped": c["skipped"], "files_truncated": c["truncated"]}
    assert est + MAX_OUT <= total, "budget dépassé"
    if dry_run or not c["paths"]: return {"meta": meta, "dry_run": True}
    raw, usage = call_openai(model, user, api_key)
    meta["usage"] = usage
    facts, mat, unsupported, missing = validate(raw, c["paths"])
    ai = decide_ai(facts)
    rg, verify = decide_rgpd(facts, ai)
    known = [v["level"] for v in mat.values() if v["level"] is not None]
    rg["maturity"] = {"levels": mat, "average": round(sum(known) / len(known), 1) if known else None, "evaluated": len(known)}
    v = verdict(ai, rg, facts)
    return {"meta": meta, "verdict": v, "verdict_label": VERDICTS[v], "ai_act": ai, "rgpd": rg,
            "coverage": round(sum(facts[k]["v"] is not None for k in CORE) / len(CORE), 2),
            "facts": {k: v for k, v in facts.items() if v["v"] is not None},
            "to_verify": sorted(set(verify + ai["unknowns"])), "missing_info": missing, "unsupported_claims": unsupported,
            "disclaimer": "Analyse automatisée d'un extrait du projet, fondée sur le flowchart FLI (non officiel) et la grille CNIL. Ne constitue pas un avis juridique."}
