#!/usr/bin/env python3
"""Minimal offline-mode Minecraft client ("fake player") for testing map logic on a local server.

It logs in, stays alive, sends commands as a non-OP player and records what the server shows
the player (chat, titles, action bar, dialogs, sounds). It does not simulate physics or load chunks.

Written against protocol 777 (26.3); packet ids come from tools/data/packets-777.json, packet
layouts were read from the unobfuscated 26.3 server jar.

Usage as a script:
    mcbot.py --name Tester --port 25599 --stay 5 "trigger my_objective set 1"
"""
import argparse
import hashlib
import json
import os
import socket
import struct
import time
import uuid
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------- wire primitives

def enc_varint(value):
    value &= 0xFFFFFFFF
    out = bytearray()
    while True:
        b = value & 0x7F
        value >>= 7
        if value:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def enc_string(text):
    raw = text.encode("utf-8")
    return enc_varint(len(raw)) + raw


class Reader:
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def take(self, n):
        if self.pos + n > len(self.data):
            raise EOFError("packet too short")
        chunk = self.data[self.pos:self.pos + n]
        self.pos += n
        return chunk

    def remaining(self):
        return len(self.data) - self.pos

    def varint(self):
        result = 0
        for shift in range(0, 35, 7):
            b = self.take(1)[0]
            result |= (b & 0x7F) << shift
            if not b & 0x80:
                break
        if result & 0x80000000:
            result -= 1 << 32
        return result

    def string(self):
        return self.take(self.varint()).decode("utf-8", errors="replace")

    def fmt(self, f):
        size = struct.calcsize(f)
        return struct.unpack(f, self.take(size))

    def boolean(self):
        return self.take(1)[0] != 0

    # --- network NBT: a type byte followed by the payload, without a root name
    def nbt(self):
        tag = self.take(1)[0]
        return self._nbt_payload(tag)

    def _nbt_payload(self, tag):
        if tag == 0:
            return None
        if tag == 1:
            return self.fmt(">b")[0]
        if tag == 2:
            return self.fmt(">h")[0]
        if tag == 3:
            return self.fmt(">i")[0]
        if tag == 4:
            return self.fmt(">q")[0]
        if tag == 5:
            return self.fmt(">f")[0]
        if tag == 6:
            return self.fmt(">d")[0]
        if tag == 7:
            return list(self.take(self.fmt(">i")[0]))
        if tag == 8:
            return self.take(self.fmt(">H")[0]).decode("utf-8", errors="replace")
        if tag == 9:
            inner = self.take(1)[0]
            count = self.fmt(">i")[0]
            return [self._nbt_payload(inner) for _ in range(count)]
        if tag == 10:
            out = {}
            while True:
                inner = self.take(1)[0]
                if inner == 0:
                    return out
                name = self.take(self.fmt(">H")[0]).decode("utf-8", errors="replace")
                out[name] = self._nbt_payload(inner)
        if tag == 11:
            return [self.fmt(">i")[0] for _ in range(self.fmt(">i")[0])]
        if tag == 12:
            return [self.fmt(">q")[0] for _ in range(self.fmt(">i")[0])]
        raise ValueError(f"unknown NBT tag {tag}")


def flatten_text(component):
    """Plain text of a text component that was read from NBT."""
    if component is None:
        return ""
    if isinstance(component, str):
        return component
    if isinstance(component, list):
        return "".join(flatten_text(c) for c in component)
    if isinstance(component, dict):
        out = ""
        if "text" in component:
            out += str(component["text"])
        elif "" in component:
            out += str(component[""])
        elif "translate" in component:
            args = [flatten_text(a) for a in component.get("with", [])]
            out += component.get("fallback") or (component["translate"] + ("(" + ", ".join(args) + ")" if args else ""))
        elif "score" in component:
            out += "<score>"
        elif "selector" in component:
            out += str(component["selector"])
        elif "keybind" in component:
            out += str(component["keybind"])
        out += "".join(flatten_text(c) for c in component.get("extra", []))
        return out
    return str(component)


def offline_uuid(name):
    digest = bytearray(hashlib.md5(("OfflinePlayer:" + name).encode("utf-8")).digest())
    digest[6] = (digest[6] & 0x0F) | 0x30
    digest[8] = (digest[8] & 0x3F) | 0x80
    return uuid.UUID(bytes=bytes(digest))


# ---------------------------------------------------------------- the bot

class Disconnected(Exception):
    pass


class Bot:
    def __init__(self, name, host="127.0.0.1", port=25599, packets_file=None, verbose=False):
        self.name = name
        self.host = host
        self.port = port
        self.verbose = verbose
        with open(packets_file or os.path.join(HERE, "data", "packets-777.json")) as fh:
            self.ids = json.load(fh)
        self.protocol = self.ids["protocol_version"]
        self.sock = None
        self.buf = b""
        self.threshold = -1
        self.state = "handshake"
        self.loaded_sent = False
        self.position = None
        self.rotation = (0.0, 0.0)
        self.health = None
        self.closed_reason = None
        # what the server showed this player, in order: (kind, text)
        self.events = []
        self.packet_counts = {}

    # --- framing
    def _send(self, name, payload=b""):
        pid = self.ids[self.state]["serverbound"][name]
        body = enc_varint(pid) + payload
        if self.threshold >= 0:
            if len(body) >= self.threshold:
                body = enc_varint(len(body)) + zlib.compress(body)
            else:
                body = enc_varint(0) + body
        self.sock.sendall(enc_varint(len(body)) + body)

    def _read_packet(self, timeout):
        """Return (packet name, Reader) or None on timeout."""
        deadline = time.time() + timeout
        while True:
            packet = self._try_parse()
            if packet is not None:
                return packet
            left = deadline - time.time()
            if left <= 0:
                return None
            self.sock.settimeout(left)
            try:
                chunk = self.sock.recv(65536)
            except socket.timeout:
                return None
            except ConnectionError:
                chunk = b""
            if not chunk:
                raise Disconnected(self.closed_reason or "connection closed by server")
            self.buf += chunk

    def _try_parse(self):
        r = Reader(self.buf)
        try:
            length = r.varint()
            body = r.take(length)
        except EOFError:
            return None
        self.buf = self.buf[r.pos:]
        if self.threshold >= 0:
            br = Reader(body)
            data_len = br.varint()
            rest = body[br.pos:]
            body = zlib.decompress(rest) if data_len else rest
        pr = Reader(body)
        pid = pr.varint()
        table = self.ids[self.state]["clientbound"]
        name = next((k for k, v in table.items() if v == pid), f"unknown_{pid}")
        self.packet_counts[name] = self.packet_counts.get(name, 0) + 1
        return name, pr

    # --- connection
    def connect(self, timeout=30.0):
        self.sock = socket.create_connection((self.host, self.port), timeout=timeout)
        self.state = "handshake"
        self._send("intention", enc_varint(self.protocol) + enc_string(self.host)
                   + struct.pack(">H", self.port) + enc_varint(2))
        self.state = "login"
        self._send("hello", enc_string(self.name) + offline_uuid(self.name).bytes)
        deadline = time.time() + timeout
        while self.state != "play" or not self.loaded_sent:
            if time.time() > deadline:
                raise TimeoutError(f"login did not finish (state={self.state})")
            packet = self._read_packet(1.0)
            if packet:
                self._handle(*packet)
        return self

    def _client_information(self):
        return (enc_string("en_us") + struct.pack(">b", 10) + enc_varint(0) + b"\x01"
                + struct.pack(">B", 0x7F) + enc_varint(1) + b"\x00" + b"\x01" + enc_varint(0))

    def _event(self, kind, text):
        self.events.append((kind, text))
        if self.verbose:
            print(f"[{self.name}] {kind}: {text}")

    def _handle(self, name, r):
        st = self.state
        if st == "login":
            if name == "login_disconnect":
                self.closed_reason = r.string()
                raise Disconnected(self.closed_reason)
            if name == "login_compression":
                self.threshold = r.varint()
            elif name == "login_finished":
                self._send("login_acknowledged")
                self.state = "configuration"
                self._send("client_information", self._client_information())
            elif name == "hello":
                raise Disconnected("server asked for encryption (online-mode=true); this bot is offline-only")
            return

        if name == "keep_alive":
            self._send("keep_alive", r.take(8))
            return
        if name == "ping":
            self._send("pong", r.take(4))
            return
        if name == "disconnect":
            self.closed_reason = flatten_text(r.nbt())
            self._event("disconnect", self.closed_reason)
            raise Disconnected(self.closed_reason)

        if st == "configuration":
            if name == "select_known_packs":
                self._send("select_known_packs", enc_varint(0))
            elif name == "finish_configuration":
                self._send("finish_configuration")
                self.state = "play"
            elif name == "resource_pack_push":
                self._answer_resource_pack(r)
            return

        # play
        if name == "player_position":
            # 26.3: the confirmation echoes the resulting position and rotation, not only the id.
            teleport_id = r.varint()
            x, y, z = r.fmt(">ddd")
            r.fmt(">ddd")  # delta movement
            y_rot, x_rot = r.fmt(">ff")
            relatives = r.fmt(">i")[0]
            old_pos = self.position or (0.0, 0.0, 0.0)
            old_rot = self.rotation
            if relatives & 1:
                x += old_pos[0]
            if relatives & 2:
                y += old_pos[1]
            if relatives & 4:
                z += old_pos[2]
            if relatives & 8:
                y_rot += old_rot[0]
            if relatives & 16:
                x_rot += old_rot[1]
            self.position = (x, y, z)
            self.rotation = (y_rot, x_rot)
            self._send("accept_teleportation", enc_varint(teleport_id) + struct.pack(">dddff", x, y, z, y_rot, x_rot))
            if not self.loaded_sent:
                self._send("player_loaded")
                self.loaded_sent = True
        elif name == "chunk_batch_finished":
            self._send("chunk_batch_received", struct.pack(">f", 20.0))
        elif name == "start_configuration":
            self._send("configuration_acknowledged")
            self.state = "configuration"
        elif name == "system_chat":
            text = flatten_text(r.nbt())
            self._event("actionbar" if r.boolean() else "chat", text)
        elif name == "set_title_text":
            self._event("title", flatten_text(r.nbt()))
        elif name == "set_subtitle_text":
            self._event("subtitle", flatten_text(r.nbt()))
        elif name == "set_action_bar_text":
            self._event("actionbar", flatten_text(r.nbt()))
        elif name == "show_dialog":
            self._event("dialog", f"{r.remaining()} bytes")
        elif name == "set_health":
            self.health = r.fmt(">f")[0]
            if self.health <= 0:
                self._send("client_command", enc_varint(0))
                self._event("respawn", "died, respawn requested")
        elif name == "resource_pack_push":
            self._answer_resource_pack(r)

    def _answer_resource_pack(self, r):
        pack_id = r.take(16)
        url = r.string()
        self._event("resource_pack", url)
        for status in (3, 0):  # accepted, then successfully loaded
            self._send("resource_pack", pack_id + enc_varint(status))

    # --- actions
    def pump(self, seconds):
        """Process incoming packets for the given time. Returns False if the server closed the connection."""
        deadline = time.time() + seconds
        try:
            while True:
                left = deadline - time.time()
                if left <= 0:
                    return True
                packet = self._read_packet(min(left, 0.5))
                if packet:
                    self._handle(*packet)
        except Disconnected:
            return False

    def command(self, cmd):
        """Run a command as this player (no leading slash)."""
        self._send("chat_command", enc_string(cmd.lstrip("/")))

    def texts(self, kind=None):
        return [t for k, t in self.events if kind is None or k == kind]

    def close(self):
        if self.sock:
            try:
                self.sock.close()
            finally:
                self.sock = None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="Tester")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=25599)
    ap.add_argument("--stay", type=float, default=3.0, help="seconds to stay connected after the last command")
    ap.add_argument("commands", nargs="*")
    args = ap.parse_args()

    bot = Bot(args.name, args.host, args.port, verbose=True).connect()
    print(f"[{bot.name}] joined at {bot.position}")
    for cmd in args.commands:
        bot.command(cmd)
        bot.pump(0.5)
    alive = bot.pump(args.stay)
    print(f"[{bot.name}] {'still connected' if alive else 'disconnected: ' + str(bot.closed_reason)}")
    print(f"[{bot.name}] packets seen: {dict(sorted(bot.packet_counts.items(), key=lambda kv: -kv[1])[:12])}")
    bot.close()


if __name__ == "__main__":
    main()
