import asyncio, base64, os, random, socket, string, struct, urllib.parse

SO_BINDTODEVICE = 25
GPROXY_CONF_PATH = "/tmp/gproxy.conf"

# Per-port sticky session & country config when using upstream HTTP proxy (gproxy)
PORT_COUNTRY = {
    10801: "us",
    10802: "GB",
    10803: "JP",
    10804: "us",
    10805: "GB",
    10811: "DE",
    10812: "JP",
    10813: "us",
    10814: "GB",
    10815: "DE",
}
PORT_SESSION = {}

def rand_session_id():
    alphabet = string.ascii_lowercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(8))

def get_port_session(local_port, rotate=False):
    if rotate or local_port not in PORT_SESSION:
        PORT_SESSION[local_port] = rand_session_id()
    return PORT_SESSION[local_port]

def load_upstream_http_proxy():
    raw = os.environ.get("GPROXY_URL", "").strip()
    if not raw and os.path.exists(GPROXY_CONF_PATH):
        try:
            with open(GPROXY_CONF_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        raw = line
                        break
        except Exception:
            pass
    if not raw:
        return None
    parsed = urllib.parse.urlsplit(raw)
    if not parsed.hostname or not parsed.port:
        return None
    user = urllib.parse.unquote(parsed.username or "")
    pw = urllib.parse.unquote(parsed.password or "")
    # Strip any trailing _country-XX so we can attach per-port country & sticky session
    if "_country-" in pw:
        pw = pw.split("_country-")[0]
    return {
        "host": parsed.hostname,
        "port": parsed.port,
        "user": user,
        "pw": pw,
    }

async def pipe(reader, writer):
    try:
        while True:
            data = await reader.read(65536)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except Exception:
        pass
    finally:
        try:
            writer.close()
        except Exception:
            pass

def should_use_tun(host, local_port):
    h = host.lower()
    return "territorial.io" in h or h == "api.ipify.org"

async def connect_via_http_proxy(upstream, target_host, target_port, local_port):
    country = PORT_COUNTRY.get(local_port, "JP")
    for attempt in range(2):
        sid = get_port_session(local_port, rotate=(attempt > 0))
        auth_str = f"{upstream['user']}:{upstream['pw']}_country-{country}_session-{sid}"
        b64_auth = base64.b64encode(auth_str.encode("utf-8")).decode("ascii")
        rem_reader = rem_writer = None
        try:
            rem_reader, rem_writer = await asyncio.wait_for(
                asyncio.open_connection(upstream["host"], upstream["port"]),
                timeout=5.0,
            )
            connect_req = (
                f"CONNECT {target_host}:{target_port} HTTP/1.1\r\n"
                f"Host: {target_host}:{target_port}\r\n"
                f"Proxy-Authorization: Basic {b64_auth}\r\n"
                f"Proxy-Connection: Keep-Alive\r\n\r\n"
            ).encode("utf-8")
            rem_writer.write(connect_req)
            await asyncio.wait_for(rem_writer.drain(), timeout=4.0)
            status_line = await asyncio.wait_for(rem_reader.readline(), timeout=6.0)
            if not status_line or b" 200 " not in status_line:
                rem_writer.close()
                continue
            while True:
                hdr_line = await asyncio.wait_for(rem_reader.readline(), timeout=4.0)
                if not hdr_line or hdr_line in (b"\r\n", b"\n"):
                    break
            return rem_reader, rem_writer
        except Exception:
            if rem_writer is not None:
                try:
                    rem_writer.close()
                except Exception:
                    pass
    return None, None

async def handle_client(reader, writer, devs, local_port):
    try:
        hdr = await asyncio.wait_for(reader.readexactly(2), timeout=5)
        ver, nmethods = hdr[0], hdr[1]
        if ver != 5:
            writer.close()
            return
        await asyncio.wait_for(reader.readexactly(nmethods), timeout=5)
        writer.write(b"\x05\x00")
        await writer.drain()

        req = await asyncio.wait_for(reader.readexactly(4), timeout=5)
        ver, cmd, _, atyp = req
        if cmd != 1:
            writer.close()
            return
        if atyp == 1:
            raw = await reader.readexactly(4)
            host = socket.inet_ntoa(raw)
        elif atyp == 3:
            ln = (await reader.readexactly(1))[0]
            host = (await reader.readexactly(ln)).decode("utf-8", errors="ignore")
        elif atyp == 4:
            raw = await reader.readexactly(16)
            host = socket.inet_ntop(socket.AF_INET6, raw)
        else:
            writer.close()
            return
        port = struct.unpack("!H", await reader.readexactly(2))[0]

        if host == "rotate.proxy.local":
            new_sid = get_port_session(local_port, rotate=True)
            print(f"[SOCKS5:{local_port}] Rotated sticky session -> {new_sid}", flush=True)
            writer.write(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")
            await writer.drain()
            writer.close()
            return

        upstream = load_upstream_http_proxy()
        if upstream is not None and should_use_tun(host, local_port):
            rem_reader, rem_writer = await connect_via_http_proxy(upstream, host, port, local_port)
            if rem_reader is None or rem_writer is None:
                writer.write(b"\x05\x04\x00\x01\x00\x00\x00\x00\x00\x00")
                await writer.drain()
                writer.close()
                return
            writer.write(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")
            await writer.drain()
            await asyncio.gather(pipe(reader, rem_writer), pipe(rem_reader, writer))
            return

        loop = asyncio.get_running_loop()
        infos = await loop.getaddrinfo(host, port, family=socket.AF_INET, type=socket.SOCK_STREAM)
        if not infos:
            writer.write(b"\x05\x04\x00\x01\x00\x00\x00\x00\x00\x00")
            await writer.drain()
            writer.close()
            return
        target_addr = infos[0][4]

        connected_sock = None
        if should_use_tun(host, local_port):
            for dev in devs:
                if not dev:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.setblocking(False)
                    try:
                        await asyncio.wait_for(loop.sock_connect(sock, target_addr), timeout=1.5)
                        connected_sock = sock
                        break
                    except Exception:
                        try:
                            sock.close()
                        except Exception:
                            pass
                    continue
                if not os.path.exists(f"/sys/class/net/{dev}"):
                    continue
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setblocking(False)
                try:
                    sock.setsockopt(socket.SOL_SOCKET, SO_BINDTODEVICE, dev.encode("utf-8") + b"\x00")
                    await asyncio.wait_for(loop.sock_connect(sock, target_addr), timeout=3.5)
                    connected_sock = sock
                    break
                except Exception:
                    try:
                        sock.close()
                    except Exception:
                        pass

        if connected_sock is None:
            if should_use_tun(host, local_port):
                writer.write(b"\x05\x04\x00\x01\x00\x00\x00\x00\x00\x00")
                await writer.drain()
                writer.close()
                return
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setblocking(False)
            await asyncio.wait_for(loop.sock_connect(sock, target_addr), timeout=4)
            connected_sock = sock

        rem_reader, rem_writer = await asyncio.open_connection(sock=connected_sock)
        writer.write(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")
        await writer.drain()
        await asyncio.gather(pipe(reader, rem_writer), pipe(rem_reader, writer))
    except Exception:
        try:
            writer.close()
        except Exception:
            pass

async def main():
    # Verified live residential public exit IPs across 8 bots (NEVER falls back to host IP):
    # tun67 (106.177.117.146 JP), tun37 (175.113.163.59 KR), tun43 (119.194.46.117 KR),
    # tun49 (180.65.115.60 KR), tun50 (113.154.84.113 JP), tun33 (121.146.152.111 KR),
    # tun47 (61.82.162.106 KR), tun22 (183.88.237.254 TH), tun58 (14.132.214.239 JP)
    mappings = [
        (10801, ["tun49", "tun50", "tun37"]),
        (10802, ["tun50", "tun49", "tun43"]),
        (10803, ["tun50", "tun31", "tun49"]),
        (10804, ["tun67", "tun50", "tun49"]),
        (10805, ["tun33", "tun49", "tun50"]),
        (10811, ["tun37", "tun49", "tun50"]),
        (10812, ["tun31", "tun58", "tun50"]),
        (10813, ["tun43", "tun49", "tun37"]),
        (10814, ["tun49", "tun50", "tun67"]),
        (10815, ["tun47", "tun33", "tun43"]),
    ]
    servers = []
    for port, devs in mappings:
        srv = await asyncio.start_server(lambda r, w, ds=devs, lp=port: handle_client(r, w, ds, lp), "127.0.0.1", port)
        servers.append(srv)
        print(f"10-Bot SOCKS5 listening on 127.0.0.1:{port} -> {devs}", flush=True)
    await asyncio.gather(*(s.serve_forever() for s in servers))

asyncio.run(main())
