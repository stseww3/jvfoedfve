import asyncio, socket, struct

SO_BINDTODEVICE = 25

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

def should_use_tun(host, dev):
    if not dev:
        return False
    h = host.lower()
    # Only the lobby servers (1/4/5.territorial.io) need IP splitting (3 on Host + 2 on tun5)!
    # game.territorial.io (in-game ticks) and territorial.io (HTML/Server 0) run on 10Gbps direct Host!
    return h in ("1.territorial.io", "4.territorial.io", "5.territorial.io", "api.ipify.org")

async def handle_client(reader, writer, dev):
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

        loop = asyncio.get_running_loop()
        infos = await loop.getaddrinfo(host, port, family=socket.AF_INET, type=socket.SOCK_STREAM)
        if not infos:
            writer.write(b"\x05\x04\x00\x01\x00\x00\x00\x00\x00\x00")
            await writer.drain()
            writer.close()
            return
        target_addr = infos[0][4]

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(False)
        if should_use_tun(host, dev):
            try:
                sock.setsockopt(socket.SOL_SOCKET, SO_BINDTODEVICE, dev.encode("utf-8") + b"\x00")
            except Exception:
                pass

        try:
            await asyncio.wait_for(loop.sock_connect(sock, target_addr), timeout=4)
        except Exception:
            try:
                sock.close()
            except Exception:
                pass
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setblocking(False)
            await asyncio.wait_for(loop.sock_connect(sock, target_addr), timeout=4)

        rem_reader, rem_writer = await asyncio.open_connection(sock=sock)
        writer.write(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")
        await writer.drain()
        await asyncio.gather(pipe(reader, rem_writer), pipe(rem_reader, writer))
    except Exception:
        try:
            writer.close()
        except Exception:
            pass

async def main():
    # 3 bots (10801, 10803, 10804) use direct Host IP ("" = no tunnel wait!);
    # 2 bots (10802, 10805) use live tun5 for lobby!
    mappings = [(10801, ""), (10802, "tun5"), (10803, ""), (10804, ""), (10805, "tun5")]
    servers = []
    for port, dev in mappings:
        srv = await asyncio.start_server(lambda r, w, d=dev: handle_client(r, w, d), "127.0.0.1", port)
        servers.append(srv)
        print(f"SOCKS5 listening on 127.0.0.1:{port} -> {dev or 'DIRECT_HOST'}", flush=True)
    await asyncio.gather(*(s.serve_forever() for s in servers))

asyncio.run(main())
