#!/usr/bin/env python3
"""RAG minimal (stdlib uniquement) : BM25 sur les fragments de kb/*.md.

CLI :   python rag.py "mon projet fait du scoring de candidats" -k 5 [--json] [--source ai_act|rgpd]
Python: from rag import search; search("deepfake", k=3)
"""
import argparse, json, math, re, sys, unicodedata
from collections import Counter
from pathlib import Path

KB = Path(__file__).parent / "kb"
STOP = set("le la les un une des de du et ou en au aux a est ce que qui dans pour par sur avec the of and or to in is a an for on with are be".split())


def tokens(text):
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    # troncature à 6 caractères : stemming FR/EN très léger (traitement/traitements, provider/providers)
    return [w[:6] for w in re.findall(r"[a-z0-9]+", text) if w not in STOP and len(w) > 1]


def load():
    chunks = []
    for f in sorted(KB.glob("*.md")):
        text = re.sub(r"<!--.*?-->", "", f.read_text(encoding="utf-8"), flags=re.S)
        for part in re.split(r"^## ", text, flags=re.M)[1:]:
            head, _, body = part.partition("\n")
            cid, _, title = head.partition("|")
            chunks.append({"id": cid.strip(), "title": title.strip(), "file": f.stem, "text": body.strip()})
    return chunks


def search(query, k=5, source=None, chunks=None):
    chunks = chunks or load()
    if source:
        chunks = [c for c in chunks if c["id"].startswith(source)]
    docs = [Counter(tokens(c["title"] * 2 + " " + c["id"] + " " + c["text"])) for c in chunks]
    n = len(docs)
    avg = sum(sum(d.values()) for d in docs) / max(n, 1)
    df = Counter(t for d in docs for t in d)
    scores = []
    for c, d in zip(chunks, docs):
        ln, s = sum(d.values()), 0.0
        for t in set(tokens(query)):
            if t in d:
                idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                s += idf * d[t] * 2.5 / (d[t] + 1.5 * (0.25 + 0.75 * ln / avg))
        scores.append((s, c))
    return [{**c, "score": round(s, 3)} for s, c in sorted(scores, key=lambda x: -x[0])[:k] if s > 0]


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("query")
    p.add_argument("-k", type=int, default=5)
    p.add_argument("--source", help="préfixe d'id : ai_act ou rgpd")
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    res = search(a.query, a.k, a.source)
    if a.json:
        json.dump(res, sys.stdout, ensure_ascii=False, indent=2)
    else:
        for r in res:
            print(f"[{r['score']}] {r['id']} – {r['title']}\n{r['text']}\n")
