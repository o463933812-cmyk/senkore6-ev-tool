from __future__ import annotations
import gzip
import os
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parent
HOST = os.environ.get("SENKORE6_HOST", "127.0.0.1")
PORT = int(os.environ.get("SENKORE6_PORT") or os.environ.get("PORT") or "8796")
PASSWORD = os.environ.get("SENKORE6_PASSWORD", "nobunaga")
INDEX_GZ = "senkore6_tool_index.html.gz"
HIST_GZ = "senkore6_hist.json.gz"
INDEX_SIZE = 6131557
HIST_SIZE = 17637845
HIST_SHA256 = "48526166fc42d8cf61a23832bd4b8683658c9331ea27a6e429d8c373cfd4d7d5"
INDEX_SHA256 = "759285e3d5120d81d163d748a3b306b9fcfe892b43209c8a35cb6f062a44673e"
APP_VERSION = "2026-07-24-senkore6-mixed-high104-tailclamp-excluded"
_cached = None

def load_index():
    global _cached
    if _cached is not None:
        return _cached
    gz_path = ROOT / INDEX_GZ
    if gz_path.exists():
        data = gz_path.read_bytes()
    else:
        data = gzip.compress((ROOT / "index.html").read_bytes(), compresslevel=6)
    _cached = data
    return data

def page_login(msg=""):
    err = f"<p style='color:#c00'>{msg}</p>" if msg else ""
    notice = "<p style='font-size:13px;line-height:1.7;color:#444;margin:10px 0 14px'>\u672c\u30c4\u30fc\u30eb\u306f\u8cfc\u5165\u8005\u9650\u5b9a\u3067\u3059\u3002\u7121\u65ad\u8ee2\u8f09\u3001\u30b3\u30d4\u30fc\u3001\u518d\u914d\u5e03\u3001URL\u30fb\u30d1\u30b9\u30ef\u30fc\u30c9\u306e\u5171\u6709\u3001\u753b\u9762\u5185\u5bb9\u30fb\u8a08\u7b97\u7d50\u679c\u306e\u5171\u6709\u3092\u542b\u3080\u884c\u70ba\u306f\u7981\u6b62\u3057\u3066\u3044\u307e\u3059\u3002\u767a\u898b\u3057\u305f\u5834\u5408\u306f\u8ca9\u58f2\u505c\u6b62\u30fb\u6cd5\u7684\u63aa\u7f6e\u3092\u542b\u3080\u5bfe\u5fdc\u3092\u884c\u3046\u5834\u5408\u304c\u3042\u308a\u307e\u3059\u3002</p>"
    return f"""<!doctype html><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>login</title><body style='font-family:sans-serif;display:grid;place-items:center;min-height:100vh;background:#eef0f3'><form method='post' action='/login' style='background:white;border:1px solid #222;box-shadow:4px 4px 0 #999;padding:20px;min-width:280px;max-width:360px'><h1 style='font-size:20px;margin:0 0 8px'>\u6226\u30b3\u30ec6 \u671f\u5f85\u5024\u30c4\u30fc\u30eb</h1>{notice}{err}<input name='password' type='password' placeholder='password' autofocus style='width:100%;font-size:18px;padding:8px;box-sizing:border-box'><button style='margin-top:12px;width:100%;font-size:16px;padding:8px'>\u958b\u304f</button></form></body>""".encode("utf-8")

class Handler(BaseHTTPRequestHandler):
    server_version = "Senkore6EV/1.0"
    def log_message(self, fmt, *args):
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {self.client_address[0]} {fmt % args}")
    def has_auth(self):
        return f"senkore6_auth={PASSWORD}" in (self.headers.get("Cookie") or "")
    def send_blob(self, status, headers, body, head_only=False):
        self.send_response(status)
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        for k, v in headers:
            self.send_header(k, v)
        self.end_headers()
        if not head_only:
            self.wfile.write(body)
    def serve_index(self, head_only=False):
        if not self.has_auth():
            self.send_response(302)
            self.send_header("Location", "/login")
            self.end_headers()
            return
        body = load_index()
        self.send_blob(HTTPStatus.OK, [("Content-Type", "text/html; charset=utf-8"), ("Content-Encoding", "gzip"), ("Content-Length", str(len(body))), ("Cache-Control", "no-store"), ("X-App-Version", APP_VERSION)], body, head_only)

    def serve_hist(self, head_only=False):
        if not self.has_auth():
            self.send_response(302)
            self.send_header("Location", "/login")
            self.end_headers()
            return
        body = (ROOT / HIST_GZ).read_bytes()
        self.send_blob(HTTPStatus.OK, [("Content-Type", "application/json; charset=utf-8"), ("Content-Encoding", "gzip"), ("Content-Length", str(len(body))), ("Cache-Control", "no-store"), ("X-App-Version", APP_VERSION)], body, head_only)
    def do_HEAD(self):
        path = urlsplit(self.path).path or "/"
        if path in ("/", "/index.html"):
            self.serve_index(True)
        elif path == "/senkore6_hist.json":
            self.serve_hist(True)
        elif path == "/healthz":
            self.send_blob(HTTPStatus.OK, [("Content-Type", "text/plain"), ("X-App-Version", APP_VERSION)], b"ok", True)
        else:
            self.send_error(HTTPStatus.NOT_FOUND)
    def do_GET(self):
        path = urlsplit(self.path).path or "/"
        if path in ("/", "/index.html"):
            self.serve_index(False)
        elif path == "/senkore6_hist.json":
            self.serve_hist(False)
        elif path == "/login":
            self.send_blob(HTTPStatus.OK, [("Content-Type", "text/html; charset=utf-8")], page_login())
        elif path == "/healthz":
            self.send_blob(HTTPStatus.OK, [("Content-Type", "text/plain"), ("X-App-Version", APP_VERSION)], b"ok")
        else:
            self.send_error(HTTPStatus.NOT_FOUND)
    def do_POST(self):
        path = urlsplit(self.path).path or "/"
        if path != "/login":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        length = int(self.headers.get("Content-Length") or "0")
        data = parse_qs(self.rfile.read(length).decode("utf-8", "ignore"))
        if (data.get("password") or [""])[0] == PASSWORD:
            self.send_response(302)
            self.send_header("Set-Cookie", f"senkore6_auth={PASSWORD}; Path=/; HttpOnly; SameSite=Lax")
            self.send_header("Location", "/")
            self.end_headers()
        else:
            self.send_blob(HTTPStatus.UNAUTHORIZED, [("Content-Type", "text/html; charset=utf-8")], page_login("パスワードが違います"))

if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"serving on {HOST}:{PORT} version={APP_VERSION}")
    server.serve_forever()
