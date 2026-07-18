from __future__ import annotations
import hashlib, html, os, secrets, time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
ROOT = Path(__file__).resolve().parent
HOST = os.environ.get("SENKORE6_HOST", "127.0.0.1")
PORT = int(os.environ.get("SENKORE6_PORT") or os.environ.get("PORT") or "8796")
INDEX_GZ = "senkore6_tool_index.html.gz"
INDEX_SIZE = 18783
INDEX_SHA256 = "c9ce749a05aed3a28cb949076d582e88c29cee697436a6613be8a16e199092ac"
APP_VERSION = "2026-07-18-senkore6-v5-ui-logic-clean15"
AUTH_COOKIE_NAME = "senkore6_auth"
SESSION_COOKIE = f"{AUTH_COOKIE_NAME}={secrets.token_urlsafe(24)}"
PASSWORD = os.environ.get("SENKORE6_PASSWORD", "")
_cached = None

def load_index():
    global _cached
    if _cached is not None:
        return _cached
    data = (ROOT / INDEX_GZ).read_bytes()
    if len(data) != INDEX_SIZE:
        raise RuntimeError("index size mismatch")
    if hashlib.sha256(data).hexdigest() != INDEX_SHA256:
        raise RuntimeError("index sha mismatch")
    _cached = data
    return data

def login_page(error: str = "") -> bytes:
    msg = f"<p class='err'>{html.escape(error)}</p>" if error else ""
    body = f"""<!doctype html><html lang='ja'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>戦コレ6 期待値検索ツール Login</title><style>body{{margin:0;font-family:system-ui,-apple-system,'Segoe UI',sans-serif;background:#f7f3e8;color:#143335;display:grid;place-items:center;min-height:100vh}}form{{width:min(360px,calc(100vw - 32px));background:#fffdf5;border-top:6px solid #00796b;border-radius:8px;padding:24px;box-shadow:0 12px 28px rgba(20,51,53,.16)}}h1{{font-size:20px;margin:0 0 16px}}label{{display:block;font-size:13px;margin-bottom:8px}}input{{box-sizing:border-box;width:100%;font-size:18px;padding:12px;border:1px solid #cdd8d2;border-radius:6px}}button{{width:100%;margin-top:16px;padding:12px;border:0;border-radius:6px;background:#00796b;color:#fff;font-weight:700;font-size:16px}}.err{{color:#b3261e;font-weight:700}}</style></head><body><form method='post' action='/login'><h1>戦コレ6 期待値検索ツール</h1>{msg}<label>パスワード</label><input name='password' type='password' autofocus autocomplete='current-password'><button type='submit'>開く</button></form></body></html>"""
    return body.encode("utf-8")

class Handler(BaseHTTPRequestHandler):
    server_version = "Senkore6EV/1.1"
    def log_message(self, fmt, *args):
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {fmt % args}")
    def blob(self, status, headers, body=b"", head=False):
        self.send_response(status)
        for k, v in headers:
            self.send_header(k, v)
        self.end_headers()
        if not head:
            self.wfile.write(body)
    def authed(self):
        if not PASSWORD:
            return True
        return SESSION_COOKIE in (self.headers.get("Cookie") or "")
    def do_HEAD(self):
        self.handle_request(True)
    def do_GET(self):
        self.handle_request(False)
    def do_POST(self):
        path = urlsplit(self.path).path or "/"
        if path != "/login":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        length = int(self.headers.get("Content-Length") or "0")
        raw = self.rfile.read(length).decode("utf-8", "replace")
        password = parse_qs(raw).get("password", [""])[0]
        if secrets.compare_digest(password, PASSWORD):
            self.blob(HTTPStatus.SEE_OTHER, [("Location", "/"), ("Set-Cookie", SESSION_COOKIE + "; Path=/; HttpOnly; SameSite=Lax"), ("Cache-Control", "no-store")])
        else:
            body = login_page("パスワードが違います")
            self.blob(HTTPStatus.UNAUTHORIZED, [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(body))), ("Cache-Control", "no-store")], body)
    def handle_request(self, head=False):
        path = urlsplit(self.path).path or "/"
        if path == "/healthz":
            self.blob(HTTPStatus.OK, [("Content-Type","text/plain")], b"ok", head)
        elif path == "/login":
            body = login_page()
            self.blob(HTTPStatus.OK, [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(body))), ("Cache-Control", "no-store")], body, head)
        elif path == "/logout":
            self.blob(HTTPStatus.SEE_OTHER, [("Location", "/login"), ("Set-Cookie", f"{AUTH_COOKIE_NAME}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax"), ("Cache-Control", "no-store")], b"", head)
        elif path in ("/", "/index.html"):
            if not self.authed():
                self.blob(HTTPStatus.SEE_OTHER, [("Location", "/login"), ("Cache-Control", "no-store")], b"", head)
                return
            body = load_index()
            self.blob(HTTPStatus.OK, [("Content-Type","text/html; charset=utf-8"), ("Content-Encoding","gzip"), ("Content-Length",str(len(body))), ("Cache-Control","no-store"), ("X-App-Version",APP_VERSION)], body, head)
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

def main():
    load_index()
    print(f"Senkore6 EV tool {APP_VERSION} serving on {HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
if __name__ == "__main__":
    main()
