"""sky/lights: every invisible light source of the map (card plan/packages/sky/lights.md;
plan/parts/sky.md 6). The rules, the ranks and what the other lines call are in sky/_lightkit.py.

build() runs after every other line (sky is the last of LINES; a test scene calls
scenes.obs.sky.build(canvas, origin) at the end of its own build()). It looks at what stands on
the canvas by then and places, in this order:

  windows   the sources behind the lit windows: the windows of main's table (main._plan.windows(),
            at `origin`) and those a scene registered with _lightkit.glazed(). The glass that
            stands in a window decides, not the table: B.WINDOW_LIT, _FROSTED and _CURTAIN get a
            source, dark glass gets none, a window that is not glazed yet is passed over. The
            source stands in the first cell behind the glass of the middle column; a tall lit
            window has two, one row above the sill and one row below the head.
  door      one source of level 14 in the main doorway, when it stands open.
  wash      in the two bays either side of the entrance three: a small projector two cells before
            the plinth (props' model, lamps "uplight", with the source of level 8 it brings), and
            where its beam lands, in the row over the plinth, sources of level 8 before the wall
            and before the pilasters. The base storey is lifted from its foot to the string course
            (8 falling to 5) and the great windows' sills get no more than 4.
  offers    what the other lines registered with _lightkit.suggest() and take(): a source is placed
            when its cell is free and something that glows is within two cells of it.

DRESS is the director's switch for everything that is laid over the whole building (group #20161):
while it is off, build() lights no window of main's table, no doorway and no wall, so the master
scene and the pictures of the other packages stay as they are until the review of this card has
passed. The offers of the other lines and the windows a scene registers are served all the same.
A scene that shows a front under its lights asks for them with _lightkit.dress(canvas).

What was done is written down in canvas.light_report (see report()); summary() gives it as text.
build() returns the number of display entities it placed (the projectors of the wash).
"""
import math

from artkit import blockfacts as F
from artkit import blocks as AB

from ..common import blocks as B
from ..common import skeleton as S
from . import _lightkit as L

ORDER = 90                              # the last of the sky packages
DRESS = False                           # see above; turned on when the review has passed

DOOR_BAY = 9
DOOR_LEVEL = 14
DOOR_Y = 1                              # the source's row: the threshold gets 13, the head of the door 9
WASH_BAYS = (6, 7, 11, 12)              # two bays either side of the entrance three
WASH_OUT = 2                            # cells between the plinth and the projector's cell, counting it
WASH_LEVEL = 8                          # the top of rank 3
WASH_ROW = S.PLINTH[1] + 1              # where the beam lands: the first row over the plinth
WASH_SPREAD = (-2, -1, 1, 2)            # ... beside the projector's row: the wall of the bay and its pilasters
DOOR_WHY, WASH_WHY, WINDOW_WHY = "sky/lights:door", "sky/lights:wash", "sky/lights:window"
GLOWING = tuple(B.PANELS[k] for k in ("tubes", "scope", "pilot_lamps"))     # glow without giving light
NEAR = ((0, -1, 0), (1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, 1, 0))


# ---- the report ----------------------------------------------------------------------------------------
def report(canvas):
    """canvas.light_report, made on the first call:

      placed     {cell: (level, why)}      every source this module placed
      ranks      {1: n, 2: n, 3: n}        how many of them in each rank
      levels     {level: n}
      rejected   [(cell, level, why, reason)]   offers that got no source
      capped     [(cell, asked, given, why)]    offers cut down to the top of their rank
      merged     [(cell, level, why)]           offers that lost their cell to a brighter one
      moved      [(asked, cell, why)]           offers whose cell was taken, placed next to it
      windows    {group: {"glass": [dark, dim, lit, bright], "sources": n, "unglazed": n,
                 "undressed": n, "by_hand": n, "pairs": [(front, storey, bay, bay)],
                 "fronts": {front: [..4..]}}}
                 the windows as they are glazed on the canvas, group by group ("" is main's table);
                 undressed: lit windows of main's table left without a source while DRESS is off
      table      {look: [dark, dim, lit, bright]}   what each look lights of main's table
      dressed    bool                       were the building's own lights asked for (DRESS, dress())
      doors      [cell]                     the sources in open main doorways (one to an origin)
      wash       [cell]                     the cells of the projectors of the wall wash
      fifteen    [cell]                     sources of level 15 on the canvas (whoever placed them)
      foreign    n                          sources on the canvas that this module did not place
      isolated   [(cell, level)]            sources with nothing that glows within reach
      notes      [str]                      what was left out and why
      problems   [str]                      what breaks a rule; empty when all is well
    """
    if not hasattr(canvas, "light_report"):
        canvas.light_report = dict(
            placed={}, ranks={1: 0, 2: 0, 3: 0}, levels={}, rejected=[], capped=[], merged=[], moved=[],
            windows={}, table={}, dressed=False, doors=[], wash=[], fifteen=[], foreign=0, isolated=[],
            notes=[], problems=[], _seen=set(), _records=[])
    return canvas.light_report


def summary(canvas):
    """The report as lines of text."""
    r = report(canvas)
    out = [f"sources placed: {len(r['placed'])} "
           f"(rank 1: {r['ranks'][1]}, rank 2: {r['ranks'][2]}, rank 3: {r['ranks'][3]}); levels "
           + (", ".join(f"{lv}x{n}" for lv, n in sorted(r["levels"].items(), reverse=True)) or "none")]
    for group, w in sorted(r["windows"].items()):
        g = w["glass"]
        if not sum(g):
            out.append(f"windows {group or 'main'}: none of its {w['unglazed']} windows is glazed here")
            continue
        total = sum(g)
        out.append(f"windows {group or 'main'}: dark {g[0]}, dim {g[1]}, lit {g[2]}, bright {g[3]} "
                   f"({100.0 * g[0] / total:.0f}% dark), {w['sources']} sources"
                   + (f", {w['undressed']} left without (not dressed)" if w["undressed"] else "")
                   + (f", {w['unglazed']} not glazed" if w["unglazed"] else "")
                   + (f", {w['by_hand']} lit by hand" if w["by_hand"] else "")
                   + (f", lit neighbours: {w['pairs']}" if w["pairs"] else ""))
    for look, n in r["table"].items():
        out.append(f"main's table under {look}: dark {n[0]}, dim {n[1]}, lit {n[2]}, bright {n[3]}")
    out.append(f"dressed: {'yes' if r['dressed'] else 'no'}; doors: {r['doors'] or 'none'}; wash: "
               f"{len(r['wash'])} projectors; not placed here: {r['foreign']}; level 15: {len(r['fifteen'])}; "
               f"isolated: {len(r['isolated'])}")
    for key in ("capped", "moved", "merged", "rejected"):
        for entry in r[key]:
            out.append(f"{key}: {entry}")
    out += [f"note: {n}" for n in r["notes"]]
    out += [f"PROBLEM: {p}" for p in r["problems"]]
    return out


# ---- what glows ------------------------------------------------------------------------------------------
def _stops(canvas, x, y, z):
    state = canvas.b.get((x, y, z))
    return state is not None and L._stops_light(state)


def _entity_index(canvas):
    index = {}
    for x, y, z, _ in canvas.entities:
        index.setdefault((int(math.floor(x)), int(math.floor(z))), []).append(y)
    return index


def _glows_near(canvas, cell, index):
    """Is something that glows within reach of a cell? A lit window, a block that gives light (a
    caged bulb, a lantern), a glowing panel, or a model: any display entity counts, a lamp's anchor
    may be at its foot or at the ceiling."""
    x, y, z = cell
    r = L.REACH
    for dx in range(-r, r + 1):
        for dz in range(-r, r + 1):
            for ey in index.get((x + dx, z + dz), ()):
                if -L.REACH_UP - 0.5 <= ey - (y + 0.5) <= L.REACH_UP + 0.5:
                    return True
            for dy in range(-r, r + 1):
                state = canvas.b.get((x + dx, y + dy, z + dz))
                if state is None:
                    continue
                name = AB.name_of(state)
                if name == B.LIGHT:
                    continue
                if (L.tier_of(name) or 0) >= L.DIM or name in GLOWING or F.emission(*AB.parse(state)) > 0:
                    return True
    return False


def _lantern_near(canvas, cell):
    x, y, z = cell
    r = L.REACH
    return any(canvas.name(x + dx, y + dy, z + dz) == B.IRON_LANTERN
               for dx in range(-r, r + 1) for dy in range(-r, r + 1) for dz in range(-r, r + 1))


def _put(canvas, r, cell, level, why):
    """Place a source, or raise the one this module placed there before. Returns what happened:
    "placed", "raised", "kept" (a brighter one of ours stays) or "taken" (the cell holds
    something else)."""
    state = canvas.b.get(cell)
    if state is None:
        canvas.set(cell[0], cell[1], cell[2], L.light(level))
        r["placed"][cell] = (level, why)
        return "placed"
    if cell in r["placed"]:
        old, old_why = r["placed"][cell]
        if level > old:
            canvas.set(cell[0], cell[1], cell[2], L.light(level))
            r["placed"][cell] = (level, why)
            if old_why != why:
                r["merged"].append((cell, old, old_why))
            return "raised"
        if old_why != why:
            r["merged"].append((cell, level, why))
        return "kept"
    return "taken"


# ---- windows -------------------------------------------------------------------------------------------
def _records(canvas, origin):
    """The windows to look at: those registered since the last call, then main's table at origin."""
    out = [dict(w, table=False) for w in getattr(canvas, "light_windows", ())]
    if hasattr(canvas, "light_windows"):
        canvas.light_windows = []
    try:
        from ..main import _plan
        table = _plan.windows()
    except ImportError:
        table = []
    for w in table:
        if not w.get("blind"):
            out.append(dict(group="", origin=tuple(int(v) for v in origin), front=w["front"], bay=w["bay"],
                            storey=w["storey"], cells=[tuple(c) for c in w["cells"]],
                            inward=tuple(w["inward"]), y=tuple(w["y"]), level=None, look=None, table=True))
    return out


def _glass(canvas, w):
    """The tier of the glass that stands in a window, or None when it is not glazed."""
    ox, oy, oz = w["origin"]
    best = None
    for x, z in w["cells"]:
        for y in range(w["y"][0], w["y"][1] + 1):
            tier = L.tier_of(canvas.name(x + ox, y + oy, z + oz))
            if tier is not None and (best is None or tier > best):
                best = tier
    return best


def _behind(canvas, r, w, tier):
    """Place the sources behind a lit window. Returns how many stand there, or None when the scene
    has put a source of its own behind this glass."""
    ox, oy, oz = w["origin"]
    y0, y1 = w["y"]
    rows = y1 - y0 + 1
    tall = rows >= L.TALL
    level = w["level"] or L.BEHIND[tier][0 if tall else 1]
    ys = (y0 + 1, y1 - 1) if tall and tier >= L.LIT else (y0 + (rows - 1) // 2,)
    dx, dz = w["inward"]
    mid = len(w["cells"]) // 2
    columns = sorted(range(len(w["cells"])), key=lambda i: (abs(i - mid), i))
    why = f"{WINDOW_WHY} {w['group'] + ' ' if w['group'] else ''}{w['front']} {w['bay']} {w['storey']}"
    behind = [(x + ox + dx, y + oy, z + oz + dz) for x, z in w["cells"] for y in range(y0, y1 + 1)]
    if any(canvas.name(*c) == B.LIGHT and c not in r["placed"] for c in behind):
        return None
    n = 0
    for y in ys:
        for i in columns:
            x, z = w["cells"][i]
            if _put(canvas, r, (x + ox + dx, y + oy, z + oz + dz), level, why) != "taken":
                n += 1
                break
        else:
            r["notes"].append(f"{why}: no free cell behind the glass in row {y + oy}")
    return n


def _windows(canvas, r, origin):
    for w in _records(canvas, origin):
        ox, oy, oz = w["origin"]
        key = (w["cells"][0][0] + ox, w["y"][0] + oy, w["cells"][0][1] + oz)
        if key in r["_seen"]:
            continue
        r["_seen"].add(key)
        group = r["windows"].setdefault(w["group"], dict(glass=[0, 0, 0, 0], sources=0, unglazed=0, undressed=0,
                                                         by_hand=0, pairs=[], fronts={}))
        tier = _glass(canvas, w)
        if tier is None:
            group["unglazed"] += 1
            continue
        group["glass"][tier] += 1
        group["fronts"].setdefault(w["front"], [0, 0, 0, 0])[tier] += 1
        r["_records"].append((w["group"], w["origin"], w["front"], w["bay"], w["storey"], tier))
        if tier > L.DARK and w["table"] and not r["dressed"]:
            group["undressed"] += 1
        elif tier > L.DARK:
            n = _behind(canvas, r, w, tier)
            if n is None:
                group["by_hand"] += 1
            else:
                group["sources"] += n


# ---- the main door -----------------------------------------------------------------------------------
def _door(canvas, r, origin):
    """The open main door: one source in the doorway. Only where a doorway stands: open from the
    glass plane to the pilaster plane, a jamb on either side, something over it, ground under it."""
    ox, oy, oz = origin
    wall = S.east_wall_x(DOOR_BAY) + ox
    z = S.bay_center_z(DOOR_BAY) + oz
    cell = (wall + S.DEPTH_GLASS, DOOR_Y + oy, z)
    if cell in r["doors"]:
        return
    through = all(not canvas.has(x, y + oy, z) or (x, y + oy, z) in r["placed"]
                  for x in range(wall + S.DEPTH_GLASS, wall + S.DEPTH_PILASTER + 1) for y in range(0, 3))
    jambs = _stops(canvas, wall, 1 + oy, z - 2) and _stops(canvas, wall, 1 + oy, z + 2)
    head = any(_stops(canvas, wall, y + oy, z) for y in range(3, S.FRIEZE + 1))
    ground = canvas.has(wall, S.PAVING_Y + oy, z)
    if through and jambs and head and ground and _put(canvas, r, cell, DOOR_LEVEL, DOOR_WHY) != "taken":
        r["doors"].append(cell)


# ---- the wall wash -----------------------------------------------------------------------------------
def _wash(canvas, r, origin):
    """A projector two cells before the plinth of each wash bay, where the front stands and the
    ground before it is free, and the sources where its beam lands: in the row over the plinth, the
    first free cell before the wall or the pilaster, as far along the front as WASH_SPREAD says.
    The lamp brings a source of its own for the ground around it, settled with the other offers.
    Returns the number of display entities placed."""
    try:
        from ..props import lamps
    except ImportError:
        r["notes"].append("no wall wash: props/lamps is not in the tree, and a source without a lamp is not placed")
        return 0
    ox, oy, oz = origin
    n = 0
    for bay in WASH_BAYS:
        z = S.bay_center_z(bay)
        front = S.east_wall_x(bay)
        out = range(front + S.DEPTH_CORNICE + 1, front - 2, -1)
        foot = next((x for x in out if canvas.has(x + ox, oy, z + oz)), None)      # the plinth's outermost block
        if foot is None:
            continue                                                               # no front stands here
        x = foot + WASH_OUT
        cell = (x + ox, oy, z + oz)
        if cell in r["wash"]:
            continue
        landing = []
        for dz in WASH_SPREAD:
            wall = next((wx for wx in range(foot, front - 2, -1)
                         if _stops(canvas, wx + ox, WASH_ROW + oy, z + dz + oz)), None)
            if wall is not None and not canvas.has(wall + 1 + ox, WASH_ROW + oy, z + dz + oz) \
                    and x - (wall + 1) <= L.REACH:
                landing.append((wall + 1 + ox, WASH_ROW + oy, z + dz + oz))
        free = all(not canvas.has(cx + ox, cy + oy, z + oz) for cx, cy in ((x - 1, 0), (x, 0), (x, 1)))
        if not free or not canvas.has(x + ox, S.PAVING_Y + oy, z + oz):
            r["notes"].append(f"no wall wash before bay {bay}: the cell {cell} is taken or has no ground")
            continue
        if not landing:
            r["notes"].append(f"no wall wash before bay {bay}: no free cell at the foot of the wall within "
                              f"{L.REACH} cells of the projector")
            continue
        n += lamps.place(canvas, "uplight", (x + 0.5, float(S.GROUND), z + 0.5), facing="west", origin=origin)
        r["wash"].append(cell)
        for spot in landing:
            _put(canvas, r, spot, WASH_LEVEL, WASH_WHY)
    return n


# ---- the offers ----------------------------------------------------------------------------------------
def _settle(canvas, r):
    index = _entity_index(canvas)
    todo, canvas.light_offers = list(L.offers(canvas)), []
    for cell, level, why, rank in todo:
        asked = level
        top = L.RANKS[rank or L.kind_rank(why) or 1][1]
        if level > top:
            level = top
            r["capped"].append((cell, asked, level, why))
        if level < 1:
            r["rejected"].append((cell, asked, why, "no level"))
            continue
        if _lantern_near(canvas, cell):
            r["rejected"].append((cell, asked, why, "an iron lantern stands within reach and lights by itself"))
            continue
        target = cell
        state = canvas.b.get(cell)
        if state is not None and cell not in r["placed"]:
            if AB.name_of(state) == B.LIGHT:
                r["rejected"].append((cell, asked, why, "the scene has put a source of its own in this cell"))
                continue
            target = next(((cell[0] + dx, cell[1] + dy, cell[2] + dz) for dx, dy, dz in NEAR
                           if (cell[0] + dx, cell[1] + dy, cell[2] + dz) not in canvas.b), None)
            if target is None:
                r["rejected"].append((cell, asked, why, "the cell and the cells next to it are taken"))
                continue
        if not _glows_near(canvas, target, index):
            r["rejected"].append((cell, asked, why, f"nothing that glows within {L.REACH} cells"))
            continue
        _put(canvas, r, target, level, why)
        if target != cell:
            r["moved"].append((cell, target, why))


# ---- the survey ------------------------------------------------------------------------------------------
def _survey(canvas, r):
    index = _entity_index(canvas)
    r["ranks"] = {1: 0, 2: 0, 3: 0}
    r["levels"] = {}
    r["fifteen"], r["isolated"], r["foreign"], r["problems"] = [], [], 0, []
    for cell, state in canvas.b.items():
        if AB.name_of(state) != B.LIGHT:
            continue
        level = F.emission(*AB.parse(state))
        ours = cell in r["placed"]
        if ours:
            r["ranks"][L.rank(level)] += 1
            r["levels"][level] = r["levels"].get(level, 0) + 1
        else:
            r["foreign"] += 1
        if level > L.TOP:
            r["fifteen"].append(cell)
        if not (ours and r["placed"][cell][1] == DOOR_WHY) and not _glows_near(canvas, cell, index):
            r["isolated"].append((cell, level))
    if r["fifteen"]:
        r["problems"].append(f"{len(r['fifteen'])} light sources of level 15: {sorted(r['fifteen'])[:6]}")
    if r["isolated"]:
        r["problems"].append(f"{len(r['isolated'])} light sources with nothing that glows within {L.REACH} "
                             f"cells: {sorted(r['isolated'])[:6]}")
    fronts = {}
    for group, origin, front, bay, storey, tier in r["_records"]:
        fronts.setdefault((group, origin, front), {})[(front, bay, storey)] = tier
        if tier == L.BRIGHT and not group and (front, bay, storey) not in L.FIXED:
            r["problems"].append(f"{front} {bay} {storey} is glazed with the brightest glass, which is kept "
                                 f"for the window over the main door")
    for w in r["windows"].values():
        w["pairs"] = []
    for (group, origin, front), tiers in sorted(fronts.items(), key=str):
        name = f"{group or 'main'} {front}"
        for _, storey, bay, other in L.lit_neighbours(tiers):
            r["windows"][group]["pairs"].append((front, storey, bay, other))
            r["problems"].append(f"{name} {storey}: bays {bay} and {other} are both lit")
        dark = sum(1 for t in tiers.values() if t == L.DARK)
        if len(tiers) >= L.DARK_FROM and dark < math.ceil(L.DARK_SHARE * len(tiers) - 1e-9):
            r["problems"].append(f"{name}: {dark} of {len(tiers)} windows are dark, under a fifth")
        low = sum(1 for (_, _, storey), t in tiers.items() if t >= L.LIT and storey in L.LOW)
        high = sum(1 for (_, _, storey), t in tiers.items() if t >= L.LIT and storey not in L.LOW)
        if low > high and any(storey not in L.LOW for _, _, storey in tiers):
            r["problems"].append(f"{name}: {low} lit windows on the low storey, {high} above it")
        if L._plain(front) in L.HUSHED and any(t >= L.LIT for t in tiers.values()):
            r["problems"].append(f"{name}: lit glass on a front that should only glow")
    table = L._main_keys()
    if table:
        r["table"] = {look: L.counts(L.tiers(table, look)) for look in L.SHARE}


def build(canvas, origin=(0, 0, 0)):
    origin = tuple(int(v) for v in origin)
    r = report(canvas)
    r["dressed"] = bool(getattr(canvas, "light_dress", DRESS))
    _windows(canvas, r, origin)
    n = 0
    if r["dressed"]:
        _door(canvas, r, origin)
        n = _wash(canvas, r, origin)
    _settle(canvas, r)
    _survey(canvas, r)
    return n
