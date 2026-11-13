#!/usr/bin/env python3
"""The local test server and the picture client on a Windows machine with a graphics card.

    winmc.py setup            write the server's and the client's settings (keeps what is there)
    winmc.py up               server, then client; returns when the camera player has joined
    winmc.py down             client, then server
    winmc.py restart          down + up (needed after biome or timeline files change)
    winmc.py status
    winmc.py server-up | server-down | client-up | client-down
    winmc.py gpu              free video memory, and whether the client may start

Everything lives under one folder, MC_ROOT (default: the current directory):
    jre/<name>/bin/java.exe   Java 25
    client26/                 the files from fetch_client.py, natives/, game/ (options, resource
                              packs, logs)
    server26/                 server.jar (fetch_client.py --server), the world, .rcon_pw
The server listens on 127.0.0.1 only; the client is started offline and joins that server alone.

The machine is somebody's desktop and has other work on its graphics card:
  - the client is not started unless MC_MIN_VRAM megabytes of video memory are free (default 2048);
  - the game window is shown without the keyboard and put behind the other windows;
  - only processes whose program lives under MC_ROOT are ever stopped.

Environment: MC_ROOT, MC_VERSION (26.3), MC_CAM (C164Cam), MC_SIZE (1280x720), MC_VIEW (render
distance in chunks at setup, 14), MC_SERVER_HEAP (2G), MC_CLIENT_HEAP (4G), MC_MIN_VRAM.
"""
import glob
import hashlib
import json
import os
import secrets
import sys
import time
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import winctl as W  # noqa: E402
from rcon import Rcon  # noqa: E402

ROOT = os.path.abspath(os.environ.get("MC_ROOT", os.getcwd()))
SERVER = os.path.join(ROOT, "server26")
CLIENT = os.path.join(ROOT, "client26")
GAME = os.path.join(CLIENT, "game")
VERSION = os.environ.get("MC_VERSION", "26.3")
CAM = os.environ.get("MC_CAM", "C164Cam")
SIZE = os.environ.get("MC_SIZE", "1280x720")
MIN_VRAM = int(os.environ.get("MC_MIN_VRAM", "2048"))
HOST, PORT, RCON_PORT = "127.0.0.1", 25599, 25598

SERVER_PROPERTIES = """\
allow-flight=true
broadcast-console-to-ops=true
broadcast-rcon-to-ops=false
difficulty=easy
enable-rcon=true
enable-status=true
force-gamemode=true
function-permission-level=2
gamemode=spectator
generate-structures=false
generator-settings={{"biome":"minecraft:the_void","layers":[{{"block":"minecraft:air","height":1}}]}}
level-name=art
level-type=minecraft:flat
max-chained-neighbor-updates=1000000
max-players=10
max-tick-time=-1
motd=c164 local test
online-mode=false
op-permission-level=4
pause-when-empty-seconds=-1
player-idle-timeout=0
rcon.password={password}
rcon.port={rcon_port}
server-ip={host}
server-port={port}
simulation-distance=6
spawn-protection=0
sync-chunk-writes=false
view-distance={view}
white-list=false
"""

# What the pictures depend on. The game adds every other option with its default on first start.
OPTIONS = """\
version:5023
ao:true
biomeBlendRadius:2
chunkSectionFadeInTime:0.0
cutoutLeaves:true
enableVsync:false
entityDistanceScaling:1.0
entityShadows:true
fov:0.0
fovEffectScale:1.0
graphicsPreset:"custom"
fullscreen:false
gamma:0.5
guiScale:2
maxAnisotropyBit:2
textureFiltering:0
maxFps:60
improvedTransparency:false
inactivityFpsLimit:"minimized"
mipmapLevels:4
narrator:0
particles:0
renderClouds:"true"
cloudRange:128
renderDistance:{view}
simulationDistance:5
vignette:false
weatherRadius:10
autoJump:false
realmsNotifications:false
bobView:false
resourcePacks:["vanilla","file/c164art"]
incompatibleResourcePacks:[]
lang:en_us
chatVisibility:2
pauseOnLostFocus:false
tutorialStep:none
skipMultiplayerWarning:true
joinedFirstServer:true
onboardAccessibility:false
telemetryOptInExtra:false
musicToast:"never"
soundCategory_master:0.0
"""


def java():
    found = sorted(glob.glob(os.path.join(ROOT, "jre", "*", "bin", "java.exe")))
    if not found:
        raise SystemExit(f"no Java under {os.path.join(ROOT, 'jre')}")
    return found[-1]


def rcon(*commands):
    with open(os.path.join(SERVER, ".rcon_pw")) as fh:
        password = fh.read().strip()
    rc = Rcon(HOST, RCON_PORT, password, timeout=10.0)
    try:
        return [rc.command(c) for c in commands]
    finally:
        rc.close()


def answers():
    try:
        return rcon("list")[0]
    except (OSError, PermissionError):
        return None


def read_pid(path):
    try:
        with open(path) as fh:
            return int(fh.read().strip())
    except (OSError, ValueError):
        return None


def running(path):
    """The process id noted in a file, if that process is still one of ours."""
    pid = read_pid(path)
    return pid if pid and W.ours(pid, ROOT) else None


# ---- setup ---------------------------------------------------------------------------------------
def setup():
    view = int(os.environ.get("MC_VIEW", "14"))
    os.makedirs(SERVER, exist_ok=True)
    os.makedirs(os.path.join(GAME, "resourcepacks"), exist_ok=True)
    pw_file = os.path.join(SERVER, ".rcon_pw")
    if not os.path.exists(pw_file):
        with open(pw_file, "w") as fh:
            fh.write(secrets.token_hex(16))
    with open(pw_file) as fh:
        password = fh.read().strip()
    written = []
    props = os.path.join(SERVER, "server.properties")
    if not os.path.exists(props):
        with open(props, "w", encoding="utf-8") as fh:
            fh.write(SERVER_PROPERTIES.format(password=password, rcon_port=RCON_PORT, host=HOST, port=PORT,
                                              view=max(view, 10)))
        written.append(props)
    eula = os.path.join(SERVER, "eula.txt")
    if not os.path.exists(eula):
        with open(eula, "w") as fh:
            fh.write("eula=true\n")
        written.append(eula)
    options = os.path.join(GAME, "options.txt")
    if not os.path.exists(options):
        with open(options, "w", encoding="utf-8") as fh:
            fh.write(OPTIONS.format(view=view))
        written.append(options)
    print("written: " + (", ".join(os.path.relpath(p, ROOT) for p in written) or "nothing, all there"))


# ---- server --------------------------------------------------------------------------------------
def server_up():
    if answers() is not None:
        print("server is up")
        return
    pid_file = os.path.join(SERVER, "server.pid")
    if not running(pid_file):
        heap = os.environ.get("MC_SERVER_HEAP", "2G")
        pid = W.start([java(), "-Xms512M", f"-Xmx{heap}", "-jar", "server.jar", "nogui"], SERVER,
                      os.path.join(SERVER, "console.log"))
        with open(pid_file, "w") as fh:
            fh.write(str(pid))
    for _ in range(300):
        if answers() is not None:
            print("server is up")
            return
        if not running(pid_file):
            raise SystemExit(f"server ended; see {os.path.join(SERVER, 'console.log')}")
        time.sleep(2)
    raise SystemExit(f"server did not come up; see {os.path.join(SERVER, 'console.log')}")


def server_down():
    pid_file = os.path.join(SERVER, "server.pid")
    if answers() is not None:
        try:
            rcon("save-all flush", "stop")
        except (OSError, PermissionError):
            pass
    pid = running(pid_file)
    for _ in range(60):
        if not pid or not W.ours(pid, ROOT):
            break
        time.sleep(1)
    else:
        W.stop(pid, ROOT)
    if os.path.exists(pid_file):
        os.remove(pid_file)
    print("server stopped")


# ---- client --------------------------------------------------------------------------------------
def offline_uuid(name):
    d = bytearray(hashlib.md5(("OfflinePlayer:" + name).encode()).digest())
    d[6] = (d[6] & 0x0F) | 0x30
    d[8] = (d[8] & 0x3F) | 0x80
    return uuid.UUID(bytes=bytes(d)).hex


def client_command():
    with open(os.path.join(CLIENT, "versions", VERSION, f"{VERSION}.json")) as fh:
        asset_index = json.load(fh)["assetIndex"]["id"]
    with open(os.path.join(CLIENT, f"classpath-{VERSION}.txt"), encoding="utf-8") as fh:
        classpath = os.pathsep.join(os.path.join(CLIENT, line.strip()) for line in fh if line.strip())
    natives = os.path.join(CLIENT, "natives")
    width, height = SIZE.split("x")
    heap = os.environ.get("MC_CLIENT_HEAP", "4G")
    return [
        java(), "-Xms512M", f"-Xmx{heap}",
        "-XX:StackShadowPages=32", "--enable-native-access=ALL-UNNAMED",
        "--add-exports", "java.base/jdk.internal.misc=ALL-UNNAMED",
        f"-Djava.library.path={os.path.join(natives, 'java')}", f"-Djna.tmpdir={os.path.join(natives, 'jna')}",
        f"-Dorg.lwjgl.system.SharedLibraryExtractPath={os.path.join(natives, 'lwjgl')}",
        f"-Dio.netty.native.workdir={os.path.join(natives, 'netty')}",
        "-Dminecraft.launcher.brand=c164-test", "-Dminecraft.launcher.version=1",
        "-cp", classpath, "net.minecraft.client.main.Main",
        "--username", CAM, "--version", VERSION, "--gameDir", GAME,
        "--assetsDir", os.path.join(CLIENT, "assets"), "--assetIndex", asset_index,
        "--uuid", offline_uuid(CAM), "--accessToken", "0", "--clientId", "0", "--xuid", "0",
        "--versionType", "release", "--width", width, "--height", height,
        "--quickPlayMultiplayer", f"{HOST}:{PORT}",
    ]


def gpu():
    free = W.free_vram()
    if free is None:
        print("video memory: cannot tell (no nvidia-smi answer)")
        return False
    ok = free >= MIN_VRAM
    print(f"video memory free: {free} MB, needed: {MIN_VRAM} MB -> " + ("may start" if ok else "not now"))
    return ok


def client_up():
    pid_file = os.path.join(CLIENT, "client.pid")
    pid = running(pid_file)
    if not pid:
        if answers() is None:
            raise SystemExit("server is not up")
        if not gpu():
            raise SystemExit(3)
        for name in ("java", "jna", "lwjgl", "netty"):
            os.makedirs(os.path.join(CLIENT, "natives", name), exist_ok=True)
        pid = W.start(client_command(), GAME, os.path.join(CLIENT, "client.log"))
        with open(pid_file, "w") as fh:
            fh.write(str(pid))
    stepped = False
    for _ in range(240):
        if not W.ours(pid, ROOT):
            raise SystemExit(f"client ended; see {os.path.join(CLIENT, 'client.log')}")
        for hwnd in W.game_windows(pid):
            W.step_back(hwnd)
            stepped = True
        listed = answers()
        if listed and CAM in listed:
            time.sleep(2)
            for hwnd in W.game_windows(pid):
                W.step_back(hwnd)
            print(f"{CAM} is online" + ("" if stepped else " (no window seen)"))
            return
        time.sleep(1)
    raise SystemExit(f"{CAM} did not join; see {os.path.join(CLIENT, 'client.log')}")


def client_down():
    pid_file = os.path.join(CLIENT, "client.pid")
    pid = running(pid_file)
    if pid:
        for hwnd in W.game_windows(pid):
            W.close(hwnd)
        for _ in range(20):
            if not W.ours(pid, ROOT):
                break
            time.sleep(1)
        else:
            W.stop(pid, ROOT)
        print("client stopped")
    if os.path.exists(pid_file):
        os.remove(pid_file)


def status():
    listed = answers()
    print("server: " + (listed.strip() if listed is not None else "no answer"))
    pid = running(os.path.join(CLIENT, "client.pid"))
    if pid:
        sizes = [W.client_size(h) for h in W.game_windows(pid)]
        print(f"client: process {pid}, windows {sizes}")
    else:
        print("client: not running")
    gpu()


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "status"
    steps = {
        "setup": [setup], "up": [server_up, client_up], "down": [client_down, server_down],
        "restart": [client_down, server_down, server_up, client_up], "status": [status], "gpu": [gpu],
        "server-up": [server_up], "server-down": [server_down],
        "client-up": [client_up], "client-down": [client_down],
    }
    if what not in steps:
        raise SystemExit("usage: winmc.py " + "|".join(steps))
    for step in steps[what]:
        step()


if __name__ == "__main__":
    main()
