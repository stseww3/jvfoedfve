#!/usr/bin/env python3
"""The walk-through check (plan/packages/common/walk.md): stations along a visitor's way, a picture
or six at each, contact sheets by stretch of the way.

The board has twelve fixed views; a visitor walks. A route file says where he walks, this tool puts a
station every four blocks along it, draws what he sees there (offline, build/render.py) and lays the
pictures out as contact sheets. Finding the faults in them is the walker's work; the tool only makes
sure that every round looks from the same places.

    walk.py check    <route.json>
        the route file's own mistakes; nothing is built
    walk.py floors   --canvas <pickle> --box=x0,z0,x1,z1 [--levels=0,7,18] [--top=y0,y1] [--out <file>]
        for writing a route: plans in characters of where feet find a floor in the built scene,
        one for each level named, and with --top the highest floor of every column between two levels
    walk.py stations <route.json> --canvas <pickle> --out <stations.json>
        the station table of a route, the feet of every station put on the floor of the built scene
    walk.py shots    <stations.json> --out <shots.json> [--stations in-A01,in-B03] [--views f,l]
        the shot list of a station table, as build/render.py and tools/shoot.py read it (so a list
        of a few stations can go to the render station for pictures from the game)
    walk.py sheets   <stations.json> --pictures <prefix> --out <folder>
        contact sheets of pictures drawn as <prefix>-<shot name>.png
    walk.py round    <route.json> --round <the assembly commit, 7 digits> [--stations <stations.json>]
                     [--only A,B] [--no-pictures]
        all of it, on a worker node: build the scene once, take the station table (the one given,
        or a new one of the route), ask the blocks how each station is reached, draw every shot,
        lay out the sheets. What is kept goes to plan/reviews/walk/<round>/: <prefix>-stations.json,
        <prefix>-reach.json and <prefix>-sheet-<stretch>-<n>.jpg. The single pictures stay in the
        work folder (--work, default /tmp/c164_walk) and are not kept. --only draws the stretches
        named and no others (a round in several jobs); --no-pictures stops before the drawing.

        bash c164-realms/tools/nodejob.sh --keep c164-realms/plan/reviews/walk \\
            python tools/walk.py round plan/reviews/walk/in-route.json --round db1ec43

The route file (JSON) -- one for each of the two walks, in-route.json and out-route.json:

    {"prefix": "in",                          station names start with it: in-A01, in-A02, ...
     "stretches": [                           the way, cut into stretches: one set of sheets each
       {"id": "A", "name": "the entrance and the star hall",       (plain ASCII: it is written on the sheets)
        "points": [
          {"at": [24.5, 0, 0.5], "node": "the court before the entrance"},
          {"at": [17.5, 0, 0.5], "node": "the doorway"},
          {"at": [8.5, 0, 0.5]},
          {"at": [4.5, 7, -8.5], "hop": true, "node": "inside the time room's door"}
        ]}]}

    at      where the feet stand: x, y, z in scene coordinates (a block's middle is .5; y is the level
            the feet are on, as the skeleton names levels). The way runs straight from point to point.
    node    a junction, a doorway, the corner of a platform -- say which. A node is looked at six
            ways (ahead, left, right, back, 45 degrees up, 45 degrees down); every other station
            ahead only.
    views   other views than those, as letters of "flrbud".
    look    [x, y, z]: the view ahead looks at this point instead of along the way.
    hop     true: the way does not run here from the point before (a room entered elsewhere, a
            place only the camera gets to). No stations between the two. The first point of a
            stretch is taken to follow the last one of the stretch before it, unless it says hop.
    note    anything; not read.

Stations: every point is one, and between two points the leg is divided evenly into steps of four
blocks or less. Their names count within the stretch (in-A01 ...), so a stretch that is changed
or added leaves the others' names alone; a round that walks again takes the station table of the
round before (--stations), and only a changed route makes a new one. The feet of a station are put
on the floor nearest to the level the route gives (tools/walkreach.py's feet() when that module is
there, a plain reading of the column otherwise); a station that finds no floor within a block and a
quarter keeps the route's level and is marked "floor": false -- the route says a floor is there,
so that is a finding, or the room has not moved in yet. A table walked again keeps its stations
where they are; "floor" then says what the floor has become (false: gone; a number: its new level).

Ways (tools/walkreach.py, when it is in the tree): what a person can walk is worked out from the
blocks' collision boxes, once from the route's first station, and every round anew. Each station
gets

    reach   how one gets there from the first station: "walk" (on foot), "hop" (it takes a jump),
            "fall" (only by dropping, and there is a way back), "trap" (no way back) or "no".
            A station without a floor has none: nobody stands there.
    from, how   for a station nobody gets to from the first one: the station a search of its own
            was started at (at most five of them: the roofs while the stair is not built, a room
            behind a shut door), and how one gets here from that one
    leg     the way from the station before it, where it is not a plain walk: "hop", "fall", "no"
    round   that way's length in blocks, when it is much longer than the straight line: something
            stands on the line

and <prefix>-reach.json keeps what walkreach found on the ground looked at (twelve blocks round
the route): pits without a way out, places reached by a jump only, low head room, gaps that only
head room closes. A model door, a model railing have no collision box: they are air to this.

Pictures: 640x360, the eye 1.62 above the feet, 77 degrees high, tick 14000, the whole scene `obs`
as the checkout builds it (every package's DRESS as it stands there). The view ahead looks the way
the leg runs and rises or falls with it (35 degrees at the most), so it looks up a stair and down
one; the last point of a run looks on level.

The sheets: the stations of a stretch in their order, each station's views in the order f l r b u d,
four across and three down. Over every picture its name -- the cell's number in a finding -- the
feet, the yaw and how light the picture is on the average (Rec. 709 luma of the sRGB values, 0 to
1): a row of stations near 0 is a way without light.
"""
import argparse
import gc
import importlib
import json
import math
import os
import pickle
import re
import subprocess
import sys
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
BUILD = os.environ.get("C164_BUILD") or os.path.join(PROJECT, "build")

EYE = 1.62                  # the eye of a standing person above the feet (the skeleton's EYE)
STEP = 4.0                  # a station at least every so many blocks
PITCH_MOST = 35.0           # the view ahead follows the way's rise or fall, but never looks steeper up or down than this
TIME = 14000                # the map's hour
FOV = 77.0                  # as build/render.py and the board take their pictures
SIZE = (640, 360)
VIEWS = "flrbud"            # ahead, left, right, back, up, down
TURN = {"f": (0.0, None), "l": (-90.0, 0.0), "r": (90.0, 0.0), "b": (180.0, 0.0), "u": (0.0, -45.0), "d": (0.0, 45.0)}
REACH = 1.25                # a station's feet are put on a floor at most this far above or below the route's level
COLS, ROWS = 4, 3           # pictures on a sheet
LABEL = 22                  # the strip over a picture
HEADER = 32                 # the strip over a sheet
DARK = 0.02                 # a view ahead darker than this on the average is listed in the round's report
STARTS = 5                  # the searches for ways: the route's first station, and so many less one of those nobody gets to
NEAR = 0.6                  # a station and a place reached are the same place within this much of height
MARGIN = 12                 # ways are looked for this far round the route
ROUND = (1.5, 2.0)          # a leg's way is "round" when longer than the straight line times this, and this more
NAME_OK = re.compile(r"[A-Za-z0-9]+\Z")
POINT_KEYS = {"at", "node", "views", "look", "hop", "note"}


# ---- the route --------------------------------------------------------------------------------------
def _is_xyz(v):
    return isinstance(v, list) and len(v) == 3 and all(isinstance(n, (int, float)) and not isinstance(n, bool) for n in v)


def route_problems(route):
    """What is wrong with a route file, as a list of sentences."""
    out = []
    if not isinstance(route, dict) or not NAME_OK.match(str(route.get("prefix", ""))):
        return ['"prefix" has to be there, letters and digits (in, out)']
    stretches = route.get("stretches")
    if not isinstance(stretches, list) or not stretches:
        return ['"stretches" has to be a list of stretches']
    seen = set()
    for n, stretch in enumerate(stretches):
        if not isinstance(stretch, dict):
            out.append(f"stretch {n + 1}: has to be an object")
            continue
        sid = str(stretch.get("id", ""))
        where = f"stretch {sid or n + 1}"
        if not NAME_OK.match(sid):
            out.append(f'{where}: "id" has to be letters and digits')
        if sid in seen:
            out.append(f"{where}: the id is used twice")
        seen.add(sid)
        name = stretch.get("name", "")
        if not isinstance(name, str) or not name or any(not 32 <= ord(ch) <= 126 for ch in name):
            out.append(f'{where}: "name" has to be there, in plain ASCII (it is written on the sheets)')
        points = stretch.get("points")
        if not isinstance(points, list) or not points:
            out.append(f"{where}: no points")
            continue
        before = None
        for k, p in enumerate(points):
            at = p.get("at") if isinstance(p, dict) else None
            if not _is_xyz(at):
                out.append(f'{where}, point {k + 1}: "at" has to be [x, y, z]')
                before = None
                continue
            if any(ch not in VIEWS for ch in str(p.get("views", ""))):
                out.append(f'{where}, point {k + 1}: "views" may hold the letters {VIEWS} only')
            if p.get("look") is not None and not _is_xyz(p["look"]):
                out.append(f'{where}, point {k + 1}: "look" has to be [x, y, z]')
            unknown = sorted(set(p) - POINT_KEYS)
            if unknown:
                out.append(f"{where}, point {k + 1}: unknown key {', '.join(unknown)}")
            if before and not p.get("hop") and math.dist(at[::2], before[::2]) < 1e-6:
                out.append(f"{where}, point {k + 1}: stands where the point before it stands")
            before = at
    return out


def load_route(path):
    with open(path, encoding="utf-8") as fh:
        route = json.load(fh)
    problems = route_problems(route)
    if problems:
        raise SystemExit(f"walk: {path}:\n  " + "\n  ".join(problems))
    return route


# ---- where the floor is -------------------------------------------------------------------------------
# A plain reading of one column, for when tools/walkreach.py (collision boxes, what can be walked) is
# not in the tree. Good enough to put a camera at eye height; it does not say what can be walked.
_NOTHING = ("air", "cave_air", "void_air", "light", "water", "lava", "fire", "structure_void", "torch", "wall_torch",
            "soul_torch", "soul_wall_torch", "redstone_torch", "redstone_wall_torch", "copper_torch", "copper_wall_torch",
            "lever", "tripwire", "tripwire_hook", "string", "vine", "glow_lichen", "sculk_vein", "redstone_wire", "rail",
            "ladder", "cobweb", "short_grass", "tall_grass", "fern", "large_fern", "dead_bush", "leaf_litter")
_NOTHING_ENDS = ("_button", "_pressure_plate", "_sign", "_banner", "_torch", "_rail", "_carpet", "_sapling", "_tulip",
                 "_fan", "_coral", "_vines", "_roots", "_bud")
_NO_FLOOR_ENDS = ("_wall", "_fence", "_fence_gate", "_bars", "_pane", "_door", "_rod", "chain", "lantern", "_candle",
                  "_head", "_skull", "_pot", "_bell")


def _split(state):
    name, _, rest = state.partition("[")
    name = name.rpartition(":")[2]
    props = dict(item.split("=", 1) for item in rest.rstrip("]").split(",") if "=" in item)
    return name, props


def _is_nothing(state):
    """A block one walks through."""
    name, props = _split(state)
    return name in _NOTHING or name.endswith(_NOTHING_ENDS) or (name == "snow" and props.get("layers", "1") == "1")


def _tops(state, fx, fz):
    """The levels above the cell's bottom at which a block carries feet standing at (fx, fz) within
    the cell (0..1 each): a list, empty for a block one walks through or cannot stand on."""
    name, props = _split(state)
    if name in _NOTHING or name.endswith(_NOTHING_ENDS):
        return []
    if name == "snow":
        return [(int(props.get("layers", 1)) - 1) / 8.0]
    if name.endswith("_slab"):
        return [0.5] if props.get("type", "bottom") == "bottom" else [1.0]
    if name.endswith("_stairs"):
        if props.get("half", "bottom") == "top":
            return [1.0]
        high = {"north": fz < 0.5, "south": fz >= 0.5, "west": fx < 0.5, "east": fx >= 0.5}[props.get("facing", "north")]
        return [1.0 if high else 0.5]
    if name.endswith("_trapdoor"):
        if props.get("open") == "true":
            return []
        return [1.0] if props.get("half") == "top" else [3.0 / 16.0]
    if name.endswith(_NO_FLOOR_ENDS):
        return []
    return [1.0]


def plain_feet(cells, x, z, near_y, reach=REACH):
    """The level of the floor nearest to near_y in the column of (x, z) with two blocks free over
    it; None when there is none within `reach`."""
    bx, bz = math.floor(x), math.floor(z)
    best = None
    for by in range(math.floor(near_y - reach) - 1, math.floor(near_y + reach) + 1):
        state = cells.get((bx, by, bz))
        if not state:
            continue
        for top in _tops(state, x - bx, z - bz):
            level = by + top
            if abs(level - near_y) > reach:
                continue
            over = range(by + 1, math.floor(level + 1.8 - 1e-9) + 1)
            if all(_is_nothing(cells.get((bx, yy, bz), "air")) for yy in over) \
                    and (best is None or abs(level - near_y) < abs(best - near_y)):
                best = level
    return best


def column_floors(cells, x, z, y0, y1):
    """Every level between y0 and y1 at which feet can stand in the column of (x, z), lowest first."""
    bx, bz = math.floor(x), math.floor(z)
    out = []
    for by in range(math.floor(y0) - 1, math.floor(y1) + 1):
        state = cells.get((bx, by, bz))
        if not state:
            continue
        for top in _tops(state, x - bx, z - bz):
            level = by + top
            if y0 <= level <= y1 and all(_is_nothing(cells.get((bx, yy, bz), "air"))
                                          for yy in range(by + 1, math.floor(level + 1.8 - 1e-9) + 1)):
                out.append(level)
    return out


PLAN_MARKS = {0.0: "o", 0.5: "^", 1.0: '"', -0.5: ",", -1.0: "_"}


def floor_plans(cells, box, levels=(), top=None):
    """Plans in characters of where feet find a floor, as lines of text: one plan for each level
    (a floor within a block of it, marked by how far over or under the level it lies), and one of
    the highest floor of every column between the two levels of `top`. For writing a route."""
    x0, z0, x1, z1 = box
    ruler = "      " + "".join(str(abs(x) % 10) for x in range(x0, x1 + 1))
    out = []
    for level in levels:
        out += [f"== feet near y {level:g}: x {x0}..{x1} left to right, rows z {z0}..{z1} (north on top). o on the "
                'level, ^ half a block over it, " a block over, comma half a block under, _ a block under, '
                "# a block and no floor, . nothing", ruler]
        for z in range(z0, z1 + 1):
            row = []
            for x in range(x0, x1 + 1):
                near = sorted(column_floors(cells, x + 0.5, z + 0.5, level - 1.0, level + 1.0), key=lambda v: abs(v - level))
                if near:
                    row.append(PLAN_MARKS.get(round((near[0] - level) * 2) / 2, "?"))
                else:
                    row.append("." if _is_nothing(cells.get((x, math.floor(level), z), "air")) else "#")
            out.append(f"{z:5d} " + "".join(row))
        out.append("")
    if top:
        ruler = "      " + "".join(f"{x:4d}" for x in range(x0, x1 + 1))
        out += [f"== the highest floor of every column between y {top[0]:g} and {top[1]:g} (+ is half a block more): "
                f"x {x0}..{x1}, rows z {z0}..{z1}", ruler]
        for z in range(z0, z1 + 1):
            row = []
            for x in range(x0, x1 + 1):
                found = column_floors(cells, x + 0.5, z + 0.5, top[0], top[1])
                if not found:
                    row.append("   .")
                else:
                    whole = math.floor(found[-1])
                    row.append(f"{whole:3d}{'+' if found[-1] - whole >= 0.5 else ' '}")
            out.append(f"{z:5d} " + "".join(row))
        out.append("")
    return out


def _walkreach():
    """tools/walkreach.py as a module; None while it is not in the tree."""
    try:
        if HERE not in sys.path:
            sys.path.insert(0, HERE)
        import walkreach  # noqa: PLC0415
    except ImportError:
        return None
    return walkreach if hasattr(walkreach, "feet") and hasattr(walkreach, "reach_of") else None


def feet_finder(cells):
    """(feet, where it comes from): feet(x, z, near_y) -> level or None. tools/walkreach.py's when
    that module is in the tree, the plain reading of the column otherwise."""
    walkreach = _walkreach()
    if walkreach is None:
        return (lambda x, z, near_y: plain_feet(cells, x, z, near_y)), "the plain reading of the column"
    return (lambda x, z, near_y: walkreach.feet(cells, x, z, near_y, REACH)), "tools/walkreach.py"


def room_finder():
    """where(x, y, z) -> the room of main/shell.py a place lies in, or None; None always while the
    shell is not in the tree."""
    try:
        if BUILD not in sys.path:
            sys.path.insert(0, BUILD)
        shell = importlib.import_module("scenes.obs.main.shell")
    except Exception:  # noqa: BLE001  the module is not there, or cannot be read
        return lambda x, y, z: None
    return lambda x, y, z: shell.room_at(math.floor(x), math.floor(y + 0.01), math.floor(z))


# ---- stations -----------------------------------------------------------------------------------------
def _yaw(dx, dz):
    """The game's yaw of a direction on the ground: 0 south (+z), 90 west (-x), 180 north, -90 east."""
    return round(math.degrees(math.atan2(-dx, dz)), 1) + 0.0


def _aim(eye, target):
    """Yaw and pitch from an eye to a point (pitch as the game has it: positive looks down)."""
    dx, dy, dz = (target[i] - eye[i] for i in range(3))
    ground = math.hypot(dx, dz)
    if ground < 1e-9:
        return 0.0, (0.0 if abs(dy) < 1e-9 else (-89.0 if dy > 0 else 89.0))
    return _yaw(dx, dz), round(max(-89.0, min(89.0, -math.degrees(math.atan2(dy, ground)))), 1)


def _runs(points):
    """The runs of points the way goes through without a hop: [[index, ...], ...]."""
    runs = []
    for k, p in enumerate(points):
        if k == 0 or p.get("hop"):
            runs.append([k])
        else:
            runs[-1].append(k)
    return runs


def _along(path, d):
    """The place on a path -- [(x, y, z), ...] -- at ground distance d from its start, the direction
    on the ground of the leg it lies on and that leg's rise for a block of ground. Past the end the
    last leg runs on."""
    if len(path) == 1:
        return path[0], (0.0, 0.0), 0.0
    for n in range(len(path) - 1):
        a, b = path[n], path[n + 1]
        length = math.dist(a[::2], b[::2])
        if d <= length or n == len(path) - 2:
            if length < 1e-9:
                return a, (0.0, 0.0), 0.0
            place = tuple(a[i] + d / length * (b[i] - a[i]) for i in range(3))
            return place, ((b[0] - a[0]) / length, (b[2] - a[2]) / length), (b[1] - a[1]) / length
        d -= length
    return path[-1], (0.0, 0.0), 0.0


def stations_of(route, feet, where=None, step=STEP):
    """The station table of a route: a list of dicts in the order of the way."""
    where = where or (lambda x, y, z: None)
    out = []
    for stretch in route["stretches"]:
        points = stretch["points"]
        count = 0
        for nth, run in enumerate(_runs(points)):
            path = [tuple(float(v) for v in points[k]["at"]) for k in run]
            marks = [0.0]                                    # the ground distance of every point from the run's start
            for a, b in zip(path, path[1:]):
                marks.append(marks[-1] + math.dist(a[::2], b[::2]))
            stops = []                                       # (distance, the point's index or None)
            for n, k in enumerate(run):
                stops.append((marks[n], k))
                if n + 1 < len(run):
                    length = marks[n + 1] - marks[n]
                    parts = max(1, math.ceil(length / step - 1e-9))
                    stops += [(marks[n] + length * j / parts, None) for j in range(1, parts)]
            for d, k in stops:
                (x, y, z), heading, slope = _along(path, d)
                if k is not None and len(path) > 1:
                    if k != run[-1]:                         # a point looks along the leg that leaves it,
                        _, heading, slope = _along(path, d + 1e-3)
                    else:                                    # the last one on the way it came, level
                        heading, slope = _along(path, max(d - 1e-3, 0.0))[1], 0.0
                level = feet(x, z, y)
                floor = level is not None
                level = y if level is None else level
                point = points[k] if k is not None else {}
                if point.get("look"):
                    yaw, pitch = _aim((x, level + EYE, z), point["look"])
                elif len(path) == 1:
                    yaw, pitch = 0.0, 0.0
                else:
                    yaw = _yaw(*heading)
                    pitch = round(max(-PITCH_MOST, min(PITCH_MOST, -math.degrees(math.atan(slope)))), 1)
                yaw, pitch = yaw + 0.0, pitch + 0.0          # no -0.0 in the table
                count += 1
                station = dict(id=f"{route['prefix']}-{stretch['id']}{count:02d}", stretch=stretch["id"],
                               feet=[round(x, 2), round(level, 3), round(z, 2)], yaw=yaw, pitch=pitch,
                               views=point.get("views") or (VIEWS if point.get("node") else "f"))
                if point.get("node"):
                    station["node"] = point["node"]
                if k == run[0] and (nth or point.get("hop")):
                    station["hop"] = True                    # the way does not come here from the station before
                if not floor:
                    station["floor"] = False
                room = where(x, level, z)
                if room:
                    station["room"] = room
                out.append(station)
    return out


def table_of(route, stations, **facts):
    table = dict(prefix=route["prefix"], step=STEP, eye=EYE, fov=FOV, size=list(SIZE), time=TIME)
    table.update(facts)
    table["stretches"] = {s["id"]: s["name"] for s in route["stretches"]}
    table["stations"] = stations
    return table


def write_table(path, table):
    """One station a line, so that a change shows as one line in a diff."""
    head = {k: v for k, v in table.items() if k != "stations"}
    lines = ",\n".join("  " + json.dumps(s, ensure_ascii=False) for s in table["stations"])
    text = json.dumps(head, ensure_ascii=False, indent=1)[:-2] + ',\n "stations": [\n' + lines + "\n ]\n}\n"
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def load_table(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# ---- shots --------------------------------------------------------------------------------------------
def shots_of(table, only=None, views=None):
    """The shot list of a station table: [dict(name, pos, yaw, pitch, time)], one for every view of
    every station (or of the stations and views named)."""
    out = []
    for s in table["stations"]:
        if only and s["id"] not in only:
            continue
        x, y, z = s["feet"]
        for v in s["views"]:
            if views and v not in views:
                continue
            turn, pitch = TURN[v]
            yaw = (s["yaw"] + turn + 180.0) % 360.0 - 180.0
            out.append(dict(name=f"{s['id']}-{v}", pos=[x, round(y + table.get("eye", EYE), 3), z], yaw=round(yaw, 1),
                            pitch=s["pitch"] if pitch is None else pitch, time=table.get("time", TIME)))
    return out


def write_shots(path, shots):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("[\n" + ",\n".join(" " + json.dumps(s) for s in shots) + "\n]\n")


# ---- sheets -------------------------------------------------------------------------------------------
def _luma(img):
    """Rec. 709 luma of the sRGB values, 0 to 1, averaged over the picture."""
    import numpy as np  # noqa: PLC0415
    a = np.asarray(img, dtype=np.float64) / 255.0
    return float((a[..., 0] * 0.2126 + a[..., 1] * 0.7152 + a[..., 2] * 0.0722).mean())


def sheets_of(table, pictures, out, cols=COLS, rows=ROWS, quality=88):
    """Lay the pictures <pictures>-<shot name>.png out as sheets in the folder `out`. Returns the
    files written and, for every shot, how light its picture is (None: there is no picture)."""
    from PIL import Image, ImageDraw, ImageFont  # noqa: PLC0415
    os.makedirs(out, exist_ok=True)
    try:
        font, big = ImageFont.load_default(size=15), ImageFont.load_default(size=19)
    except TypeError:               # an older Pillow: the small bitmap font only
        font = big = ImageFont.load_default()
    width, height = table.get("size", SIZE)
    prefix, written, light = table["prefix"], [], {}
    for sid, name in table["stretches"].items():
        cells = [(f"{s['id']}-{v}", s) for s in table["stations"] if s["stretch"] == sid for v in s["views"]]
        per = cols * rows
        pages = max(1, math.ceil(len(cells) / per))
        for page in range(pages):
            part = cells[page * per:(page + 1) * per]
            down = max(1, math.ceil(len(part) / cols))
            sheet = Image.new("RGB", (cols * width, HEADER + down * (height + LABEL)), (24, 24, 28))
            draw = ImageDraw.Draw(sheet)
            draw.text((8, 4), f"walk-{prefix}   round {table.get('round', '?')}   stretch {sid}: {name}   "
                              f"(sheet {page + 1} of {pages})", fill=(235, 235, 235), font=big)
            for n, (shot, s) in enumerate(part):
                left, top = (n % cols) * width, HEADER + (n // cols) * (height + LABEL)
                path = f"{pictures}-{shot}.png"
                x, y, z = s["feet"]
                label = f"{shot}   feet {x:g}, {y:g}, {z:g}   yaw {s['yaw']:g}"
                if os.path.exists(path):
                    with Image.open(path) as img:
                        img = img.convert("RGB")
                        if img.size != (width, height):
                            img = img.resize((width, height))
                        light[shot] = _luma(img)
                        sheet.paste(img, (left, top + LABEL))
                    label += f"   light {light[shot]:.3f}"
                else:
                    light[shot] = None
                    draw.rectangle((left, top + LABEL, left + width - 1, top + LABEL + height - 1), fill=(60, 60, 66))
                    draw.text((left + 12, top + LABEL + 12), "no picture", fill=(220, 220, 220), font=big)
                marks = []
                if s.get("floor") is False:
                    marks.append("NO FLOOR")
                elif s.get("floor") is not None:
                    marks.append(f"FLOOR NOW {s['floor']:g}")
                elif s.get("reach", "walk") != "walk":
                    marks.append(f"REACH {s['reach']}" + (f" ({s['how']} from {s['from'].partition('-')[2]})" if s.get("from") else ""))
                if s.get("leg"):
                    marks.append(f"LEG {s['leg']}")
                if s.get("round"):
                    marks.append(f"ROUND {s['round']:g}")
                label += "".join("   " + m for m in marks)
                if s.get("node") and shot.endswith("-f"):
                    label += f"   [{s['node']}]"
                draw.text((left + 4, top + 3), label[:int(width / 7.6)], font=font,
                          fill=(255, 140, 120) if marks else (255, 214, 120) if s.get("node") else (210, 210, 210))
            path = os.path.join(out, f"{prefix}-sheet-{sid}-{page + 1}.jpg")
            sheet.save(path, quality=quality)
            written.append(path)
    return written, light


# ---- the scene ----------------------------------------------------------------------------------------
def scene_cells(scene, canvas):
    """The built scene's cells: read from the pickle build/render.py --canvas keeps, or built and
    kept there."""
    if canvas and os.path.exists(canvas):
        with open(canvas, "rb") as fh:
            return pickle.load(fh)["b"]
    if BUILD not in sys.path:
        sys.path.insert(0, BUILD)
    built = importlib.import_module(f"scenes.{scene}").build()
    if canvas:
        os.makedirs(os.path.dirname(os.path.abspath(canvas)), exist_ok=True)
        with open(canvas, "wb") as fh:
            pickle.dump({"b": built.b, "entities": built.entities}, fh, protocol=4)
    return built.b


def make_table(route, cells, **facts):
    feet, source = feet_finder(cells)
    return table_of(route, stations_of(route, feet, room_finder()), floor_from=source, **facts)


# ---- what the blocks say of the stations ----------------------------------------------------------------
SURVEYED = ("floor", "reach", "from", "how", "leg", "round")
ROWS_KEPT = 60              # of each list in walkreach's report (they are sorted, the worst first)


def _node(reach, q, x, y, z):
    """The node of a Reach at a station: the place reached at the lattice point nearest to it, or at
    one beside that, whose feet are within NEAR of the station's. None: nobody gets there."""
    world = reach.world
    i0, j0 = world.lattice(x, z)
    best = None
    for i in range(i0 - 1, i0 + 2):
        for j in range(j0 - 1, j0 + 2):
            for top, _ in world.stand(i, j):
                node = (i, j, int(round(top * q)))
                if node in reach.kind and abs(top - y) <= NEAR + 1e-6:
                    off = (max(abs(i - i0), abs(j - j0)), abs(top - y))
                    if best is None or off < best[0]:
                        best = (off, node)
    return best[1] if best else None


def _leg(reach, a, b, most, jump):
    """The easiest way from node a to node b of a Reach within `most` lattice steps: (kind, steps).
    "walk"; "hop" with jumps and drops of a jump's height; "fall" with any drop; ("no", None)."""
    tries = (("walk", lambda kind, rise: kind == "walk"),
             ("hop", lambda kind, rise: kind in ("walk", "jump") or -rise <= jump + 1e-6),
             ("fall", lambda kind, rise: True))
    for name, allow in tries:
        seen, todo = {a: 0}, deque([a])
        while todo:
            node = todo.popleft()
            if node == b:
                return name, seen[node]
            if seen[node] >= most:
                continue
            for nxt, kind, rise in reach.out.get(node) or ():
                if nxt not in seen and allow(kind, rise):
                    seen[nxt] = seen[node] + 1
                    todo.append(nxt)
    return "no", None


def _short(report):
    """walkreach's report with its long lists cut to ROWS_KEPT rows (how many there were is noted)."""
    out = {}
    for key, value in report.items():
        if isinstance(value, list) and len(value) > ROWS_KEPT:
            out[key] = value[:ROWS_KEPT]
            out[f"{key}: rows in all"] = len(value)
        else:
            out[key] = value
    return out


def survey(table, cells, say=print):
    """What the built scene says of every station of a table: the floor under it and, with
    tools/walkreach.py in the tree, how it is reached (the docstring's "Ways"). Sets floor, reach,
    from, how, leg and round of every station anew; returns what <prefix>-reach.json keeps, None
    without walkreach."""
    feet, source = feet_finder(cells)
    table["floor_from"] = source
    stations = table["stations"]
    for s in stations:
        for key in SURVEYED:
            s.pop(key, None)
        x, y, z = s["feet"]
        level = feet(x, z, y)
        if level is None:
            s["floor"] = False
        elif abs(level - y) > 0.01:
            s["floor"] = round(level, 3)
    walkreach = _walkreach()
    if walkreach is None or not stations:
        return None
    q, grid = walkreach.Q, walkreach.GRID
    xs, zs = [s["feet"][0] for s in stations], [s["feet"][2] for s in stations]
    bounds = (math.floor(min(xs)) - MARGIN, math.floor(min(zs)) - MARGIN,
              math.floor(max(xs)) + MARGIN, math.floor(max(zs)) + MARGIN)
    starts, nodes = [], {}                  # [(station, Reach)]; {station: (which start, node)}
    place = {}                              # {station: where its feet stand now}; none without a floor
    for s in stations:
        if s.get("floor") is False:
            continue
        x, y, z = place[s["id"]] = (s["feet"][0], s.get("floor", s["feet"][1]), s["feet"][2])
        for n, (_, reach) in enumerate(starts):
            node = _node(reach, q, x, y, z)
            if node is not None:
                nodes[s["id"]] = (n, node)
                break
        else:
            if "floor" in s or len(starts) >= STARTS:
                continue
            try:
                reach = walkreach.reach_of(cells, (x, y, z), bounds)
            except ValueError:              # nobody can stand there after all
                continue
            node = _node(reach, q, x, y, z)
            if node is None:
                continue
            starts.append((s["id"], reach))
            nodes[s["id"]] = (len(starts) - 1, node)
            say(f"walk: ways from {s['id']} ({x:g}, {y:g}, {z:g}): {len(reach.kind)} places reached"
                + ("; CUT SHORT" if reach.cut else ""), flush=True)
    table["reach_from"] = starts[0][0] if starts else None
    table["reach_bounds"] = list(bounds)
    before = None
    for s in stations:
        hit = nodes.get(s["id"])
        if s["id"] not in place:
            pass                            # no floor: nobody stands there, and that is said already
        elif hit is None:
            s["reach"] = "no"
        elif hit[0] == 0:
            s["reach"] = starts[0][1].kind[hit[1]]
        else:
            s["reach"] = "no"
            s["from"], s["how"] = starts[hit[0]][0], starts[hit[0]][1].kind[hit[1]]
        gone = nodes.get(before["id"]) if before is not None and not s.get("hop") else None
        if gone is not None and s["id"] in place:
            reach = starts[gone[0]][1]      # the ways that lead on from the station before
            here = hit[1] if hit is not None and hit[0] == gone[0] else _node(reach, q, *place[s["id"]])
            straight = math.dist(before["feet"][::2], s["feet"][::2])
            kind, steps = ("no", None) if here is None else \
                _leg(reach, gone[1], here, int(6 * straight / grid) + 24, walkreach.JUMP)
            if kind != "walk":
                s["leg"] = kind
            if steps is not None and steps * grid > ROUND[0] * straight + ROUND[1]:
                s["round"] = round(steps * grid, 1)
        before = s
    try:
        if BUILD not in sys.path:
            sys.path.insert(0, BUILD)
        line = float(importlib.import_module("scenes.obs.site.terrain").CLOUD_TOP + 1)
    except Exception:  # noqa: BLE001  no such module, no such sheet: nobody is sent home
        line = None
    found = dict(round=table.get("round"), scene=table.get("scene"), bounds=list(bounds), line=line, starts=[])
    for n, (sid, reach) in enumerate(starts):
        mine = [k for k, hit in nodes.items() if hit[0] == n]
        found["starts"].append(dict(station=sid, stations=len(mine), report=_short(reach.report(None, line=line))))
    return found


def write_found(path, found):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(found, fh, ensure_ascii=False, indent=1)
        fh.write("\n")


def report(table, light=None):
    """A few lines for the job's receipt: how many stations and pictures each stretch has, which
    stations found no floor, which pictures are missing or dark."""
    lines = []
    for sid, name in table["stretches"].items():
        mine = [s for s in table["stations"] if s["stretch"] == sid]
        shots = [f"{s['id']}-{v}" for s in mine for v in s["views"]]
        floating = [s["id"] for s in mine if s.get("floor") is False]
        line = f"stretch {sid} ({name}): {len(mine)} stations, {len(shots)} pictures"
        if floating:
            line += f"; no floor at {len(floating)}: {', '.join(floating[:12])}{' ...' if len(floating) > 12 else ''}"
        moved = [f"{s['id']} ({s['floor']:g})" for s in mine if s.get("floor") not in (None, False)]
        if moved:
            line += f"; the floor has moved at {len(moved)}: {', '.join(moved[:12])}{' ...' if len(moved) > 12 else ''}"
        if any("reach" in s for s in mine):
            for kind in ("hop", "fall", "trap", "no"):
                rows = [s["id"] + (f" ({s['how']} from {s['from']})" if s.get("from") else "")
                        for s in mine if s.get("reach") == kind and s.get("floor") is not False]
                if rows:
                    line += f"; reached '{kind}' {len(rows)}: {', '.join(rows[:12])}{' ...' if len(rows) > 12 else ''}"
            legs = [f"{s['id']} ({s['leg']})" for s in mine if s.get("leg")]
            if legs:
                line += f"; the leg to it is no plain walk at {len(legs)}: {', '.join(legs[:12])}{' ...' if len(legs) > 12 else ''}"
            far = [f"{s['id']} ({s['round']:g})" for s in mine if s.get("round")]
            if far:
                line += f"; a long way round to {len(far)}: {', '.join(far[:12])}{' ...' if len(far) > 12 else ''}"
        if light is not None:
            missing = [n for n in shots if light.get(n) is None]
            dark = [n for n in shots if n.endswith("-f") and light.get(n) is not None and light[n] < DARK]
            if missing:
                line += f"; {len(missing)} pictures missing"
            if dark:
                line += f"; ahead darker than {DARK} at {len(dark)}: {', '.join(dark[:12])}{' ...' if len(dark) > 12 else ''}"
        lines.append(line)
    return lines


# ---- the commands ---------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("check")
    p.add_argument("route")
    p = sub.add_parser("floors")
    p.add_argument("--scene", default="obs")
    p.add_argument("--canvas", help="the pickle build/render.py --canvas keeps; built and kept there if it is not")
    p.add_argument("--box", required=True, help="x0,z0,x1,z1 (write --box=-12,-40,20,40: a value may start with a minus)")
    p.add_argument("--levels", default="", help="comma separated levels: a plan of the floors near each")
    p.add_argument("--top", help="y0,y1: a plan of the highest floor of every column between the two")
    p.add_argument("--out", help="write the plans to this file instead of printing them")
    p = sub.add_parser("stations")
    p.add_argument("route")
    p.add_argument("--scene", default="obs")
    p.add_argument("--canvas", help="the pickle build/render.py --canvas keeps; built and kept there if it is not")
    p.add_argument("--round", default="?", help="the assembly commit the scene was built of (noted in the table)")
    p.add_argument("--out", required=True)
    p = sub.add_parser("shots")
    p.add_argument("table")
    p.add_argument("--stations", help="comma separated station names; default all")
    p.add_argument("--views", help="comma separated views (f, l, r, b, u, d); default every view a station has")
    p.add_argument("--out", required=True)
    p = sub.add_parser("sheets")
    p.add_argument("table")
    p.add_argument("--pictures", required=True, help="the pictures are <this>-<shot name>.png")
    p.add_argument("--out", required=True)
    p = sub.add_parser("round")
    p.add_argument("route")
    p.add_argument("--round", required=True, help="the assembly commit this round follows, 7 digits")
    p.add_argument("--stations", help="walk again from this station table instead of making one of the route")
    p.add_argument("--scene", default="obs")
    p.add_argument("--work", default="/tmp/c164_walk", help="where the scene's pickle and the single pictures go")
    p.add_argument("--out", help="default plan/reviews/walk/<round>/")
    p.add_argument("--only", help="comma separated stretch ids: draw these stretches only")
    p.add_argument("--no-pictures", action="store_true", help="the station table and the ways only: nothing is drawn")
    args = ap.parse_args()

    if args.cmd == "check":
        with open(args.route, encoding="utf-8") as fh:
            route = json.load(fh)
        problems = route_problems(route)
        for line in problems:
            print("walk:", line)
        if not problems:
            points = sum(len(s["points"]) for s in route["stretches"])
            print(f"walk: {args.route}: {len(route['stretches'])} stretches, {points} points, nothing wrong")
        return 1 if problems else 0

    if args.cmd == "floors":
        box = [int(v) for v in args.box.split(",")]
        lines = floor_plans(scene_cells(args.scene, args.canvas), box,
                            [float(v) for v in args.levels.split(",") if v],
                            [float(v) for v in args.top.split(",")] if args.top else None)
        if args.out:
            os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
            with open(args.out, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines) + "\n")
            print(f"walk: {len(lines)} lines -> {args.out}")
        else:
            print("\n".join(lines))
        return 0

    if args.cmd == "stations":
        route = load_route(args.route)
        cells = scene_cells(args.scene, args.canvas)
        table = make_table(route, cells, scene=args.scene, round=args.round, route_file=os.path.basename(args.route))
        found = survey(table, cells)
        write_table(args.out, table)
        if found is not None:
            write_found(os.path.join(os.path.dirname(os.path.abspath(args.out)), f"{route['prefix']}-reach.json"), found)
        print("\n".join(report(table)))
        return 0

    if args.cmd == "shots":
        shots = shots_of(load_table(args.table), args.stations.split(",") if args.stations else None,
                         args.views.split(",") if args.views else None)
        write_shots(args.out, shots)
        print(f"walk: {len(shots)} shots -> {args.out}")
        return 0

    if args.cmd == "sheets":
        table = load_table(args.table)
        written, light = sheets_of(table, args.pictures, args.out)
        print("\n".join(report(table, light)))
        print(f"walk: {len(written)} sheets -> {args.out}")
        return 0

    # round
    route = load_route(args.route)
    prefix = route["prefix"]
    out = args.out or os.path.join(PROJECT, "plan", "reviews", "walk", args.round)
    work = os.path.join(args.work, f"{prefix}-{args.round}")
    os.makedirs(work, exist_ok=True)
    canvas = os.path.join(args.work, f"{args.scene}-{args.round}.pkl")
    cells = scene_cells(args.scene, canvas)
    if args.stations:
        table = load_table(args.stations)
        table["round"] = args.round
    else:
        table = make_table(route, cells, scene=args.scene, round=args.round, route_file=os.path.basename(args.route))
    found = survey(table, cells)
    kept = os.path.join(out, f"{prefix}-stations.json")
    write_table(kept, table)
    if found is not None:
        write_found(os.path.join(out, f"{prefix}-reach.json"), found)
    del cells, found                        # the drawing reads the scene again, in a process of its own
    walkreach = _walkreach()
    if walkreach is not None:
        walkreach._WORLDS.clear()
    gc.collect()
    if args.no_pictures:
        print("\n".join(report(table)))
        print(f"walk: {os.path.basename(kept)} -> {os.path.relpath(out, PROJECT)}; nothing drawn")
        return 0
    if args.only:
        wanted = args.only.split(",")
        table["stretches"] = {k: v for k, v in table["stretches"].items() if k in wanted}
        table["stations"] = [s for s in table["stations"] if s["stretch"] in wanted]
    shots = shots_of(table)
    shot_file = os.path.join(work, "shots.json")
    write_shots(shot_file, shots)
    print(f"walk: {len(table['stations'])} stations, {len(shots)} shots; drawing", flush=True)
    width, height = table.get("size", SIZE)
    pictures = os.path.join(work, "p")
    done = subprocess.run([sys.executable, "render.py", args.scene, "--shots", shot_file, "--out", pictures,
                           "--size", f"{width}x{height}", "--fov", str(table.get("fov", FOV)), "--canvas", canvas],
                          cwd=BUILD, capture_output=True, text=True)
    print("\n".join((done.stdout + done.stderr).strip().splitlines()[-6:]), flush=True)
    written, light = sheets_of(table, pictures, out)
    print("\n".join(report(table, light)))
    print(f"walk: {len(written)} sheets and {os.path.basename(kept)} -> {os.path.relpath(out, PROJECT)}")
    return 0 if done.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
