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
INDEX_SIZE = 2380119
INDEX_SHA256 = "25ff6df99d841be64fef3230bcad7af0defbe2e7ccfead5a54a68d656e49612e"
APP_VERSION = '2026-07-22-senkore6-cycle-yame-follow'
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
    notice = "<p style='font-size:13px;line-height:1.7;color:#444;margin:10px 0 14px'>本ツールは購入者限定です。無断転載・コピー・再配布（URL・パスワード共有、画面内容・算出結果の共有を含む）は禁止しています。発見した場合は、販売停止・法的措置を含む対応を行う場合があります。</p>"
    return f"""<!doctype html><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>login</title><body style='font-family:sans-serif;display:grid;place-items:center;min-height:100vh;background:#eef0f3'><form method='post' action='/login' style='background:white;border:1px solid #222;box-shadow:4px 4px 0 #999;padding:20px;min-width:280px;max-width:360px'><h1 style='font-size:20px;margin:0 0 8px'>戦コレ6 期待値ツール</h1>{notice}{err}<input name='password' type='password' placeholder='password' autofocus style='width:100%;font-size:18px;padding:8px;box-sizing:border-box'><button style='margin-top:12px;width:100%;font-size:16px;padding:8px'>開く</button></form></body>""".encode("utf-8")

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
    def do_HEAD(self):
        path = urlsplit(self.path).path or "/"
        if path in ("/", "/index.html"):
            self.serve_index(True)
        elif path == "/healthz":
            self.send_blob(HTTPStatus.OK, [("Content-Type", "text/plain"), ("X-App-Version", APP_VERSION)], b"ok", True)
        else:
            self.send_error(HTTPStatus.NOT_FOUND)
    def do_GET(self):
        path = urlsplit(self.path).path or "/"
        if path in ("/", "/index.html"):
            self.serve_index(False)
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
