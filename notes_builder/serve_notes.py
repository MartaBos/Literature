#!/usr/bin/env python3
"""Serve the paper-notes pages and save "My comments" from them (localhost only, key-protected).

  GET  /                                   list of the pages
  GET  /<folder>/paper_notes_<folder>.html  a page (always the latest build)
  GET  /api/comments?folder=<folder>       comments of that folder
  POST /api/comments  {"key": "<folder>/<stem>", "text": "..."}   save one paper's comment

Comments are stored in notes/comments.json ({key: {"text", "updated"}}); every save is also appended
to notes/comments_history.jsonl, so earlier versions are never lost.

abacus2 is a shared machine, so the server listens on 127.0.0.1 only and needs the private key from
.server_token: open the link printed by start_notes_server.sh once (…/?t=KEY); after that a cookie is
used. Start/stop: start_notes_server.sh / kill the PID in .server.pid. Port: config.json "server_port".
"""
import datetime as dt
import html
import http.server
import json
import os
import pathlib
import re
import secrets
import threading
import urllib.parse

HERE = pathlib.Path(__file__).resolve().parent
CFG = json.loads((HERE / "config.json").read_text())
PAPERS = pathlib.Path(CFG["papers_root"]).resolve()
NOTES = pathlib.Path(CFG["notes_root"])
COMMENTS = NOTES / "comments.json"
HISTORY = NOTES / "comments_history.jsonl"
PORT = int(CFG.get("server_port", 21060))
TOKEN_FILE = HERE / ".server_token"
LOCK = threading.Lock()
KEY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.\-]+$")


def token():
    if not TOKEN_FILE.exists():
        TOKEN_FILE.write_text(secrets.token_urlsafe(24))
    os.chmod(TOKEN_FILE, 0o600)
    return TOKEN_FILE.read_text().strip()


TOKEN = token()


def load_comments():
    return json.loads(COMMENTS.read_text()) if COMMENTS.exists() else {}


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "paper-notes/1.0"

    def log_message(self, fmt, *args):  # quiet: only errors go to the log
        pass

    def send(self, code, body, ctype="text/html; charset=utf-8", extra=None):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def authed(self):
        cookies = dict(c.strip().split("=", 1) for c in self.headers.get("Cookie", "").split(";") if "=" in c)
        return secrets.compare_digest(cookies.get("pn_token", ""), TOKEN)

    def do_GET(self):
        u = urllib.parse.urlsplit(self.path)
        q = urllib.parse.parse_qs(u.query)
        if q.get("t") and secrets.compare_digest(q["t"][0], TOKEN):  # first visit with the key -> cookie
            return self.send(302, "", extra={"Location": u.path or "/",
                                             "Set-Cookie": f"pn_token={TOKEN}; HttpOnly; SameSite=Strict; Path=/"})
        if not self.authed():
            return self.send(403, "Forbidden: open the link printed by start_notes_server.sh (it ends in ?t=...).",
                             "text/plain; charset=utf-8")
        if u.path == "/":
            pages = sorted(PAPERS.glob("*/paper_notes_*.html"))
            links = "".join(f'<li><a href="/{p.parent.name}/{p.name}">{html.escape(p.parent.name)}</a></li>' for p in pages)
            return self.send(200, f"<!doctype html><meta charset=utf-8><title>Paper notes</title>"
                                  f"<body style='font-family:sans-serif;padding:24px'><h1>Paper notes</h1><ul>{links}</ul>")
        if u.path == "/api/comments":
            folder = (q.get("folder") or [""])[0]
            with LOCK:
                c = load_comments()
            return self.send(200, json.dumps({k: v for k, v in c.items() if k.startswith(folder + "/")},
                                             ensure_ascii=False), "application/json; charset=utf-8")
        m = re.fullmatch(r"/([A-Za-z0-9_.-]+)/(paper_notes_[A-Za-z0-9_.-]+\.html)", u.path)
        if m:
            f = (PAPERS / m.group(1) / m.group(2)).resolve()
            if f.parent.parent == PAPERS and f.is_file():
                return self.send(200, f.read_bytes())
        return self.send(404, "Not found", "text/plain; charset=utf-8")

    def do_POST(self):
        if self.path != "/api/comments" or not self.authed():
            return self.send(403, "Forbidden", "text/plain; charset=utf-8")
        if "application/json" not in self.headers.get("Content-Type", ""):
            return self.send(415, "JSON only", "text/plain; charset=utf-8")
        n = int(self.headers.get("Content-Length", 0))
        if n > 500_000:
            return self.send(413, "Too large", "text/plain; charset=utf-8")
        try:
            body = json.loads(self.rfile.read(n))
            key, text = str(body["key"]), str(body["text"])
        except Exception:
            return self.send(400, "Bad request", "text/plain; charset=utf-8")
        if not KEY_RE.match(key) or not (PAPERS / key.split("/")[0]).is_dir() or len(text) > 200_000:
            return self.send(400, "Bad key or text", "text/plain; charset=utf-8")
        now = dt.datetime.now().isoformat(timespec="seconds")
        with LOCK:
            c = load_comments()
            c[key] = {"text": text, "updated": now}
            tmp = COMMENTS.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(c, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            tmp.replace(COMMENTS)
            with open(HISTORY, "a", encoding="utf-8") as h:
                h.write(json.dumps({"time": now, "key": key, "text": text}, ensure_ascii=False) + "\n")
            for f in (COMMENTS, HISTORY):  # private: abacus2 is shared
                os.chmod(f, 0o600)
        return self.send(200, json.dumps({"updated": now}), "application/json; charset=utf-8")


if __name__ == "__main__":
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    (HERE / ".server.pid").write_text(str(os.getpid()))
    print(f"serving on http://localhost:{PORT}/?t={TOKEN}", flush=True)
    srv.serve_forever()
