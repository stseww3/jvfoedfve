import asyncio, os, socket, struct

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

def should_use_tun(host, local_port):
    h = host.lower()
    return h in ("1.territorial.io", "api.ipify.org")

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
                    await asyncio.wait_for(loop.sock_connect(sock, target_addr), timeout=1.6)
                    connected_sock = sock
                    break
                except Exception:
                    try:
                        sock.close()
                    except Exception:
                        pass

        if connected_sock is None:
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
    # 10 bots (10801..10805 + 10811..10815), each with its own dedicated primary + backup tunnel exit IP!
    mappings = [
        (10801, ["tun90", "tun13"]),
        (10802, ["tun50", "tun22"]),
        (10803, ["tun55", "tun13"]),
        (10804, ["tun58", "tun22"]),
        (10805, ["tun66", "tun90"]),
        (10811, ["tun67", "tun50"]),
        (10812, ["tun78", "tun55"]),
        (10813, ["tun80", "tun58"]),
        (10814, ["tun83", "tun66"]),
        (10815, ["tun86", "tun67"]),
    ]
    servers = []
    for port, devs in mappings:
        srv = await asyncio.start_server(lambda r, w, ds=devs, lp=port: handle_client(r, w, ds, lp), "127.0.0.1", port)
        servers.append(srv)
        print(f"10-Bot SOCKS5 listening on 127.0.0.1:{port} -> {devs}", flush=True)
    await asyncio.gather(*(s.serve_forever() for s in servers))

asyncio.run(main())
