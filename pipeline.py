#!/usr/bin/env python3
"""CLI : évalue un projet (dossier local, URL GitHub publique ou fichier de doc) vs AI Act + RGPD.

    export OPENAI_API_KEY=sk-...          (ou : set -a; source .env; set +a)
    python pipeline.py https://github.com/org/repo
    python pipeline.py ./projet --dry-run          # budget de tokens sans appel API
    python pipeline.py --doc description.md --out rapport.json
Un seul appel API ; entrée + sortie <= 50 000 tokens (--max-total).
"""
import argparse, json, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "api"))
import _core as core


def text_report(r):
    m = r["meta"]
    out = [f"Tokens : entrée estimée {m['estimated_input']} + sortie max {m['max_output']} / {m['budget']} "
           f"| fichiers {m['files_included']}/{m['files_total']} (tronqués {m['files_truncated']}, ignorés {m['files_skipped']})"]
    if "usage" in m: out.append(f"Usage réel : {m['usage']['prompt_tokens']} + {m['usage']['completion_tokens']} = {m['usage']['total_tokens']}")
    if r.get("dry_run"): return "\n".join(out)
    ai, rg = r["ai_act"], r["rgpd"]
    out += ["", f"VERDICT : {r['verdict_label']}  (couverture des faits clés : {int(r['coverage'] * 100)} %)",
            f"AI Act : {ai['label']} | rôles : {', '.join(ai['roles']) or '?'}"]
    out += [f"  {p['step']:8} {p['answer']}" for p in ai["path"]]
    out += ["  Obligations :"] + [f"   - {o['ref']} : {o['label']}" for o in ai["obligations"]]
    out += ["", f"RGPD : applicable={rg['applicable']} | AIPD requise={rg['aipd_required']} ({', '.join(rg['criteria'])})"]
    out += [f"  [{x['severity']}] {x['text']} ({x['ref']})" for x in rg["findings"]]
    if "maturity" in rg:
        out.append("  Maturité CNIL : " + ", ".join(f"{k}={v['level'] if v['level'] is not None else '?'}" for k, v in rg["maturity"]["levels"].items()))
    if r["to_verify"]: out += ["", "À vérifier :"] + [f"  - {x}" for x in r["to_verify"]]
    if r["missing_info"]: out += ["", "Questions au porteur :"] + [f"  - {x}" for x in r["missing_info"]]
    if r["unsupported_claims"]: out += ["", "Affirmations du modèle écartées (preuve invalide) : " + ", ".join(r["unsupported_claims"])]
    return "\n".join(out + ["", r["disclaimer"]])


def main():
    a = argparse.ArgumentParser()
    a.add_argument("source", nargs="?", help="dossier local ou URL https://github.com/owner/repo")
    a.add_argument("--doc", help="fichier texte décrivant le projet (à la place d'un dépôt)")
    a.add_argument("--model", default=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"))
    a.add_argument("--max-total", type=int, default=core.TOTAL)
    a.add_argument("--out", help="écrit le rapport JSON complet")
    a.add_argument("--dry-run", action="store_true")
    a = a.parse_args()
    if a.doc: name, ents = core.load_doc(Path(a.doc).read_text(encoding="utf-8"), Path(a.doc).name)
    elif a.source and a.source.startswith("http"): name, ents = core.load_github(a.source)
    elif a.source: name, ents = core.load_local(a.source)
    else: sys.exit("Indique un dépôt/dossier ou --doc.")
    if not a.dry_run and "OPENAI_API_KEY" not in os.environ: sys.exit("OPENAI_API_KEY manquante.")
    r = core.analyze(name, ents, a.model, os.environ.get("OPENAI_API_KEY"), a.max_total, a.dry_run)
    if a.out: Path(a.out).write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(text_report(r))
    if r.get("meta", {}).get("usage", {}).get("total_tokens", 0) > a.max_total: print("ATTENTION : budget réel dépassé.")


if __name__ == "__main__":
    main()
