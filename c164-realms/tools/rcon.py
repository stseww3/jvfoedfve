#!/usr/bin/env python3
"""Minimal Minecraft RCON client for driving a local test server.

Usage:
  rcon.py [--host 127.0.0.1] [--port 25598] [--pw-file PATH] "command" ["command" ...]
  rcon.py ... --stdin          # one command per line from stdin

The password is read from --pw-file or the RCON_PASSWORD environment variable.
"""
import argparse
import os
import socket
import struct
import sys

LOGIN, COMMAND, RESPONSE = 3, 2, 0
# Minecraft answers any unknown packet type with "Unknown request <hex>"; used as an end marker
# because long replies are split into several packets.
PROBE = 100


class Rcon:
    def __init__(self, host="127.0.0.1", port=25598, password="", timeout=30.0):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.req = 0
        self._send(LOGIN, password)
        rid, _, _ = self._recv()
        if rid == -1:
            raise PermissionError("RCON login rejected")

    def _send(self, ptype, payload):
        self.req += 1
        body = struct.pack("<ii", self.req, ptype) + payload.encode("utf-8") + b"\x00\x00"
        self.sock.sendall(struct.pack("<i", len(body)) + body)
        return self.req

    def _read_exact(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("RCON connection closed")
            buf += chunk
        return buf

    def _recv(self):
        (length,) = struct.unpack("<i", self._read_exact(4))
        body = self._read_exact(length)
        rid, ptype = struct.unpack("<ii", body[:8])
        return rid, ptype, body[8:-2].decode("utf-8", errors="replace")

    def command(self, cmd):
        cmd_id = self._send(COMMAND, cmd)
        rid, _, payload = self._recv()
        parts = [payload] if rid == cmd_id else []
        # The server handles one packet per socket read, so the probe must not be sent
        # together with the command.
        probe_id = self._send(PROBE, "")
        while True:
            rid, _, payload = self._recv()
            if rid == probe_id:
                break
            if rid == cmd_id:
                parts.append(payload)
        return "".join(parts)

    def close(self):
        self.sock.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=25598)
    ap.add_argument("--pw-file")
    ap.add_argument("--stdin", action="store_true")
    ap.add_argument("--quiet", action="store_true", help="print only replies, without echoing commands")
    ap.add_argument("commands", nargs="*")
    args = ap.parse_args()

    if args.pw_file:
        with open(args.pw_file) as fh:
            password = fh.read().strip()
    else:
        password = os.environ.get("RCON_PASSWORD", "")

    commands = list(args.commands)
    if args.stdin:
        commands += [line.rstrip("\n") for line in sys.stdin if line.strip() and not line.startswith("#")]

    rc = Rcon(args.host, args.port, password)
    try:
        for cmd in commands:
            reply = rc.command(cmd)
            if args.quiet:
                print(reply)
            else:
                print(f"> {cmd}\n{reply}")
    finally:
        rc.close()


if __name__ == "__main__":
    main()
