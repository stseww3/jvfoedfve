#!/usr/bin/env python3
"""The map as a save that can be uploaded to Realms (plan/packages/common/export.md).

    export.py make --scene obs --name c164-obs [--look on] [--out dist/<name>]
        on a worker node: a fresh server and a void world, the scene placed, the delivery list's
        settings, the world saved, cleaned and zipped: <out>/<name>.zip with <name>.json (what
        is in it, what was run) and <name>.log beside it
    export.py verify dist/<name>/<name>.zip [--strip]
        on a worker node: the save unpacked into a clean folder and started again; a fake
        player joins, falls, leaves and comes back; what was found goes to <name>.verify.json
    export.py pack --scene obs --name x --out /tmp/x
        anywhere, no server: only what the tool itself adds, for reading: the data pack's own
        functions and the resource pack
    export.py compare a.zip b.zip
        do two exports hold the same files

What a save made here carries
  - the world: one void dimension with the scene, placed by build/place.py as for the pictures;
  - datapacks/c164art: the motion loop's functions (build/scenes/obs/motion/_kit.py) and the map's
    own, namespace c164map: who arrives is put on the spot and turned the way the scene's SPAWN
    (for the whole map the skeleton's V1) says, is in adventure mode and reaches no block; who
    drops under the cloud sea is put back on the spot. The structure files and the place, clear
    and forceload functions that only served the building are taken out, and the pack's filter
    hides the game's own advancements and recipes;
  - resourcepacks/resources.zip: the scene's resource pack (build/makepack.py);
  - the settings of the delivery list (plan/STATUS.md): time and weather held, adventure,
    peaceful, the game rules, the spawn with its facing.

--look on|off (default off): whether the save carries our biome and our timeline. They are data of
dynamic registries, the game marks a world that holds any as "experimental", and Realms says it
does not take such worlds (plan/reviews/export/realms-rules.md). Off, the two files and the
timeline tag are not written and no biome is filled: the sky is then the game's own, or what the
resource pack makes of it.

--trial <label> makes a save for a trial upload: on every joining it puts the player on the spot
and says in the chat what it found (the functions run, the biome is there or is not, game mode and
difficulty), and a line of text with the label hangs in the first view.

The server (the director's conditions, #61069): started only inside a job on a worker node, never
on the machine the sessions share nor on the director's; no client; it listens on 127.0.0.1; it is
stopped before the command returns, whatever happens; server.jar comes from Mojang, by the version
manifest, and is checked against its SHA-1; game files and worlds stay under MC_ROOT and /tmp, the
archive goes to dist/ and from there to the branch cursor/c164-dist-<suffix>, never to the assembly.
"""
import argparse
import atexit
import glob
import hashlib
import importlib
import json
import math
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
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
REPO = os.path.dirname(PROJECT)
BUILD = os.path.join(PROJECT, "build")
ROOT = os.path.abspath(os.environ.get("MC_ROOT", "/agent/realms-study"))
WORK = os.environ.get("C164_EXPORT_WORK", "/tmp/c164_export")

VERSION = "26.3"
JAVA_MAJOR = 25
ADOPTIUM = ("https://api.adoptium.net/v3/assets/latest/{major}/hotspot"
            "?architecture=x64&image_type=jre&os=linux&vendor=eclipse")
HOST, PORT, RCON_PORT = "127.0.0.1", 25689, 25688      # not the picture server's 25599 and 25598
HEAP = os.environ.get("C164_EXPORT_HEAP", "1500M")

PACK = "c164art"            # the data pack's folder in the world: build/place.py writes there
ART = "c164art"             # the namespace of the scene's structures, loop and look
NS = "c164map"              # the namespace of the map's own functions
IN_TAG = "c164.in"          # on a player who has been here before
LEFT = "c164j"              # objective: times the player has left since he was last greeted
FACTS = "c164v"             # objective of a trial save: what the functions found
BOT = "C164Probe"           # the fake player of verify
CATCH = -30                 # scene y: feet under it are put back on the spot (agreed with cloud
                            # c329 #62206 and a4 c323 #64103: the cloud layer's top is -28, the
                            # lowest rock a foot finds is -27, the eye is in the cloud by then)
DATA_FORMAT = 121           # 26.3, as build/artkit/export.py
REGISTRY_FOLDERS = ("worldgen", "timeline", "dimension", "dimension_type")   # what --strip takes out

# The delivery list (plan/STATUS.md, "成品地图交付清单"; the director's #61069), in the order it is run.
# max_block_modifications is put back to the game's own value separately.
RULES = [
    ("advance_time", "false"), ("advance_weather", "false"), ("fall_damage", "false"),
    ("random_tick_speed", "0"), ("spawn_mobs", "false"), ("block_drops", "false"), ("entity_drops", "false"),
    ("spawn_wandering_traders", "false"), ("spawn_patrols", "false"), ("spawn_phantoms", "false"),
    ("pvp", "false"), ("send_command_feedback", "false"), ("command_block_output", "false"),
    ("fire_damage", "false"), ("drowning_damage", "false"), ("freeze_damage", "false"),
    ("immediate_respawn", "true"), ("show_death_messages", "false"), ("locator_bar", "false"),
    ("respawn_radius", "0"),
]

PROPERTIES = {
    "allow-flight": "true", "broadcast-console-to-ops": "false", "broadcast-rcon-to-ops": "false",
    "difficulty": "peaceful", "enable-query": "false", "enable-rcon": "true", "enable-status": "false",
    "force-gamemode": "false", "function-permission-level": "2", "gamemode": "adventure",
    "generate-structures": "false",
    "generator-settings": '{"biome":"minecraft:the_void","layers":[{"block":"minecraft:air","height":1}]}',
    "level-seed": "164", "level-type": "minecraft:flat", "max-chained-neighbor-updates": "1000000",
    "max-players": "4", "max-tick-time": "-1", "motd": "c164 export", "online-mode": "false",
    "pause-when-empty-seconds": "-1", "player-idle-timeout": "0", "server-ip": HOST,
    "simulation-distance": "10", "spawn-protection": "0", "sync-chunk-writes": "true",
    "view-distance": "10", "white-list": "false",
}

# online-mode=false is what lets the fake player in; the server says so in four warnings
EXPECTED_WARNINGS = ("SERVER IS RUNNING IN OFFLINE/INSECURE MODE", "The server will make no attempt to authenticate",
                     "While this makes the game possible to play without internet access",
                     'To change this, set "online-mode" to "true"')

T0 = time.time()
LOG = []


def say(text):
    line = f"[export {time.time() - T0:5.0f}s] {text}"
    LOG.append(line)
    print(line, flush=True)


def fail(text):
    say("FAILED: " + text)
    raise SystemExit(1)


def git(*args):
    out = subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else ""


def commit():
    """(short name of the commit the tree is on, with + when files of the project differ from it;
    its time in seconds)."""
    head = git("rev-parse", "--short=8", "HEAD") or "unknown"
    dirty = git("status", "--porcelain", "--", "c164-realms/build", "c164-realms/tools")
    when = git("show", "-s", "--format=%ct", "HEAD")
    return head + ("+" if dirty else ""), int(when or 0)


# ------------------------------------------------------------------ the game's files

def node_only():
    root = os.path.realpath(REPO)
    if not root.startswith("/tmp/dais_jobs/") or root.startswith("/tmp/dais_jobs/c164a0"):
        fail(f"the server is started only inside a job on a worker node (tools/nodejob.sh), not here ({root}): "
             "not on the machine the sessions share, not on the director's (plan/STATUS.md, the delivery list)")


def get(url, tries=4):
    last = None
    for attempt in range(tries):
        if attempt:
            time.sleep(3 * 2 ** (attempt - 1))
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "c164-export"})
            with urllib.request.urlopen(request, timeout=300) as resp:
                return resp.read()
        except Exception as exc:        # retried, then reported
            last = exc
    fail(f"cannot fetch {url}: {last}")


def java_version(path):
    try:
        out = subprocess.run([path, "-version"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    m = re.search(r'version "(\d+)', out.stderr + out.stdout)
    return int(m.group(1)) if m else None


def find_java():
    """A Java 25: the one named in JAVA, one under MC_ROOT/jdk (where tools/mc.sh and the real
    machine's set-up keep theirs), one of the system's; else Adoptium's runtime is put under
    MC_ROOT/jdk, checked against the SHA-256 Adoptium gives for it."""
    named = os.environ.get("JAVA")
    candidates = ([named] if named else []) + sorted(glob.glob(os.path.join(ROOT, "jdk", "*", "bin", "java")), reverse=True) \
        + sorted(glob.glob("/usr/lib/jvm/*/bin/java")) + [shutil.which("java") or ""]
    for path in candidates:
        if path and os.access(path, os.X_OK) and java_version(path) == JAVA_MAJOR:
            return path
    package = json.loads(get(ADOPTIUM.format(major=JAVA_MAJOR)))[0]["binary"]["package"]
    say(f"java: fetching {package['name']} ({package['size'] >> 20} MB) from Adoptium")
    data = get(package["link"])
    if hashlib.sha256(data).hexdigest() != package["checksum"]:
        fail(f"java: {package['name']} does not have the SHA-256 Adoptium gives for it")
    target = os.path.join(ROOT, "jdk")
    os.makedirs(target, exist_ok=True)
    archive = os.path.join(target, package["name"])
    with open(archive, "wb") as fh:
        fh.write(data)
    with tarfile.open(archive) as tar:
        tar.extractall(target, filter="data")
    os.remove(archive)
    for path in sorted(glob.glob(os.path.join(target, "*", "bin", "java")), reverse=True):
        if java_version(path) == JAVA_MAJOR:
            return path
    fail(f"java: what was unpacked under {target} is not a Java {JAVA_MAJOR}")


def server_jar():
    """Mojang's server.jar of VERSION under MC_ROOT/export26, by the version manifest, checked
    against the SHA-1 the manifest's version file gives. Returns (path, sha1)."""
    sys.path.insert(0, HERE)
    import fetch_client as FC
    versions = json.loads(get(FC.MANIFEST))["versions"]
    entry = next((v for v in versions if v["id"] == VERSION), None)
    if entry is None:
        fail(f"Mojang's version manifest does not list {VERSION}")
    server = json.loads(get(entry["url"]))["downloads"]["server"]
    if not server["url"].startswith("https://piston-data.mojang.com/"):
        fail(f"the server jar's address is not Mojang's: {server['url']}")
    path = os.path.join(ROOT, "export26", "server.jar")
    fetched = FC.fetch(server["url"], path, server["sha1"])
    if FC.sha1_of(path) != server["sha1"]:
        fail("server.jar does not have the SHA-1 Mojang gives for it")
    say(f"server.jar {VERSION}: {'fetched' if fetched else 'there'}, sha1 {server['sha1']}")
    return path, server["sha1"]


# ------------------------------------------------------------------ the server

class Server:
    """One server process in its own folder. It is stopped when the tool ends, however it ends."""

    def __init__(self, folder, level, java, jar):
        self.folder, self.level, self.java, self.jar = folder, level, java, jar
        self.world = os.path.join(folder, level)
        self.pw_file = os.path.join(folder, ".rcon_pw")
        self.log = os.path.join(folder, "console.log")
        self.proc = None
        self.rc = None
        self.said = []              # (command, reply) of everything sent
        os.makedirs(folder, exist_ok=True)
        if not os.path.exists(self.pw_file):
            with open(os.open(self.pw_file, os.O_WRONLY | os.O_CREAT, 0o600), "w") as fh:
                fh.write(secrets.token_hex(16))
        with open(self.pw_file) as fh:
            self.password = fh.read().strip()

    def settings(self, **over):
        props = dict(PROPERTIES)
        props.update({"level-name": self.level, "rcon.password": self.password, "rcon.port": str(RCON_PORT),
                      "server-port": str(PORT)})
        props.update({k.replace("_", "-"): v for k, v in over.items()})
        with open(os.path.join(self.folder, "server.properties"), "w", encoding="utf-8") as fh:
            fh.write("".join(f"{k}={v}\n" for k, v in sorted(props.items())))
        with open(os.path.join(self.folder, "eula.txt"), "w") as fh:
            fh.write("eula=true\n")

    def start(self, wait=300):
        from rcon import Rcon
        out = open(self.log, "ab")
        self.proc = subprocess.Popen([self.java, "-Xms512M", f"-Xmx{HEAP}", "-jar", self.jar, "nogui"],
                                     cwd=self.folder, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT)
        out.close()
        atexit.register(self.kill)
        t = time.time()
        while time.time() - t < wait:
            if self.proc.poll() is not None:
                fail(f"the server ended while starting (exit {self.proc.returncode}):\n" + self.tail(40))
            try:
                self.rc = Rcon(HOST, RCON_PORT, self.password, timeout=600.0)
                self.rc.command("list")
                say(f"server up after {time.time() - t:.0f} s ({os.path.basename(self.folder)}/{self.level})")
                return time.time() - t
            except (OSError, ConnectionError, PermissionError):
                self.rc = None
                time.sleep(1.0)
        self.kill()
        fail(f"the server did not answer within {wait} s:\n" + self.tail(40))

    def cmd(self, command, quiet=False):
        reply = self.rc.command(command).strip()
        self.said.append((command, reply))
        if not quiet:
            say(f"  > {command}\n      {reply[:300] or '(no reply)'}")
        return reply

    def stop(self, wait=120):
        if self.proc is None or self.proc.poll() is not None:
            return
        try:
            self.cmd("save-all flush")
            self.rc.command("stop")
        except (OSError, ConnectionError):
            pass
        try:
            self.proc.wait(wait)
        except subprocess.TimeoutExpired:
            self.kill()
            fail("the server did not stop when told to; it was killed, the world may not be whole")
        if self.rc is not None:
            self.rc.close()
            self.rc = None
        say("server stopped")

    def kill(self):
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(20)
            except subprocess.TimeoutExpired:
                self.proc.kill()

    def tail(self, n=25):
        try:
            with open(self.log, encoding="utf-8", errors="replace") as fh:
                return "".join(fh.readlines()[-n:])
        except OSError:
            return ""

    def issues(self):
        """Lines of the console that are warnings or errors, without their time stamps. What a
        server without log-in always says of itself is left out."""
        out = []
        try:
            with open(self.log, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if any(known in line for known in EXPECTED_WARNINGS):
                        continue
                    if re.search(r"/(WARN|ERROR|FATAL)\]", line) or "Exception" in line:
                        out.append(re.sub(r"^\[[0-9:]+\] ", "", line.rstrip())[:400])
        except OSError:
            pass
        return out


def _on_term(signum, frame):
    raise SystemExit(f"stopped by signal {signum}")     # atexit then stops the server


# ------------------------------------------------------------------ what the scene says

def scene_spec(args):
    """Where the scene stands, where its spawn is and which way it looks, in world coordinates."""
    sys.path.insert(0, BUILD)
    scene = importlib.import_module(f"scenes.{args.scene}")
    from scenes.obs.common import blocks as B
    from scenes.obs.common import skeleton as S
    spot = getattr(scene, "SPAWN", None) or S.V1
    ox, oy, oz = args.at
    ex, ey, ez = spot["pos"]
    dx, dy, dz = (b - a for a, b in zip(spot["pos"], spot["look_at"]))
    look = bool(args.look == "on" and getattr(scene, "BIOME", None))
    when = args.time
    if when is None:
        when = getattr(scene, "TIME", 14000) if look else getattr(scene, "TIME_PLAIN", getattr(scene, "TIME", 14000))
    return {
        "scene": args.scene, "name": args.name, "at": [ox, oy, oz], "look": look,
        "biome": f"{ART}:{scene.BIOME}" if look else None,
        "time": int(when),
        "feet": [round(ox + ex, 4), round(oy + ey - S.EYE, 4), round(oz + ez, 4)],
        "yaw": round(math.degrees(math.atan2(-dx, dz)), 2),
        "pitch": round(-math.degrees(math.atan2(dy, math.hypot(dx, dz))), 2),
        "catch": oy + args.catch,
        "cloud": [f"minecraft:{b}" for b in B.CLOUD] if args.on_cloud == "back" else [],
        "trial": args.trial,
    }


def num(v):
    """A coordinate as a command wants it: no exponent, no needless digits."""
    text = f"{v:.4f}".rstrip("0").rstrip(".")
    return text if text not in ("", "-0") else "0"


def snbt(text, color=None):
    body = 'text:"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return "{" + body + (f',color:"{color}"' if color else "") + "}"


def functions(spec):
    """The map's own functions, {name: [lines]}, and whether the tick tag is needed."""
    x, y, z = spec["feet"]
    low = -512
    out = {
        "load": [f"scoreboard objectives add {LEFT} minecraft.custom:minecraft.leave_game"],
        "tick": [
            f"execute as @a[tag=!{IN_TAG}] run function {NS}:first",
            f"execute as @a[scores={{{LEFT}=1..}}] run function {NS}:join",
            # feet under the line: the volume from y to y + dy + 1 is tested against the player's box
            f"execute as @a at @s if entity @s[y={low},dy={spec['catch'] - low - 1}] run function {NS}:back",
        ],
        "first": [f"tag @s add {IN_TAG}", f"function {NS}:back", f"function {NS}:join"],
        "join": [
            f"scoreboard players set @s {LEFT} 0",
            "gamemode adventure @s",
            "attribute @s minecraft:block_interaction_range base set 0",
        ],
        "back": [f"tp @s {num(x)} {num(y)} {num(z)} {num(spec['yaw'])} {num(spec['pitch'])}"],
    }
    if spec["cloud"]:
        out["tick"].append(f"execute as @a at @s if block ~ ~-0.2 ~ #{NS}:cloud run function {NS}:back")
    label = spec["trial"]
    if label:
        head = snbt(f"[c164 试传 {label}] ", "gold")
        out["load"].append(f"scoreboard objectives add {FACTS} dummy")
        # a trial save greets on every joining, from the spot, and remembers how the player came in
        out["join"][1:1] = [f"tag @s remove c164.adv", "execute if entity @s[gamemode=adventure] run tag @s add c164.adv"]
        out["join"] += [f"function {NS}:back", "tag @s add c164.say1"]
        # say2 stands before say1 in the tick function, so it runs one tick after it whatever
        # became of say1's last line (a function that is not there when the biome is not)
        out["tick"] += [f"execute as @a[tag=c164.say2] at @s run function {NS}:say2",
                        f"execute as @a[tag=c164.say1] at @s run function {NS}:say1"]
        out["say1"] = [
            "tag @s remove c164.say1",
            "tag @s add c164.say2",
            f"tellraw @s [{head},{snbt('数据包的函数在跑：这几行字是函数说的。')}]",
            f"scoreboard players set #biome {FACTS} 0",
        ]
        out["say2"] = ["tag @s remove c164.say2", f"execute store result score #diff {FACTS} run difficulty"]
        if spec["look"]:
            out["say1"].append(f"function {NS}:biome")
            out["biome"] = [f"execute if biome ~ ~ ~ {spec['biome']} run scoreboard players set #biome {FACTS} 1"]
            out["say2"] += [
                f"execute if score #biome {FACTS} matches 1 run tellraw @s "
                f"[{head},{snbt('生物群系 ' + spec['biome'] + '：在。', 'green')}]",
                f"execute unless score #biome {FACTS} matches 1 run tellraw @s "
                f"[{head},{snbt('生物群系 ' + spec['biome'] + '：不在（注册表文件没有跟过来）。', 'red')}]",
            ]
        else:
            out["say2"].append(f"tellraw @s [{head},{snbt('这个存档不带自定义生物群系和时间线，天是游戏自己的。')}]")
        score = "{score:{name:\"#diff\",objective:\"" + FACTS + "\"}}"
        out["say2"] += [
            f"execute if entity @s[tag=c164.adv] run tellraw @s [{head},{snbt('进来时已经是冒险模式；难度 ')},{score},{snbt('（0 是和平）。')}]",
            f"execute unless entity @s[tag=c164.adv] run tellraw @s [{head},{snbt('进来时不是冒险模式（函数已改成冒险）；难度 ')},{score},{snbt('（0 是和平）。')}]",
            f"tellraw @s [{head},{snbt('请先别动鼠标，按 F2 截一张图；再低头看平台、回头看身后。', 'yellow')}]",
        ]
    return out


def _tag(path, entry):
    """Add a function to a function tag of the minecraft namespace, keeping what is there."""
    tag = {"values": []}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            tag = json.load(fh)
    values = [v for v in tag.get("values", []) if (v.get("id") if isinstance(v, dict) else v) != entry]
    values.append({"id": entry, "required": False})
    tag["values"] = values
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(tag, fh, indent=1)
        fh.write("\n")


def write_functions(pack_dir, spec):
    folder = os.path.join(pack_dir, "data", NS)
    if os.path.isdir(folder):
        shutil.rmtree(folder)
    files = functions(spec)
    for name, lines in files.items():
        path = os.path.join(folder, "function", name + ".mcfunction")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lines) + "\n")
    if spec["cloud"]:
        path = os.path.join(folder, "tags", "block", "cloud.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"values": spec["cloud"]}, fh, indent=1)
            fh.write("\n")
    tags = os.path.join(pack_dir, "data", "minecraft", "tags", "function")
    _tag(os.path.join(tags, "load.json"), f"{NS}:load")
    _tag(os.path.join(tags, "tick.json"), f"{NS}:tick")
    return sorted(files)


def pack_meta(pack_dir, description, filtered):
    meta = {"pack": {"description": description, "min_format": DATA_FORMAT, "max_format": DATA_FORMAT}}
    if filtered:        # the game's own advancements and recipes: no toasts of either (the director's #61069, 8)
        meta["filter"] = {"block": [{"namespace": "minecraft", "path": "advancement/.*"},
                                    {"namespace": "minecraft", "path": "recipe/.*"}]}
    os.makedirs(pack_dir, exist_ok=True)
    with open(os.path.join(pack_dir, "pack.mcmeta"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(meta, fh, indent=1)
        fh.write("\n")


PLACE = """\
import importlib, sys
sys.argv = {argv!r}
sys.path.insert(0, {build!r})
import place
if not {look!r}:      # no biome, no timeline: nothing of a dynamic registry goes into the pack
    importlib.import_module("scenes." + sys.argv[1]).BIOME = None
    place.MOOD.write = lambda *a, **k: []
place.main()
"""


def place(spec, server, *more):
    """build/place.py as it is, in a process of its own; with the look off, told to leave the look
    out. Returns its output."""
    argv = ["place.py", spec["scene"], "--world", server.world, "--pw-file", server.pw_file,
            "--rcon-port", str(RCON_PORT), "--at", *(str(v) for v in spec["at"]), *more]
    code = PLACE.format(argv=argv, build=BUILD, look=spec["look"])
    run = subprocess.run([sys.executable, "-c", code], cwd=PROJECT, capture_output=True, text=True,
                         env=dict(os.environ, PYTHONUNBUFFERED="1"))
    text = run.stdout + run.stderr
    for line in text.splitlines():
        say("  place: " + line)
    if run.returncode != 0:
        fail(f"build/place.py ended with {run.returncode}")
    return text


def resource_pack(scene, path, description, when):
    """The scene's resource pack as the world carries it: resources.zip, the pack's files at its top."""
    sys.path.insert(0, BUILD)
    import makepack
    tmp = os.path.join(WORK, "respack-" + os.path.basename(os.path.dirname(path)) + f"-{os.getpid()}")
    if os.path.isdir(tmp):
        shutil.rmtree(tmp)
    makepack.write(scene, tmp)
    meta = os.path.join(tmp, "pack.mcmeta")
    with open(meta) as fh:
        data = json.load(fh)
    data["pack"]["description"] = description
    with open(meta, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, indent=1)
        fh.write("\n")
    standins = sorted(os.path.relpath(p, tmp) for p in glob.glob(os.path.join(tmp, "**", "ph_*"), recursive=True))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    count = zip_tree(tmp, path, "", when)
    shutil.rmtree(tmp)
    return count, standins


# ------------------------------------------------------------------ archives

def zip_tree(folder, path, top, when):
    """A zip of a folder that is the same bytes for the same files: names sorted, one date."""
    stamp = time.gmtime(max(when, 315532800))[:6]       # zip dates start in 1980
    names = []
    for base, dirs, files in os.walk(folder):
        dirs.sort()
        for f in sorted(files):
            names.append(os.path.relpath(os.path.join(base, f), folder))
    names.sort()
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for name in names:
            info = zipfile.ZipInfo((top + "/" if top else "") + name.replace(os.sep, "/"), date_time=stamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            with open(os.path.join(folder, name), "rb") as fh:
                zf.writestr(info, fh.read(), compresslevel=9)
    return len(names)


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def listing(folder):
    out = []
    for base, dirs, files in os.walk(folder):
        dirs.sort()
        for f in sorted(files):
            p = os.path.join(base, f)
            out.append({"path": os.path.relpath(p, folder).replace(os.sep, "/"), "size": os.path.getsize(p),
                        "sha256": sha256_of(p)[:16]})
    return sorted(out, key=lambda e: e["path"])


def numbers(world):
    """Chunks and entities of the saved world, counted from its region files."""
    sys.path.insert(0, HERE)
    import census
    out = {"chunks": 0, "entities": {}, "regions": 0}
    for kind in ("region", "entities"):
        for path in sorted(glob.glob(os.path.join(world, "dimensions", "minecraft", "overworld", kind, "*.mca"))):
            if kind == "region":
                out["regions"] += 1
            for _cx, _cz, raw in census.read_chunks(path):
                if kind == "region":
                    out["chunks"] += 1
                    continue
                try:
                    for e in census.parse_nbt(raw).get("Entities", []):
                        key = str(e.get("id", "?"))
                        out["entities"][key] = out["entities"].get(key, 0) + 1
                except Exception as exc:        # a count, not a gate
                    out["entities"]["unreadable: " + type(exc).__name__] = 1
    return out


def level_facts(world):
    """What level.dat says of the things the delivery list sets, as plain values."""
    import nbtlib
    out = {}
    try:
        data = nbtlib.load(os.path.join(world, "level.dat"))
        data = data.get("Data", data.get("", {}).get("Data", data))
        for key in ("GameType", "Difficulty", "difficulty_settings", "spawn", "SpawnX", "SpawnY", "SpawnZ", "SpawnAngle",
                    "LevelName", "DataVersion", "Version", "DataPacks", "allowCommands", "hardcore", "initialized",
                    "WasModded", "ServerBrands", "raining", "thundering", "clearWeatherTime", "DayTime", "Time",
                    "enabled_features", "world_gen_settings", "WorldGenSettings"):
            if key in data:
                out[key] = json.loads(json.dumps(data[key].unpack(json=True) if hasattr(data[key], "unpack") else data[key],
                                                 default=str))
    except Exception as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


# ------------------------------------------------------------------ make

def setting_commands(spec):
    x, y, z = spec["feet"]
    out = [f"gamerule {name} {value}" for name, value in RULES]
    out += ["difficulty peaceful", "defaultgamemode adventure",
            f"setworldspawn {math.floor(x)} {math.floor(y)} {math.floor(z)} {num(spec['yaw'])} {num(spec['pitch'])}",
            f"time set {spec['time']}", "weather clear 1d"]
    return out


def make(args):
    node_only()
    if not re.fullmatch(r"[A-Za-z0-9_\-]{1,40}", args.name):
        fail("--name: letters, digits, - and _ only (it is the save's folder and its level name)")
    signal.signal(signal.SIGTERM, _on_term)
    head, when = commit()
    spec = scene_spec(args)
    out_dir = os.path.abspath(args.out or os.path.join(PROJECT, "dist", args.name))
    os.makedirs(out_dir, exist_ok=True)
    for old in glob.glob(os.path.join(out_dir, args.name + ".*")):
        os.remove(old)
    say(f"make {args.name}: scene {args.scene} of {head} at {spec['at']}, look {'on' if spec['look'] else 'off'}, "
        f"tick {spec['time']}, spawn feet {spec['feet']} yaw {spec['yaw']} pitch {spec['pitch']}, "
        f"back to it under y {spec['catch']}" + (f", trial {spec['trial']}" if spec["trial"] else ""))
    facts = {"name": args.name, "commit": head, "version": VERSION, "spec": spec, "ok": False}
    work = os.path.join(WORK, args.name)
    if os.path.isdir(work):
        shutil.rmtree(work)
    try:
        java = find_java()
        jar, sha1 = server_jar()
        facts.update(java=java, server_sha1=sha1)
        server = Server(os.path.join(work, "srv"), args.name, java, jar)
        server.settings()
        pack_dir = os.path.join(server.world, "datapacks", PACK)
        # in the pack before the first start: the world is made with them, and a look is only there
        # from a start on
        pack_meta(pack_dir, "c164", False)
        written = write_functions(pack_dir, spec)
        say(f"functions {NS}: " + ", ".join(written))
        if spec["look"]:
            place(spec, server, "--look-only")
        facts["start_seconds"] = round(server.start(), 1)
        facts["packs"] = server.cmd("datapack list enabled")
        if f"file/{PACK}" not in facts["packs"]:
            fail(f"the world did not take the data pack file/{PACK}")
        default = re.search(r"(-?\d+)\s*$", server.cmd("gamerule max_block_modifications"))
        if not default:
            fail("the server does not tell max_block_modifications")
        text = place(spec, server)
        placed = re.search(r"placed in [0-9.]+s, (\d+) failed", text)
        if not placed or int(placed.group(1)) or "!!" in text:
            fail("build/place.py did not place everything (see its lines above)")
        x, y, z = spec["feet"]
        under = server.cmd(f"execute unless block {math.floor(x)} {math.floor(y - 0.01)} {math.floor(z)} minecraft:air")
        if "passed" not in under:
            fail(f"there is no block under the spawn's feet {spec['feet']}")
        facts["settings"] = []
        for command in setting_commands(spec):
            reply = server.cmd(command)
            bad = any(w in reply for w in ("Unknown or incomplete", "Incorrect argument", "Expected", "Invalid"))
            facts["settings"].append({"command": command, "reply": reply, "ok": not bad})
        refused = [s["command"] for s in facts["settings"] if not s["ok"]]
        if refused:
            fail("the server refused: " + "; ".join(refused))
        if spec["trial"]:
            # the label: seven blocks ahead of who arrives, between what stands there and the sky
            turn = math.radians(spec["yaw"])
            lx, ly, lz = x - 7.0 * math.sin(turn), y + 4.6, z + 7.0 * math.cos(turn)
            server.cmd(f"summon minecraft:text_display {num(lx)} {num(ly)} {num(lz)} "
                       "{text:{text:\"c164 " + spec["trial"] + "\",color:\"gold\"},billboard:\"center\",background:0,"
                       "brightness:{sky:15,block:15},Tags:[\"c164.label\"],transformation:{left_rotation:[0f,0f,0f,1f],"
                       "right_rotation:[0f,0f,0f,1f],translation:[0f,0f,0f],scale:[1.5f,1.5f,1.5f]}}")
        server.cmd(f"gamerule max_block_modifications {default.group(1)}")
        facts["loop"] = server.cmd("scoreboard players get #run c164m")
        server.cmd("forceload remove all")
        facts["tick"] = server.cmd("tick query")
        server.stop()
        facts["issues"] = server.issues()
        seal(server.world, spec, out_dir, head, when, facts)
        facts["ok"] = True
    finally:
        facts["seconds"] = round(time.time() - T0)
        with open(os.path.join(out_dir, args.name + ".json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(facts, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        with open(os.path.join(out_dir, args.name + ".log"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(LOG) + "\n")
    say(f"made {facts['zip']['file']}: {facts['zip']['bytes'] / 1e6:.2f} MB, {facts['zip']['files']} files, "
        f"{facts['numbers']['chunks']} chunks, {sum(facts['numbers']['entities'].values())} entities")


def seal(world, spec, out_dir, head, when, facts):
    """The saved world made ready for strangers and zipped."""
    name = spec["name"]
    stage = os.path.join(WORK, name, "seal", name)
    shutil.copytree(world, stage)
    removed = []
    for rel in ("session.lock", "level.dat_old", "players", "playerdata", "stats", "advancements"):
        path = os.path.join(stage, rel)
        if os.path.isdir(path):
            shutil.rmtree(path)
            removed.append(rel + "/")
        elif os.path.exists(path):
            os.remove(path)
            removed.append(rel)
    pack_dir = os.path.join(stage, "datapacks", PACK)
    # what only served the building: the structure files, the functions that place and clear them,
    # the driver's notes. The loop's folder (<scene>-motion) and the tags stay.
    for path in [os.path.join(pack_dir, "data", ART, "structure"),
                 os.path.join(pack_dir, "data", ART, "function", spec["scene"])]:
        if os.path.isdir(path):
            shutil.rmtree(path)
            removed.append(os.path.relpath(path, stage) + "/")
    for path in glob.glob(os.path.join(pack_dir, "*.json")):
        os.remove(path)
        removed.append(os.path.relpath(path, stage))
    pack_meta(pack_dir, f"c164 {name} ({head})", True)
    registry = sorted(os.path.relpath(p, pack_dir) for folder in REGISTRY_FOLDERS
                      for p in glob.glob(os.path.join(pack_dir, "data", "*", folder, "**", "*.json"), recursive=True))
    if registry and not spec["look"]:
        fail("the look is off and the data pack still holds registry files: " + ", ".join(registry))
    count, standins = resource_pack(spec["scene"], os.path.join(stage, "resourcepacks", "resources.zip"),
                                    f"c164 {name} ({head})", when)
    facts.update(removed=sorted(removed), registry_files=registry, resource_pack={"files": count, "standins": standins},
                 numbers=numbers(stage), level=level_facts(stage), files=listing(stage))
    path = os.path.join(out_dir, name + ".zip")
    files = zip_tree(stage, path, name, when)
    facts["zip"] = {"file": os.path.basename(path), "bytes": os.path.getsize(path), "files": files,
                    "sha256": sha256_of(path), "top": name}
    say(f"sealed: removed {', '.join(sorted(removed)) or 'nothing'}; registry files: {', '.join(registry) or 'none'}; "
        f"resource pack {count} files" + (f", {len(standins)} stand-ins (ph_) still in it" if standins else ""))


# ------------------------------------------------------------------ verify

def check(results, name, ok, detail):
    results.append({"check": name, "ok": bool(ok), "detail": detail})
    say(f"  [{'ok' if ok else 'NO'}] {name}: {detail}")


def near(a, b, eps=0.02):
    return a is not None and all(abs(p - q) <= eps for p, q in zip(a, b))


def visit(server, spec, results, tag):
    """A fake player joins, is looked at, falls, leaves, comes back."""
    sys.path.insert(0, HERE)
    import mcbot
    feet = tuple(spec["feet"])
    aim = (spec["yaw"] % 360.0, spec["pitch"])

    def turned(bot):
        return bot.rotation is not None and abs((bot.rotation[0] - aim[0] + 180.0) % 360.0 - 180.0) < 0.05 \
            and abs(bot.rotation[1] - aim[1]) < 0.05

    t = time.time()
    try:
        bot = mcbot.Bot(BOT, HOST, PORT).connect(timeout=60.0)
    except Exception as exc:
        check(results, tag + "join", False, f"the fake player could not join: {type(exc).__name__}: {exc}")
        return
    joined = time.time() - t
    first = bot.position
    bot.pump(3.0)
    check(results, tag + "join", near(bot.position, feet) and turned(bot),
          f"joined in {joined:.1f} s at {first}, after the functions at {bot.position} facing {bot.rotation}; "
          f"wanted {feet} facing {aim}")
    mode = server.cmd(f"data get entity {BOT} playerGameType", quiet=True)
    reach = server.cmd(f"attribute {BOT} minecraft:block_interaction_range base get", quiet=True)
    tags = server.cmd(f"tag {BOT} list", quiet=True)
    check(results, tag + "mode", mode.rstrip().endswith(": 2"), mode)
    check(results, tag + "reach", re.search(r"is 0(\.0+)?\s*$", reach) is not None, reach)
    check(results, tag + "tag", IN_TAG in tags, tags)
    said = bot.texts("chat")
    if spec["trial"]:
        check(results, tag + "greeting", any("函数在跑" in s for s in said) and any("F2" in s for s in said),
              " | ".join(said) or "nothing was said")
    else:
        check(results, tag + "quiet", not said, " | ".join(said) or "nothing was said, as it should be")
    # under the line: put there by hand, the tick function has him back before the next look
    server.cmd(f"tp {BOT} {num(feet[0] + 20)} {num(spec['catch'] - 6)} {num(feet[2])}", quiet=True)
    bot.pump(1.5)
    check(results, tag + "fall", near(bot.position, feet) and turned(bot),
          f"put at y {spec['catch'] - 6}, a moment later at {bot.position} facing {bot.rotation}")
    # just over the line he is left alone
    over = (feet[0] + 20, spec["catch"] + 0.5, feet[2])
    server.cmd(f"tp {BOT} {num(over[0])} {num(over[1])} {num(over[2])}", quiet=True)
    bot.pump(1.5)
    check(results, tag + "over the line", near(bot.position, over), f"put at y {over[1]}, a moment later at {bot.position}")
    one = server.cmd("tick query", quiet=True)
    check(results, tag + "tick, one player", True, one.replace("\n", " | "))
    before = len(bot.events)
    bot.close()
    time.sleep(2.0)
    try:
        bot = mcbot.Bot(BOT, HOST, PORT).connect(timeout=60.0)
    except Exception as exc:
        check(results, tag + "rejoin", False, f"the fake player could not come back: {type(exc).__name__}: {exc}")
        return
    bot.pump(3.0)
    said = bot.texts("chat")
    reach = server.cmd(f"attribute {BOT} minecraft:block_interaction_range base get", quiet=True)
    mode = server.cmd(f"data get entity {BOT} playerGameType", quiet=True)
    if spec["trial"]:
        ok = near(bot.position, feet) and turned(bot) and any("函数在跑" in s for s in said)
        where = f"back on the spot and greeted again: {bot.position}; {' | '.join(said) or 'nothing was said'}"
    else:
        ok = near(bot.position, over)
        where = f"where he left: {bot.position} (left at {over})"
    check(results, tag + "rejoin", ok and mode.rstrip().endswith(": 2") and re.search(r"is 0(\.0+)?\s*$", reach) is not None,
          f"{where}; {mode}; {reach}; {before} things shown before he left")
    bot.close()
    time.sleep(1.0)


def loop_runs(server, pack_dir, spec, results, tag):
    """Does a part move: one display entity's turn read twice. Needs the player's chunks loaded."""
    names = set()
    for path in glob.glob(os.path.join(pack_dir, "data", ART, "function", f"{spec['scene']}-motion", "**", "*.mcfunction"),
                          recursive=True):
        with open(path, encoding="utf-8") as fh:
            names.update(re.findall(r"tag=(m\.[A-Za-z0-9_.+\-]+)", fh.read()))
    if not names:
        check(results, tag + "loop", True, "the scene registers nothing that moves")
        return
    run = server.cmd("scoreboard players get #run c164m", quiet=True)
    for name in sorted(names)[:12]:
        ask = f"data get entity @e[type=minecraft:item_display,tag={name},limit=1] transformation.left_rotation"
        a = server.cmd(ask, quiet=True)
        if "entity data" not in a:
            continue
        seen = {a}
        for _ in range(6):
            time.sleep(0.5)
            seen.add(server.cmd(ask, quiet=True))
        check(results, tag + "loop", len(seen) > 1, f"{name}: {len(seen)} different turns in 3 s; {run}")
        return
    check(results, tag + "loop", False, f"none of the moving parts is loaded near the spawn ({len(names)} names); {run}")


def verify(args):
    node_only()
    signal.signal(signal.SIGTERM, _on_term)
    archive = os.path.abspath(args.archive)
    name = os.path.basename(archive)[:-4]
    with open(archive[:-4] + ".json", encoding="utf-8") as fh:
        made = json.load(fh)
    spec = made["spec"]
    results = []
    report = {"name": name, "archive_sha256": sha256_of(archive), "made_from": made["commit"], "checks": results}
    check(results, "archive", report["archive_sha256"] == made["zip"]["sha256"],
          f"{os.path.getsize(archive)} bytes, sha256 {report['archive_sha256'][:16]}, as the note beside it says"
          if report["archive_sha256"] == made["zip"]["sha256"] else "the archive is not the one its note describes")
    java = find_java()
    jar, _sha1 = server_jar()
    work = os.path.join(WORK, name + "-verify")
    if os.path.isdir(work):
        shutil.rmtree(work)
    runs = [("", False)] + ([("stripped: ", True)] if args.strip else [])
    try:
        for tag, strip in runs:
            folder = os.path.join(work, "stripped" if strip else "srv")
            os.makedirs(folder)
            with zipfile.ZipFile(archive) as zf:
                tops = {n.split("/", 1)[0] for n in zf.namelist()}
                zf.extractall(folder)
            if tops != {name}:
                check(results, tag + "layout", False, f"the archive's top is {sorted(tops)}, wanted one folder {name}")
                break
            world = os.path.join(folder, name)
            pack_dir = os.path.join(world, "datapacks", PACK)
            if not strip:
                level = level_facts(world)
                report["level"] = level
                check(results, "level.dat", level.get("GameType") == 2 and "error" not in level,
                      f"GameType {level.get('GameType')}, difficulty {level.get('Difficulty', level.get('difficulty_settings'))}, "
                      f"spawn {level.get('spawn', [level.get('SpawnX'), level.get('SpawnY'), level.get('SpawnZ')])}")
                has = [n for n in ("level.dat", "resourcepacks/resources.zip", f"datapacks/{PACK}/pack.mcmeta")
                       if os.path.exists(os.path.join(world, n))]
                junk = [n for n in ("session.lock", "players", "playerdata", "level.dat_old") if os.path.exists(os.path.join(world, n))]
                check(results, "files", len(has) == 3 and not junk, f"has {has}; left over {junk or 'nothing'}")
                with zipfile.ZipFile(os.path.join(world, "resourcepacks", "resources.zip")) as zf:
                    inner = zf.namelist()
                check(results, "resource pack", "pack.mcmeta" in inner and any(n.startswith("assets/") for n in inner),
                      f"{len(inner)} files, pack.mcmeta at its top: {'pack.mcmeta' in inner}; "
                      f"{sum(1 for n in inner if os.path.basename(n).startswith('ph_'))} stand-ins (ph_)")
            else:
                gone = []
                for kind in REGISTRY_FOLDERS:
                    for path in glob.glob(os.path.join(pack_dir, "data", "*", kind)):
                        shutil.rmtree(path)
                        gone.append(os.path.relpath(path, pack_dir))
                tag_file = os.path.join(pack_dir, "data", "minecraft", "tags", "timeline")
                if os.path.isdir(tag_file):
                    shutil.rmtree(tag_file)
                    gone.append(os.path.relpath(tag_file, pack_dir))
                say(f"stripped run: taken out of the data pack: {', '.join(gone) or 'nothing (the save has no registry files)'}")
                if not gone:
                    break
            # not the world's own settings, on purpose: what holds must come from the save
            server = Server(folder, name, java, jar)
            server.settings(gamemode="survival", difficulty="easy")
            started = server.start()
            check(results, tag + "starts", True, f"up in {started:.0f} s")
            packs = server.cmd("datapack list enabled", quiet=True)
            check(results, tag + "data pack", f"file/{PACK}" in packs, packs)
            if not strip:
                rules = {}
                for rule, value in RULES + [("max_block_modifications", None)]:
                    reply = server.cmd(f"gamerule {rule}", quiet=True)
                    rules[rule] = reply.rsplit(": ", 1)[-1].strip()
                wrong = {r: v for r, v in rules.items() if dict(RULES).get(r) not in (None, v)}
                report["rules"] = rules
                check(results, "game rules", not wrong, f"{len(rules) - len(wrong)} of {len(rules)} as the list says"
                      + (f"; not: {wrong}" if wrong else "") + f"; max_block_modifications {rules['max_block_modifications']}")
                check(results, "forced chunks", True, server.cmd("forceload query", quiet=True))
                time.sleep(3.0)
                check(results, "tick, empty", True, server.cmd("tick query", quiet=True).replace("\n", " | "))
            visit(server, spec, results, tag)
            if not strip:
                import mcbot
                bot = mcbot.Bot(BOT, HOST, PORT).connect(timeout=60.0)
                bot.pump(2.0)
                loop_runs(server, pack_dir, spec, results, tag)
                bot.close()
            server.stop()
            issues = server.issues()
            report[tag + "issues"] = issues
            check(results, tag + "console", not issues if not strip else True,
                  f"{len(issues)} warnings and errors" + ("".join("\n        " + i for i in issues[:25]) if issues else ""))
    finally:
        report["ok"] = bool(results) and all(r["ok"] for r in results)
        report["seconds"] = round(time.time() - T0)
        with open(archive[:-4] + ".verify.json", "w", encoding="utf-8", newline="\n") as fh:
            json.dump(report, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        with open(archive[:-4] + ".verify.log", "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(LOG) + "\n")
    bad = [r["check"] for r in results if not r["ok"]]
    say(f"verify {name}: " + ("every check holds" if not bad else "NOT: " + ", ".join(bad)))
    if bad:
        raise SystemExit(1)


# ------------------------------------------------------------------ pack, compare

def pack(args):
    spec = scene_spec(args)
    out = os.path.abspath(args.out)
    head, when = commit()
    pack_dir = os.path.join(out, "datapacks", PACK)
    pack_meta(pack_dir, f"c164 {args.name} ({head})", True)
    written = write_functions(pack_dir, spec)
    count, standins = resource_pack(args.scene, os.path.join(out, "resourcepacks", "resources.zip"),
                                    f"c164 {args.name} ({head})", when)
    say(f"spec: {json.dumps(spec, ensure_ascii=False)}")
    say(f"functions {NS}: {', '.join(written)}; resource pack {count} files, {len(standins)} stand-ins; in {out}")
    for command in setting_commands(spec):
        say("  would run: " + command)


def compare(args):
    def read(path):
        with zipfile.ZipFile(path) as zf:
            return {i.filename.split("/", 1)[-1]: (i.file_size, hashlib.sha256(zf.read(i)).hexdigest()) for i in zf.infolist()}
    a, b = read(args.a), read(args.b)
    only_a, only_b = sorted(set(a) - set(b)), sorted(set(b) - set(a))
    differ = sorted(n for n in set(a) & set(b) if a[n] != b[n])
    print(f"{len(a)} and {len(b)} files; {len(set(a) & set(b)) - len(differ)} the same, {len(differ)} differ, "
          f"{len(only_a)} only in the first, {len(only_b)} only in the second")
    for n in only_a:
        print("  only in the first:  " + n)
    for n in only_b:
        print("  only in the second: " + n)
    for n in differ:
        print(f"  differs: {n} ({a[n][0]} and {b[n][0]} bytes)")
    raise SystemExit(1 if only_a or only_b or differ else 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="what", required=True)
    for what in ("make", "pack"):
        p = sub.add_parser(what)
        p.add_argument("--scene", default="obs")
        p.add_argument("--name", required=True, help="the save's folder and level name")
        p.add_argument("--look", choices=("on", "off"), default="off",
                       help="carry our biome and timeline (registry data: the world counts as experimental)")
        p.add_argument("--at", type=int, nargs=3, default=[0, 200, 0], metavar=("X", "Y", "Z"))
        p.add_argument("--time", type=int, help="the tick the clock is held at (default: the scene's TIME, or TIME_PLAIN "
                                                "with the look off)")
        p.add_argument("--catch", type=int, default=CATCH, help="scene y: feet under it are put back on the spot")
        p.add_argument("--on-cloud", choices=("back", "ignore"), default="ignore",
                       help="back: who stands on a cloud block is put back on the spot too")
        p.add_argument("--trial", help="label of a trial save (see the text at the top)")
        p.add_argument("--out", help="folder of the archive (make: default dist/<name>)", required=(what == "pack"))
    p = sub.add_parser("verify")
    p.add_argument("archive")
    p.add_argument("--strip", action="store_true",
                   help="start it a second time with the registry files taken out of the data pack, as an upload might")
    p = sub.add_parser("compare")
    p.add_argument("a")
    p.add_argument("b")
    args = ap.parse_args()
    {"make": make, "pack": pack, "verify": verify, "compare": compare}[args.what](args)


if __name__ == "__main__":
    main()
