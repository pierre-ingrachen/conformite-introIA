# Conformité AI Act & RGPD

Analyse un projet (dépôt GitHub public ou description) et produit un rapport AI Act + RGPD.
Le LLM (OpenAI) **extrait des faits avec preuve** ; le statut AI Act (flowchart FLI), les obligations, les constats RGPD
et le verdict sont **calculés par des règles** dans `api/_core.py`. Un seul appel API, ≤ 50 000 tokens (entrée + sortie).

- `kb/` : base de connaissances (flowchart FLI, grille de maturité CNIL, complément RGPD hors sources fournies)
- `rag.py` : recherche BM25 dans `kb/` (utilitaire, non nécessaire au pipeline)
- `pipeline.py` : CLI — `python pipeline.py https://github.com/org/repo [--dry-run] [--out rapport.json]`
- `api/analyze.py` + `public/index.html` : version web (Vercel)
- `tests/` : `python -m unittest discover tests`

## Déploiement Vercel (plan Hobby gratuit)
1. Importer le dépôt dans Vercel (framework « Other », aucun build).
2. Variables d'environnement : `OPENAI_API_KEY` (obligatoire), `ACCESS_CODE` (**fortement recommandé**, sinon toute personne
   ayant l'URL consomme votre clé), `OPENAI_MODEL` (défaut `gpt-4.1-mini`).
3. La fonction dure 10 à 40 s (limite configurée : 60 s). Dépôts GitHub publics uniquement, ≤ 30 Mo.

Limites : analyse d'un extrait du projet (fichiers priorisés : docs, manifestes, code lié aux données), pas un avis juridique.
