#!/usr/bin/env python3
"""One trip into a save on a worker node that tries what the save says to a visitor and asks of
one (plan/packages/motion/guide.md): the title on first joining, the plaques, the star charts,
the close before the eyepiece, what is left of it after leaving and joining again, and a second
visitor beside the first. savetrip.py shoots the board's views of a save; this walks it.

    bash c164-realms/tools/nodejob.sh --always --tail 60 --limit 1080 python tools/guidetrip.py \\
        --branch cursor/c164-dist-f4b8 --at <commit> --zip dist/A8/c164-A8.zip [--sha256 <hex>] \\
        [--parts joined,walk,rejoin,second,plaques] [--budget 900]               (timeout_sec=1200)

What the save holds is read out of its files first (saveguide.py): the text displays, the words
its functions show, and the places its functions watch (a tag given to who comes near). Then

  joined   the game joins as a new player, and from the server's line that it joined on the game
           is asked for its own picture again and again (--frames of them, --gap seconds apart):
           the title is in these or it was not shown. joined_NN.jpg, with how much of the middle of
           each differs from the last one
  walk     the visitor is put on its feet, in the game mode the save gave it, inside the reach of
           each watched place in turn -- the step before any chart, three charts, the step, the
           other charts, the first chart again, the step with all of them, the step once more --
           a picture at each (what the game writes over the view is in it) and the player's tags
           asked of the server after each
  rejoin   the game is closed and started again: the pictures from the joining on once more (no
           title a second time), and the tags, which must be the ones it left with
  second   a second client beside the first (nodemc.py, MC_SEAT): a new player of its own, walked
           to one chart; its tags and the first one's, a picture by each of the two
  plaques  every text display from where it is read (a spectator's view, two each: straight on
           from a visitor's distance, and from the side with what stands around it)

and guide.txt in renders/real-save/<name>-guide/ says what was found, stop by stop, and what
did not come out as the card has it. The pictures are judged by whoever reads them: this trip
cannot read a title off a picture, it says where to look.

Exit code 0: every part asked for ran and its pictures are kept; 1 otherwise. What the card asks
and the save does not do is in guide.txt, not in the exit code.
"""
import argparse
import json
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import traceback
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import nodetrip  # noqa: E402
import saveguide  # noqa: E402
import savetrip  # noqa: E402
from nodetrip import ROOT, WORK, CLOSING, Trip, end  # noqa: E402
from savetrip import SERVER, LEVEL, KEPT, HOUR, ask, number  # noqa: E402

PARTS = ("joined", "walk", "rejoin", "second", "plaques")
SEAT, SECOND = "b", "C164Two"           # the second client's seat and its player
EYE = saveguide.EYE
FRAME = (960, 540)                      # the pictures taken in a row are kept this size
HEAD = ("# a save walked as a visitor (tools/guidetrip.py): shot, the save's hour (daytime) when the trip began, "
        "commit that holds the zip, first 16 of the picture file's sha256, when it was taken, the distances")


def slug(text, most=22):
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:most] or "text"


def tags_of(answer):
    """The tags in the server's answer to `tag <player> list`."""
    if "has no tags" in answer or ":" not in answer:
        return []
    return [tag.strip() for tag in answer.split(":", 1)[1].split(",") if tag.strip()]


class Row(threading.Thread):
    """Pictures in a row from the moment a player joins: the game is asked for its own screenshot
    again and again from the server's line `<player> joined the game` on."""

    def __init__(self, trip, player, seat, out, prefix, frames, gap, patience=420.0):
        super().__init__(daemon=True)
        self.trip, self.player, self.out, self.prefix = trip, player, out, prefix
        self.frames, self.gap, self.patience = frames, gap, patience
        self.game = os.path.join(ROOT, "client26", "game" + ("-" + seat if seat else ""))
        self.console = os.path.join(SERVER, "console.log")
        self.offset = savetrip.console_size()
        self.taken = []                 # [(name, seconds after the joining)]
        self.note = "the player did not join"

    def joined(self):
        try:
            with open(self.console, "rb") as fh:
                fh.seek(self.offset)
                return f"{self.player} joined the game".encode() in fh.read()
        except OSError:
            return False

    def run(self):
        import shoot
        end_at = time.monotonic() + self.patience
        while not self.joined():
            if time.monotonic() > end_at:
                return
            time.sleep(0.1)
        t0 = time.monotonic()
        os.makedirs(self.out, exist_ok=True)
        take = shoot.game_camera(self.game, os.path.join(self.game, "c164cam"))
        self.note = "taken"
        for i in range(self.frames):
            due = t0 + i * self.gap
            if time.monotonic() < due:
                time.sleep(due - time.monotonic())
            name = f"{self.prefix}_{i:02d}"
            try:
                take(os.path.join(self.out, name + ".png"))
            except (SystemExit, Exception) as why:      # the game may not be ready for a picture yet
                self.note = f"a picture failed: {why}"
                time.sleep(0.3)
                continue
            self.taken.append((name, time.monotonic() - t0))


def middle_differs(folder, names):
    """For each picture, the share of its middle (the band a title is written in) that differs
    from the last picture's: a title, or a screen that covers the world, shows as a large share."""
    from PIL import Image, ImageChops
    if not names:
        return {}
    def band(name):
        with Image.open(os.path.join(folder, name + ".png")) as picture:
            picture = picture.convert("RGB")
            w, h = picture.size
            return picture.crop((w // 5, h // 5, w - w // 5, h * 3 // 5))
    last = band(names[-1])
    out = {}
    for name in names:
        red, green, blue = ImageChops.difference(band(name), last).split()
        most = ImageChops.lighter(ImageChops.lighter(red, green), blue)
        out[name] = sum(most.histogram()[41:]) / float(most.size[0] * most.size[1])
    return out


def glyphs(text):
    """Font pixels a line of the game's own font is wide, near enough: six a glyph, four a space, and one."""
    return sum(4 if ch == " " else 6 for ch in text) + 1


def plaques_of(found):
    """The text displays that hang together taken as one plaque (a6's are five: two plates of
    colour, which hold one space, and a display for each line): [{"words": the lines from the top
    down, "pos", "normal", "wide", "displays", "brightness", "see_through"}]."""
    groups = []
    for display in found["plaques"]:
        for group in groups:
            first = group[0]
            alike = (display["normal"] is None) == (first["normal"] is None) and (
                display["normal"] is None or sum(a * b for a, b in zip(display["normal"], first["normal"])) > 0.9)
            if alike and math.dist(display["pos"], first["pos"]) < 0.75:
                group.append(display)
                break
        else:
            groups.append([display])
    out = []
    for group in groups:
        def wide(display):
            return max(glyphs(line) for line in display["text"].split("\n")) * 0.025 * display["scale"][0]
        widest = max(group, key=wide)
        lines = sorted((d for d in group if d["text"].strip()), key=lambda d: -d["pos"][1])
        if not lines:
            continue
        out.append({"words": [d["text"] for d in lines], "pos": widest["pos"], "normal": widest["normal"],
                    "wide": round(wide(widest), 2), "displays": len(group),
                    "brightness": sorted({str(d["brightness"]) for d in group}),
                    "see_through": any(d["see_through"] for d in group)})
    return out


def plaque_shots(found, blocks):
    """A spectator's views of every plaque: straight on from a block and a half (what it says), from
    three blocks (is it read from where a visitor stands), and from the side with what is around it
    (does it hang on its wall, is anything in its way). Returns (shots, [(name, plaque)])."""
    shots, listed = [], []
    for i, plaque in enumerate(plaques_of(found)):
        name = f"p{i + 1:02d}_{slug(plaque['words'][0])}"
        centre, normal = plaque["pos"], plaque["normal"]
        listed.append((name, plaque))
        if not normal:
            shots.append({"name": name + "_near", "pos": [centre[0] + 2.5, centre[1], centre[2]], "look_at": centre,
                          "settle": 2.5, "still": 9.0})
            continue
        flat = math.hypot(normal[0], normal[2]) or 1.0
        ahead = (normal[0] / flat, normal[2] / flat)

        def eye(far, side, up):
            at = None
            for _ in range(8):          # nearer while the place is inside something
                at = [centre[0] + ahead[0] * far - ahead[1] * side, centre[1] + up, centre[2] + ahead[1] * far + ahead[0] * side]
                if blocks.open(*at) or far <= 1.0:
                    break
                far, side = far * 0.8, side * 0.8
            return [round(v, 2) for v in at]
        for kind, place in (("near", eye(max(1.5, 1.6 * plaque["wide"]), 0.0, 0.0)), ("at3", eye(3.0, 0.0, 0.0)),
                            ("from", eye(4.0, 2.4, 0.5))):
            shots.append({"name": f"{name}_{kind}", "pos": place, "look_at": centre, "settle": 2.5, "still": 9.0})
    return shots, listed


def walk_shots(found):
    """The walk through the watched places, and what each stop is for. Returns (shots, stops,
    charts, close): stops is [(shot, what is expected, tags the player must have after it)]."""
    places = found["watched"]
    charts = sorted((tag for tag in places if re.search(r"\.c\d+$", tag) and places[tag]["stand"]),
                    key=lambda tag: int(re.search(r"(\d+)$", tag).group(1)))
    close = next((tag for tag in places if tag.endswith(".done") and places[tag]["stand"]), None)
    shots, stops, have = [], [], []

    def stop(name, tag, expect, settle, add=None):
        place = places[tag]
        feet = place["stand"]
        if add:
            have.append(add)
        shots.append({"name": name, "walk": True, "pos": [feet[0], feet[1] + EYE, feet[2]], "look_at": place["at"],
                      "settle": settle, "still": 0, "ask": ["tag {player} list"]})
        stops.append((name, expect, list(have)))

    n = 0
    if close:
        stop(f"w{n:02d}_step_before", close, "before any chart: nothing is written, no tag is given", 2.0)
        n += 1
    for k, tag in enumerate(charts):
        stop(f"w{n:02d}_chart{k + 1}", tag, f"the action bar says chart {k + 1} of {len(charts)}; the tag {tag} is given",
             1.2, add=tag)
        n += 1
        if close and k + 1 == len(charts) // 2:
            stop(f"w{n:02d}_step_some", close, f"with {k + 1} of {len(charts)}: the action bar counts them, no close", 1.5)
            n += 1
    if charts:
        stop(f"w{n:02d}_chart1_again", charts[0], "a chart taken before: nothing is written, nothing is counted twice", 1.5)
        n += 1
    if close:
        stop(f"w{n:02d}_step_all", close, "with every chart: the closing title, a bell, the tag " + close, 1.6,
             add=close if charts else None)
        n += 1
        shots.append({"name": f"w{n:02d}_step_after", "stay": True, "settle": 3.0, "still": 0})
        stops.append((shots[-1]["name"], "three seconds later, the same place: the title going, the motes rising", list(have)))
        n += 1
        if charts:
            away = places[charts[-1]]
            shots.append({"name": f"w{n:02d}_away", "walk": True, "pos": [away["stand"][0], away["stand"][1] + EYE, away["stand"][2]],
                          "look_at": away["at"], "settle": 8.0, "still": 0})
            stops.append((shots[-1]["name"], "away from the step, until the title is gone", list(have)))
            n += 1
        stop(f"w{n:02d}_step_again", close, "the step once more: nothing is written", 2.0)
    return shots, stops, charts, close


def vantage(blocks, feet, far=3.0):
    """An eye from which somebody standing at `feet` is seen: the first of eight sides whose place
    and the way to the player are open."""
    target = (feet[0], feet[1] + 1.0, feet[2])
    for turn in range(8):
        angle = math.radians(45 * turn + 22)
        eye = (feet[0] + far * math.cos(angle), feet[1] + 1.9, feet[2] + far * math.sin(angle))
        way = [tuple(eye[k] + (target[k] - eye[k]) * step / 6 for k in range(3)) for step in range(6)]
        if all(blocks.open(*point) for point in way):
            return [round(v, 2) for v in eye], list(target)
    return [round(feet[0] + far, 2), feet[1] + 1.9, feet[2]], list(target)


def asked(text):
    """{shot: [answers]} from shoot.py's lines `asked at <shot>: <command> -> <answer>`."""
    out = {}
    for line in text.splitlines():
        m = re.match(r"\s*asked at (\S+): (.+?) -> (.*)$", line)
        if m:
            out.setdefault(m.group(1), []).append((m.group(2), m.group(3)))
    return out


def main():
    ap = argparse.ArgumentParser(description="one trip into a save on a worker node that walks its guide")
    ap.add_argument("--branch", required=True)
    ap.add_argument("--at", metavar="COMMIT")
    ap.add_argument("--zip", required=True, metavar="PATH")
    ap.add_argument("--sha256")
    ap.add_argument("--name")
    ap.add_argument("--parts", default=",".join(PARTS))
    ap.add_argument("--frames", type=int, default=22)
    ap.add_argument("--gap", type=float, default=0.75)
    ap.add_argument("--view", type=int, default=nodetrip.BOARD_VIEW)
    ap.add_argument("--server-view", type=int, default=nodetrip.REALM_VIEW)
    ap.add_argument("--clouds", type=int, default=128)
    ap.add_argument("--budget", type=float, default=900.0)
    args = ap.parse_args()
    import boardrender
    import realshots
    parts = [p for p in args.parts.split(",") if p]
    if any(p not in PARTS for p in parts):
        sys.exit(f"--parts: of {', '.join(PARTS)}")
    name = (args.name or os.path.splitext(os.path.basename(args.zip))[0]) + "-guide"
    if not realshots.NAME_OK.match(name):
        sys.exit(f"--name {name}: a name of letters, digits, - and _")

    commit = savetrip.clean_commit(args.branch, args.at)
    work = os.path.join(WORK, "save", name)
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    zip_path = os.path.join(work, os.path.basename(args.zip))
    with open(zip_path, "wb") as fh:
        got = subprocess.run(["git", "-C", PROJECT, "show", f"{commit}:c164-realms/{args.zip}"], stdout=fh,
                             stderr=subprocess.PIPE)
    if got.returncode != 0:
        sys.exit(f"{commit[:8]} of {args.branch} has no c164-realms/{args.zip}: "
                 + got.stderr.decode("utf-8", "replace").strip()[-200:])
    sha = savetrip.digest(zip_path, whole=True)
    if args.sha256 and sha != args.sha256.lower():
        sys.exit(f"{args.zip} of {commit[:8]} is not the file asked for: its sha256 is {sha}, not {args.sha256}")

    stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    log_path = os.path.join(PROJECT, "renders", "real", "_trips", f"{stamp}-{commit[:7]}-save-{name}.log")
    trip = Trip(log_path, args.budget)
    started = time.time()

    def cut_short(*_):
        if trip.running is not None:
            end(trip.running, patience=4.0)
        sys.exit(143)
    signal.signal(signal.SIGTERM, cut_short)
    station = os.path.join(HERE, "nodemc.py")
    shooter = os.path.join(HERE, "shoot.py")
    distances = {"MC_VIEW": str(args.view), "MC_SERVER_VIEW": str(args.server_view), "MC_CLOUDS": str(args.clouds)}
    view = f"view{args.view},server{args.server_view},clouds{args.clouds}"
    trip.say(f"the guide of the save {args.zip} of {commit[:8]} ({args.branch}): sha256 {sha}"
             + (", as asked" if args.sha256 else "") + f"; parts {', '.join(parts)}; {os.cpu_count()} cores, "
             f"{args.budget:.0f} s at most")
    failed, report, console = [], [], savetrip.console_size()
    facts = [f"# the save: {args.zip} of {commit[:8]} ({args.branch}), {os.path.getsize(zip_path)} bytes, sha256 {sha}"]
    out = os.path.join(work, "shots")
    os.makedirs(out)
    groups = {}                         # part -> the names of its pictures, in order
    cam = savetrip.nodetrip_cam()
    tick = None

    def tell(line):
        report.append(line)
        trip.say("guide: " + line)

    try:
        found = saveguide.read(zip_path)
        archive = zipfile.ZipFile(zip_path)
        blocks = saveguide.Blocks(archive)
        tell(f"in the save's files: {len(found['plaques'])} text displays, {len(found['shown'])} commands that show "
             f"words, {len(found['watched'])} watched places, {found['functions']} functions")
        for plaque in plaques_of(found):
            tell(f"  plaque at {plaque['pos']}, read from {plaque['normal']}: {' / '.join(plaque['words'])} "
                 f"({plaque['displays']} displays, {plaque['wide']} wide)")
        for function, kind, words in found["shown"]:
            tell(f"  {function}: {kind} {words}")
        for tag, place in found["watched"].items():
            tell(f"  {tag}: within {place['reach']} of {place['at']} ({place['function']}); a visitor's feet at "
                 f"{place['stand']} on {place['on']}, {place['far']} away")
        walk, stops, charts, close = walk_shots(found)
        plaques, listed = plaque_shots(found, blocks)
        if "walk" in parts and not walk:
            tell("no watched place gives a tag: there is nothing to walk (the walk is left out)")
        if "plaques" in parts and not plaques:
            tell("no text display: there is no plaque to read (the plaques are left out)")

        trip.stage("clean", station, "down", budget=180)
        console = savetrip.console_size()
        world = os.path.join(SERVER, LEVEL)
        os.makedirs(SERVER, exist_ok=True)
        top, count = savetrip.unpack(zip_path, world)
        level = savetrip.level_facts(world)
        trip.say(f"the save: the world folder {top} ({count} entries) is unpacked as server26/{LEVEL}/; level.dat: "
                 + ", ".join(f"{key} {value}" for key, value in level.items()))
        mode, hard = level["mode"] or "adventure", level["difficulty"] or "peaceful"
        as_slot = {**distances, "MC_LEVEL": LEVEL, "MC_GAMEMODE": mode, "MC_FORCE_GAMEMODE": "false", "MC_DIFFICULTY": hard}
        facts.append(f"# the server: the node's test server on this save, game mode {mode} (not forced), difficulty {hard}, "
                     f"as a Realm's slot is filled from the world; the camera is no operator")
        code, _ = trip.stage("setup", station, "setup", budget=min(1500, trip.left() - 300), env=as_slot)
        if code != 0:
            raise SystemExit("the node could not be made ready")
        said, _ = savetrip.give_pack(world)
        trip.say("resource pack: " + said)
        code, _ = trip.stage("server", station, "server-up", budget=min(400, trip.left() - CLOSING), env=as_slot)
        if code != 0:
            raise SystemExit("the server did not come up on the save")
        tick = number(ask(trip, HOUR)[0])

        def join(prefix, what):
            """The game started, with the pictures in a row from its joining on."""
            row = Row(trip, cam, "", out, prefix, args.frames, args.gap)
            row.start()
            code, _ = trip.stage("game", station, "client-up", budget=trip.left() - CLOSING, env=as_slot)
            if code != 0:
                raise SystemExit("the game did not come up or did not join")
            row.join(timeout=args.frames * (args.gap + 3.0) + 30)
            names = [n for n, _ in row.taken]
            groups[prefix] = names
            differs = middle_differs(out, names)
            tell(f"{what}: {len(names)} pictures in a row from the joining on ({row.note}), {prefix}_NN; seconds after "
                 f"the joining and the share of the middle that differs from the last one: "
                 + ", ".join(f"{n[-2:]} {t:.1f}s {differs[n]:.0%}" for n, t in row.taken))
            if len(names) < args.frames // 2:
                failed.append(f"{prefix}: {len(names)} of {args.frames} pictures in a row")
            return ask(trip, f"tag {cam} list", f"data get entity {cam} Pos", f"data get entity {cam} playerGameType")

        def shoot(what, shots, *more, env=None):
            shots_file = os.path.join(work, f"{what}.json")
            with open(shots_file, "w", encoding="utf-8") as fh:
                json.dump(shots, fh)
            code, text = trip.stage(what, shooter, shots_file, "--pw-file", os.path.join(SERVER, ".rcon_pw"),
                                    "--out", out, "--keep-clock", "--settle", 3.0, "--first-settle", 3.0, *more,
                                    budget=trip.left() - CLOSING, env=env or as_slot)
            taken = [s["name"] for s in shots if os.path.exists(os.path.join(out, s["name"] + ".png"))]
            if code != 0 or len(taken) != len(shots):
                failed.append(f"{what}: {len(taken)} of {len(shots)} pictures")
            return taken, asked(text)

        first = join("joined", "first joining")
        had = tags_of(first[0])
        tell(f"after the first joining the player has the tags {', '.join(had) or 'none'}; {first[1]}; {first[2]}")
        if "joined" not in parts:
            groups.pop("joined", None)

        if "walk" in parts and walk:
            taken, answers = shoot("walk", walk, "--walk-as", mode)
            groups["walk"] = taken
            for shot, expect, must in stops:
                got = answers.get(shot)
                if got is None:
                    tell(f"{shot}: {expect}" + ("" if shot in taken else " -- NO PICTURE"))
                    continue
                had = tags_of(got[0][1])
                lacking = [t for t in must if t not in had]
                extra = [t for t in had if t in found["watched"] and t not in must]
                verdict = "as the card has it" if not lacking and not extra else \
                    "NOT SO: " + "; ".join(x for x in (f"lacks {', '.join(lacking)}" if lacking else "",
                                                       f"has {', '.join(extra)} already" if extra else "") if x)
                tell(f"{shot}: {expect}. Tags after it: {', '.join(had) or 'none'} -- {verdict}")
        left_with = tags_of(ask(trip, f"tag {cam} list")[0])

        if "rejoin" in parts:
            trip.stage("leave", station, "client-down", budget=120, env=as_slot)
            again = join("rejoin", "joining again")
            back = tags_of(again[0])
            tell(f"after leaving and joining again the player has the tags {', '.join(back) or 'none'} -- "
                 + ("the ones it left with" if sorted(back) == sorted(left_with)
                    else f"NOT the ones it left with ({', '.join(left_with) or 'none'})") + f"; {again[2]}")

        if "second" in parts:
            seat = {**as_slot, "MC_SEAT": SEAT, "MC_CAM": SECOND, "MC_VIEW": "5", "MC_CLIENT_HEAP": "2G"}
            before = tags_of(ask(trip, f"tag {cam} list")[0])
            code, _ = trip.stage("second visitor", station, "client-up", budget=min(420, trip.left() - CLOSING), env=seat)
            if code != 0:
                failed.append("the second client did not come up or did not join")
            else:
                both = ask(trip, "list", f"tag {SECOND} list", f"tag {cam} list")
                tell(f"two visitors: {both[0]}; the second one has the tags {', '.join(tags_of(both[1])) or 'none'} "
                     f"on joining, the first still {', '.join(tags_of(both[2])) or 'none'}")
                names = []
                if charts:
                    place = found["watched"][charts[min(1, len(charts) - 1)]]
                    feet = place["stand"]
                    taken, answers = shoot("second-own", [{
                        "name": "two_own_chart", "walk": True, "pos": [feet[0], feet[1] + EYE, feet[2]],
                        "look_at": place["at"], "settle": 1.2, "still": 0,
                        "ask": ["tag {player} list", f"tag {cam} list"]}],
                        "--seat", SEAT, "--player", SECOND, "--walk-as", mode, env=seat)
                    names += taken
                    got = answers.get("two_own_chart", [])
                    eye, target = vantage(blocks, feet)
                    seen, _ = shoot("second-seen", [{"name": "two_seen_by_first", "pos": eye, "look_at": target,
                                                     "settle": 3.0, "still": 0}])
                    names += seen
                    after = tags_of(ask(trip, f"tag {cam} list")[0])
                    tell(f"the second visitor at one chart: its tags {', '.join(tags_of(got[0][1])) if got else '?'}; the "
                         f"first one's tags {', '.join(after) or 'none'} -- "
                         + ("unchanged by the second" if sorted(after) == sorted(before) else
                            f"CHANGED (they were {', '.join(before) or 'none'})"))
                else:
                    seen, _ = shoot("second-seen", [{"name": "two_seen_by_first", "stay": True, "settle": 3.0}])
                    names += seen
                groups["second"] = names
                trip.stage("second visitor leaves", station, "client-down", budget=120, env=seat)

        if "plaques" in parts and plaques:
            taken, _ = shoot("plaques", plaques)
            groups["plaques"] = taken
            for shot, plaque in listed:
                tell(f"{shot}: {' / '.join(plaque['words'])}; {plaque['wide']} blocks wide, {plaque['displays']} displays, "
                     f"shown at brightness {', '.join(plaque['brightness'])}"
                     + (", SEEN THROUGH WALLS" if plaque["see_through"] else "")
                     + ("" if shot + "_near" in taken else " -- NO PICTURE"))
    except SystemExit as stop:
        if stop.code not in (0, None):
            trip.say(f"stopped: {stop}")
            failed.append(str(stop)[:200])
    except Exception as exc:            # the node is closed down and what there is is kept all the same
        trip.say("stopped by an error of this script:\n" + traceback.format_exc())
        failed.append(f"{type(exc).__name__}: {exc}"[:200])
    finally:
        said_path = log_path[:-len(".log")] + "-client.txt"
        try:
            trip.stage("what the game said", station, "client-said", f"{started:.0f}", said_path, budget=30)
        except Exception as exc:
            trip.say(f"what the game said could not be read ({exc})")
        try:
            warnings, errors = savetrip.server_said(console, log_path[:-len(".log")] + "-server.txt", trip.secret())
            trip.say(f"the server on the save: {warnings} warnings, {errors} errors in its log")
        except Exception as exc:
            trip.say(f"what the server said could not be read ({exc})")
        trip.stage("close", station, "down", budget=180)
        trip.stage("back to the test world", station, "setup", budget=120, env=distances)
        kept_in = os.path.join(KEPT, name)
        try:
            keep(trip, kept_in, out, groups, facts, report, commit, tick, view, name, sha, failed)
        except Exception as exc:
            trip.say(f"the pictures could not be kept ({type(exc).__name__}: {exc})")
            failed.append("the pictures could not be kept")
        trip.say(("trip done" if not failed else "trip done with failures: " + "; ".join(failed))
                 + f"; kept: {kept_in}/; log {os.path.relpath(log_path, PROJECT)}")
        trip.log.close()
    return 1 if failed else 0


def keep(trip, kept_in, out, groups, facts, report, commit, tick, view, name, sha, failed):
    """The pictures as JPEGs in renders/real-save/<name>/, a sheet for each part, real.txt, guide.txt."""
    from PIL import Image
    import boardrender
    import realshots
    folder = os.path.join(PROJECT, kept_in)
    shutil.rmtree(folder, ignore_errors=True)
    os.makedirs(folder)
    when = time.strftime("%Y-%m-%dT%H:%M", time.gmtime())
    rows = []
    for part, names in groups.items():
        for shot in names:
            path = os.path.join(folder, shot + ".jpg")
            with Image.open(os.path.join(out, shot + ".png")) as picture:
                picture = picture.convert("RGB")
                if part in ("joined", "rejoin"):
                    picture = picture.resize(FRAME, Image.LANCZOS)
                picture.save(path, "JPEG", quality=88)
            rows.append(f"{shot} {'?' if tick is None else tick} {commit[:8]} {savetrip.digest(path)} {when} {view}")
        if names:
            boardrender.sheet(folder, names, f"c164 the save {name[:-len('-guide')]} (sha256 {sha[:12]}) walked as a visitor: "
                              f"{part}", ext=".jpg", out=f"{part}.jpg")
    with open(os.path.join(folder, realshots.NOTE), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(HEAD + "\n" + "".join(line + "\n" for line in facts) + "".join(row + "\n" for row in rows))
    with open(os.path.join(folder, "guide.txt"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(f"the guide of the save {name[:-len('-guide')]} (sha256 {sha}), walked on a node {when} UTC\n"
                 + "".join(line + "\n" for line in report)
                 + ("".join(f"FAILED: {line}\n" for line in failed)))
    trip.say(f"{len(rows)} pictures kept in {kept_in}/ with guide.txt and a sheet for each of "
             f"{', '.join(part for part, names in groups.items() if names) or 'no part'}")


if __name__ == "__main__":
    sys.exit(main())
