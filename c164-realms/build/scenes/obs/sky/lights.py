"""sky/lights: every invisible light source of the map (card plan/packages/sky/lights.md;
plan/parts/sky.md 6). The rules, the ranks and what the other lines call are in sky/_lightkit.py.

build() runs after every other line (sky is the last of LINES; a test scene calls
scenes.obs.sky.build(canvas, origin) at the end of its own build()). It looks at what stands on
the canvas by then and places, in this order:

  windows   the sources behind the lit windows: the windows of main's table (main._plan.windows(),
            at `origin`) and those a scene registered with _lightkit.glazed(). The glass that
            stands in a window decides, not the table: B.WINDOW_LIT, _FROSTED and _CURTAIN get a
            source, dark glass gets none, a window that is not glazed yet is passed over. The
            source stands in the cell before the glass of the middle column (the window's
            recess), two levels under the level the window has behind its glass: outside that is
            the same light, and the room behind the window keeps to its own lamps. Where that
            cell is taken (the bars of a base window) the source stands behind the glass, at
            the full level; so it does for a window registered as "inside". A tall
            lit window has two, one row above the sill and one row below the head. The brightest
            window lends each of its sources to the recesses of the two windows beside it, where
            those are lit themselves, three levels lower: the entrance's three windows stand in
            one light (_lightkit.LENDS).
  entrance  as long as the star hall has not moved in (main/facade.furnished()), the sources that
            stand in for the hall's lamps; no lamp is shown for any of them. Where a wall stands
            close behind the doorway (a vestibule, the facade's stand-in wall): one source of
            level 14 in the main doorway, when it stands open, and one of 12 against that wall,
            so that the doorway reads as a warm bright face and not as a hole (10 behind the
            arches beside the doorway, where the entrance is an arcade). Where the hall stands
            open behind the arches (OPEN_HALL, with main/shell in the tree; the director's
            ruling D): one source of 14 before the telescope pier's east face, where the mother
            clock will hang, and one of 11 over the foot of the flight behind either side arch;
            none in the doorway, whose frame stays darker than the pier it frames. All of them
            go when the star hall moves in, the one in the doorway too (the director, #58129).
  wash      on either wing, the two pilasters next to the entrance's corner pilaster (which carries
            a bracket lamp): at the foot of each a small projector two cells before the plinth
            (props' model, lamps "uplight", with the source of level 8 it brings), and where its
            beam lands, before the foot of the shaft, one source (_lightkit.WASH, 10; the
            director, #62755: no higher). From there the light falls by one a row and is spent
            under the string course, as a beam from below is: a wing shows three upright bands,
            brightest at the foot, that lead to the entrance (review cr2-#3: the wash has to
            have a shape). The wall between two pilasters gets what spreads from them, 8 next to
            the foot of a shaft and 7 in the middle of the bay; nothing is placed before the wall.
  offers    what the other lines registered with _lightkit.suggest() and take(): a source is placed
            when its cell is free and something that glows is within two cells of it.

DRESS is the director's switch for everything that is laid over the whole building (group #20161).
It is on since the review of this card has passed (cr2-#3; the director, 11-16: on, and 12
behind the lit windows of the wings, #58003). Off, build() lights no window of main's table and no wall,
and the fronts of the master scene stay bare; the entrance is lit all the same (director, #21989:
in the master scene the doorway is not to be a black hole), and so are the offers of the other
lines and the windows a scene registers. A scene asks for the building's lights, or for the bare
fronts, whatever the switch says, with _lightkit.dress(canvas) and dress(canvas, False).

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
DRESS = True                            # see above

DOOR_BAY = 9
ENTRANCE_BAYS = (DOOR_BAY, DOOR_BAY - 1, DOOR_BAY + 1)      # the doorway, then the arches an arcade has beside it
DOOR_LEVEL = 14
DOOR_Y = 1                              # the source's row: the threshold gets 13, the head of the door 9
HALL_LEVEL, SIDE_LEVEL = 12, 10         # against the back of the vestibule: behind the doorway, behind an arch
HALL_Y = 2                              # the row of those sources: the middle of what a doorway shows of the wall
HALL_DEPTH = 8                          # a wall this close behind the glass plane is the back of a vestibule
# The hall as main/shell builds it, open from the entrance to the telescope pier, is lit from here
# until the star hall moves in. main/facade asks for this word (hall_lit()) and leaves its stand-in
# wall out when it is set and the shell is in the tree.
OPEN_HALL = True
HALL_REACH = 14                         # the face the doorway looks at is looked for this far behind the glass plane
# Before that face, the telescope pier's east one, where the mother clock will hang (y 1 to 5). The
# row is the one that serves the court and the doorway both: from the court the middle arch shows
# the face at 0.31 to 0.32 with the source in row 3 or 4 and at 0.28 to 0.29 with it in row 5; seen
# from the doorway the pale floor before the pier stands at 0.34 beside a face of 0.34 with row 3,
# at 0.31 beside 0.33 with row 4.
PIER_LEVEL, PIER_Y = 14, 4
# The doorway of the open hall gets no source (0): what one sees through the middle arch is the lit
# pier, and the frame of the doorway has to stay darker than what it frames. With 14 in the doorway
# its reveals stood at 0.42 against a pier's face that does not get past 0.36.
OPEN_DOOR_LEVEL = 0
FLIGHT_REACH = 18                       # the foot of a flight behind an arch beside the doorway, this far at most
# Over that foot, under the head of the hall's west arcade. At 11 the flights are warm and a step
# under the pier (0.21 against 0.33), which gives the hall its depth; at 9 or 8 they turn grey.
FLIGHT_LEVEL, FLIGHT_Y = 11, 4
WASH_PILASTERS = (5, 6, 11, 12)         # the skeleton's numbers: the two of either wing next to the entrance's corner
WASH_OUT = 2                            # cells between the plinth and the projector's cell, counting it
WASH_ROW = S.BASE[0]                    # where the beam lands: the foot of the shaft, the row over the plinth
DOOR_WHY, HALL_WHY = "sky/lights:door", "sky/lights:hall"
WASH_WHY, WINDOW_WHY = "sky/lights:wash", "sky/lights:window"
GLOWING = tuple(B.PANELS[k] for k in ("tubes", "scope", "pilot_lamps"))     # glow without giving light
NEAR = ((0, -1, 0), (1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, 1, 0))


# ---- the report ----------------------------------------------------------------------------------------
def report(canvas):
    """canvas.light_report, made on the first call:

      placed     {cell: (level, why)}      every source this module placed
      ranks      {1: n, 2: n, 3: n}        how many of them in each rank; a window's source before the
                                           glass counts as the source behind the glass it stands for
      levels     {level: n}                the levels as they are placed
      rejected   [(cell, level, why, reason)]   offers that got no source
      capped     [(cell, asked, given, why)]    offers cut down to the top of their rank
      merged     [(cell, level, why)]           offers that lost their cell to a brighter one
      moved      [(asked, cell, why)]           offers whose cell was taken, placed next to it
      windows    {group: {"glass": [dark, dim, lit, bright], "sources": n, "before": n, "lent": n,
                 "unglazed": n, "undressed": n, "by_hand": n, "pairs": [(front, storey, bay, bay)],
                 "fronts": {front: [..4..]}}}
                 the windows as they are glazed on the canvas, group by group ("" is main's table);
                 before: how many of the sources stand before the glass (the others behind it);
                 lent: the sources the brightest window lends to the windows beside it, on top
                 of `sources`;
                 undressed: lit windows of main's table left without a source while DRESS is off
      table      {look: [dark, dim, lit, bright]}   what each look lights of main's table
      dressed    bool                       were the building's own lights asked for (DRESS, dress())
      doors      [cell]                     the sources in open main doorways (one to an origin; none
                                            where the hall stands open behind the doorway)
      hall       [cell]                     the sources behind them: against the back of a vestibule, or
                                            in the open hall (before the pier, over the flights' feet)
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
            windows={}, table={}, dressed=False, doors=[], hall=[], wash=[], fifteen=[], foreign=0, isolated=[],
            notes=[], problems=[], _seen=set(), _records=[], _before=set(), _entered=set())
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
                   + (f" ({w['sources'] - w['before']} of them behind the glass)" if w["sources"] > w["before"] else "")
                   + (f" and {w['lent']} lent by the brightest window to the windows beside it" if w.get("lent") else "")
                   + (f", {w['undressed']} left without (not dressed)" if w["undressed"] else "")
                   + (f", {w['unglazed']} not glazed" if w["unglazed"] else "")
                   + (f", {w['by_hand']} lit by hand" if w["by_hand"] else "")
                   + (f", lit neighbours: {w['pairs']}" if w["pairs"] else ""))
    for look, n in r["table"].items():
        out.append(f"main's table under {look}: dark {n[0]}, dim {n[1]}, lit {n[2]}, bright {n[3]}")
    out.append(f"dressed: {'yes' if r['dressed'] else 'no'}; doors: {r['doors'] or 'none'}; behind them: "
               f"{len(r['hall'])} sources; wash: {len(r['wash'])} projectors; not placed here: {r['foreign']}; level 15: {len(r['fifteen'])}; "
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
                r["_before"].discard(cell)
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
                            inward=tuple(w["inward"]), y=tuple(w["y"]), level=None, inside=False, look=None,
                            table=True))
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
    """Place the sources of a lit window: in the cell before the glass, L.THROUGH under the level
    the window has behind it, or, where no column has that cell free, behind the glass at that
    level; a window registered as "inside" keeps them there whatever is free (_lightkit.glazed()
    says what for). Returns them as [(cell, level, is it before the glass)], or None when the
    scene has put a source of its own next to this glass."""
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
    beside = [(x + ox + s * dx, y + oy, z + oz + s * dz)
              for s in (1, -1) for x, z in w["cells"] for y in range(y0, y1 + 1)]
    if any(canvas.name(*c) == B.LIGHT and c not in r["placed"] for c in beside):
        return None
    out = []
    for y in ys:
        spots = []
        if level > L.THROUGH and not w.get("inside"):
            spots += [((x + ox - dx, y + oy, z + oz - dz), level - L.THROUGH, True)
                      for x, z in (w["cells"][i] for i in columns)]
        spots += [((x + ox + dx, y + oy, z + oz + dz), level, False)
                  for x, z in (w["cells"][i] for i in columns)]
        for cell, given, before in spots:
            done = _put(canvas, r, cell, given, why)
            if done == "taken":
                continue
            if before and done != "kept":
                r["_before"].add(cell)
            out.append((cell, given, before))
            break
        else:
            r["notes"].append(f"{why}: no free cell before or behind the glass in row {y + oy}")
    return out


def _lend(canvas, r, glazed):
    """What the brightest window lends to the windows next to it (L.LENDS). For each of its sources
    before the glass one more in the recess of the window on either side: in the column nearest
    to the source and in its row, as many levels lower as the two cells are apart. Only to a
    window that is lit itself (a dark one stays dark), and only along one wall plane: a neighbour
    round a corner, or in a wall that is set back, gets nothing.
    glazed: {(group, origin, front, storey, bay): (record, tier, the sources _behind() placed)}."""
    for (group, origin, front, storey, bay), (w, tier, sources) in glazed.items():
        if tier not in L.LENDS:
            continue
        ox, oy, oz = origin
        dx, dz = w["inward"]
        for step in (-1, 1):
            v, lit = glazed.get((group, origin, front, storey, bay + step), (None, L.DARK))[:2]
            if v is None or lit == L.DARK or tuple(v["inward"]) != (dx, dz):
                continue
            why = f"{WINDOW_WHY} {group + ' ' if group else ''}{front} {bay} {storey}, lent to bay {bay + step}"
            for (x, y, z), level, before in sources:
                if not before:
                    continue
                nx, nz = min(((cx + ox - dx, cz + oz - dz) for cx, cz in v["cells"]),
                             key=lambda c: (abs(c[0] - x) + abs(c[1] - z), c))
                if (nx - x) * dx + (nz - z) * dz:
                    continue
                row = min(max(y, v["y"][0] + oy), v["y"][1] + oy)
                lent = level - abs(nx - x) - abs(nz - z) - abs(row - y)
                if lent < 1:
                    continue
                done = _put(canvas, r, (nx, row, nz), lent, why)
                if done in ("placed", "raised"):
                    r["_before"].add((nx, row, nz))
                    r["windows"][group]["lent"] += 1
                elif done == "taken":
                    r["notes"].append(f"{why}: the cell {(nx, row, nz)} before its glass is taken")


def _windows(canvas, r, origin):
    glazed = {}
    for w in _records(canvas, origin):
        ox, oy, oz = w["origin"]
        key = (w["cells"][0][0] + ox, w["y"][0] + oy, w["cells"][0][1] + oz)
        if key in r["_seen"]:
            continue
        r["_seen"].add(key)
        group = r["windows"].setdefault(w["group"], dict(glass=[0, 0, 0, 0], sources=0, before=0, lent=0,
                                                         unglazed=0, undressed=0, by_hand=0, pairs=[], fronts={}))
        tier = _glass(canvas, w)
        if tier is None:
            group["unglazed"] += 1
            continue
        group["glass"][tier] += 1
        group["fronts"].setdefault(w["front"], [0, 0, 0, 0])[tier] += 1
        r["_records"].append((w["group"], w["origin"], w["front"], w["bay"], w["storey"], tier))
        sources = None
        if tier > L.DARK and w["table"] and not r["dressed"]:
            group["undressed"] += 1
        elif tier > L.DARK:
            outside = len(r["_before"])
            sources = _behind(canvas, r, w, tier)
            if sources is None:
                group["by_hand"] += 1
            else:
                group["sources"] += len(sources)
                group["before"] += len(r["_before"]) - outside
        glazed[(w["group"], w["origin"], w["front"], w["storey"], w["bay"])] = (w, tier, sources or [])
    _lend(canvas, r, glazed)


# ---- the entrance -------------------------------------------------------------------------------------
def _furnished():
    """Has the star hall moved into the shell (main/facade.furnished(), once the facade has it)?
    What the arches show is the hall itself then, and the hall's own lamps light it."""
    try:
        from ..main import facade
    except ImportError:
        return False
    return bool(getattr(facade, "furnished", lambda: False)())


def _entrance(canvas, r, origin):
    """The light of the entrance, which stands in for the lamps of a hall nobody has furnished yet.
    One source in the open main doorway, where a doorway stands: open from the glass plane to the
    pilaster plane, a jamb on either side, something over it, ground under it. And the vestibule
    behind it: where a wall closes the view through the doorway within HALL_DEPTH cells of the
    glass plane, a source stands against it; the same, two steps lower, behind the arches beside
    the doorway when the entrance is an arcade.
    Where no wall closes the view and the hall stands open behind the arches (OPEN_HALL, with
    main/shell in the tree), the light is in the hall and not in the doorway: a source before the
    face the doorway looks at, the telescope pier's east face, and one over the foot of the flight
    behind either arch beside the doorway. The doorway itself gets OPEN_DOOR_LEVEL, nothing: its
    frame stays darker than the pier it frames (the director's ruling D: from the court the
    brightest thing in the middle arch is the pier's east face, and the arches beside it are darker).
    Once the star hall has moved in, nothing of this is placed: the hall's own lamps light what
    the arches show, and the source in the doorway, which made the door's frame the brightest thing
    seen from inside the hall, goes with the hall's moving in (the director, #58129)."""
    ox, oy, oz = origin
    if _furnished() or tuple(origin) in r["_entered"]:
        return
    for bay in ENTRANCE_BAYS:
        wall = S.east_wall_x(bay) + ox
        z = S.bay_center_z(bay) + oz
        glass = wall + S.DEPTH_GLASS
        door = bay == DOOR_BAY
        if door:
            cell = (glass, DOOR_Y + oy, z)
            through = all(not canvas.has(x, y + oy, z) or (x, y + oy, z) in r["placed"]
                          for x in range(glass, wall + S.DEPTH_PILASTER + 1) for y in range(0, 3))
            jambs = _stops(canvas, wall, 1 + oy, z - 2) and _stops(canvas, wall, 1 + oy, z + 2)
            head = any(_stops(canvas, wall, y + oy, z) for y in range(3, S.FRIEZE + 1))
            ground = canvas.has(wall, S.PAVING_Y + oy, z)
            if not (through and jambs and head and ground):
                return
        elif _stops(canvas, wall, DOOR_Y + oy, z):
            continue                                    # a bay with a wall in it: no arch
        back = next((x for x in range(glass - 1, glass - 1 - HALL_DEPTH, -1) if _stops(canvas, x, HALL_Y + oy, z)), None)
        spot, level, in_door = None, 0, DOOR_LEVEL
        if back is not None:                            # a vestibule: against its back wall
            if back + 1 < glass:
                spot, level = (back + 1, HALL_Y + oy, z), HALL_LEVEL if door else SIDE_LEVEL
        elif not OPEN_HALL:
            pass
        elif door:                                      # the open hall: before the face the doorway looks at
            deep = range(glass - 1 - HALL_DEPTH, glass - 1 - HALL_REACH, -1)
            face = next((x for x in deep if _stops(canvas, x, PIER_Y + oy, z)), None)
            if face is not None:
                spot, level, in_door = (face + 1, PIER_Y + oy, z), PIER_LEVEL, OPEN_DOOR_LEVEL
        else:                                           # ... and over the foot of what rises behind an arch
            foot = next((x for x in range(glass - 1, glass - 1 - FLIGHT_REACH, -1) if canvas.has(x, S.GROUND + oy, z)), None)
            if foot is not None:
                spot, level = (foot, FLIGHT_Y + oy, z), FLIGHT_LEVEL
        if door:
            r["_entered"].add(tuple(origin))
            if in_door and _put(canvas, r, cell, in_door, DOOR_WHY) != "taken":
                r["doors"].append(cell)
        if spot is not None and _put(canvas, r, spot, level, HALL_WHY) != "taken":
            r["hall"].append(spot)


# ---- the wall wash -----------------------------------------------------------------------------------
def _wash(canvas, r, origin):
    """A projector at the foot of each wash pilaster, two cells before the plinth, where the front
    stands and the ground before it is free; and the source where its beam lands: in the row over
    the plinth, the first free cell before what stands in the pilaster's line there (its shaft), no
    further out than the projector itself. One source and no more: the light falls by one a row up
    the shaft, which is the shape of a beam from below. Nothing is placed before the wall between
    two pilasters: the wash is a row of upright bands, not a lighter storey.
    The lamp brings a source of its own for the ground around it, settled with the other offers.
    Returns the number of display entities placed."""
    try:
        from ..props import lamps
    except ImportError:
        r["notes"].append("no wall wash: props/lamps is not in the tree, and a source without a lamp is not placed")
        return 0
    ox, oy, oz = origin
    n = 0
    for k in WASH_PILASTERS:
        z = S.pilaster_z(k)
        front = max(S.east_wall_x(k), S.east_wall_x(k + 1))     # a pilaster stands with the bay that comes further out
        out = range(front + S.DEPTH_CORNICE + 1, front - 2, -1)
        foot = next((x for x in out if canvas.has(x + ox, oy, z + oz)), None)      # the plinth's outermost block
        if foot is None:
            continue                                                               # no front stands here
        x = foot + WASH_OUT
        cell = (x + ox, oy, z + oz)
        if cell in r["wash"]:
            continue
        line = [(sx + ox, WASH_ROW + oy, z + oz) for sx in range(x, front - 2, -1)]     # from over the projector inwards
        shaft = next((i for i, spot in enumerate(line) if canvas.has(*spot) and spot not in r["placed"]), None)
        free = all(not canvas.has(cx + ox, cy + oy, z + oz) for cx, cy in ((x - 1, 0), (x, 0), (x, 1)))
        if not free or not canvas.has(x + ox, S.PAVING_Y + oy, z + oz):
            r["notes"].append(f"no wall wash at pilaster {k}: the cell {cell} is taken or has no ground")
            continue
        if not shaft:
            r["notes"].append(f"no wall wash at pilaster {k}: no free cell before the foot of its shaft")
            continue
        n += lamps.place(canvas, "uplight", (x + 0.5, float(S.GROUND), z + 0.5), facing="west", origin=origin)
        r["wash"].append(cell)
        _put(canvas, r, line[shaft - 1], L.WASH, WASH_WHY)
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
            r["ranks"][L.rank(level + L.THROUGH if cell in r["_before"] else level)] += 1
            r["levels"][level] = r["levels"].get(level, 0) + 1
        else:
            r["foreign"] += 1
        if level > L.TOP:
            r["fifteen"].append(cell)
        if not (ours and r["placed"][cell][1] in (DOOR_WHY, HALL_WHY)) and not _glows_near(canvas, cell, index):
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
        if tier == L.DIM and not group and (front, bay, storey) not in L.FIXED:
            r["problems"].append(f"{front} {bay} {storey} is glazed with the curtain, which is kept for the "
                                 f"entrance and the fixed window at the foot of the clock tower")
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
        if L._plain(front) in L.HUSHED and any(t > L.DARK for t in tiers.values()):
            r["problems"].append(f"{name}: lit glass on a front that is kept dark")
    table = L._main_keys()
    if table:
        r["table"] = {look: L.counts(L.tiers(table, look)) for look in L.SHARE}


def build(canvas, origin=(0, 0, 0)):
    origin = tuple(int(v) for v in origin)
    r = report(canvas)
    r["dressed"] = bool(getattr(canvas, "light_dress", DRESS))
    _windows(canvas, r, origin)
    _entrance(canvas, r, origin)
    n = _wash(canvas, r, origin) if r["dressed"] else 0
    _settle(canvas, r)
    _survey(canvas, r)
    return n
