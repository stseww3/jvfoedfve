#!/usr/bin/env python3
"""The local test server and the picture client on a Linux worker node (no graphics card).

    nodemc.py setup           put in place what the node lacks: the X server and Mesa's software
                              Vulkan driver (apt), Java 25, the game's files (from Mojang, each
                              checked against its SHA-1), the server's and the client's settings.
                              What is there is left alone, except the view distance and the
                              cloud range, which are set to what is asked
    nodemc.py up              server, then client; returns when the camera player has joined
    nodemc.py down            client, then server, then the display; also what an earlier job left
    nodemc.py restart         down + up (needed after biome or timeline files change)
    nodemc.py status
    nodemc.py server-up | server-down | client-up | client-down

The same commands as winmc.py has for the admin's computer, so that the shuttle (win/shuttle.py)
drives either. Everything lives under one folder, MC_ROOT (default /agent/realms-study):
    jdk/<name>/bin/java       Java 25, fetched from Adoptium when the node has none
    client26/                 the files from fetch_client.py, natives/, game/ (options, resource
                              packs, logs)
    server26/                 server.jar (fetch_client.py --server), the world, .rcon_pw
The server listens on 127.0.0.1 only; the client is started offline and joins that server alone.

The client draws on an X display of its own (Xvfb) with Mesa's software renderer: the picture is
the game's, only slow. 26.3 opens its window through SDL and has two backends; under Xvfb the
OpenGL one finds no GLX visual it accepts and the game goes on with Vulkan, which Mesa's lavapipe
serves on the processor (verify/server-26.3-check.md; the game's log says "Using graphics backend
Vulkan ... llvmpipe"). So the node needs the Vulkan loader and that driver, and setup installs
them. The client is started through the picture helper (win/CamHelper.java, its class comes with
the checkout), so that tools/shoot.py can ask the game for its own screenshot; without the helper
(MC_HELPER=0), or when the game cannot save one, shoot.py takes the pictures off the X display.

A node keeps its disk between jobs and runs one job at a time, but a job that was cut short may
have left the game running: `down` also stops every server, client and display that was started
from MC_ROOT, whoever noted its process id.

Environment: MC_ROOT, MC_VERSION (26.3), MC_CAM (C164Cam), MC_SIZE (1280x720), MC_DISPLAY (164),
MC_VIEW (the client's render distance in chunks, 12), MC_SERVER_VIEW (the server's view distance,
10: what a Realm runs at and cannot change -- the client draws the smaller of the two; these are
the distances the board is judged at), MC_CLOUDS (cloud range in chunks, 128), MC_SERVER_HEAP (1500M), MC_CLIENT_HEAP (3G), LP_NUM_THREADS (the cores),
MC_HELPER, JAVA (a Java 25 binary to use instead of looking for one).
"""
import ctypes.util
import glob
import hashlib
import json
import os
import re
import secrets
import shutil
import signal
import subprocess
import sys
import tarfile
import time
import urllib.request
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from rcon import Rcon  # noqa: E402

ROOT = os.path.abspath(os.environ.get("MC_ROOT", "/agent/realms-study"))
SERVER = os.path.join(ROOT, "server26")
CLIENT = os.path.join(ROOT, "client26")
GAME = os.path.join(CLIENT, "game")
VERSION = os.environ.get("MC_VERSION", "26.3")
CAM = os.environ.get("MC_CAM", "C164Cam")
SIZE = os.environ.get("MC_SIZE", "1280x720")
DISPLAY = os.environ.get("MC_DISPLAY", "164")
VIEW = int(os.environ.get("MC_VIEW", "12"))
SERVER_VIEW = int(os.environ.get("MC_SERVER_VIEW", "10"))
CLOUDS = int(os.environ.get("MC_CLOUDS", "128"))
HOST, PORT, RCON_PORT = "127.0.0.1", 25599, 25598
JAVA_MAJOR = 25
ADOPTIUM = ("https://api.adoptium.net/v3/assets/latest/{major}/hotspot"
            "?architecture=x64&image_type=jre&os=linux&vendor=eclipse")
HELPER_SOURCE = os.path.join(HERE, "win", "CamHelper.java")
HELPER = os.path.join(CLIENT, "helper")
ASKS = "c164cam"        # folder under GAME through which the helper is asked for pictures (shoot.py)
PIDS = {"server": os.path.join(SERVER, "server.pid"), "client": os.path.join(CLIENT, "client.pid"),
        "display": os.path.join(CLIENT, "xvfb.pid")}

# The settings are winmc.py's (the admin's computer, 11-14), so that a picture means the same on
# either machine; only the distances differ: the board is judged at 12 chunks.
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
cloudRange:{clouds}
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


def say(text):
    try:
        print(f"[nodemc {time.strftime('%H:%M:%S')}] {text}", flush=True)
    except OSError:
        # nobody reads us any more: the trip that started this was killed. `down` goes on all the
        # same, or the game would be left running on the node
        pass


# ---- processes -----------------------------------------------------------------------------------
def link(pid, what):
    try:
        return os.readlink(f"/proc/{pid}/{what}")
    except OSError:
        return ""


def ours(pid):
    """True when the process is alive and was started from MC_ROOT (its program lives there, or
    its working directory does). Nothing is stopped on the strength of a number in a file alone."""
    root = os.path.realpath(ROOT) + os.sep
    return any((os.path.realpath(p) + os.sep).startswith(root) for p in (link(pid, "exe"), link(pid, "cwd")) if p)


def read_pid(path):
    try:
        with open(path) as fh:
            return int(fh.read().strip())
    except (OSError, ValueError):
        return None


def running(kind):
    """The process id noted for the server, the client or the display, if it is still ours."""
    pid = read_pid(PIDS[kind])
    return pid if pid and ours(pid) else None


def start(cmd, cwd, log, env=None, kind=None):
    """Start a program that outlives the caller, in a session of its own; its output goes to `log`."""
    with open(log, "ab", buffering=0) as out:
        proc = subprocess.Popen(cmd, cwd=cwd, stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                env=env, close_fds=True, start_new_session=True)
    if kind:
        with open(PIDS[kind], "w") as fh:
            fh.write(str(proc.pid))
    try:        # if the machine runs out of memory, ours should be the ones to go
        with open(f"/proc/{proc.pid}/oom_score_adj", "w") as fh:
            fh.write("600")
    except OSError:
        pass
    return proc.pid


def stop(pid, wait=20):
    """End one of our own processes: asked first, then killed."""
    if not ours(pid):
        return False
    for sig, patience in ((signal.SIGTERM, wait), (signal.SIGKILL, 5)):
        try:
            os.kill(pid, sig)
        except OSError:
            return True
        end = time.monotonic() + patience
        while time.monotonic() < end:
            if not ours(pid):
                return True
            time.sleep(0.5)
    return not ours(pid)


def strays(pattern, anybody=False):
    """Process ids of ours whose command line matches, whatever the pid files say; with `anybody`,
    of whoever started them."""
    found = []
    for path in glob.glob("/proc/[0-9]*/cmdline"):
        pid = int(path.split("/")[2])
        if pid == os.getpid():
            continue
        try:
            with open(path, "rb") as fh:
                line = fh.read().replace(b"\0", b" ").decode("utf-8", "replace")
        except OSError:
            continue
        if re.search(pattern, line) and (anybody or ours(pid)):
            found.append(pid)
    return found


def tail(path, n=25):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return "".join(fh.readlines()[-n:]).rstrip()
    except OSError:
        return f"(no {path})"


# ---- the server's answers --------------------------------------------------------------------------
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


# ---- setup -----------------------------------------------------------------------------------------
def java_version(path):
    try:
        out = subprocess.run([path, "-version"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    m = re.search(r'version "(\d+)', out.stderr + out.stdout)
    return int(m.group(1)) if m else None


def java(fetch=False):
    """A Java 25 binary: the one named in JAVA, one under MC_ROOT/jdk, one of the system's; with
    `fetch`, Adoptium's runtime is put under MC_ROOT/jdk when there is none."""
    named = os.environ.get("JAVA")
    candidates = ([named] if named else []) + sorted(glob.glob(os.path.join(ROOT, "jdk", "*", "bin", "java")),
                                                     reverse=True) \
        + sorted(glob.glob("/usr/lib/jvm/*/bin/java")) + [shutil.which("java") or ""]
    for path in candidates:
        if path and os.access(path, os.X_OK) and java_version(path) == JAVA_MAJOR:
            return path
    if not fetch:
        raise SystemExit(f"no Java {JAVA_MAJOR} here (nodemc.py setup fetches one)")
    try:
        return fetch_java()
    except SystemExit as stop:
        package = f"openjdk-{JAVA_MAJOR}-jre-headless"
        say(f"{stop}; trying the system's {package}")
        if apt_install([package]):
            for path in sorted(glob.glob("/usr/lib/jvm/*/bin/java")):
                if java_version(path) == JAVA_MAJOR:
                    return path
        raise


def get(url, tries=4):
    last = None
    for attempt in range(tries):
        if attempt:
            time.sleep(3 * 2 ** (attempt - 1))
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "c164-nodemc"})
            with urllib.request.urlopen(request, timeout=300) as resp:
                return resp.read()
        except Exception as exc:  # retried, then reported
            last = exc
    raise SystemExit(f"cannot fetch {url}: {last}")


def fetch_java():
    """Adoptium's Java 25 runtime for Linux x64 into MC_ROOT/jdk, checked against its SHA-256."""
    package = json.loads(get(ADOPTIUM.format(major=JAVA_MAJOR)))[0]["binary"]["package"]
    say(f"java: fetching {package['name']} ({package['size'] >> 20} MB) from Adoptium")
    data = get(package["link"])
    if hashlib.sha256(data).hexdigest() != package["checksum"]:
        raise SystemExit(f"java: {package['name']} does not have the SHA-256 Adoptium gives for it")
    target = os.path.join(ROOT, "jdk")
    os.makedirs(target, exist_ok=True)
    archive = os.path.join(target, package["name"])
    with open(archive, "wb") as fh:
        fh.write(data)
    with tarfile.open(archive) as tar:
        tar.extractall(target, filter="data")
    os.remove(archive)
    found = sorted(glob.glob(os.path.join(target, "*", "bin", "java")), reverse=True)
    for path in found:
        if java_version(path) == JAVA_MAJOR:
            return path
    raise SystemExit(f"java: what was unpacked under {target} is not a Java {JAVA_MAJOR}")


def apt_install(packages):
    """Install packages of the system (a node gives sudo without a password). True when it went."""
    # another installation may be at work on a node that was just started: its lock is waited for
    apt = ["sudo", "-n", "env", "DEBIAN_FRONTEND=noninteractive", "apt-get", "-o", "DPkg::Lock::Timeout=180"]
    said = ""
    for attempt in (0, 1):
        try:
            got = subprocess.run(apt + ["install", "-y", "-qq", "--no-install-recommends", *packages],
                                 capture_output=True, text=True, timeout=900)
        except (OSError, subprocess.SubprocessError) as exc:
            said = str(exc)
            break
        if got.returncode == 0:
            return True
        said = (got.stdout + got.stderr).strip()
        if attempt == 0:        # the package lists of a fresh machine may be old or absent
            subprocess.run(apt + ["update", "-qq"], capture_output=True, timeout=600)
    say(f"apt-get install {' '.join(packages)} did not go: {said[-400:]}")
    return False


def library(name):
    return ctypes.util.find_library(name) or glob.glob(f"/usr/lib/x86_64-linux-gnu/lib{name}.so*")


# (what tells that it is there, the package that brings it). The X libraries are the ones SDL
# loads for its window; a display server, the Vulkan loader and Mesa's software driver for it.
SYSTEM = [
    (lambda: shutil.which("Xvfb"), "xvfb"),
    (lambda: library("vulkan"), "libvulkan1"),
    (lambda: glob.glob("/usr/share/vulkan/icd.d/lvp_icd*.json"), "mesa-vulkan-drivers"),     # SOFTWARE_VULKAN
    (lambda: shutil.which("vulkaninfo"), "vulkan-tools"),
    (lambda: library("X11"), "libx11-6"), (lambda: library("Xext"), "libxext6"),
    (lambda: library("Xcursor"), "libxcursor1"), (lambda: library("Xi"), "libxi6"),
    (lambda: library("Xrandr"), "libxrandr2"), (lambda: library("Xfixes"), "libxfixes3"),
    (lambda: library("Xss"), "libxss1"), (lambda: library("xkbcommon"), "libxkbcommon0"),
]
NEEDED = ("xvfb", "libvulkan1", "mesa-vulkan-drivers")      # without these there is no picture
SOFTWARE_VULKAN = "/usr/share/vulkan/icd.d/lvp_icd*.json"   # the description of Mesa's software driver


def system():
    """The packages the client needs of the system; installs the ones that are missing."""
    missing = [package for there, package in SYSTEM if not there()]
    if missing:
        say("installing " + " ".join(missing))
        went = apt_install(missing)
        still = [package for there, package in SYSTEM if not there()]
        if [p for p in still if p in NEEDED]:
            raise SystemExit("the node lacks " + " ".join(still) + " and apt-get could not install "
                             + ("them" if len(still) > 1 else "it"))
        say("installed" if went and not still else "still missing, the game is tried without: " + " ".join(still))
    say("vulkan: " + vulkan())


def software():
    """The environment that makes Mesa draw on the processor: OpenGL through llvmpipe, and of the
    Vulkan drivers the package brings (for graphics cards the node does not have) only lavapipe."""
    env = {"LIBGL_ALWAYS_SOFTWARE": "1", "GALLIUM_DRIVER": "llvmpipe",
           "LP_NUM_THREADS": os.environ.get("LP_NUM_THREADS", str(os.cpu_count() or 4))}
    driver = sorted(glob.glob(SOFTWARE_VULKAN))
    if driver:
        env["VK_DRIVER_FILES"] = env["VK_ICD_FILENAMES"] = driver[0]     # the loader's name for it, new and old
    return env


def vulkan():
    """What Vulkan the machine offers, in a line: the device and its driver, as vulkaninfo names them."""
    if not shutil.which("vulkaninfo"):
        return "not asked (no vulkaninfo)"
    # asked without a display: with one, vulkaninfo opens a window on it first, and a node's own
    # desktop refuses that
    env = {key: value for key, value in os.environ.items() if key not in ("DISPLAY", "WAYLAND_DISPLAY")}
    try:
        got = subprocess.run(["vulkaninfo", "--summary"], capture_output=True, text=True, timeout=60,
                             env={**env, **software()})
    except (OSError, subprocess.SubprocessError) as exc:
        return f"vulkaninfo failed ({exc})"
    found = re.findall(r"^\s*(deviceName|driverInfo|apiVersion)\s*=\s*(.+)$", got.stdout, re.M)
    if not found:
        return "vulkaninfo names no device: " + " ".join((got.stdout + got.stderr).split())[-300:]
    return ", ".join(f"{key} {value.strip()}" for key, value in found[:6])


def set_line(path, key, sep, value):
    """Make `key<sep>value` the file's line for that key. Returns True when the file changed."""
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    want, hit = f"{key}{sep}{value}", False
    for i, line in enumerate(lines):
        if line.startswith(key + sep):
            if line == want:
                return False
            lines[i], hit = want, True
    if not hit:
        lines.insert(len(lines) - 1 if lines and lines[-1] == "" else len(lines), want)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines))
    return True


def game_files():
    """The client's libraries and assets and the server's jar, through fetch_client.py. A note is
    left when they are whole, so that the next job does not hash five thousand files again."""
    note = os.path.join(CLIENT, f"fetched-{VERSION}.json")
    need = [os.path.join(CLIENT, f"classpath-{VERSION}.txt"), os.path.join(SERVER, "server.jar"),
            os.path.join(CLIENT, "versions", VERSION, f"{VERSION}.jar"), note]
    if all(os.path.exists(p) for p in need):
        with open(note) as fh:
            say(f"game files: whole ({fh.read().strip()[:160]})")
        return
    t0 = time.time()
    got = subprocess.run([sys.executable, os.path.join(HERE, "fetch_client.py"), VERSION, CLIENT, "--skip-music",
                          "--server", SERVER], capture_output=True, text=True)
    if got.returncode != 0:
        raise SystemExit("game files: fetch_client.py failed\n" + (got.stdout + got.stderr)[-1500:])
    report = got.stdout.strip().splitlines()[-1]
    with open(note, "w") as fh:
        fh.write(report + "\n")
    say(f"game files: fetched from Mojang in {time.time() - t0:.0f} s ({report[:200]})")


def setup():
    for folder in (SERVER, os.path.join(GAME, "resourcepacks")):
        os.makedirs(folder, exist_ok=True)
    system()
    path = java(fetch=True)
    say(f"java: {path}")
    game_files()

    pw_file = os.path.join(SERVER, ".rcon_pw")
    if not os.path.exists(pw_file):
        with open(os.open(pw_file, os.O_WRONLY | os.O_CREAT, 0o600), "w") as fh:
            fh.write(secrets.token_hex(16))
    with open(pw_file) as fh:
        password = fh.read().strip()
    written = []
    props = os.path.join(SERVER, "server.properties")
    if not os.path.exists(props):
        with open(props, "w", encoding="utf-8") as fh:
            fh.write(SERVER_PROPERTIES.format(password=password, rcon_port=RCON_PORT, host=HOST, port=PORT,
                                              view=SERVER_VIEW))
        written.append(props)
    elif set_line(props, "view-distance", "=", SERVER_VIEW):
        written.append(props + " (view-distance)")
    eula = os.path.join(SERVER, "eula.txt")
    if not os.path.exists(eula):
        with open(eula, "w") as fh:
            fh.write("eula=true\n")
        written.append(eula)
    options = os.path.join(GAME, "options.txt")
    if not os.path.exists(options):
        with open(options, "w", encoding="utf-8") as fh:
            fh.write(OPTIONS.format(view=VIEW, clouds=CLOUDS))
        written.append(options)
    else:
        changed = [key for key, value in (("renderDistance", VIEW), ("cloudRange", CLOUDS))
                   if set_line(options, key, ":", value)]
        if changed:
            written.append(options + " (" + ", ".join(changed) + ")")
    say("settings written: " + (", ".join(os.path.relpath(p, ROOT) for p in written) or "nothing, all there")
        + f"; render distance {VIEW}, the server's view distance {SERVER_VIEW}, cloud range {CLOUDS}")
    if any("view-distance" in w or "renderDistance" in w or "cloudRange" in w for w in written):
        # a running game holds the old distances
        if running("client") or running("server"):
            say("the distances changed: the game is stopped, the next `up` starts it with the new ones")
            client_down()
            server_down()


def distances():
    """What the pictures are taken at, read from the files the game reads: (render distance of the
    client, view distance of the server, cloud range), None where a file does not say."""
    def find(path, pattern):
        try:
            with open(path, encoding="utf-8") as fh:
                m = re.search(pattern, fh.read(), re.M)
        except OSError:
            return None
        return int(m.group(1)) if m else None
    options = os.path.join(GAME, "options.txt")
    return (find(options, r"^renderDistance:(\d+)"), find(os.path.join(SERVER, "server.properties"), r"^view-distance=(\d+)"),
            find(options, r"^cloudRange:(\d+)"))


# ---- server ----------------------------------------------------------------------------------------
def server_up():
    if answers() is not None:
        say("server is up")
        return
    if not running("server"):
        heap = os.environ.get("MC_SERVER_HEAP", "1500M")
        start(["nice", "-n", "5", java(), "-Xms512M", f"-Xmx{heap}", "-jar", "server.jar", "nogui"], SERVER,
              os.path.join(SERVER, "console.log"), kind="server")
    t0 = time.monotonic()
    while time.monotonic() - t0 < 600:
        if answers() is not None:
            say(f"server is up ({time.monotonic() - t0:.0f} s)")
            return
        if not running("server"):
            raise SystemExit("server ended:\n" + tail(os.path.join(SERVER, "console.log")))
        time.sleep(2)
    raise SystemExit("server did not come up:\n" + tail(os.path.join(SERVER, "console.log")))


def server_down():
    if answers() is not None:
        try:
            rcon("save-all flush", "stop")
        except (OSError, PermissionError):
            pass
    pid = running("server")
    stopped = bool(pid)
    for _ in range(60):
        if not pid or not ours(pid):
            break
        time.sleep(1)
    else:
        stop(pid)
    for stray in strays(r"-jar server\.jar nogui"):
        stopped = stop(stray) or stopped
    if os.path.exists(PIDS["server"]):
        os.remove(PIDS["server"])
    if stopped:
        say("server stopped")


# ---- client ----------------------------------------------------------------------------------------
def offline_uuid(name):
    d = bytearray(hashlib.md5(("OfflinePlayer:" + name).encode()).digest())
    d[6] = (d[6] & 0x0F) | 0x30
    d[8] = (d[8] & 0x3F) | 0x80
    return uuid.UUID(bytes=bytes(d)).hex


def helper():
    """The folder that holds the picture helper's class for the client's class path, or None when
    it is switched off (MC_HELPER=0) or the class kept with the checkout is not of its source."""
    if os.environ.get("MC_HELPER", "1") == "0":
        return None
    kept = os.path.join(HERE, "win", "helper")
    try:
        with open(HELPER_SOURCE, "rb") as fh:
            want = hashlib.sha1(fh.read().replace(b"\r\n", b"\n")).hexdigest()
        with open(os.path.join(kept, "CamHelper.sha1")) as fh:
            made_from = fh.read().strip()
    except OSError:
        return None
    if made_from != want or not os.path.exists(os.path.join(kept, "CamHelper.class")):
        say("the picture helper's class is not of the source beside it (win/build_helper.py makes it); "
            "starting without the helper")
        return None
    os.makedirs(HELPER, exist_ok=True)
    shutil.copyfile(os.path.join(kept, "CamHelper.class"), os.path.join(HELPER, "CamHelper.class"))
    return HELPER


def helper_runs(pid):
    """True when the client with this process id was started through the helper and it is listening."""
    return read_pid(os.path.join(GAME, ASKS, "ready")) == pid


def display_up():
    """The X display the client draws on. Returns the environment for a program that uses it."""
    socket = f"/tmp/.X11-unix/X{DISPLAY}"
    if not os.path.exists(socket) or not running("display"):
        if os.path.exists(socket) and not strays(rf"Xvfb :{DISPLAY}\b"):
            if strays(rf"\bX\w* :{DISPLAY}\b", anybody=True):
                raise SystemExit(f"display :{DISPLAY} is somebody else's; name another with MC_DISPLAY")
            os.remove(socket)           # left by a display that is gone
            try:
                os.remove(f"/tmp/.X{DISPLAY}-lock")
            except OSError:
                pass
        if not os.path.exists(socket):
            start(["Xvfb", f":{DISPLAY}", "-screen", "0", f"{SIZE}x24", "+extension", "GLX", "-nolisten", "tcp"],
                  CLIENT, os.path.join(CLIENT, "xvfb.log"), kind="display")
            end = time.monotonic() + 20
            while not os.path.exists(socket):
                if time.monotonic() > end:
                    raise SystemExit("the X display did not come up:\n" + tail(os.path.join(CLIENT, "xvfb.log")))
                time.sleep(0.2)
    return {**os.environ, "DISPLAY": f":{DISPLAY}", **software(), "SDL_VIDEODRIVER": "x11", "ALSOFT_DRIVERS": "null"}


def client_command():
    with open(os.path.join(CLIENT, "versions", VERSION, f"{VERSION}.json")) as fh:
        asset_index = json.load(fh)["assetIndex"]["id"]
    with open(os.path.join(CLIENT, f"classpath-{VERSION}.txt"), encoding="utf-8") as fh:
        classpath = os.pathsep.join(os.path.join(CLIENT, line.strip()) for line in fh if line.strip())
    natives = os.path.join(CLIENT, "natives")
    width, height = SIZE.split("x")
    heap = os.environ.get("MC_CLIENT_HEAP", "3G")
    main, asks = "net.minecraft.client.main.Main", []
    folder = helper()
    if folder:
        # The helper's main() starts that same main class; the client runs in GAME, so ASKS is under it.
        classpath, main, asks = classpath + os.pathsep + folder, "CamHelper", [f"-Dc164.cam={ASKS}"]
    return [
        "nice", "-n", "5", java(), "-Xms512M", f"-Xmx{heap}",
        "-XX:StackShadowPages=32", "--enable-native-access=ALL-UNNAMED",
        "--add-exports", "java.base/jdk.internal.misc=ALL-UNNAMED",
        f"-Djava.library.path={os.path.join(natives, 'java')}", f"-Djna.tmpdir={os.path.join(natives, 'jna')}",
        f"-Dorg.lwjgl.system.SharedLibraryExtractPath={os.path.join(natives, 'lwjgl')}",
        f"-Dio.netty.native.workdir={os.path.join(natives, 'netty')}",
        "-Dminecraft.launcher.brand=c164-test", "-Dminecraft.launcher.version=1", *asks,
        "-cp", classpath, main,
        "--username", CAM, "--version", VERSION, "--gameDir", GAME,
        "--assetsDir", os.path.join(CLIENT, "assets"), "--assetIndex", asset_index,
        "--uuid", offline_uuid(CAM), "--accessToken", "0", "--clientId", "0", "--xuid", "0",
        "--versionType", "release", "--width", width, "--height", height,
        "--quickPlayMultiplayer", f"{HOST}:{PORT}",
    ]


def client_log():
    """The closing lines of what the game said: its output, which holds its log and what the
    Java machine said when it fell over."""
    return tail(os.path.join(CLIENT, "client.log"), 40)


def graphics():
    """What the game says it draws with, from its output: the backend it chose and why."""
    found = []
    try:
        with open(os.path.join(CLIENT, "client.log"), encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if re.search(r"graphics backend|GLX visual|Backend library|llvmpipe|lavapipe|Failed to (create|initiali[sz]e)",
                             line, re.I):
                    found.append(" ".join(line.split())[:220])
    except OSError:
        pass
    return found[:6]


def client_up():
    pid = running("client")
    if not pid:
        if answers() is None:
            raise SystemExit("server is not up")
        env = display_up()
        for name in ("java", "jna", "lwjgl", "netty"):
            os.makedirs(os.path.join(CLIENT, "natives", name), exist_ok=True)
        ready = os.path.join(GAME, ASKS, "ready")
        if os.path.exists(ready):
            os.remove(ready)
        log = os.path.join(CLIENT, "client.log")
        if os.path.exists(log):
            os.replace(log, log + ".1")
        pid = start(client_command(), GAME, log, env=env, kind="client")
    t0 = time.monotonic()
    while time.monotonic() - t0 < 900:
        if not ours(pid):
            raise SystemExit("client ended:\n" + client_log())
        listed = answers()
        if listed and CAM in listed:
            say(f"{CAM} is online ({time.monotonic() - t0:.0f} s)")
            for line in graphics():
                say("game: " + line)
            say("pictures: " + ("saved by the game itself (helper)" if helper_runs(pid)
                                else "taken off the X display"))
            return
        time.sleep(2)
    raise SystemExit(f"{CAM} did not join:\n" + client_log())


def client_down():
    pid = running("client")
    stopped = stop(pid) if pid else False
    for stray in strays(r"net\.minecraft\.client\.main\.Main|CamHelper"):
        stopped = stop(stray) or stopped
    for stale in (PIDS["client"], os.path.join(GAME, ASKS, "ready")):
        if os.path.exists(stale):
            os.remove(stale)
    if stopped:
        say("client stopped")


def display_down():
    pid = running("display")
    if pid:
        stop(pid, wait=5)
    for stray in strays(rf"Xvfb :{DISPLAY}\b"):
        stop(stray, wait=5)
    if os.path.exists(PIDS["display"]):
        os.remove(PIDS["display"])


def status():
    listed = answers()
    print("server: " + (listed.strip() if listed is not None else "no answer"))
    pid = running("client")
    if pid:
        print(f"client: process {pid}")
        print("pictures: " + ("saved by the game itself (helper)" if helper_runs(pid) else "taken off the X display"))
    else:
        print("client: not running")
    print("display: " + (f"Xvfb :{DISPLAY}, process {running('display')}" if running("display") else "none"))
    client, server, clouds = distances()
    print(f"distances: client renderDistance {client}, server view-distance {server}, cloudRange {clouds}")
    with open("/proc/meminfo") as fh:
        memory = dict(line.split(":") for line in fh)
    with open("/proc/loadavg") as fh:
        load = fh.read().split()[0]
    print(f"machine: {os.cpu_count()} cores, load {load}, "
          f"{int(memory['MemAvailable'].split()[0]) >> 10} MB of memory available, "
          f"{shutil.disk_usage(ROOT).free >> 30} GB of disk free under {ROOT}")


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "status"
    steps = {
        "setup": [setup], "up": [server_up, client_up], "down": [client_down, server_down, display_down],
        "restart": [client_down, server_down, server_up, client_up], "status": [status],
        "server-up": [server_up], "server-down": [server_down],
        "client-up": [client_up], "client-down": [client_down],
    }
    if what not in steps:
        raise SystemExit("usage: nodemc.py " + "|".join(steps))
    for step in steps[what]:
        step()


if __name__ == "__main__":
    main()
