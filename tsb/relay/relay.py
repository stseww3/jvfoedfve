#!/usr/bin/env python3
"""Command / result relay for the strategy bot extension, in place of webhook.site.

The part of webhook.site's API the extension, send-command.mjs and the agents' tools use:
  POST /token                         new address -> {"uuid": ...}
  POST /<uuid>                        store the body -> "ok", header X-Request-Id: <request uuid>
  GET  /token/<uuid>/requests         {"data": [...], "total": n, ...}; ?sorting=newest|oldest&per_page=&page=
  GET  /token/<uuid>                  the address: created_at, latest_request_at, total
Addresses are made by POST /token only; a POST to an unknown one is a 404, as on webhook.site.
No request limit and no expiry: each address keeps its last KEEP requests (on disk too).
Commands are signed by the sender, so the relay itself does not check who posts.

usage: python3 relay.py [--host 0.0.0.0] [--port 8790] [--data ./data]
"""
import argparse
import json
import os
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

KEEP = 500
MAX_TOKENS = 100
MAX_BODY = 4 << 20
# requests per IP in a minute (a game tab polls about 20 times a minute)
RATE = 600
UUID_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
CORS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, OPTIONS',
    'Access-Control-Allow-Headers': '*',
    'Access-Control-Expose-Headers': 'X-Request-Id, X-Token-Id',
}


def stamp():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')


class Store:
    def __init__(self, data):
        self.data = data
        self.lock = threading.Lock()
        self.tokens = {}
        self.requests = {}
        self.lines = {}
        os.makedirs(data, exist_ok=True)
        try:
            with open(self._meta()) as f:
                self.tokens = json.load(f)
        except (OSError, ValueError):
            self.tokens = {}
        for t in self.tokens:
            reqs = []
            try:
                with open(self._file(t), encoding='utf-8') as f:
                    for line in f:
                        try:
                            reqs.append(json.loads(line))
                        except ValueError:
                            pass
            except OSError:
                pass
            self.lines[t] = len(reqs)
            self.requests[t] = reqs[-KEEP:]

    def _meta(self):
        return os.path.join(self.data, 'tokens.json')

    def _file(self, t):
        return os.path.join(self.data, t + '.jsonl')

    def _save_meta(self):
        tmp = self._meta() + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(self.tokens, f)
        os.replace(tmp, self._meta())

    def new_token(self):
        with self.lock:
            if len(self.tokens) >= MAX_TOKENS:
                return None
            t = str(uuid.uuid4())
            self.tokens[t] = {'uuid': t, 'created_at': stamp()}
            self.requests[t] = []
            self.lines[t] = 0
            self._save_meta()
            return dict(self.tokens[t])

    def info(self, t):
        with self.lock:
            if t not in self.tokens:
                return None
            reqs = self.requests[t]
            last = reqs[-1] if reqs else None
            return {**self.tokens[t], 'total': len(reqs),
                    'latest_request_at': last and last['created_at'], 'latest_request_id': last and last['uuid']}

    def add(self, t, req):
        with self.lock:
            if t not in self.tokens:
                return False
            reqs = self.requests[t]
            reqs.append(req)
            del reqs[:-KEEP]
            line = json.dumps(req, ensure_ascii=False) + '\n'
            if self.lines[t] >= 2 * KEEP:
                tmp = self._file(t) + '.tmp'
                with open(tmp, 'w', encoding='utf-8') as f:
                    f.writelines(json.dumps(r, ensure_ascii=False) + '\n' for r in reqs)
                os.replace(tmp, self._file(t))
                self.lines[t] = len(reqs)
            else:
                with open(self._file(t), 'a', encoding='utf-8') as f:
                    f.write(line)
                self.lines[t] += 1
            return True

    def page(self, t, newest, per_page, page):
        with self.lock:
            if t not in self.tokens:
                return None
            reqs = list(reversed(self.requests[t])) if newest else list(self.requests[t])
        total = len(reqs)
        start = (page - 1) * per_page
        data = reqs[start:start + per_page]
        return {'data': data, 'total': total, 'per_page': per_page, 'current_page': page,
                'is_last_page': start + per_page >= total,
                'from': start + 1 if data else None, 'to': start + len(data) if data else None}


class Limiter:
    def __init__(self):
        self.lock = threading.Lock()
        self.hits = {}

    def ok(self, ip):
        now = time.monotonic()
        with self.lock:
            q = [t for t in self.hits.get(ip, ()) if now - t < 60]
            if len(q) >= RATE:
                self.hits[ip] = q
                return False
            q.append(now)
            self.hits[ip] = q
            if len(self.hits) > 10000:
                self.hits = {k: v for k, v in self.hits.items() if v and now - v[-1] < 60}
            return True


class Handler(BaseHTTPRequestHandler):
    server_version = 'tsb-relay/1'
    timeout = 30

    def log_message(self, fmt, *args):
        pass

    def send(self, status, body, ctype='application/json', headers=None):
        raw = body if isinstance(body, bytes) else (json.dumps(body) if ctype == 'application/json' else body).encode('utf-8')
        self.send_response(status)
        for k, v in {**CORS, **(headers or {})}.items():
            self.send_header(k, v)
        self.send_header('Content-Type', ctype + '; charset=utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(raw)

    def gate(self):
        if self.server.limiter.ok(self.client_address[0]):
            return True
        self.send(429, {'error': True, 'message': 'Too many requests'}, headers={'Retry-After': '10'})
        return False

    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in CORS.items():
            self.send_header(k, v)
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_GET(self):
        if not self.gate():
            return
        u = urlsplit(self.path)
        parts = [p for p in u.path.split('/') if p]
        store = self.server.store
        if not parts or parts == ['health']:
            return self.send(200, 'ok\n', 'text/plain')
        if len(parts) >= 2 and parts[0] == 'token' and UUID_RE.match(parts[1]):
            t = parts[1]
            if len(parts) == 2:
                info = store.info(t)
                return self.send(200, info) if info else self.send(404, {'error': True, 'message': 'Token not found'})
            if len(parts) == 3 and parts[2] == 'requests':
                q = parse_qs(u.query)
                arg = lambda k, d: (q.get(k) or [d])[0]
                try:
                    per_page = max(1, min(100, int(arg('per_page', '50'))))
                    page = max(1, int(arg('page', '1')))
                except ValueError:
                    return self.send(400, {'error': True, 'message': 'per_page and page are numbers'})
                res = store.page(t, arg('sorting', 'oldest') == 'newest', per_page, page)
                return self.send(200, res) if res else self.send(404, {'error': True, 'message': 'Token not found'})
        if len(parts) == 1 and UUID_RE.match(parts[0]):
            ok = store.info(parts[0]) is not None
            return self.send(200 if ok else 404, 'POST here; the requests are listed at /token/<uuid>/requests\n' if ok else 'Token not found\n', 'text/plain')
        self.send(404, {'error': True, 'message': 'Not found'})

    do_HEAD = do_GET

    def do_POST(self):
        if not self.gate():
            return
        u = urlsplit(self.path)
        parts = [p for p in u.path.split('/') if p]
        store = self.server.store
        try:
            n = int(self.headers.get('Content-Length') or 0)
        except ValueError:
            n = -1
        if n < 0 or n > MAX_BODY:
            self.close_connection = True
            return self.send(413, {'error': True, 'message': 'Body too large'})
        body = self.rfile.read(n) if n else b''
        if parts == ['token']:
            tok = store.new_token()
            return self.send(201, tok) if tok else self.send(507, {'error': True, 'message': 'Too many addresses'})
        if len(parts) == 1 and UUID_RE.match(parts[0]):
            t = parts[0]
            rid = str(uuid.uuid4())
            now = stamp()
            ctype = self.headers.get('Content-Type') or ''
            agent = self.headers.get('User-Agent') or ''
            req = {'uuid': rid, 'type': 'web', 'token_id': t, 'ip': self.client_address[0], 'method': self.command,
                   'user_agent': agent, 'content': body.decode('utf-8', 'replace'), 'query': u.query or None,
                   'headers': {'content-type': [ctype], 'user-agent': [agent]}, 'url': self.path,
                   'size': len(body), 'files': [], 'created_at': now, 'updated_at': now}
            if not store.add(t, req):
                return self.send(404, 'Token not found\n', 'text/plain')
            print(f'{now} {self.command} {t[:8]} {len(body)} B from {self.client_address[0]}', flush=True)
            return self.send(200, 'ok', 'text/plain', {'X-Request-Id': rid, 'X-Token-Id': t})
        self.send(404, {'error': True, 'message': 'Not found'})

    do_PUT = do_POST


def main():
    ap = argparse.ArgumentParser(description='webhook.site-style relay for the strategy bot extension')
    ap.add_argument('--host', default='0.0.0.0')
    ap.add_argument('--port', type=int, default=8790)
    ap.add_argument('--data', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data'))
    a = ap.parse_args()
    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    srv.daemon_threads = True
    srv.store = Store(a.data)
    srv.limiter = Limiter()
    print(f'tsb relay on {a.host}:{srv.server_address[1]}, {len(srv.store.tokens)} addresses, data in {a.data}', flush=True)
    srv.serve_forever()


if __name__ == '__main__':
    main()
