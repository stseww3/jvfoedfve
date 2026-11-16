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
    export.py compare a.zip b.zip [--deep]
        do two exports hold the same files; --deep: do their chunks hold the same blocks and
        entities (the files themselves never are the same bytes: every chunk carries the hour it
        was written, every entity an id drawn by chance)
    export.py page dist [--commit <c>] [--note <text>]
        anywhere: the newest whole save (dist/A<n>/) is written into dist/history.json and the
        table of dist/README.md; tools/exportnext.sh runs it after every round

What a save made here carries
  - the world: one void dimension with the scene, placed by build/place.py as for the pictures;
  - datapacks/c164art: the motion loop's functions (build/scenes/obs/motion/_kit.py) and the map's
    own, namespace c164map: who arrives is put on the spot and turned the way the scene's SPAWN
    (for the whole map the skeleton's V1) says, is in adventure mode and reaches no block; who
    drops under the cloud sea, or comes to stand on it (its blocks are solid), is put back on the
    spot -- but for who is in spectator or creative mode, which only an operator can be. The
    structure files and the place, clear and forceload functions that only served the building
    are taken out, and the pack's filter hides the game's own advancements and recipes;
  - resourcepacks/resources.zip: the scene's resource pack (build/makepack.py);
  - the settings of the delivery list (plan/STATUS.md): time and weather held, adventure,
    peaceful, the game rules, the spawn with its facing.

--look on|off (default off): whether the save carries our biome and our timeline. They are data of
dynamic registries, the game marks a world that holds any as "experimental", and Realms says it
does not take such worlds (plan/reviews/export/realms-rules.md). Off, the two files and the
timeline tag are not written and no biome is filled: the sky is then the game's own, or what the
resource pack makes of it.

--shaders auto|on|off (default auto): whether the resource pack carries the look as core shaders
(build/scenes/obs/sky/_shaders.py, card sky/safe-look; verified on a real client, a2 c322 #72794).
auto: yes when the scene has a look, the save goes without it, the save is no trial and the tree
has that module. Never together with --look on: the two skies would lie on top of each other.

--on-cloud back|ignore (default back, for a trial save ignore): whether standing on one of the
cloud sea's blocks (the block table's CLOUD) puts a player back on the spot, as dropping under the
line does. The sea is a skin of solid blocks: without this, who climbs over a parapet walks on it.

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
import calendar
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
# What other packages hang on a visitor's arrival (plan/packages/motion/guide.md, part one): functions
# of theirs in the scene's data pack, run as the player and where he stands, the moment a newcomer
# has been tagged, put on the spot and set up. The map's function calls a function tag of its own
# that names them; a function that is not in the pack is passed over, so a save without the guide
# is made of the same lines. Who comes back is told nothing (the card, as of 11:13).
HOOKS = {"first": [f"{ART}:guide/first"]}
GUIDE_SUB = "An evening above the clouds"       # under the title, which is the scene's MAP_TITLE
CATCH = -30                 # scene y: feet under it are put back on the spot (agreed with cloud
                            # c329 #62206 and a4 c323 #64103: the cloud layer's top is -28, the
                            # lowest rock a foot finds is -27, the eye is in the cloud by then)
DATA_FORMAT = 121           # 26.3, as build/artkit/export.py
DAY_EASE = (0.362, 0.241, 0.638, 0.759)     # the cubic bezier of the game's day (see plain_time)
# what a finished map's data pack may hold (COMMON.md 5.5). Any other folder is a registry's, and
# one file of a registry makes the game call the world experimental, which Realms does not take.
ALLOWED_KINDS = ("function", "tags", "structure", "advancement", "loot_table", "predicate", "recipe", "item_modifier")

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
    if look:
        from artkit import mood as MOOD
        try:
            module = importlib.import_module(f"scenes.{args.scene}.mood")
        except ModuleNotFoundError:
            module = None
        if getattr(MOOD, "carried", None) is not None and MOOD.carried(module) is not None:
            fail("--look on: this scene's look is carried by the resource pack (artkit.mood.Carried), and the "
                 "drivers write no biome and no timeline for it any more. The save with the biome is gone; "
                 "the look is in the save made without --look (its resource pack's shaders)")
    on_cloud = args.on_cloud or ("ignore" if args.trial else "back")
    when = args.time
    if when is None and (look or not getattr(scene, "BIOME", None)):
        when = getattr(scene, "TIME", 14000)
    elif when is None:
        # the scene has a look and the save goes without it: the game's own sky, held where its moon
        # stands as the look keeps ours (the comet is the moon's picture)
        # (a2 c322 #71364: the sky's shaders count the stars' turn from the same tick, mood.LOCK_TICK
        # once that is in the assembly; plain_time() is the same number worked out from the look)
        from scenes.obs.sky import mood
        when = getattr(scene, "TIME_PLAIN", None) or getattr(mood, "LOCK_TICK", None) or plain_time()
    asked = getattr(args, "shaders", "auto")
    shaders = False
    if asked == "on" and look:
        fail("--shaders on with --look on: the look would be there twice, as the biome's and as the shaders'")
    if (asked == "on" or (asked == "auto" and not args.trial)) and not look and getattr(scene, "BIOME", None):
        try:
            importlib.import_module("scenes.obs.sky._shaders")
            shaders = True
        except ImportError as e:
            if asked == "on":
                fail(f"--shaders on, and this tree has no scenes/obs/sky/_shaders.py ({e})")
    return {
        "scene": args.scene, "name": args.name, "at": [ox, oy, oz], "look": look, "shaders": shaders,
        # the guide (titles, plaques, star charts: plan/packages/motion/guide.md) is the scene's, and in the
        # save when the scene says GUIDE = True and --no-guide was not asked for
        "guide": bool(getattr(scene, "GUIDE", False)) and not getattr(args, "no_guide", False),
        "title": getattr(scene, "MAP_TITLE", None),      # the map's name, the one place it is written
        "biome": f"{ART}:{scene.BIOME}" if look else None,
        "time": int(when),
        "feet": [round(ox + ex, 4), round(oy + ey - S.EYE, 4), round(oz + ez, 4)],
        "yaw": round(math.degrees(math.atan2(-dx, dz)), 2),
        "pitch": round(-math.degrees(math.atan2(dy, math.hypot(dx, dz))), 2),
        "catch": oy + args.catch,
        "cloud": [f"minecraft:{b}" for b in B.CLOUD] if on_cloud == "back" else [],
        "trial": args.trial,
    }


def plain_time():
    """The tick at which the game's own clock holds the moon where the look holds it for good, in
    the phase the default look wears. The comet is the moon's picture (sky/comet.py); without the
    timeline the moon follows the game's day, and at the look's own tick 14000 it stands 20 degrees
    up in the east, the comet upside down behind who arrives.

    The game's day, data/minecraft/timeline/day.json of 26.3: the moon's angle from the zenith
    westwards runs from 180 at tick 6000 through a full turn in 24000 ticks, eased by DAY_EASE (the
    sun's and the stars' likewise). The phase follows the count of days (timeline/moon.json):
    full_moon on day 0, the next on day 1, eight in all."""
    from scenes.obs.sky import mood
    phases = ("full_moon", "waning_gibbous", "third_quarter", "waning_crescent", "new_moon", "waxing_crescent",
              "first_quarter", "waxing_gibbous")
    x1, y1, x2, y2 = DAY_EASE

    def curve(t, p, q):
        return 3.0 * (1.0 - t) ** 2 * t * p + 3.0 * (1.0 - t) * t * t * q + t ** 3

    want = ((mood.MOON_ANGLE - 180.0) % 360.0) / 360.0      # how far through its turn the moon is to be
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2.0
        if curve(mid, y1, y2) < want:
            lo = mid
        else:
            hi = mid
    tick = int(round(6000.0 + 24000.0 * curve(lo, x1, x2))) % 24000
    return tick + 24000 * phases.index(mood.LOOKS[mood.DEFAULT]["moon_phase"])


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
    # who is held to the walks: every visitor (the functions set adventure at every joining). An
    # operator who has put himself in spectator or creative mode is left to fly where he likes.
    held = "@a[gamemode=!spectator,gamemode=!creative]"
    out = {
        "load": [f"scoreboard objectives add {LEFT} minecraft.custom:minecraft.leave_game"],
        "tick": [
            f"execute as @a[tag=!{IN_TAG}] run function {NS}:first",
            f"execute as @a[scores={{{LEFT}=1..}}] run function {NS}:join",
            # feet under the line: the volume from y to y + dy + 1 is tested against the player's box
            f"execute as {held} at @s if entity @s[y={low},dy={spec['catch'] - low - 1}] run function {NS}:back",
        ],
        # who is new is set up and then handed to what other packages hang on his arrival (HOOKS), as
        # himself and where he stands; who comes back is set up again and told nothing
        "first": [f"tag @s add {IN_TAG}", f"function {NS}:back", f"function {NS}:join", f"execute at @s run function #{NS}:first"],
        "join": [
            f"scoreboard players set @s {LEFT} 0",
            "gamemode adventure @s",
            "attribute @s minecraft:block_interaction_range base set 0",
        ],
        "back": [f"tp @s {num(x)} {num(y)} {num(z)} {num(spec['yaw'])} {num(spec['pitch'])}"],
    }
    if spec["cloud"]:
        # the block the feet rest on (the cloud sea is a skin of full blocks)
        out["tick"].append(f"execute as {held} at @s if block ~ ~-0.2 ~ #{NS}:cloud run function {NS}:back")
    if spec["trial"]:
        trial_functions(spec, out)
    else:
        # a server sets its difficulty from its own settings at every start, not from the save
        out["load"].append("difficulty peaceful")
    return out


def trial_functions(spec, out):
    """What a trial save's functions do beyond the map's: on every joining the player is put on the
    spot and told what they found: once in the chat, and for as long as he stays in the line over
    the hotbar, which is sent anew every second. What stands there is what the functions find now,
    on this server; no line there means that no function runs. (Nothing is written into the world
    for this: a line of text kept in the save would still tell of the last time it was opened.)

    Three steps, each its own function, a later step on a later tick: say1 at once; say2 two
    seconds on, when the chunk is loaded for certain; say3 the tick after. say2's last line calls a
    function that is not there when the biome is not (a command naming an unknown biome does not
    parse, and the file with it is dropped), so nothing may follow it."""
    name = f"c164 试传 {spec['trial']}"
    head = snbt(f"[{name}] ", "gold")
    score = "{score:{name:\"#diff\",objective:\"" + FACTS + "\"}"
    out["load"].append(f"scoreboard objectives add {FACTS} dummy")
    out["join"][1:1] = ["tag @s remove c164.adv", "execute if entity @s[gamemode=adventure] run tag @s add c164.adv"]
    out["join"] += [f"function {NS}:back", "tag @s remove c164.say2", "tag @s remove c164.say3", "tag @s remove c164.bar",
                    "tag @s add c164.say1"]
    out["tick"] += [
        f"execute as @a[tag=c164.say3] at @s run function {NS}:say3",
        f"execute as @a[tag=c164.say2] run scoreboard players add @s {FACTS} 1",
        f"execute as @a[tag=c164.say2,scores={{{FACTS}=40..}}] at @s run function {NS}:say2",
        f"execute as @a[tag=c164.say1] at @s run function {NS}:say1",
        f"scoreboard players add #beat {FACTS} 1",
        f"execute if score #beat {FACTS} matches 20.. run function {NS}:bar",
    ]
    out["say1"] = [
        "tag @s remove c164.say1",
        "tag @s add c164.say2",
        f"scoreboard players set @s {FACTS} 0",
        f"tellraw @s [{head},{snbt('数据包的函数在跑：这几行字是函数说的。')}]",
    ]
    out["say2"] = ["tag @s remove c164.say2", "tag @s add c164.say3", f"execute store result score #diff {FACTS} run difficulty"]
    out["say3"] = ["tag @s remove c164.say3", "tag @s add c164.bar"]
    if spec["look"]:
        out["say2"] += [f"scoreboard players set #biome {FACTS} 0", f"function {NS}:biome"]
        out["biome"] = [f"execute if biome ~ ~ ~ {spec['biome']} run scoreboard players set #biome {FACTS} 1"]
        out["say3"] += [
            f"execute if score #biome {FACTS} matches 1 run tellraw @s "
            f"[{head},{snbt('生物群系 ' + spec['biome'] + '：在。', 'green')}]",
            f"execute unless score #biome {FACTS} matches 1 run tellraw @s "
            f"[{head},{snbt('生物群系 ' + spec['biome'] + '：不在（注册表文件没有跟过来）。', 'red')}]",
        ]
    else:
        out["say3"].append(f"tellraw @s [{head},{snbt('这个存档不带自定义生物群系和时间线，天是游戏自己的。')}]")
    out["say3"] += [
        f"execute if entity @s[tag=c164.adv] run tellraw @s [{head},{snbt('进来时已经是冒险模式；难度 ')},{score}}},{snbt('（0 是和平）。')}]",
        f"execute unless entity @s[tag=c164.adv] run tellraw @s [{head},{snbt('进来时不是冒险模式（函数已改成冒险）；难度 ')},{score}}},{snbt('（0 是和平）。')}]",
        f"tellraw @s [{head},{snbt('请先别动鼠标，按 F2 截一张图；再低头看平台、回头看身后。', 'yellow')}]",
        f"function {NS}:bar",
    ]
    # the line over the hotbar: one command for each way things can stand
    dot = snbt(" · ", "gray")
    out["bar"] = [f"scoreboard players set #beat {FACTS} 0"]
    for adventure in (True, False):
        for biome in ((True, False) if spec["look"] else (None,)):
            for peaceful in (True, False):
                who = f"@a[tag=c164.bar,tag={'' if adventure else '!'}c164.adv]"
                when = "" if biome is None else f"{'if' if biome else 'unless'} score #biome {FACTS} matches 1 "
                when += f"{'if' if peaceful else 'unless'} score #diff {FACTS} matches 0 "
                parts = [snbt(name + " ", "gold"), snbt("函数在跑", "green"), dot,
                         snbt("不带生物群系", "gray") if biome is None else
                         snbt("生物群系在", "green") if biome else snbt("生物群系不在", "red"), dot,
                         snbt("进来时冒险", "green") if adventure else snbt("进来时不是冒险", "yellow"), dot]
                parts += [snbt("难度和平", "green")] if peaceful else \
                    [snbt("难度 ", "yellow"), score + ',color:"yellow"}', snbt("（不是和平）", "yellow")]
                out["bar"].append(f"execute as {who} {when}run title @s actionbar [{','.join(parts)}]")


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
    for hook, names in HOOKS.items():
        path = os.path.join(folder, "tags", "function", hook + ".json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"values": [{"id": n, "required": False} for n in names] if spec.get("guide") else []}, fh, indent=1)
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
scene = importlib.import_module("scenes." + sys.argv[1])
if not {look!r}:      # no biome, no timeline: nothing of a dynamic registry goes into the pack
    scene.BIOME = None
    place.MOOD.write = lambda *a, **k: []
if not {guide!r} and hasattr(scene, "GUIDE"):       # --no-guide: the scene is built without that layer
    scene.GUIDE = False
place.main()
"""


def place(spec, server, *more):
    """build/place.py as it is, in a process of its own; with the look off, told to leave the look
    out. Returns its output."""
    argv = ["place.py", spec["scene"], "--world", server.world, "--pw-file", server.pw_file,
            "--rcon-port", str(RCON_PORT), "--at", *(str(v) for v in spec["at"]), *more]
    code = PLACE.format(argv=argv, build=BUILD, look=spec["look"], guide=bool(spec.get("guide")))
    run = subprocess.run([sys.executable, "-c", code], cwd=PROJECT, capture_output=True, text=True,
                         env=dict(os.environ, PYTHONUNBUFFERED="1"))
    text = run.stdout + run.stderr
    for line in text.splitlines():
        say("  place: " + line)
    if run.returncode != 0:
        fail(f"build/place.py ended with {run.returncode}")
    return text


def resource_pack(scene, path, description, when, shaders=False):
    """The scene's resource pack as the world carries it: resources.zip, the pack's files at its top.
    With shaders, the look is written into it as core shaders (sky/_shaders.py reads the game's own
    shader text from the client jar: MC_JAR or MC_ROOT). Returns the number of files, the stand-ins
    and the shader files."""
    sys.path.insert(0, BUILD)
    import makepack
    tmp = os.path.join(WORK, "respack-" + os.path.basename(os.path.dirname(path)) + f"-{os.getpid()}")
    if os.path.isdir(tmp):
        shutil.rmtree(tmp)
    makepack.write(scene, tmp, look=False)      # the look goes in below or not at all (--shaders)
    if shaders:
        from scenes.obs.sky import _shaders
        for line in _shaders.pack(tmp) or []:
            say(str(line))
    sky = sorted(os.path.relpath(p, tmp).replace(os.sep, "/")
                 for p in glob.glob(os.path.join(tmp, "assets", "minecraft", "shaders", "**", "*"), recursive=True)
                 if os.path.isfile(p))
    if shaders and not sky:
        fail("sky/_shaders.pack() wrote no file under assets/minecraft/shaders/")
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
    return count, standins, sky


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
    """Chunks and entities of the saved world, counted from its region files, wherever this
    version of the game keeps them."""
    sys.path.insert(0, HERE)
    import census
    out = {"chunks": 0, "entities": {}, "regions": 0, "folders": []}
    for base, dirs, files in os.walk(world):
        dirs.sort()
        kind = os.path.basename(base)
        names = sorted(f for f in files if f.endswith(".mca")) if kind in ("region", "entities") else []
        if names:
            out["folders"].append(os.path.relpath(base, world).replace(os.sep, "/"))
        for name in names:
            if kind == "region":
                out["regions"] += 1
            for _cx, _cz, raw in census.read_chunks(os.path.join(base, name)):
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
        out["keys"] = sorted(str(k) for k in data.keys())
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


def find_cloud(server, spec, reach=320, step=4):
    """The nearest block of the cloud sea a player could stand on (two blocks of air over it), looked
    for outwards from the spawn on eight bearings: ([x, y, z] or None, how many blocks were asked for)."""
    x0, _y, z0 = (math.floor(v) for v in spec["feet"])
    asked = 0
    for r in range(step, reach + 1, step):
        for ax, az in ((1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)):
            x, z = x0 + ax * r, z0 + az * r
            for y in range(spec["catch"] + 14, spec["catch"] - 1, -1):
                asked += 1
                if "passed" in server.cmd(f"execute if block {x} {y} {z} #{NS}:cloud if block {x} {y + 1} {z} minecraft:air "
                                          f"if block {x} {y + 2} {z} minecraft:air", quiet=True):
                    return [x, y, z], asked
    return None, asked


def light_state(world, before=None):
    """{(folder, region file, cx, cz): (digest of the chunk as saved, digest of its light)} of every
    chunk of the world's region files. A chunk saved as it was at the reading before is not opened again."""
    sys.path.insert(0, HERE)
    import census
    out = {}
    for base, dirs, files in os.walk(world):
        dirs.sort()
        if os.path.basename(base) != "region":
            continue
        for name in sorted(f for f in files if f.endswith(".mca")):
            for cx, cz, raw in census.read_chunks(os.path.join(base, name)):
                key = (os.path.relpath(base, world), name, cx, cz)
                saved = hashlib.blake2b(raw, digest_size=16).digest()
                old = (before or {}).get(key)
                if old is not None and old[0] == saved:
                    out[key] = old
                    continue
                light = hashlib.blake2b(digest_size=16)
                for section in sorted(census.parse_nbt(raw).get("sections", []), key=lambda s: int(s.get("Y", 0))):
                    for part in ("SkyLight", "BlockLight"):
                        value = section.get(part)
                        light.update(f"{int(section.get('Y', 0))} {part} ".encode())
                        light.update(b"-" if value is None else value.tobytes())
                out[key] = (saved, light.digest())
    return out


def settle_light(server, limit=180.0, pause=2.0, quiet=3):
    """Waits for the game's light engine to come to rest, with the chunks still loaded. The engine
    works behind the game: after the last block is set it still has light to take away and to
    spread, a chunk is saved with the light it has at that moment, and what was not done by then
    is not done when the chunk is loaded again (two saves of one commit held different light in
    274 of 2862 chunks, by up to 15). So the world is saved and the light of every chunk read,
    over and over, until `quiet` readings in a row are the same as the one before each."""
    t = time.time()
    state, changed, still = None, [], 0
    while True:
        server.cmd("save-all flush", quiet=True)
        try:
            new = light_state(server.world, state)
        except Exception as exc:    # noqa: BLE001 -- a file met half written; the reading is taken again
            say(f"  light: a reading failed ({type(exc).__name__}: {exc}); again")
            new = None
        if new is not None:
            if state is not None:
                changed.append(sum(1 for k, v in new.items() if state.get(k, (None, None))[1] != v[1]))
                still = still + 1 if changed[-1] == 0 else 0
            state = new
        if still >= quiet or time.time() - t > limit:
            break
        time.sleep(pause)
    out = {"settled": still >= quiet, "seconds": round(time.time() - t, 1), "chunks": len(state or {}), "changed": changed}
    say(f"light: {'at rest' if out['settled'] else 'NOT at rest'} after {out['seconds']} s; {out['chunks']} chunks, "
        f"chunks whose light had changed at each reading: {changed}")
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
        f"back to it under y {spec['catch']}" + (" and from the cloud sea's blocks" if spec["cloud"] else "")
        + (f", trial {spec['trial']}" if spec["trial"] else ""))
    facts = {"name": args.name, "commit": head, "assembly": args.assembly, "version": VERSION, "spec": spec, "ok": False,
             "made_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
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
        built, moving = re.search(r"built (\d+) blocks, (\d+) entities", text), re.search(r"motion: (\d+) parts", text)
        facts["built"] = {"blocks": int(built.group(1)) if built else None, "entities": int(built.group(2)) if built else None,
                          "moving": int(moving.group(1)) if moving else 0}
        x, y, z = spec["feet"]
        # what carries who arrives: the first block under the spawn's feet
        top = math.floor(y - 0.01)
        ground = next((by for by in range(top, spec["catch"] - 1, -1) if "passed" in server.cmd(
            f"execute unless block {math.floor(x)} {by} {math.floor(z)} minecraft:air", quiet=True)), None)
        if ground is None:
            fail(f"there is nothing under the spawn's feet {spec['feet']} down to y {spec['catch']}, where players "
                 "are put back on the spot: who arrives would fall for ever")
        spec["ground"] = ground + 1
        facts["notes"] = []
        if ground < top:
            facts["notes"].append(f"the spawn hangs {top - ground} blocks over what carries it: feet {spec['feet']}, the first "
                                  f"block under them at y {ground}. Who arrives drops that far (no fall damage).")
            say("NOTE: " + facts["notes"][-1])
        if spec["cloud"]:
            t = time.time()
            spec["cloud_at"], asked = find_cloud(server, spec)
            if spec["cloud_at"] is None:
                facts["notes"].append(f"no block of the cloud sea was found within 320 blocks of the spawn ({asked} blocks asked "
                                      "for): the rule that puts back who stands on one is in the pack, but there is nothing to try it on.")
                say("NOTE: " + facts["notes"][-1])
            else:
                say(f"a cloud block to stand on: {spec['cloud_at']} ({asked} blocks asked for in {time.time() - t:.1f} s)")
        facts["settings"] = []
        for command in setting_commands(spec):
            reply = server.cmd(command)
            bad = any(w in reply for w in ("Unknown or incomplete", "Incorrect argument", "Expected", "Invalid"))
            facts["settings"].append({"command": command, "reply": reply, "ok": not bad})
        refused = [s["command"] for s in facts["settings"] if not s["ok"]]
        if refused:
            fail("the server refused: " + "; ".join(refused))
        if spec["trial"]:
            # the save's name, hung seven blocks ahead of who arrives, between what stands there and the sky
            turn = math.radians(spec["yaw"])
            reply = server.cmd(
                f"summon minecraft:text_display {num(x - 7.0 * math.sin(turn))} {num(y + 5.4)} {num(z + 7.0 * math.cos(turn))} "
                f"{{text:{snbt('c164 试传 ' + spec['trial'], 'gold')},billboard:\"center\",shadow:1b,"
                "brightness:{sky:15,block:15},Tags:[\"c164.label\"],"
                "transformation:{left_rotation:[0f,0f,0f,1f],right_rotation:[0f,0f,0f,1f],"
                "translation:[0f,0f,0f],scale:[1.5f,1.5f,1.5f]}}")
            if "Summoned" not in reply:
                fail(f"the save's name was not hung up: {reply}")
        server.cmd(f"gamerule max_block_modifications {default.group(1)}")
        facts["loop"] = server.cmd("scoreboard players get #run c164m")
        # last of all, with every chunk still loaded: the light is waited for
        facts["light"] = settle_light(server)
        if not facts["light"]["settled"]:
            facts["notes"].append(f"the light was still changing {facts['light']['seconds']} s after the last block was set "
                                  f"(chunks whose light changed at each reading: {facts['light']['changed']}): the save holds "
                                  "the light of that moment, and two saves of this commit will not hold the same.")
            say("NOTE: " + facts["notes"][-1])
        server.cmd("forceload remove all")
        # the spawn's own chunk stays loaded. Where the default game mode is adventure the game sets
        # who is new on the world spawn and lets him sink to the first thing that carries him; in
        # 26.3 nothing is loaded at that moment, and without this he starts at the world's floor
        # (seen in verify: y -63) until the first tick of the functions.
        facts["forced"] = server.cmd(f"forceload add {math.floor(x)} {math.floor(z)}")
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


def registry_files(pack_dir):
    """The pack's files outside the kinds a finished map may carry, from the pack's root. The tags
    of timelines are counted with them: ours names a timeline that exists only with those files."""
    out = []
    data = os.path.join(pack_dir, "data")
    for namespace in sorted(os.listdir(data)) if os.path.isdir(data) else []:
        for kind in sorted(os.listdir(os.path.join(data, namespace))):
            top = os.path.join(data, namespace, kind)
            if kind == "tags":
                top = os.path.join(top, "timeline")
            elif kind in ALLOWED_KINDS:
                continue
            if os.path.isfile(top):
                out.append(os.path.relpath(top, pack_dir))
            for folder, _dirs, names in os.walk(top):
                out.extend(os.path.relpath(os.path.join(folder, n), pack_dir) for n in names)
    return sorted(out)


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
    registry = registry_files(pack_dir)
    if registry and not spec["look"]:
        fail("the look is off and the data pack still holds registry files: " + ", ".join(registry))
    count, standins, sky = resource_pack(spec["scene"], os.path.join(stage, "resourcepacks", "resources.zip"),
                                         f"c164 {name} ({head})", when, spec.get("shaders"))
    kinds = {}
    for folder, _dirs, names in os.walk(os.path.join(pack_dir, "data")):
        part = os.path.relpath(folder, os.path.join(pack_dir, "data")).split(os.sep)
        if len(part) > 1 and names:
            kinds[part[1]] = kinds.get(part[1], 0) + len(names)
    facts.update(removed=sorted(removed), registry_files=registry, data_pack=kinds,
                 resource_pack={"files": count, "standins": standins, "shaders": sky,
                                "bytes": os.path.getsize(os.path.join(stage, "resourcepacks", "resources.zip"))},
                 numbers=numbers(stage), level=level_facts(stage), files=listing(stage))
    path = os.path.join(out_dir, name + ".zip")
    files = zip_tree(stage, path, name, when)
    facts["zip"] = {"file": os.path.basename(path), "bytes": os.path.getsize(path), "files": files,
                    "sha256": sha256_of(path), "top": name}
    say(f"sealed: removed {', '.join(sorted(removed)) or 'nothing'}; registry files: {', '.join(registry) or 'none'}; "
        f"resource pack {count} files" + (f", {len(standins)} stand-ins (ph_) still in it" if standins else "")
        + (f", {len(sky)} of them shaders (the look)" if sky else ", no shaders"))


# ------------------------------------------------------------------ verify

def check(results, name, ok, detail):
    results.append({"check": name, "ok": bool(ok), "detail": detail})
    say(f"  [{'ok' if ok else 'NO'}] {name}: {detail}")


def near(a, b, eps=0.02):
    return a is not None and all(abs(p - q) <= eps for p, q in zip(a, b))


def told(bot):
    """What the chat showed the fake player, without the server's own word of who came and went."""
    return [s for s in bot.texts("chat") if not s.startswith("multiplayer.player.")]


def visit(server, spec, results, tag, came):
    """A fake player joins, is looked at, falls, leaves, comes back. `came` is what this server's
    own settings and this save make of who joins: {"adventure", "peaceful": bool, "biome": bool or
    None}; a trial save is to tell exactly that."""
    sys.path.insert(0, HERE)
    import mcbot
    feet = tuple(spec["feet"])
    aim = (spec["yaw"] % 360.0, spec["pitch"])
    wait = 5.0 if spec["trial"] else 3.0        # a trial save takes two seconds to say all it says

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
    first = (bot.position, bot.rotation)
    bot.pump(wait)
    check(results, tag + "join", near(bot.position, feet) and turned(bot),
          f"joined in {joined:.1f} s at {first[0]} facing {first[1]}, after the functions at {bot.position} "
          f"facing {bot.rotation}; wanted {feet} facing {aim}")
    # where the game itself sets him, before any function: on the world spawn, or on what carries it, with
    # its facing. Held to that where the server's game mode is adventure, as the save asks for; a
    # server in survival looks for the top of the column, and the functions are what brings him back.
    low = spec.get("ground", feet[1])
    put = first[0] is not None and abs(first[0][0] - feet[0]) < 0.02 and abs(first[0][2] - feet[2]) < 0.02 \
        and low - 1.02 <= first[0][1] <= feet[1] + 0.02 and abs(first[1][1] - aim[1]) < 0.05 \
        and abs((first[1][0] - aim[0] + 180.0) % 360.0 - 180.0) < 0.05
    check(results, tag + "spawn", put or not came["adventure"],
          f"the game set him at {first[0]} facing {first[1]}" + ("" if put else ", not on the spawn")
          + ("" if came["adventure"] else " (this server's game mode is survival: told, not held against the save)"))
    mode = server.cmd(f"data get entity {BOT} playerGameType", quiet=True)
    reach = server.cmd(f"attribute {BOT} minecraft:block_interaction_range base get", quiet=True)
    tags = server.cmd(f"tag {BOT} list", quiet=True)
    check(results, tag + "mode", mode.rstrip().endswith(": 2"), mode)
    check(results, tag + "reach", re.search(r"is 0(\.0+)?\s*$", reach) is not None, reach)
    check(results, tag + "tag", IN_TAG in tags, tags)
    said = told(bot)
    if spec["trial"]:
        check(results, tag + "greeting", any("函数在跑" in s for s in said) and any("F2" in s for s in said),
              " | ".join(said) or "nothing was said")
        bars = bot.texts("actionbar")
        bar = bars[-1] if bars else ""
        right = ["函数在跑" in bar, ("不是冒险" in bar) != came["adventure"], ("不是和平" in bar) != came["peaceful"]]
        if came["biome"] is not None:
            right += [("生物群系不在" in bar) != came["biome"], "生物群系" in bar,
                      any("：在。" in s for s in said) == came["biome"], any("不在" in s for s in said) != came["biome"]]
        check(results, tag + "line over the hotbar", all(right),
              (f"{bar} (sent {len(bars)} times)" if bars else "no such line was sent")
              + f"; wanted it to tell: adventure {came['adventure']}, peaceful {came['peaceful']}"
              + (f", biome {came['biome']}" if came["biome"] is not None else ""))
    else:
        # the chat is what has to stay empty; titles and the line over the hotbar are the guide's
        # to use (plan/packages/motion/guide.md) and are looked at below
        spoken = sum(bot.packet_counts.get(n, 0) for n in ("player_chat", "disguised_chat"))
        check(results, tag + "quiet", not said and not spoken,
              (" | ".join(said) or "nothing stood in the chat, as it should be")
              + (f"; {spoken} messages came as a player's chat" if spoken else ""))
    # under the line: put there by hand, the tick function has him back before the next look
    under = (feet[0] + 20, spec["catch"] - 6, feet[2])
    go = f"tp {BOT} {num(under[0])} {num(under[1])} {num(under[2])}"
    server.cmd(go, quiet=True)
    bot.pump(1.5)
    check(results, tag + "fall", near(bot.position, feet) and turned(bot),
          f"put at y {under[1]}, a moment later at {bot.position} facing {bot.rotation}")
    # an operator in spectator mode is left where he flies; back in adventure, the line has him at once
    server.cmd(f"gamemode spectator {BOT}", quiet=True)
    server.cmd(go, quiet=True)
    bot.pump(1.0)
    stayed = bot.position
    server.cmd(f"gamemode adventure {BOT}", quiet=True)
    bot.pump(1.0)
    check(results, tag + "spectator", near(stayed, under) and near(bot.position, feet),
          f"as a spectator put at y {under[1]}: a moment later at {stayed}; set to adventure there: a moment later at {bot.position}")
    # the tick with him where the map begins, over the last hundred ticks
    bot.pump(4.0)
    one = server.cmd("tick query", quiet=True)
    check(results, tag + "tick, one player", True, one.replace("\n", " | "))
    if spec.get("cloud"):
        at = spec.get("cloud_at")
        if not at:
            check(results, tag + "on the cloud", False, "the rule is in the pack, but make found no cloud block to try it on")
        else:
            what = server.cmd(f"execute if block {at[0]} {at[1]} {at[2]} #{NS}:cloud", quiet=True)
            server.cmd(f"tp {BOT} {num(at[0] + 0.5)} {num(at[1] + 1)} {num(at[2] + 0.5)}", quiet=True)
            bot.pump(1.5)
            check(results, tag + "on the cloud", "passed" in what and near(bot.position, feet) and turned(bot),
                  f"stood on the cloud block at {at} ({what}), a moment later at {bot.position} facing {bot.rotation}")
            high = (at[0] + 0.5, at[1] + 4.0, at[2] + 0.5)
            server.cmd(f"tp {BOT} {num(high[0])} {num(high[1])} {num(high[2])}", quiet=True)
            bot.pump(1.5)
            check(results, tag + "over the cloud", near(bot.position, high),
                  f"put three blocks over it, a moment later at {bot.position}")
    # just over the line he is left alone. Far out, where nothing stands: over the sea the block
    # under such feet may be a cloud block, which is the other rule's business
    over = (feet[0] + 3000, spec["catch"] + 0.5, feet[2])
    server.cmd(f"tp {BOT} {num(over[0])} {num(over[1])} {num(over[2])}", quiet=True)
    bot.pump(2.5)
    check(results, tag + "over the line", near(bot.position, over), f"put at y {over[1]}, a moment later at {bot.position}")
    # the guide greets who is new once, with a title, and who comes back with a line over the hotbar
    greets = spec.get("guide") and os.path.exists(os.path.join(
        server.world, "datapacks", PACK, "data", *HOOKS["first"][0].split(":", 1)[0:1], "function",
        HOOKS["first"][0].split(":", 1)[1] + ".mcfunction"))
    if spec.get("guide") and not greets:
        say(f"  {tag}the save has the guide, but no function {HOOKS['first'][0]}: nothing greets who arrives")
    if greets:
        titles, subs, bars = bot.texts("title"), bot.texts("subtitle"), bot.texts("actionbar")
        check(results, tag + "title", titles == [spec.get("title")] and subs == [GUIDE_SUB],
              f"titles shown to who is new: {titles or 'none'}; under them: {subs or 'none'}; "
              f"lines over the hotbar: {sorted(set(bars)) or 'none'}; wanted once each: {spec.get('title')} / {GUIDE_SUB}")
    before = len(bot.events)
    bot.close()
    time.sleep(2.0)
    try:
        bot = mcbot.Bot(BOT, HOST, PORT).connect(timeout=60.0)
    except Exception as exc:
        check(results, tag + "rejoin", False, f"the fake player could not come back: {type(exc).__name__}: {exc}")
        return
    bot.pump(wait)
    said = told(bot)
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
    if greets:
        titles, bars = bot.texts("title") + bot.texts("subtitle"), bot.texts("actionbar")
        check(results, tag + "title, again", not titles and not bars,
              f"titles shown to who comes back: {titles or 'none'}; lines over the hotbar: {sorted(set(bars)) or 'none'}; "
              "wanted neither (he is told nothing)")
    bot.close()
    time.sleep(1.0)


def loop_runs(server, pack_dir, spec, results, tag):
    """Does anything move: the display entities the loop names are read twice, three seconds
    apart. Needs a player near, so that their chunks are loaded and the loop is awake."""
    names = set()
    for path in glob.glob(os.path.join(pack_dir, "data", ART, "function", f"{spec['scene']}-motion", "**", "*.mcfunction"),
                          recursive=True):
        with open(path, encoding="utf-8") as fh:
            names.update(re.findall(r"tag=(m\.[A-Za-z0-9_.+\-]+)", fh.read()))
    if not names:
        check(results, tag + "loop", True, "the scene registers nothing that moves")
        return
    run = server.cmd("scoreboard players get #run c164m", quiet=True)

    def read(name):
        reply = server.cmd(f"data get entity @e[tag={name},limit=1]", quiet=True)
        if "entity data" not in reply:
            return None
        # what the loop changes: how the part is turned and placed, and what it shows
        return tuple(re.findall(r"(?:left_rotation|right_rotation|translation|scale): \[[^\]]*\]|item_model\W+[a-z0-9_:./]+"
                                r"|Rotation: \[[^\]]*\]|Pos: \[[^\]]*\]", reply))

    some = sorted(names)[:40]
    before = {name: read(name) for name in some}
    time.sleep(3.0)
    after = {name: read(name) for name in some}
    there = [n for n in some if before[n] is not None]
    moved = [n for n in there if before[n] != after[n]]
    check(results, tag + "loop", bool(moved),
          f"{len(names)} moving parts named in the loop, {len(there)} of the first {len(some)} loaded near the spawn, "
          f"{len(moved)} of them changed within 3 s" + (f" (e.g. {', '.join(moved[:4])})" if moved else "") + f"; {run}")


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
    # A server takes the game mode of who is new and the difficulty from its own settings at every
    # start, not from the save (on Realms: from the slot's settings). The first start is given the
    # wrong ones on purpose: what the save's functions are to hold must hold all the same. Then once
    # more with the right ones, as a slot is set that was filled from this save.
    hostile, as_set = dict(gamemode="survival", difficulty="easy"), dict(gamemode="adventure", difficulty="peaceful")
    runs = [("", "srv", hostile), ("as set: ", "set", as_set)] + ([("stripped: ", "stripped", hostile)] if args.strip else [])
    try:
        for tag, kind, own in runs:
            strip, first = kind == "stripped", kind == "srv"
            folder = os.path.join(work, kind)
            os.makedirs(folder)
            with zipfile.ZipFile(archive) as zf:
                tops = {n.split("/", 1)[0] for n in zf.namelist()}
                zf.extractall(folder)
            if tops != {name}:
                check(results, tag + "layout", False, f"the archive's top is {sorted(tops)}, wanted one folder {name}")
                break
            world = os.path.join(folder, name)
            pack_dir = os.path.join(world, "datapacks", PACK)
            if first:
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
                # the look as core shaders: there when the save goes without the biome and was made
                # to carry them, and never beside the biome (a2 c322 #72794: two skies, one on the other)
                sky = sorted(n for n in inner if n.startswith("assets/minecraft/shaders/") and not n.endswith("/"))
                noted = (made.get("resource_pack") or {}).get("shaders")
                check(results, "shaders", bool(sky) == bool(spec.get("shaders")) and not (sky and spec["look"])
                      and (noted is None or sky == sorted(noted)),
                      (f"{len(sky)} shader files in the resource pack" if sky else "no shader file in the resource pack")
                      + f"; the save was made {'to carry' if spec.get('shaders') else 'without'} the look as shaders"
                      + f", {'with' if spec['look'] else 'without'} the biome")
                light = made.get("light")       # saves made before the light was waited for say nothing of it
                if light is not None:
                    check(results, "light", bool(light.get("settled")),
                          f"the light was {'at rest' if light.get('settled') else 'NOT at rest'} when the world was saved: waited "
                          f"{light.get('seconds')} s, chunks whose light had changed at each reading {light.get('changed')}")
            elif strip:
                gone = registry_files(pack_dir)
                for rel in gone:
                    os.remove(os.path.join(pack_dir, rel))
                say(f"stripped run: taken out of the data pack: {', '.join(gone) or 'nothing (the save has no registry files)'}")
                if not gone:
                    break
            server = Server(folder, name, java, jar)
            server.settings(**own)
            started = server.start()
            check(results, tag + "starts", True, f"up in {started:.0f} s, the server's own settings: {own}")
            packs = server.cmd("datapack list enabled", quiet=True)
            check(results, tag + "data pack", f"file/{PACK}" in packs, packs)
            if first:
                rules = {}
                for rule, value in RULES + [("max_block_modifications", None)]:
                    reply = server.cmd(f"gamerule {rule}", quiet=True)
                    rules[rule] = (re.search(r"set to (\S+)\s*$", reply) or re.search(r"()$", reply)).group(1) or reply
                wrong = {r: v for r, v in rules.items() if dict(RULES).get(r) not in (None, v)}
                report["rules"] = rules
                check(results, "game rules", not wrong, f"{len(rules) - len(wrong)} of {len(rules)} as the list says"
                      + (f"; not: {wrong}" if wrong else "") + f"; max_block_modifications {rules['max_block_modifications']}")
                forced = server.cmd("forceload query", quiet=True)
                check(results, "forced chunks", len(re.findall(r"\[-?\d+, -?\d+\]", forced)) == 1,
                      forced + " (wanted: the spawn's chunk and no other)")
                time.sleep(3.0)
                check(results, "tick, empty", True, server.cmd("tick query", quiet=True).replace("\n", " | "))
                found = server.cmd("difficulty", quiet=True)
                if spec["trial"]:       # a trial save leaves it alone, to tell what the server made of it
                    check(results, "difficulty", True, found + " (the server's own; a trial save does not set it)")
                else:
                    check(results, "difficulty", "Peaceful" in found, found + " (the server's own setting is easy)")
            came = {"adventure": own["gamemode"] == "adventure", "peaceful": own["difficulty"] == "peaceful",
                    "biome": (not strip) if spec["look"] else None}
            visit(server, spec, results, tag, came)
            if first:
                import mcbot
                bot = mcbot.Bot(BOT, HOST, PORT).connect(timeout=60.0)
                # he left far out; the parts are read with him where the map begins
                server.cmd("tp {} {} {} {}".format(BOT, *(num(v) for v in spec["feet"])), quiet=True)
                bot.pump(3.0)
                loop_runs(server, pack_dir, spec, results, tag)
                bot.close()
            server.stop()
            issues = server.issues()
            report[tag + "issues"] = issues
            # the stripped save is expected to complain; a slow tick is the machine's, told but not held against the save
            real = [] if strip else [i for i in issues if "Can't keep up!" not in i]
            check(results, tag + "console", not real,
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
    count, standins, sky = resource_pack(args.scene, os.path.join(out, "resourcepacks", "resources.zip"),
                                         f"c164 {args.name} ({head})", when, spec.get("shaders"))
    say(f"spec: {json.dumps(spec, ensure_ascii=False)}")
    say(f"functions {NS}: {', '.join(written)}; resource pack {count} files, {len(standins)} stand-ins, "
        f"{len(sky)} shader files; in {out}")
    for command in setting_commands(spec):
        say("  would run: " + command)


# What two saves of one world never share, left out when their chunks are compared: the game's clock
# at the moment a chunk was written and how long players have been near it, and the ids the game
# draws by chance for every entity.
VOLATILE = ("LastUpdate", "InhabitedTime", "UUID")
UNORDERED = ("Entities", "block_entities", "Records")       # lists the game writes in no fixed order


def steady(value, key=None):
    """An NBT value as plain data that can be compared and sorted, without the VOLATILE keys."""
    if isinstance(value, dict):
        return tuple(sorted((str(k), steady(v, str(k))) for k, v in value.items() if k not in VOLATILE))
    if hasattr(value, "tobytes"):       # the arrays
        return value.tobytes()
    if isinstance(value, (list, tuple)):
        items = [steady(v) for v in value]
        return tuple(sorted(items, key=repr)) if key in UNORDERED else tuple(items)
    if isinstance(value, float):
        return float(value)
    if isinstance(value, int):
        return int(value)
    return str(value)


def chunks_of(world):
    """{(kind, region file, cx, cz): the chunk's steady value} of every .mca under a world."""
    sys.path.insert(0, HERE)
    import census
    out = {}
    for base, dirs, files in os.walk(world):
        dirs.sort()
        for name in sorted(f for f in files if f.endswith(".mca")):
            for cx, cz, raw in census.read_chunks(os.path.join(base, name)):
                out[(os.path.basename(base), name, cx, cz)] = (steady(census.parse_nbt(raw)), raw)
    return out


def blocks_of(raw):
    """{block name: how many} of a region chunk, and per section what it holds besides."""
    import census
    counts, parts = {}, {}
    for section in census.parse_nbt(raw).get("sections", []):
        names, n = census.section_counts(section)
        for name, k in zip(names or (), n if n is not None else ()):
            counts[str(name)] = counts.get(str(name), 0) + int(k)
        y = int(section.get("Y", 0))
        for key in section:
            if key != "Y":
                parts[(y, str(key))] = steady(section[key], str(key))
    return counts, parts


def light_of(pairs):
    """What differs in the light of pairs of one chunk [(raw of the first save, raw of the second)]:
    the lines to print. The game saves the light it has at that moment; work its light engine has
    not come to is not in the file, and is not done again when the chunk is loaded."""
    import census
    lone, both, worst, gaps = {}, {}, [], []
    for raw_a, raw_b in pairs:
        ta, tb = census.parse_nbt(raw_a), census.parse_nbt(raw_b)
        x0, z0 = int(ta.get("xPos", 0)) * 16, int(ta.get("zPos", 0)) * 16
        sa = {int(s.get("Y", 0)): s for s in ta.get("sections", [])}
        sb = {int(s.get("Y", 0)): s for s in tb.get("sections", [])}
        for y in sorted(set(sa) | set(sb)):
            for part in ("SkyLight", "BlockLight"):
                la, lb = sa.get(y, {}).get(part), sb.get(y, {}).get(part)
                la, lb = (None if v is None else v.tobytes() for v in (la, lb))
                if la == lb:
                    continue
                if la is None or lb is None:
                    there = la or lb
                    same = len(set(there)) == 1 and there[0] >> 4 == there[0] & 15
                    key = (part, f"all {there[0] & 15}" if same else "mixed")
                    lone[key] = lone.get(key, 0) + 1
                    gaps.append((part, x0, y * 16, z0, "first" if la is None else "second", key[1],
                                 sum(((b & 15) > 0) + ((b >> 4) > 0) for b in there)))
                    continue
                n = big = up = 0
                for p, q in zip(la, lb):
                    if p != q:
                        for shift in (0, 4):
                            d = ((q >> shift) & 15) - ((p >> shift) & 15)
                            if d:
                                n, big, up = n + 1, max(big, abs(d)), up + (d > 0)
                s, k, b, u = both.get(part, (0, 0, 0, 0))
                both[part] = (s + 1, k + n, max(b, big), u + up)
                worst.append((n, big, part, x0, y * 16, z0))
    lines = []
    for part in ("SkyLight", "BlockLight"):
        alone = {k[1]: v for k, v in lone.items() if k[0] == part}
        s, k, b, u = both.get(part, (0, 0, 0, 0))
        if alone or s:
            lines.append(f"  {part}: in {s} sections both saves have it and {k} values differ, by up to {b} "
                         f"({u} are higher in the second, {k - u} lower); in {sum(alone.values())} sections one save has none"
                         + (" (the other's is " + ", ".join(f"{name} in {v}" for name, v in sorted(alone.items())) + ")" if alone else ""))
    for part in ("SkyLight", "BlockLight"):     # by height: what lies under a floor nobody gets under is not seen
        levels = {}
        for n, big, p, x, y, z in worst:
            if p == part:
                s, k, b = levels.get(y, (0, 0, 0))
                levels[y] = (s + 1, k + n, max(b, big))
        if levels:
            lines.append(f"      {part} by height: " + "; ".join(
                f"y {y}..{y + 15}: {s} sections, {k} values, by up to {b}" for y, (s, k, b) in sorted(levels.items())))
    for part, x, y, z, which, kind, lit in sorted(gaps, key=lambda g: (g[0], -g[6]))[:20]:
        lines.append(f"      x {x}..{x + 15} y {y}..{y + 15} z {z}..{z + 15}: {part}, none in the {which} save; "
                     f"the other's is {kind}, {lit} values above 0")
    few = [w for w in worst if w[2] == "BlockLight"]
    for n, big, part, x, y, z in sorted(few, reverse=True)[:16] + sorted((w for w in worst if w[2] == "SkyLight"), reverse=True)[:8]:
        lines.append(f"      x {x}..{x + 15} y {y}..{y + 15} z {z}..{z + 15}: {part}, {n} values, by up to {big}")
    if worst:
        xs, ys, zs = [w[3] for w in worst], [w[4] for w in worst], [w[5] for w in worst]
        lines.append(f"      all of them within x {min(xs)}..{max(xs) + 15}, y {min(ys)}..{max(ys) + 15}, z {min(zs)}..{max(zs) + 15}")
    return lines


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
    if not args.deep:
        raise SystemExit(1 if only_a or only_b or differ else 0)

    # The region files of two saves never are the same bytes (every chunk carries the hour it was
    # written, every entity an id drawn by chance). What has to be the same is what is in the
    # chunks: so they are opened and compared without those.
    work = os.path.join(WORK, f"compare-{os.getpid()}")
    worlds = []
    try:
        for i, path in enumerate((args.a, args.b)):
            folder = os.path.join(work, str(i))
            with zipfile.ZipFile(path) as zf:
                zf.extractall(folder)
            worlds.append(chunks_of(folder))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    first, second = worlds
    bad = False
    for kind in sorted({k[0] for k in list(first) + list(second)}):
        mine = {k: v[0] for k, v in first.items() if k[0] == kind}
        theirs = {k: v[0] for k, v in second.items() if k[0] == kind}
        lone = sorted(set(mine) ^ set(theirs))
        changed = sorted(k for k in set(mine) & set(theirs) if mine[k] != theirs[k])
        print(f"{kind}: {len(mine)} and {len(theirs)} chunks; {len(set(mine) & set(theirs)) - len(changed)} hold the same, "
              f"{len(changed)} differ, {len(lone)} are in one save only")
        bad = bad or bool(lone) or bool(changed)
        for k in lone[:10]:
            print(f"  in one save only: {k[1]} chunk {k[2]} {k[3]}")
        if kind == "region" and changed:
            # what of a section differs, and whether the blocks themselves do: counted by name
            where, moved, other = {}, {}, 0
            for k in changed:
                (ca, pa), (cb, pb) = blocks_of(first[k][1]), blocks_of(second[k][1])
                for part in sorted({p[1] for p in set(pa) | set(pb) if pa.get(p) != pb.get(p)}):
                    where[part] = where.get(part, 0) + 1
                if ca != cb:
                    other += 1
                    for name in set(ca) | set(cb):
                        if ca.get(name, 0) != cb.get(name, 0):
                            moved[name] = moved.get(name, 0) + cb.get(name, 0) - ca.get(name, 0)
            print("  in the sections of the chunks that differ: "
                  + (", ".join(f"{part} in {n} chunks" for part, n in sorted(where.items())) or "nothing (another key of the chunk)"))
            print(f"  chunks whose blocks, counted by name, are not the same: {other}")
            for name, n in sorted(moved.items(), key=lambda kv: (-abs(kv[1]), kv[0]))[:20]:
                print(f"      {name}: {n:+d} in the second")
            for text in light_of([(first[k][1], second[k][1]) for k in changed]):
                print(text)
        told = 0
        for k in changed:
            x, y = dict(mine[k]), dict(theirs[k])
            keys = sorted(n for n in set(x) | set(y) if x.get(n) != y.get(n))
            if told < 12:
                told += 1
                print(f"  differs: {k[1]} chunk {k[2]} {k[3]}: {', '.join(keys)}")
                for n in keys:
                    if n in UNORDERED and isinstance(x.get(n), tuple) and isinstance(y.get(n), tuple):
                        gone = [e for e in x[n] if e not in y[n]]
                        come = [e for e in y[n] if e not in x[n]]
                        print(f"      {n}: {len(x[n])} and {len(y[n])}; {len(gone)} of the first are not in the second, "
                              f"{len(come)} of the second not in the first")
                        for e in gone[:3]:
                            d = dict(e) if e and isinstance(e[0], tuple) else {}
                            e2 = next((dict(c) for c in come if dict(c).get("id") == d.get("id")
                                       and dict(c).get("Tags") == d.get("Tags")), {})
                            print(f"        {d.get('id', '?')} {d.get('Tags', '')}: "
                                  + (", ".join(sorted(f for f in set(d) | set(e2) if d.get(f) != e2.get(f))) if e2
                                     else "no entity of that id and those tags in the second"))
        if len(changed) > told:
            print(f"  ... and {len(changed) - told} more")
    print("the chunks hold the same in both saves" if not bad else "the chunks do NOT hold the same")
    raise SystemExit(1 if bad or only_a or only_b else 0)


PAGE_OPEN = "<!-- 下面到「到这里」为止由 tools/export.py page 写，手改会被下一轮盖掉 -->"
PAGE_CLOSE = "<!-- 到这里 -->"


def page(args):
    """dist/history.json gets the newest whole save's row, dist/README.md its table."""
    dist = os.path.abspath(args.dist)
    path = os.path.join(dist, "history.json")
    rows = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            rows = json.load(fh)
    folders = sorted((int(os.path.basename(f)[1:]), f) for f in glob.glob(os.path.join(dist, "A[0-9]*")) if os.path.isdir(f))
    if not folders:
        fail(f"no whole save (A<n>/) under {dist}")
    n, folder = folders[-1]
    name = f"c164-A{n}"
    with open(os.path.join(folder, name + ".json"), encoding="utf-8") as fh:
        made = json.load(fh)
    checks = {"ok": None, "seconds": None, "checks": [], "issues": None}
    if os.path.exists(os.path.join(folder, name + ".verify.json")):
        with open(os.path.join(folder, name + ".verify.json"), encoding="utf-8") as fh:
            checks = json.load(fh)
    if not made.get("ok"):
        fail(f"{name}.json says the save was not made whole; the page is left as it is")
    at = None
    if made.get("made_at"):         # the project's clock is UTC+8
        at = time.strftime("%m-%d %H:%M", time.gmtime(calendar.timegm(time.strptime(made["made_at"], "%Y-%m-%dT%H:%M:%SZ")) + 8 * 3600))
    failed = [c["check"] for c in checks["checks"] if not c["ok"]]
    look = None
    if os.path.exists(os.path.join(folder, name + "-look.json")):
        with open(os.path.join(folder, name + "-look.json"), encoding="utf-8") as fh:
            with_look = json.load(fh)
        if with_look.get("ok"):
            look = {"file": with_look["zip"]["file"], "bytes": with_look["zip"]["bytes"], "sha256": with_look["zip"]["sha256"],
                    "registry_files": len(with_look["registry_files"]), "time": with_look["spec"]["time"]}
    plain = None
    if os.path.exists(os.path.join(folder, name + "-plain.json")):
        with open(os.path.join(folder, name + "-plain.json"), encoding="utf-8") as fh:
            without = json.load(fh)
        if without.get("ok"):
            plain = {"file": without["zip"]["file"], "bytes": without["zip"]["bytes"], "sha256": without["zip"]["sha256"],
                     "shaders": len(without["resource_pack"].get("shaders") or []), "verified": None}
            if os.path.exists(os.path.join(folder, name + "-plain.verify.json")):
                with open(os.path.join(folder, name + "-plain.verify.json"), encoding="utf-8") as fh:
                    plain["verified"] = json.load(fh).get("ok")
    row = {
        "n": f"A{n}", "assembly": made.get("assembly"), "at": at, "time": made["spec"]["time"], "look": look, "plain": plain,
        "zip_bytes": made["zip"]["bytes"], "sha256": made["zip"]["sha256"],
        "pack_bytes": made["resource_pack"].get("bytes"), "pack_files": made["resource_pack"]["files"],
        "standins": len(made["resource_pack"]["standins"]),
        "shaders": len(made["resource_pack"].get("shaders") or []),
        "blocks": (made.get("built") or {}).get("blocks"), "entities": sum(made["numbers"]["entities"].values()),
        "moving": (made.get("built") or {}).get("moving"),
        "functions": (made.get("data_pack") or {}).get("function"), "tags": (made.get("data_pack") or {}).get("tags"),
        "registry_files": len(made["registry_files"]), "cloud": bool(made["spec"].get("cloud")),
        "make_s": made["seconds"], "verify_s": checks["seconds"], "checks": len(checks["checks"]), "failed": failed,
        "verified": checks["ok"], "console": len(made.get("issues") or []) + sum(
            len(v) for k, v in checks.items() if k.endswith("issues") and isinstance(v, list)),
        "note": args.note, "commit": args.commit,
        # the light at rest before the world was saved (seconds waited), False when it never was;
        # None for the saves made before it was waited for (A1 to A6)
        "light": None if made.get("light") is None else made["light"]["seconds"] if made["light"].get("settled") else False,
    }
    # what this run does not know stays as the row had it (a note given earlier, the figures of a
    # save made before its note told them)
    old = next((r for r in rows if r["n"] == row["n"]), {})
    for key, value in row.items():
        if value is None and old.get(key) is not None:
            row[key] = old[key]
    rows = [r for r in rows if r["n"] != row["n"]] + [row]
    rows.sort(key=lambda r: -int(r["n"][1:]))
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rows, fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    def mb(v):
        return "?" if v is None else f"{v:,} 字节（{v / 1048576:.1f} 兆）".replace(",", " ")

    def line(r):
        if r.get("verified") is None:
            checked = "没验"
        elif r["verified"]:
            checked = f"{r['checks']} 项全过" if r.get("checks") else "全过"
        else:
            checked = "没过：" + "、".join(r.get("failed") or ["?"])
        here = os.path.isdir(os.path.join(dist, r["n"]))
        gone = "" if here else "已从这里拿掉。"
        return (f"| {'[' + r['n'] + '](' + r['n'] + '/)' if here else r['n']} | {r['assembly'] or '?'} | {r['at'] or '?'} | "
                f"{mb(r['zip_bytes'])} | {mb(r['pack_bytes'])}，{r['pack_files']} 个文件 | "
                f"{r['blocks'] if r['blocks'] is not None else '?'} / {r['entities']} / {r['moving'] if r['moving'] is not None else '?'} | "
                f"{r.get('time') or '?'} | {checked} | {r['note'] or ''}{gone} | {r['commit'] or '?'} |")

    kept = [f"A{k}" for k, _ in folders]        # no numbered folder is taken out again: its path may have been given out
    text = [
        PAGE_OPEN,
        f"**最新，传 Realms 用这个：`A{n}/{name}.zip`**（总装 {row['assembly']}，{row['at']} 导出，{mb(row['zip_bytes'])}，"
        f"sha256 `{row['sha256']}`）。不带注册表文件，钟锁在 {row['time']} 刻；"
        + (f"我们的天由资源包里的 {row['shaders']} 个着色器文件带着（sky/safe-look）。" if row.get("shaders")
           else "**资源包里没有着色器，天是原版的夜空。**"),
        *([f"**资源包在你的机器上加载失败（楼成了原版的方块）就换这个：`A{n}/{plain['file']}`**（{mb(plain['bytes'])}，"
           f"sha256 `{plain['sha256']}`）：同一个总装头，资源包里不带着色器，天是原版的夜空，别的都一样。"
           + ("冷启动验证全过。" if plain.get("verified") else "**冷启动验证没过。**" if plain.get("verified") is False else "没验。")]
          if plain and row.get("shaders") else []),
        *([f"同一个总装头、带着我们的天的：`A{n}/{look['file']}`（{mb(look['bytes'])}，sha256 `{look['sha256']}`，钟锁在 {look['time']} 刻）。"
           f"**它带 {look['registry_files']} 个注册表文件（群系、时间线），只给单人打开看样子，不传 Realms。**"] if look else []),
        "总装每半小时跟着 s2 报的绿头重导一次，编号往上加。**编号的文件夹只加不删**：表里编号带链接的都还在这里，"
        f"路径是 `{kept[-1]}/c164-{kept[-1]}.zip` 这个样子，给出去的路径一直有效（现在有 {'、'.join(kept)}）。"
        "更早的几个不在这里了，在分支历史里，表的最后一列是它所在的提交。",
        "",
        "| 编号 | 总装头 | 导出时间 | 存档 zip | 其中资源包 | 方块 / 显示实体 / 会动的件 | 钟 | 冷启动验证 | 说明 | 在提交 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        *[line(r) for r in rows],
        "",
        f"最新这一个：建世界到封包 {row['make_s']} 秒" + (f"，验证 {row['verify_s']} 秒" if row["verify_s"] is not None else "，没验")
        + f"；服务端日志里的警告和报错一共 {row['console']} 条（做的那次，加上验的两次冷启动：一次按最不利的服务端设置生存、简单，"
        "一次按 Realms 槽位会填的冒险、和平）。"
        + f"数据包里函数 {row['functions']} 个、标签 {row['tags']} 个，注册表文件 {row['registry_files']} 个；"
        + (f"资源包里还有 {row['standins']} 张占位贴图（`ph_` 开头，等正式的换下来）。" if row["standins"] else "资源包里没有占位贴图。")
        + ("" if row["cloud"] else "**这一个没开「站到云海方块上送回」。**")
        + ("存盘前等光照算完了（存一次读一次，连着三次不变才收，等了 {} 秒）。".format(row["light"]) if row.get("light")
           else "**存盘时光照还在变，这一个的光不全。**" if row.get("light") is False
           else "这一个存盘前没等光照算完（A6 和更早的都没等）。"),
        PAGE_CLOSE,
    ]
    readme = os.path.join(dist, "README.md")
    with open(readme, encoding="utf-8") as fh:
        old = fh.read()
    if PAGE_OPEN not in old or PAGE_CLOSE not in old:
        fail(f"{readme} has no place for the table (the two marker lines)")
    new = old[:old.index(PAGE_OPEN)] + "\n".join(text) + old[old.index(PAGE_CLOSE) + len(PAGE_CLOSE):]
    with open(readme, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(new)
    say(f"page: {row['n']} of assembly {row['assembly']} written into {os.path.relpath(readme, PROJECT)} and history.json")
    print("REPORT " + json.dumps(row, ensure_ascii=False))


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
        p.add_argument("--time", type=int, help="the tick the clock is held at (default: the scene's TIME; with the look "
                                                "off the scene's TIME_PLAIN, or the tick at which the game's own moon "
                                                "stands where the look keeps the comet)")
        p.add_argument("--catch", type=int, default=CATCH, help="scene y: feet under it are put back on the spot")
        p.add_argument("--on-cloud", choices=("back", "ignore"),
                       help="back: who stands on a block of the cloud sea is put back on the spot too "
                            "(default: back, for a trial save ignore)")
        p.add_argument("--shaders", choices=("auto", "on", "off"), default="auto",
                       help="the look as core shaders in the resource pack (auto: when the save goes without "
                            "the look and the tree has sky/_shaders.py; never with --look on)")
        p.add_argument("--no-guide", action="store_true",
                       help="leave the guide out (titles, plaques, star charts: the scene's GUIDE is set to False "
                            "for the building, and nothing hangs on a visitor's arrival)")
        p.add_argument("--trial", help="label of a trial save (see the text at the top)")
        p.add_argument("--assembly", help="the assembly's commit this is made of, for the note beside the save")
        p.add_argument("--out", help="folder of the archive (make: default dist/<name>)", required=(what == "pack"))
    p = sub.add_parser("verify")
    p.add_argument("archive")
    p.add_argument("--strip", action="store_true",
                   help="start it a second time with the registry files taken out of the data pack, as an upload might")
    p = sub.add_parser("compare")
    p.add_argument("a")
    p.add_argument("b")
    p.add_argument("--deep", action="store_true",
                   help="open the region files and compare what the chunks hold, without the hour they were "
                        "written and the entities' ids (on a node: it reads every chunk)")
    p = sub.add_parser("page")
    p.add_argument("dist", help="the folder of the saves (c164-realms/dist on the dist branch)")
    p.add_argument("--commit", help="the commit that holds the newest save's files")
    p.add_argument("--note", help="a line for the table: what is new in this one")
    args = ap.parse_args()
    {"make": make, "pack": pack, "verify": verify, "compare": compare, "page": page}[args.what](args)


if __name__ == "__main__":
    main()
