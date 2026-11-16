#!/usr/bin/env python3
"""One trip into a save on a worker node that tries whether somebody who rides a display entity
is carried smoothly (the director's #85316, a2's #85748: the train of the opening).

    bash c164-realms/tools/nodejob.sh --always --tail 60 --limit 900 python tools/ridetrip.py \\
        --branch cursor/c164-dist-f4b8 --at <commit> --zip dist/A8/c164-A8.zip [--sha256 <hex>] \\
        [--rides a,b,c,d] [--from X Y Z] [--step DX DY DZ] [--ticks 160] [--budget 700]

The save is opened as savetrip.py opens it, with one thing added to the copy on the node: a data
pack of three functions (c164ride), the stand-in for the kit that is still to be written. Two
clients join: one rides, one watches from beside the line. A ride: an item display (a plank) is
summoned at --from, the first player is put on it with `ride`, and the plank is carried --step a
tick for --ticks ticks, in one of four ways (a2's four):

  a   teleport_duration 1, a `tp` every tick
  b   teleport_duration 0, a `tp` every tick
  c   teleport_duration 20, a `tp` every 20 ticks that moves it the way of 20 ticks
  d   teleport_duration 59, a `tp` every 59 ticks

What is measured, not judged by eye: the riding client writes down where its camera stands at
every frame it draws (the picture helper's `track`), so a ride that halts, jumps or goes back shows
as numbers -- how far the camera is from an even run along the line, frame by frame, and at the
seams of c and d. The watching client writes down where it has the rider and the plank at every
tick of its own. The server is asked after each ride whether the player still sits on the plank.
Pictures in a row by both clients go with it. All of it is in ride.txt in
renders/real-save/<name>-ride/.

Exit code 0: every ride asked for ran and was measured; 1 otherwise.
"""
import argparse
import math
import os
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
import savetrip  # noqa: E402
from guidetrip import Row, SEAT, SECOND, FRAME  # noqa: E402
from nodetrip import ROOT, WORK, CLOSING, Trip, end  # noqa: E402
from savetrip import SERVER, LEVEL, KEPT, ask  # noqa: E402

RIDES = {"a": (1, 1), "b": (0, 1), "c": (20, 20), "d": (59, 59)}     # teleport_duration, a tp every so many ticks
CAR = "@e[type=minecraft:item_display,tag=c164.ride,limit=1]"
HEAD = ("# rides on a display entity tried in a save (tools/ridetrip.py): shot, the ride, commit that holds the "
        "zip, first 16 of the picture file's sha256, when it was taken, the distances")


def stand_in(world, step):
    """The data pack that carries the plank: c164ride. Scores of the objective c164ride: #go is the
    number of ticks between two moves (0: nothing moves), #t the tick of the ride, #end its last."""
    pack = os.path.join(world, "datapacks", "c164ride")
    shutil.rmtree(pack, ignore_errors=True)
    os.makedirs(os.path.join(pack, "data", "c164ride", "function"))
    os.makedirs(os.path.join(pack, "data", "minecraft", "tags", "function"))
    own = os.path.join(world, "datapacks", "c164art", "pack.mcmeta")       # the format this game takes
    shutil.copyfile(own, os.path.join(pack, "pack.mcmeta"))
    car = "@e[type=minecraft:item_display,tag=c164.ride]"
    lines = ["scoreboard players add #t c164ride 1",
             "execute if score #t c164ride >= #end c164ride run return run scoreboard players set #go c164ride 0",
             "scoreboard players operation #m c164ride = #t c164ride",
             "scoreboard players operation #m c164ride %= #go c164ride"]
    for every in sorted({every for _, every in RIDES.values()}):
        move = " ".join(f"~{v * every:.4f}" for v in step)
        lines.append(f"execute if score #m c164ride matches 0 if score #go c164ride matches {every} as {car} at @s "
                     f"run tp @s {move}")
    with open(os.path.join(pack, "data", "c164ride", "function", "step.mcfunction"), "w", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    with open(os.path.join(pack, "data", "c164ride", "function", "tick.mcfunction"), "w", newline="\n") as fh:
        fh.write("execute if score #go c164ride matches 1.. run function c164ride:step\n")
    with open(os.path.join(pack, "data", "minecraft", "tags", "function", "tick.json"), "w", newline="\n") as fh:
        fh.write('{"values": ["c164ride:tick"]}\n')
    return lines


def track(seat, name, seconds, other=None):
    """Asks a client's picture helper to write down what moves for so many seconds. Returns a
    function that waits for the file and gives its text (None when the client did not answer)."""
    game = os.path.join(ROOT, "client26", "game" + ("-" + seat if seat else ""))
    asks = os.path.join(game, "c164cam")
    key = f"{os.getpid()}-t{name}"
    with open(os.path.join(asks, key + ".tmp"), "w", encoding="utf-8") as fh:
        fh.write(f"track {name}.txt {seconds:.1f}" + (f" {other}" if other else ""))
    os.replace(os.path.join(asks, key + ".tmp"), os.path.join(asks, key + ".req"))

    def result(patience):
        end_at = time.monotonic() + patience
        while time.monotonic() < end_at:
            if os.path.exists(os.path.join(asks, key + ".done")):
                with open(os.path.join(asks, name + ".txt"), encoding="utf-8") as fh:
                    return fh.read()
            if os.path.exists(os.path.join(asks, key + ".fail")):
                with open(os.path.join(asks, key + ".fail"), encoding="utf-8") as fh:
                    return "# FAILED: " + fh.read().strip() + "\n"
            time.sleep(0.1)
        return None
    return result


def rows(text, kind):
    out = []
    for line in (text or "").splitlines():
        parts = line.split()
        if parts and parts[0] == kind:
            try:
                out.append([float(v) for v in parts[1:]])
            except ValueError:
                continue
    return out


def quantile(values, q):
    values = sorted(values)
    return values[min(len(values) - 1, max(0, int(round(q * (len(values) - 1)))))] if values else float("nan")


def judge_camera(text, step, ticks, every):
    """What the riding client's camera did, from its `C t x y z` lines: a list of sentences."""
    cam = rows(text, "C")
    if len(cam) < 10:
        return [f"the camera's track has {len(cam)} lines: nothing to measure"], None
    far = math.sqrt(sum(v * v for v in step))
    unit = [v / far for v in step]
    whole = far * ticks
    first = cam[0][1:4]
    along = [sum((row[1 + k] - first[k]) * unit[k] for k in range(3)) for row in cam]
    aside = [math.sqrt(max(0.0, sum((row[1 + k] - first[k]) ** 2 for k in range(3)) - s * s)) for row, s in zip(cam, along)]
    times = [row[0] / 1000.0 for row in cam]
    moving = [i for i, s in enumerate(along) if 0.05 < s < max(along) - 0.05]
    if len(moving) < 8:
        return [f"the camera moved {max(along):.2f} blocks along the line in all (the plank was to go {whole:.1f}): "
                f"no ride to measure"], None
    a, b = moving[0], moving[-1]
    span = times[b] - times[a]
    n = b - a
    # an even run through the first and the last frame of the ride; how far every frame is from it
    speed = (along[b] - along[a]) / span
    off = [along[i] - (along[a] + speed * (times[i] - times[a])) for i in range(a, b + 1)]
    steps = [(along[i + 1] - along[i], times[i + 1] - times[i]) for i in range(a, b)]
    back = [ds for ds, _ in steps if ds < -0.003]
    still = max(dt for _, dt in steps)
    per_frame = [ds / dt for ds, dt in steps if dt > 0]
    out = [f"the camera went {max(along):.2f} blocks along the line (the plank was to go {whole:.1f}) and at most "
           f"{max(aside):.3f} aside of it; {n} frames in {span:.2f} s of riding ({n / span:.0f} a second), "
           f"{speed:.2f} blocks a second on average (asked for: {far * 20:.2f})",
           f"against an even run from the first frame of the ride to the last: every frame within "
           f"{max(abs(v) for v in off):.3f} blocks of it ({math.sqrt(sum(v * v for v in off) / len(off)):.3f} rms; "
           f"one tick's way is {far:.3f}); frame by frame the speed is {quantile(per_frame, 0.05):.2f} to "
           f"{quantile(per_frame, 0.95):.2f} blocks a second for nine frames in ten, {min(per_frame):.2f} at the least, "
           f"{max(per_frame):.2f} at the most; the longest the camera stood still: {still * 1000:.0f} ms; "
           f"{len(back)} frames went back" + (f" (by up to {-min(back):.3f} blocks)" if back else "")]
    if every > 1:
        # the seams: where one move ends and the next begins, by the camera's own clock
        leg = every / 20.0
        worst = []
        for k in range(1, ticks // every):
            seam = times[a] + k * leg * (span / (ticks / 20.0)) if span else 0
            near = [abs(off[i - a]) for i in range(a, b + 1) if abs(times[i] - seam) < 0.2]
            gap = [dt for (ds, dt), i in zip(steps, range(a, b)) if abs(times[i] - seam) < 0.2]
            if near:
                worst.append((max(near), max(gap) if gap else 0.0))
        if worst:
            out.append(f"at the {len(worst)} seams (a fifth of a second either side of each): at most "
                       f"{max(w[0] for w in worst):.3f} blocks off the even run, the longest stand "
                       f"{max(w[1] for w in worst) * 1000:.0f} ms")
    return out, (max(abs(v) for v in off), still, len(back), speed)


def judge_pair(text, label):
    """Whether a player and what it rides go together, from `P`/`O t x y z vx vy vz` lines."""
    seen = rows(text, label)
    riding = [row for row in seen if len(row) >= 7 and not math.isnan(row[4])]
    if len(riding) < 5:
        return (f"{len(seen)} positions written down, {len(riding)} of them with something ridden: "
                f"the client does not have the player on the plank")
    gaps = [[row[1 + k] - row[4 + k] for k in range(3)] for row in riding]
    middle = [quantile([g[k] for g in gaps], 0.5) for k in range(3)]
    apart = max(math.dist(g, middle) for g in gaps)
    moved = math.dist(riding[0][4:7], riding[-1][4:7])
    ticks = [riding[i + 1][0] - riding[i][0] for i in range(len(riding) - 1)]
    return (f"{len(riding)} positions with the player on the plank (of {len(seen)}), the plank {moved:.1f} blocks from "
            f"its first to its last; the player stays {middle[1]:+.2f} over the plank and never more than {apart:.3f} "
            f"blocks from that place; a new position every {quantile(ticks, 0.5):.0f} ms (the longest wait "
            f"{max(ticks):.0f} ms)")


def main():
    ap = argparse.ArgumentParser(description="one trip into a save on a worker node that tries rides on a display entity")
    ap.add_argument("--branch", required=True)
    ap.add_argument("--at", metavar="COMMIT")
    ap.add_argument("--zip", required=True, metavar="PATH")
    ap.add_argument("--sha256")
    ap.add_argument("--name")
    ap.add_argument("--rides", default="a,b,c,d")
    ap.add_argument("--from", dest="start", type=float, nargs=3, default=[130.0, 190.0, -45.0], metavar=("X", "Y", "Z"))
    ap.add_argument("--step", type=float, nargs=3, default=[-0.18, 0.09, 0.0], metavar=("DX", "DY", "DZ"))
    ap.add_argument("--ticks", type=int, default=160)
    ap.add_argument("--view", type=int, default=nodetrip.BOARD_VIEW)
    ap.add_argument("--server-view", type=int, default=nodetrip.REALM_VIEW)
    ap.add_argument("--clouds", type=int, default=128)
    ap.add_argument("--budget", type=float, default=700.0)
    args = ap.parse_args()
    import realshots
    rides = [r for r in args.rides.split(",") if r]
    if any(r not in RIDES for r in rides):
        sys.exit(f"--rides: of {', '.join(RIDES)}")
    name = (args.name or os.path.splitext(os.path.basename(args.zip))[0]) + "-ride"
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
    distances = {"MC_VIEW": str(args.view), "MC_SERVER_VIEW": str(args.server_view), "MC_CLOUDS": str(args.clouds)}
    view = f"view{args.view},server{args.server_view},clouds{args.clouds}"
    far = math.sqrt(sum(v * v for v in args.step))
    trip.say(f"rides on a display entity in the save {args.zip} of {commit[:8]} ({args.branch}), sha256 {sha}: "
             f"{', '.join(rides)}; from {args.start}, {args.step} a tick ({far * 20:.2f} blocks a second) for "
             f"{args.ticks} ticks; {os.cpu_count()} cores, {args.budget:.0f} s at most")
    failed, report, console = [], [], savetrip.console_size()
    facts = [f"# the save: {args.zip} of {commit[:8]} ({args.branch}), sha256 {sha}; the plank goes from {args.start} "
             f"{args.step} a tick for {args.ticks} ticks"]
    out = os.path.join(work, "shots")
    os.makedirs(out)
    groups, tracks = {}, {}
    cam = savetrip.nodetrip_cam()

    def tell(line):
        report.append(line)
        trip.say("ride: " + line)

    try:
        trip.stage("clean", station, "down", budget=180)
        console = savetrip.console_size()
        world = os.path.join(SERVER, LEVEL)
        os.makedirs(SERVER, exist_ok=True)
        savetrip.unpack(zip_path, world)
        level = savetrip.level_facts(world)
        mode, hard = level["mode"] or "adventure", level["difficulty"] or "peaceful"
        as_slot = {**distances, "MC_LEVEL": LEVEL, "MC_GAMEMODE": mode, "MC_FORCE_GAMEMODE": "false", "MC_DIFFICULTY": hard}
        lines = stand_in(world, args.step)
        tell("the stand-in data pack c164ride, its step function: " + " | ".join(lines))
        code, _ = trip.stage("setup", station, "setup", budget=min(1500, trip.left() - 300), env=as_slot)
        if code != 0:
            raise SystemExit("the node could not be made ready")
        said, _ = savetrip.give_pack(world)
        trip.say("resource pack: " + said)
        code, _ = trip.stage("server", station, "server-up", budget=min(400, trip.left() - CLOSING), env=as_slot)
        if code != 0:
            raise SystemExit("the server did not come up on the save")
        packs = ask(trip, "datapack list enabled")[0]
        if "c164ride" not in packs:
            ask(trip, 'datapack enable "file/c164ride"')
        ask(trip, "scoreboard objectives add c164ride dummy", "scoreboard players set #go c164ride 0")
        code, _ = trip.stage("game", station, "client-up", budget=trip.left() - CLOSING, env=as_slot)
        if code != 0:
            raise SystemExit("the game did not come up or did not join")
        seat = {**as_slot, "MC_SEAT": SEAT, "MC_CAM": SECOND, "MC_VIEW": "8", "MC_CLIENT_HEAP": "2G"}
        code, _ = trip.stage("the one who watches", station, "client-up", budget=min(420, trip.left() - CLOSING), env=seat)
        watching = code == 0
        if not watching:
            failed.append("the second client did not come up or did not join")
        time.sleep(12)                  # the title of a first joining is gone, the chunks are there
        middle = [args.start[k] + args.step[k] * args.ticks / 2 for k in range(3)]
        beside = [middle[0], middle[1] + 2.0, middle[2] + 14.0]
        if watching:
            ask(trip, f"gamemode spectator {SECOND}",
                f"tp {SECOND} {beside[0]:.2f} {beside[1]:.2f} {beside[2]:.2f} 180 8")
        spawn = ask(trip, f"data get entity {cam} Pos")[0]
        home = " ".join(f"{float(v):.2f}" for v in __import__("re").findall(r"(-?\d+\.?\d*)d", spawn)[:3]) or "88.5 196 -32.5"
        seconds = args.ticks / 20.0

        for ride in rides:
            smooth, every = RIDES[ride]
            ticks = (args.ticks // every) * every if every > 1 else args.ticks
            took = ticks / 20.0
            start = " ".join(f"{v:.2f}" for v in args.start)
            ask(trip, "scoreboard players set #go c164ride 0", "kill @e[type=minecraft:item_display,tag=c164.ride]",
                f"summon minecraft:item_display {start} {{Tags:[\"c164.ride\"],teleport_duration:{smooth},"
                f"item:{{id:\"minecraft:oak_planks\",count:1}}}}")
            mounted = ask(trip, f"ride {cam} mount {CAR}")[0]
            time.sleep(2.5)
            own = track("", f"ride_{ride}", took + 4.0)
            theirs = track(SEAT, f"watch_{ride}", took + 4.0, cam) if watching else None
            row = Row(trip, cam, "", out, f"ride_{ride}", int((took + 2.0) / 0.9), 0.9, at_once=True)
            row.start()
            seen = Row(trip, SECOND, SEAT, out, f"watch_{ride}", 4, took / 4.0, at_once=True) if watching else None
            if seen:
                seen.start()
            time.sleep(1.0)
            ask(trip, "scoreboard players set #t c164ride -1", f"scoreboard players set #end c164ride {ticks}",
                f"scoreboard players set #go c164ride {every}")
            time.sleep(took + 1.5)
            after = ask(trip, f"execute as {cam} on vehicle run data get entity @s Pos", f"data get entity {cam} Pos",
                        "tick query")
            row.join(timeout=30)
            if seen:
                seen.join(timeout=30)
            groups[f"ride_{ride}"] = [n for n, _ in row.taken] + ([n for n, _ in seen.taken] if seen else [])
            ask(trip, f"tp {cam} {home}", "kill @e[type=minecraft:item_display,tag=c164.ride]")
            tell(f"RIDE {ride}: teleport_duration {smooth}, a tp every {every} tick(s), {ticks} ticks. Mounting: {mounted}. "
                 f"After the ride the server has the player's vehicle at: {after[0] or 'NOTHING (not riding)'}; the player: "
                 f"{after[1]}; the server's ticks: {after[2][:160]}")
            text = own(took + 30)
            tracks[f"ride_{ride}.txt"] = text or ""
            if text is None or text.startswith("# FAILED"):
                failed.append(f"ride {ride}: the riding client wrote no track")
                tell(f"  ride {ride}, the riding client: no track ({(text or 'no answer').strip()[:200]})")
            else:
                found, _ = judge_camera(text, args.step, ticks, every)
                for line in found:
                    tell(f"  ride {ride}, the rider's camera: {line}")
                tell(f"  ride {ride}, the rider's own client: {judge_pair(text, 'P')}")
            if theirs:
                text = theirs(took + 30)
                tracks[f"watch_{ride}.txt"] = text or ""
                tell(f"  ride {ride}, the watching client: " + (judge_pair(text, "O") if text else "no track"))
    except SystemExit as stop:
        if stop.code not in (0, None):
            trip.say(f"stopped: {stop}")
            failed.append(str(stop)[:200])
    except Exception as exc:            # the node is closed down and what there is is kept all the same
        trip.say("stopped by an error of this script:\n" + traceback.format_exc())
        failed.append(f"{type(exc).__name__}: {exc}"[:200])
    finally:
        try:
            trip.stage("what the game said", station, "client-said", f"{started:.0f}",
                       log_path[:-len(".log")] + "-client.txt", budget=30)
        except Exception as exc:
            trip.say(f"what the game said could not be read ({exc})")
        try:
            warnings, errors = savetrip.server_said(console, log_path[:-len(".log")] + "-server.txt", trip.secret())
            trip.say(f"the server on the save: {warnings} warnings, {errors} errors in its log")
        except Exception as exc:
            trip.say(f"what the server said could not be read ({exc})")
        trip.stage("close", station, "down", budget=180)
        shutil.rmtree(os.path.join(SERVER, LEVEL, "datapacks", "c164ride"), ignore_errors=True)
        trip.stage("back to the test world", station, "setup", budget=120, env=distances)
        kept_in = os.path.join(KEPT, name)
        try:
            keep(trip, kept_in, out, groups, tracks, facts, report, commit, view, name, sha, failed)
        except Exception as exc:
            trip.say(f"the pictures could not be kept ({type(exc).__name__}: {exc})")
            failed.append("the pictures could not be kept")
        trip.say(("trip done" if not failed else "trip done with failures: " + "; ".join(failed))
                 + f"; kept: {kept_in}/; log {os.path.relpath(log_path, PROJECT)}")
        trip.log.close()
    return 1 if failed else 0


def keep(trip, kept_in, out, groups, tracks, facts, report, commit, view, name, sha, failed):
    """The pictures as JPEGs in renders/real-save/<name>/, a sheet for each ride, the tracks, ride.txt."""
    from PIL import Image
    import boardrender
    import realshots
    folder = os.path.join(PROJECT, kept_in)
    shutil.rmtree(folder, ignore_errors=True)
    os.makedirs(folder)
    when = time.strftime("%Y-%m-%dT%H:%M", time.gmtime())
    rows_ = []
    for part, names in groups.items():
        for shot in names:
            path = os.path.join(folder, shot + ".jpg")
            with Image.open(os.path.join(out, shot + ".png")) as picture:
                picture.convert("RGB").resize(FRAME, Image.LANCZOS).save(path, "JPEG", quality=85)
            rows_.append(f"{shot} {part} {commit[:8]} {savetrip.digest(path)} {when} {view}")
        if names:
            boardrender.sheet(folder, names, f"c164 the save {name[:-len('-ride')]} (sha256 {sha[:12]}), a ride on a "
                              f"display entity: {part}", ext=".jpg", out=f"{part}.jpg")
    for file, text in tracks.items():
        with open(os.path.join(folder, file), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    with open(os.path.join(folder, realshots.NOTE), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(HEAD + "\n" + "".join(line + "\n" for line in facts) + "".join(row + "\n" for row in rows_))
    with open(os.path.join(folder, "ride.txt"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(f"rides on a display entity in the save {name[:-len('-ride')]} (sha256 {sha}), on a node {when} UTC\n"
                 + "".join(line + "\n" for line in report) + "".join(f"FAILED: {line}\n" for line in failed))
    trip.say(f"{len(rows_)} pictures and {len(tracks)} tracks kept in {kept_in}/ with ride.txt")


if __name__ == "__main__":
    sys.exit(main())
