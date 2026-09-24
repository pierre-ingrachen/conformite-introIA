#!/usr/bin/env python3
"""Serveur local : page (public/) + API (api/analyze.py). Usage : python3 dev.py [port]  →  http://localhost:8000"""
import os, sys
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "api"))
import analyze  # noqa: E402

for line in (ROOT / ".env").read_text().splitlines() if (ROOT / ".env").exists() else []:
    k, sep, v = line.partition("=")
    if sep and not k.strip().startswith("#"): os.environ.setdefault(k.strip(), v.strip().strip("'\""))


class Dev(SimpleHTTPRequestHandler):
    def _api(self): return self.path.split("?")[0] == "/api/analyze"
    def do_GET(self): analyze.handler.do_GET(self) if self._api() else super().do_GET()
    def do_POST(self):
        if self._api(): analyze.handler.do_POST(self)
        else: self.send_error(404)
    _send = analyze.handler._send


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"http://localhost:{port}  (clé OpenAI : {'ok' if os.environ.get('OPENAI_API_KEY') else 'MANQUANTE'})")
    HTTPServer(("127.0.0.1", port), partial(Dev, directory=str(ROOT / "public"))).serve_forever()
