#!/usr/bin/env python3
"""Receive files over HTTP into one folder: pictures coming back from the machine that runs the game.

    inbox.py <folder> [--port 8765] [--token-file <path>]

Listens on 127.0.0.1 only and is meant to be reached through a tunnel for as long as a transfer
lasts. Every upload has to carry the token as the first part of its path:

    curl -T shot.png https://<tunnel host>/<token>/shot.png

The token is random, written to the token file (default <folder>/.token) and never printed.
File names are reduced to plain names, nothing is written outside the folder, nothing is ever
sent back, and a file may be 64 MB at most.
"""
import argparse
import http.server
import os
import re
import secrets
import urllib.parse

LIMIT = 64 << 20
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,119}")


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _body(self, out):
        """Copy the request body to `out`; returns the number of bytes, or -1 if it is too long or cut."""
        total = 0
        if "chunked" in self.headers.get("Transfer-Encoding", "").lower():
            while True:
                line = self.rfile.readline(64)
                try:
                    size = int(line.split(b";")[0].strip() or b"0", 16)
                except ValueError:
                    return -1
                if size == 0:
                    while self.rfile.readline(1024) not in (b"\r\n", b"\n", b""):
                        pass
                    return total
                total += size
                if total > LIMIT:
                    return -1
                data = self.rfile.read(size)
                if len(data) != size:
                    return -1
                out.write(data)
                self.rfile.readline(8)
        left = int(self.headers.get("Content-Length", "-1"))
        if not 0 <= left <= LIMIT:
            return -1
        while left:
            data = self.rfile.read(min(left, 1 << 16))
            if not data:
                return -1
            out.write(data)
            left -= len(data)
            total += len(data)
        return total

    def _answer(self, code, text):
        body = (text + "\n").encode()
        self.send_response(code)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def do_PUT(self):
        parts = self.path.split("?")[0].strip("/").split("/")
        if len(parts) != 2 or not secrets.compare_digest(parts[0].encode(), self.server.token.encode()):
            self._answer(404, "not found")
            return
        name = urllib.parse.unquote(parts[1])
        if not NAME.fullmatch(name):
            self._answer(400, "bad name")
            return
        tmp = os.path.join(self.server.folder, name + ".part")
        with open(tmp, "wb") as out:
            size = self._body(out)
        if size < 0:
            os.remove(tmp)
            self._answer(400, "bad body")
            return
        os.replace(tmp, os.path.join(self.server.folder, name))
        print(f"{name} {size}", flush=True)
        self._answer(201, f"stored {size}")

    do_POST = do_PUT

    def do_GET(self):
        self._answer(404, "not found")

    def log_message(self, fmt, *args):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--token-file")
    args = ap.parse_args()
    os.makedirs(args.folder, exist_ok=True)
    token_file = args.token_file or os.path.join(args.folder, ".token")
    token = secrets.token_urlsafe(24)
    with open(token_file, "w") as fh:
        fh.write(token)
    os.chmod(token_file, 0o600)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.token, server.folder = token, os.path.abspath(args.folder)
    print(f"listening on 127.0.0.1:{args.port}, files go to {server.folder}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
