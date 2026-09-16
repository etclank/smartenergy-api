#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
exec python3 - "$@" <<'PYTHON'
import os
import posixpath
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, unquote

class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="site", **kwargs)

    def translate_path(self, path):
        return super().translate_path(path.removeprefix("/site"))

    def do_GET(self):
        if not (posixpath.normpath(unquote(urlsplit(self.path).path)).startswith("/site/") or unquote(urlsplit(self.path).path) == "/site/"):
            self.send_error(404)
            return
        super().do_GET()

    def do_HEAD(self):
        if not (posixpath.normpath(unquote(urlsplit(self.path).path)).startswith("/site/") or unquote(urlsplit(self.path).path) == "/site/"):
            self.send_error(404)
            return
        super().do_HEAD()

port = int(os.environ.get("PORT", "5173"))
server = ThreadingHTTPServer(("127.0.0.1", port), DashboardHandler)
print(f"Dashboard: http://localhost:{server.server_port}/site/", flush=True)
server.serve_forever()
PYTHON
