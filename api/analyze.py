"""Fonction serverless Vercel : POST /api/analyze  {"repo": "https://github.com/o/r"} ou {"doc": "texte…"}.

Variables d'environnement : OPENAI_API_KEY (obligatoire), OPENAI_MODEL (optionnel), ACCESS_CODE (recommandé :
sans lui, n'importe qui peut consommer votre clé OpenAI).
"""
import hmac, json, os, sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(__file__))
import _core as core

MAX_BODY = 200_000


class handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # la page lit ceci pour savoir si un code d'accès est demandé
        self._send(200, {"ok": True, "needs_code": bool(os.environ.get("ACCESS_CODE"))})

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY: return self._send(413, {"error": "Requête trop volumineuse."})
            body = json.loads(self.rfile.read(n) or b"{}")
            code = os.environ.get("ACCESS_CODE")
            if code and not hmac.compare_digest(str(body.get("access_code", "")), code):
                return self._send(401, {"error": "Code d'accès invalide."})
            key = os.environ.get("OPENAI_API_KEY")
            if not key: return self._send(500, {"error": "OPENAI_API_KEY non configurée sur le serveur."})
            if body.get("repo"): name, ents = core.load_github(str(body["repo"])[:300])
            elif body.get("doc"): name, ents = core.load_doc(str(body["doc"])[:MAX_BODY])
            else: return self._send(400, {"error": "Fournir « repo » (URL GitHub) ou « doc » (texte)."})
            self._send(200, core.analyze(name, ents, os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"), key))
        except ValueError as e:
            self._send(400, {"error": str(e)})
        except Exception as e:
            self._send(502, {"error": str(e)[:400]})
