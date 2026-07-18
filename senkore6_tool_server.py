from __future__ import annotations
import hashlib, os, time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
ROOT = Path(__file__).resolve().parent
HOST = os.environ.get("SENKORE6_HOST", "127.0.0.1")
PORT = int(os.environ.get("SENKORE6_PORT") or os.environ.get("PORT") or "8796")
INDEX_GZ = "senkore6_tool_index.html.gz"
INDEX_SIZE = 10534
INDEX_SHA256 = "56524820b5d7a32389917c56729d5666871cc8340fa3f4657ae6de999d01c98a"
APP_VERSION = "2026-07-18-senkore6-v4"
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
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {fmt % args}")
    def blob(self, status, headers, body=b"", head=False):
        self.send_response(status)
        for k, v in headers:
            self.send_header(k, v)
        self.end_headers()
        if not head:
            self.wfile.write(body)
    def do_HEAD(self):
        self.handle_request(True)
    def do_GET(self):
        self.handle_request(False)
    def handle_request(self, head=False):
        path = urlsplit(self.path).path or "/"
        if path == "/healthz":
            self.blob(HTTPStatus.OK, [("Content-Type","text/plain")], b"ok", head)
        elif path in ("/", "/index.html"):
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
