#!/usr/bin/env python3
"""Évalue un projet git (chemin local ou URL) vs AI Act + RGPD via l'API OpenAI.

    export OPENAI_API_KEY=sk-...
    python pipeline.py https://github.com/org/repo            # ou ./chemin/local
    python pipeline.py ./projet --dry-run                     # sans appel API : affiche le budget
Options : --model gpt-4.1-mini  --max-total 50000  --out rapport.json

Budget : entrée (consigne + KB complète + projet) + sortie <= --max-total tokens.
Un seul appel API. Stdlib uniquement (tiktoken utilisé s'il est installé, sinon estimation prudente).
"""
import argparse, json, os, re, subprocess, sys, tempfile, urllib.request, urllib.error
from pathlib import Path

from rag import load

MAX_OUT = 4000          # tokens réservés à la réponse
FILE_CAP = 3000         # tokens max par fichier
TREE_CAP = 1500         # tokens max pour l'arborescence
MAX_FILE_BYTES = 200_000

try:
    import tiktoken
    _enc = tiktoken.get_encoding("o200k_base")
    def count(s): return int(len(_enc.encode(s, disallowed_special=())) * 1.03)
    def cut(s, n): return _enc.decode(_enc.encode(s, disallowed_special=())[:n])
except Exception:       # estimation volontairement pessimiste (~3 car./token)
    def count(s): return len(s) // 3 + 1
    def cut(s, n): return s[: n * 3]

TEXT_EXT = {".md", ".rst", ".txt", ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".kt", ".go", ".rs", ".rb", ".php",
            ".cs", ".sql", ".yml", ".yaml", ".toml", ".json", ".ini", ".cfg", ".html", ".prisma", ".proto", ".graphql"}
SKIP_PARTS = {"node_modules", "vendor", "dist", "build", ".git", "__pycache__", ".venv", "venv", "test", "tests", "__tests__"}
SKIP_NAMES = re.compile(r"(^\.env|\.pem$|\.key$|id_rsa|lock\.json$|\.lock$|package-lock|\.min\.|secret|credential)", re.I)
SECRET = re.compile(r"(sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|(?i:(password|passwd|secret|token|api[_-]?key)\s*[=:]\s*)['\"][^'\"\n]{6,}['\"])")


def priority(p: Path):
    n, s = p.name.lower(), str(p).lower()
    if n.startswith("readme") or s.startswith("docs/") or p.suffix in {".md", ".rst"}: return 0
    if n in {"requirements.txt", "pyproject.toml", "package.json", "pom.xml", "go.mod", "cargo.toml", "dockerfile",
             "docker-compose.yml", "docker-compose.yaml"}: return 1
    if re.search(r"(model|schema|migration|openapi|swagger|config|settings|privacy|consent|user|auth|data)", s) or p.suffix in {".sql", ".prisma", ".proto"}: return 2
    return 3


def get_repo(src):
    if re.match(r"^(https?://|git@)", src):
        tmp = tempfile.mkdtemp(prefix="compliance_")
        subprocess.run(["git", "clone", "--depth", "1", "--quiet", src, tmp], check=True)
        return Path(tmp)
    return Path(src).resolve()


def list_files(root: Path):
    try:
        out = subprocess.run(["git", "-C", str(root), "ls-files"], capture_output=True, text=True, check=True).stdout
        files = [Path(l) for l in out.splitlines()]
    except Exception:
        files = [p.relative_to(root) for p in root.rglob("*") if p.is_file()]
    return [f for f in files if not (set(f.parts) & SKIP_PARTS) and not SKIP_NAMES.search(f.name)
            and (f.suffix.lower() in TEXT_EXT or f.name.lower() in {"dockerfile", "readme"})]


def collect(root: Path, budget: int):
    files = list_files(root)
    tree = cut("\n".join(map(str, sorted(files))), TREE_CAP)
    budget -= count(tree)
    ordered = sorted(files, key=lambda f: (priority(f), (root / f).stat().st_size if (root / f).exists() else 0))
    parts, skipped = [], 0
    for f in ordered:
        fp = root / f
        try:
            if fp.stat().st_size > MAX_FILE_BYTES: skipped += 1; continue
            text = SECRET.sub("[REDACTED]", fp.read_text(encoding="utf-8"))
        except Exception:
            skipped += 1; continue
        if not text.strip(): continue
        if count(text) > FILE_CAP: text = cut(text, FILE_CAP) + "\n[... tronqué ...]"
        block = f"### {f}\n{text}\n"
        c = count(block)
        if c > budget:
            skipped += 1; continue      # essaie un fichier plus petit ensuite
        parts.append(block); budget -= c
    return tree, "".join(parts), len(parts), skipped


def kb_text():
    return "\n".join(f"## {c['id']} | {c['title']}\n" + "\n".join(l for l in c["text"].splitlines() if not l.startswith("mots-clés:"))
                     for c in load())


SYSTEM = """Tu es un auditeur de conformité. Évalue le projet fourni selon UNIQUEMENT la base de connaissances (AI Act via le \
flowchart FLI, RGPD via la grille de maturité CNIL). Suis le flowchart dans l'ordre (E1..E3, HR1..HR6, S1, R1..R5) en \
citant les ids. Ne suppose rien : si une information manque dans le projet, dis-le dans "missing_info" plutôt que d'inventer. \
Pour la maturité RGPD, note chacune des 8 activités de 0 à 5 avec preuve concrète (fichier), ou null si non évaluable.
Réponds en JSON strict :
{"ai_act":{"is_ai_system":bool|null,"roles":[str],"status":"prohibited|high_risk|limited_transparency|minimal|out_of_scope|undetermined",
"path":[{"step":"id","answer":str,"evidence":str}],"obligations":[str]},
"rgpd":{"personal_data_processed":[str],"maturity":{"procedures|gouvernance|registre|conformite|formation|droits|securite|violations":{"level":int|null,"evidence":str}},"gaps":[str]},
"verdict":"conforme|risques_moderes|non_conforme|indetermine","summary":str,"missing_info":[str],"next_actions":[str]}
Ceci n'est pas un avis juridique."""


def call_openai(model, system, user):
    body = json.dumps({"model": model, "max_completion_tokens": MAX_OUT, "response_format": {"type": "json_object"},
                       "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}).encode()
    req = urllib.request.Request("https://api.openai.com/v1/chat/completions", body,
                                 {"Content-Type": "application/json", "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"Erreur API {e.code}: {e.read().decode()[:500]}")


def main():
    a = argparse.ArgumentParser()
    a.add_argument("source", help="chemin local ou URL git")
    a.add_argument("--model", default=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"))
    a.add_argument("--max-total", type=int, default=50_000)
    a.add_argument("--out", help="écrit le rapport JSON dans ce fichier")
    a.add_argument("--dry-run", action="store_true")
    a = a.parse_args()

    kb = kb_text()
    fixed = count(SYSTEM) + count(kb) + 300           # 300 : gabarit du message utilisateur
    input_budget = a.max_total - MAX_OUT - int(a.max_total * 0.05) - fixed   # marge 5 %
    if input_budget < 2000: sys.exit(f"Budget insuffisant pour le projet ({input_budget} tokens).")

    root = get_repo(a.source)
    tree, content, n, skipped = collect(root, input_budget)
    user = f"# BASE DE CONNAISSANCES\n{kb}\n\n# PROJET : {root.name}\n## Arborescence\n{tree}\n\n## Fichiers\n{content}"
    est = count(SYSTEM) + count(user)
    print(f"[budget] entrée estimée {est} + sortie max {MAX_OUT} = {est + MAX_OUT} / {a.max_total} "
          f"({n} fichiers inclus, {skipped} ignorés/tronqués)", file=sys.stderr)
    assert est + MAX_OUT <= a.max_total, "budget dépassé"
    if a.dry_run: return

    if "OPENAI_API_KEY" not in os.environ: sys.exit("OPENAI_API_KEY manquante.")
    resp = call_openai(a.model, SYSTEM, user)
    u = resp["usage"]
    print(f"[usage réel] {u['prompt_tokens']} + {u['completion_tokens']} = {u['total_tokens']} tokens", file=sys.stderr)
    if u["total_tokens"] > a.max_total: print("ATTENTION : budget réel dépassé.", file=sys.stderr)
    report = json.loads(resp["choices"][0]["message"]["content"])
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if a.out: Path(a.out).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
