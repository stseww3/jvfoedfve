"""python -m scenes.obs_site_cablecar.clear [--scene] [--json FILE] (in build/): the cable station
against the part of the arrival view it keeps clear (skeleton.V1_CLEAR, V1_COMET; A0 #442),
measured exactly.

A0's rule leaves no margin: seen from V1's eye nothing of the station stands between the two ends
of the main building from the level of the eye up to 61 degrees (block A), nor where the comet
hangs north of that (block B). tools/check.py tests it with sight lines a quarter of a degree
apart and skeleton.in_v1_clear() tells of one point; a sliver between two sight lines or two
points passes both. Here nothing is sampled. Every box of every block (the game's own models, read
from the jar and from the materials line's pack, joined to their neighbours as the game joins
them) is cut by the planes of a block of the view, and what is left of the box is a convex solid:

  A  the wedge of bearings between the building's two ends, above the eye's level. A cone of
     directions higher than 61 degrees is convex, so the solid lies wholly above 61 degrees when
     all its corners do: it is in A when one corner is at 61 degrees or lower.
  B  the wedge from 15 degrees north of west to the building's north end. The solid is connected,
     so it is in B when its corners reach from 61 degrees or lower to 35 degrees or higher. (The
     highest point of a box cut by a wedge that leaves out due west is one of its corners.)

A point on a block's boundary counts as in it. Display entities are measured by the box round
each of their pieces, which is larger than the piece; the pieces are read from the pack the scene
writes, with the models of all its lines. One that has no pieces to read (a text display; a model
the pack does not hold) is not passed over: it is measured as the cell it stands in and one cell
round it, and named. The corners are also put to skeleton.in_v1_clear(), the skeleton's own word,
and the two answers are compared.

Without --scene the station is measured as its package builds it on an empty canvas, a second's
work. With --scene the whole test scene is built and everything that stands within the station's
box and six cells round it is measured, whoever set it there: the car, the winch and its cable,
lamps, benches, the name board; and the cells of the station that are not as its package set them
are named (another package laid something over them, or the mountain stood there first). Ends with
1 when something stands in either block.

The table names, part by part, how near the station comes: under "A" the least elevation of what
lies in A's bearings above the eye (clear when over 61) and the nearest bearing of what lies
outside them; under "B" the same for the comet's block. The last lines say how much of V1's
picture the station takes, and where, and how much block light lies on what is seen of it: the
waiting room is the picture's right edge and is kept dark (the reviewer's figure: no cell of it
in the picture above FRAME_LIGHT). The light is spread as the sky line's kit spreads it, from the
sources that stand on the canvas: without --scene those of the station's own windows, with it
everybody's.

--picture FILE reads a drawn picture of V1 (the kept v1.png) as well: how bright the waiting
room's wall, its shut windows and the sky beside it are in it, against the reviewer's figures for
a frame that neither glares nor goes black (TONES). It tells; it does not change the result.
"""
import argparse
import json
import math
import os
import sys
import tempfile
from itertools import combinations

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "..", "tools")))

import sightline as SL  # noqa: E402
from artkit import models as M  # noqa: E402
from artkit.canvas import Canvas  # noqa: E402
from artkit.gameassets import Assets  # noqa: E402
from artkit.shapes import Shaper  # noqa: E402
from scenes.obs import materials  # noqa: E402
from scenes.obs.common import blocks as B  # noqa: E402
from scenes.obs.common import skeleton as S  # noqa: E402
from scenes.obs.site import cablecar as C  # noqa: E402
from scenes.obs.sky import _lightkit as L  # noqa: E402
from scenes.obs.sky import lights  # noqa: E402

EYE = np.array(S.V1["pos"], dtype=float)
NORTH, SOUTH = S.v1_clear_span()
TOP = float(S.V1_CLEAR)
COMET_NORTH, COMET_LOW = -float(S.V1_COMET["north"]), float(S.V1_COMET["low"])
REACH = 6                       # as tools/check.py: what belongs to the station stays within this of its box
TOL = 1e-9
FOV, ASPECT = 77.0, 16.0 / 9.0  # the billboard pictures (build/render.py, tools/check.py)
GRID = (480, 270)               # sight lines over V1's picture, for the station's share of it
FRAME_LIGHT = 4                 # the most block light on what V1 sees of the waiting room (card, record 5)
FRAME = "waiting room"
OTHERS = "other packages"       # what stands at the station and is not its own
# The same record's figures for a drawn picture of V1, in the picture's own brightness (0 .. 1):
# the wall's median within `apart` of the sky's beside it and not over `wall`, the shut windows'
# not under `blind`.
TONES = dict(apart=0.05, wall=0.19, blind=0.03)
TONE_GRID = (640, 360)          # sight lines over the picture, for what each of its pixels shows
SKY_ROWS = (0.18, 0.60)         # the rows of the picture where the room's edge stands against the sky
SKY_BAND = (2, 30)              # the sight lines left of that edge that are taken for the sky beside it


def bearing(x, z):
    return math.degrees(math.atan2(z - EYE[2], EYE[0] - x))


def elevation(p):
    r = math.hypot(EYE[0] - p[0], p[2] - EYE[2])
    if r < TOL:
        return 90.0 if p[1] > EYE[1] + TOL else -90.0 if p[1] < EYE[1] - TOL else 0.0
    return math.degrees(math.atan2(p[1] - EYE[1], r))


def _wedge(a, b):
    """The two half-spaces n . p <= c of the bearings a .. b (degrees south of west, b - a < 180)."""
    sa, ca = math.sin(math.radians(a)), math.cos(math.radians(a))
    sb, cb = math.sin(math.radians(b)), math.cos(math.radians(b))
    return [((-sa, 0.0, -ca), -(EYE[0] * sa + EYE[2] * ca)),
            ((sb, 0.0, cb), EYE[0] * sb + EYE[2] * cb)]


WEDGE_A = _wedge(NORTH, SOUTH) + [((0.0, -1.0, 0.0), -EYE[1])]      # and not below the eye
WEDGE_B = _wedge(COMET_NORTH, NORTH)
_TRIPLES = {}


def corners(lo, hi, cut):
    """The corners of the box lo .. hi cut by the half-spaces `cut`: (k, 3), empty when nothing of
    the box is left. Every three of the planes are met; a meeting point that lies within all of
    them is a corner."""
    normals = [(-1.0, 0, 0), (1.0, 0, 0), (0, -1.0, 0), (0, 1.0, 0), (0, 0, -1.0), (0, 0, 1.0)]
    consts = [-lo[0], hi[0], -lo[1], hi[1], -lo[2], hi[2]]
    n = np.array(normals + [c[0] for c in cut], dtype=float)
    c = np.array(consts + [c[1] for c in cut], dtype=float)
    m = len(c)
    idx = _TRIPLES.get(m)
    if idx is None:
        idx = _TRIPLES[m] = np.array(list(combinations(range(m), 3)))
    a, rhs = n[idx], c[idx]
    det = np.linalg.det(a)
    ok = np.abs(det) > 1e-12
    if not ok.any():
        return np.zeros((0, 3))
    pts = np.linalg.solve(a[ok], rhs[ok][..., None])[..., 0]
    inside = np.all(pts @ n.T <= c[None, :] + TOL, axis=1)
    return pts[inside]


def measure(lo, hi):
    """One box against the two blocks. Returns a dict: in_a, in_b; a_low, the least elevation of
    the part of it in A's bearings above the eye (None when it has none); b_span, the least and
    the greatest elevation of the part in B's bearings; span, the bearings of its plan; above,
    does any of it stand above the eye's level."""
    out = dict(in_a=False, in_b=False, a_low=None, b_span=None, above=bool(hi[1] >= EYE[1] - TOL))
    plan = [(x, z) for x in (lo[0], hi[0]) for z in (lo[2], hi[2])]
    if lo[0] - TOL <= EYE[0] <= hi[0] + TOL and lo[2] - TOL <= EYE[2] <= hi[2] + TOL:
        out["span"] = (-180.0, 180.0)           # the box stands over or under the eye
    else:
        mid = bearing((lo[0] + hi[0]) / 2.0, (lo[2] + hi[2]) / 2.0)
        rel = [(bearing(x, z) - mid + 180.0) % 360.0 - 180.0 for x, z in plan]
        out["span"] = (mid + min(rel), mid + max(rel))
    if not out["above"]:
        return out
    pa = corners(lo, hi, WEDGE_A)
    if len(pa):
        up = [elevation(p) for p in pa]
        out["a_low"] = min(up)
        out["in_a"] = min(up) <= TOP + TOL
        out["a_at"] = [round(float(v), 3) for v in pa[int(np.argmin(up))]]
    pb = corners(lo, hi, WEDGE_B)
    if len(pb):
        up = [elevation(p) for p in pb]
        out["b_span"] = (min(up), max(up))
        out["in_b"] = min(up) <= TOP + TOL and max(up) >= COMET_LOW - TOL
    return out


def by_skeleton(lo, hi):
    """skeleton.in_v1_clear() at the box's corners and at the corners of what the two wedges leave
    of it: the skeleton's own answer, to hold against measure()'s."""
    pts = [np.array([x, y, z]) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
    pts += list(corners(lo, hi, WEDGE_A)) + list(corners(lo, hi, WEDGE_B))
    return any(S.in_v1_clear(*(float(v) for v in p)) for p in pts)


def part_of(cell):
    """Which part of the station a cell of site/cablecar belongs to."""
    x, y, z = cell
    if x > C.X1:
        return "trestle"
    wx0, wz0, wx1, wz1 = C.WAIT
    hx0, hz0, hx1, hz1 = C.WINCH
    cx0, cz0, cx1, cz1 = C.CANOPY
    if (x, z) == C.STACK["cell"] and y >= C.STACK["y"][0]:
        return "chimney"
    if y >= C.FEET and hx0 <= x <= hx1 and hz0 <= z <= hz1:
        return "winch house"
    if y >= C.FEET and wx0 <= x <= wx1 and wz0 <= z <= wz1:
        return "waiting room"
    if y >= C.EAVES and cx0 <= x <= cx1 and cz0 <= z <= C.GIRDER_Z:
        return "glass roof"
    if y >= C.FEET and (x, z) in C.COLUMNS:
        return "columns"
    if y >= C.FEET:
        return "rails, buffers"
    return "platform"


def _pack(scene=None):
    """The pack the boxes are read from. For the station alone the materials line's, with the
    models of the repainted blocks; for the test scene its whole pack as tools/check.py makes it,
    which holds the models of every line's display entities as well."""
    d = tempfile.mkdtemp(prefix="c164_clear_")
    if scene is None:
        M.write_pack(d, list((materials.models() or {}).values()))
        materials.pack(d)
    else:
        M.write_pack(d, list(scene.build_models().values()))
        scene.write_pack(d)
    return d


def _model(nbt):
    """What a display entity shows, in tools/sightline.py's words: its item model, the block of a
    block display; else its kind."""
    ref = ((nbt.get("item") or {}).get("components") or {}).get("minecraft:item_model")
    if ref:
        return f"model {ref}"
    if nbt.get("id") == "minecraft:block_display":
        return "block display " + str((nbt.get("block_state") or {}).get("Name", "")).split(":", 1)[-1]
    return str(nbt.get("id", "entity")).rpartition(":")[2].replace("_", " ")


def _stand(entity):
    """Where a display entity stands and what it shows: by this the station's own are told from
    those another package set in the same place."""
    x, y, z, nbt = entity
    return (round(float(x), 3), round(float(y), 3), round(float(z), 3), _model(nbt))


def station_cells(canvas=None):
    """{cell: state} of the station as its package builds it (on `canvas`, or on an empty one), the
    display entities it placed, and the canvas."""
    c = Canvas() if canvas is None else canvas
    before = len(c.entities)
    seen = dict(c.b)
    C.build(c, (0, 0, 0))
    return {p: s for p, s in c.b.items() if seen.get(p) != s}, c.entities[before:], c


def block_light(canvas):
    """{cell: level} round the station, from the sources that stand on `canvas`."""
    x0, z0, x1, z1 = S.CABLE_STATION
    return L.levels(canvas, (x0 - 2 * REACH, S.STATION_GROUND - 4, z0 - 2 * REACH),
                    (x1 + 2 * REACH, S.STATION_GROUND + 16, z1 + 2 * REACH))


def boxes_of(cells, entities, shapes, names, whose):
    """[(what, part, cell, lo, hi)] in scene coordinates: the boxes of the blocks `cells` (joined to
    their neighbours) and the boxes round the pieces of the display entities; and [(what, cell)] of
    the display entities that have no pieces to read, each taken as its cell and one cell round
    it. names(cell) and whose(entity) say which part a block and a display entity belong to."""
    cells = dict(cells)
    Shaper(cells, shapes.is_cube).run()
    out, unread = [], []
    for cell, state in sorted(cells.items()):
        base = np.array(cell, dtype=float)
        for lo, hi, _ in shapes.state(state)[1]:
            out.append((state.partition("[")[0], names(cell), cell, base + lo, base + hi))
    for entity in entities:
        x, y, z, nbt = entity
        cell = tuple(int(math.floor(v)) for v in (x, y, z))
        pieces = SL.entity_boxes(shapes, x, y, z, nbt)
        for inv, off, blo, bhi, _, label in pieces:
            world = (SL._corners(blo, bhi) - off) @ np.linalg.inv(inv).T
            out.append((label, whose(entity), cell, world.min(axis=0), world.max(axis=0)))
        if not pieces:
            base = np.array(cell, dtype=float)
            out.append((_model(nbt), whose(entity), cell, base - 1.0, base + 2.0))
            unread.append((_model(nbt), cell))
    return out, unread


def picture(cells, entities, shapes, names, whose, light=None):
    """How much of V1's picture the given blocks and display entities take, part by part, and
    where: sight lines through a grid over the picture, against these alone. With `light` ({cell:
    level}) also the block light on what each sight line meets: that of the cell the line is in
    when it arrives, which is the cell before a whole block's face and a thin block's own cell, as
    the game lights them. Per part: light, {level: share of the part's sight lines}."""
    lo = np.array([min(p[i] for p in cells) for i in range(3)]) - 1
    hi = np.array([max(p[i] for p in cells) for i in range(3)]) + 1
    lo, hi = np.minimum(lo, np.floor(EYE).astype(int) - 1), np.maximum(hi, np.floor(EYE).astype(int) + 1)
    bl = SL.Blockers(dict(cells), entities, shapes, lo, hi)
    shown = {(tuple(int(math.floor(v)) for v in e[:3]), _model(e[3])): whose(e) for e in entities}
    cam = SL.frame(EYE, S.V1["look_at"])
    w, h = GRID
    rays = SL.picture_rays(cam, FOV, ASPECT, w, h).reshape(-1, 3)
    got = bl.cast(EYE, rays, 400.0)
    first = np.minimum(got["t"], got["thru_t"])
    hit = np.isfinite(first)
    solid = got["t"] <= got["thru_t"]
    cell = np.where(solid[:, None], got["cell"], got["thru_cell"])
    box = np.where(solid, got["box"], got["thru_box"])
    rows, cols = np.divmod(np.arange(len(rays)), w)
    out = {"share": float(hit.mean()), "parts": {}}
    for i in np.nonzero(hit)[0]:
        at = tuple(int(v) for v in cell[i])
        name = names(at) if box[i] < 0 else shown.get((at, bl.labels[bl.boxes[box[i]]["what"]]), OTHERS)
        d = out["parts"].setdefault(name, dict(n=0, left=1.0, right=0.0, top=1.0, bottom=0.0, light={}))
        d["n"] += 1
        d["left"], d["right"] = min(d["left"], cols[i] / w), max(d["right"], (cols[i] + 1) / w)
        d["top"], d["bottom"] = min(d["top"], rows[i] / h), max(d["bottom"], (rows[i] + 1) / h)
        if light is not None:
            before = tuple(int(v) for v in np.floor(EYE + rays[i] * (first[i] - 1e-4)))
            level = int(light.get(before, 0))
            d["light"][level] = d["light"].get(level, 0) + 1
    for d in out["parts"].values():
        d["light"] = {k: v / float(d["n"]) for k, v in sorted(d["light"].items())}
        d["share"] = d.pop("n") / float(len(rays))
    return out


def _name(state):
    return state.partition("[")[0]


def tones(path, canvas, own, shapes):
    """The reviewer's figures for V1's right edge, read off a drawn picture of V1 (16:9, any size):
    the median brightness (Rec. 709 luma of the picture's own values, 0 .. 1) of the waiting room's
    wall, of its shut windows, of its roof and of the sky just left of it. What a pixel shows is
    told by a sight line through it against all that stands on `canvas`. The wall is the room's
    stone (its door and the dark light over it are left out); the sky is where the SKY_BAND sight
    lines left of the room meet nothing, in the rows SKY_ROWS. Returns {wall, blind, roof, sky:
    (median or None, sight lines)} and the picture's size."""
    from PIL import Image

    im = np.asarray(Image.open(path).convert("RGB"), dtype=float) / 255.0
    ph, pw = im.shape[:2]
    if abs(pw / float(ph) - ASPECT) > 0.01:
        sys.exit(f"{path}: {pw} x {ph} is not a picture of V1 (16:9)")
    luma = im @ np.array([0.2126, 0.7152, 0.0722])
    w, h = TONE_GRID
    pts = np.array(list(canvas.b), dtype=np.int64)
    lo = np.minimum(pts.min(axis=0), np.floor(EYE).astype(int)) - 1
    hi = np.maximum(pts.max(axis=0), np.floor(EYE).astype(int)) + 1
    bl = SL.Blockers(canvas.b, canvas.entities, shapes, lo, hi)
    rays = SL.picture_rays(SL.frame(EYE, S.V1["look_at"]), FOV, ASPECT, w, h).reshape(-1, 3)
    got = bl.cast(EYE, rays, 600.0)
    hit = np.isfinite(np.minimum(got["t"], got["thru_t"]))
    cell = np.where((got["t"] <= got["thru_t"])[:, None], got["cell"], got["thru_cell"])
    kinds = {_name(state): kind for kind, states in (("wall", (C.WALL, C.COURSE, C.CORBEL)),
                                                     ("roof", (C.ROOF, C.ROOF_FLAT)), ("blind", (C.SHUT,)))
             for state in states}
    wx0, wz0, wx1, wz1 = C.WAIT
    near = hit & (cell[:, 0] >= wx0) & (cell[:, 0] <= wx1) & (cell[:, 2] >= wz0) & (cell[:, 2] <= wz1)
    what = np.full(len(rays), "", dtype=object)
    for i in np.nonzero(near)[0]:
        p = tuple(int(v) for v in cell[i])
        state = own.get(p)
        if state is not None and canvas.b.get(p) == state and part_of(p) == FRAME:
            what[i] = kinds.get(_name(state), "other")
    what, hit = what.reshape(h, w), hit.reshape(h, w)
    rows = ((np.arange(h) + 0.5) * ph / h).astype(int)
    cols = ((np.arange(w) + 0.5) * pw / w).astype(int)
    seen = luma[np.ix_(rows, cols)]
    room = what != ""
    sky = np.zeros((h, w), dtype=bool)
    for j in range(int(SKY_ROWS[0] * h), int(SKY_ROWS[1] * h)):
        at = np.nonzero(room[j])[0]
        if len(at):
            sky[j, max(0, at[0] - SKY_BAND[1]):max(0, at[0] - SKY_BAND[0])] = True
    sky &= ~hit
    masks = (("wall", what == "wall"), ("blind", what == "blind"), ("roof", what == "roof"), ("sky", sky))
    return {k: (float(np.median(seen[m])) if m.any() else None, int(m.sum())) for k, m in masks}, (pw, ph)


def _deg(v):
    return "due west" if abs(v) < 0.005 else f"{abs(v):.2f} {'S' if v > 0 else 'N'}"


def main():
    ap = argparse.ArgumentParser(description="the cable station against the view it keeps clear of V1")
    ap.add_argument("--scene", action="store_true", help="build the whole test scene and measure all that "
                    "stands within the station's box and its reach")
    ap.add_argument("--json", help="write the figures here as well")
    ap.add_argument("--picture", help="a drawn picture of V1 (renders/obs_site_cablecar/v1.png): tell how bright "
                    "the waiting room and the sky beside it are in it")
    ap.add_argument("--jar", default=os.environ.get("MC_JAR") or os.path.join(
        os.environ.get("MC_ROOT", "/agent/realms-study"), "client26", "versions", "26.3", "26.3.jar"))
    args = ap.parse_args()

    scene = None
    if args.scene:
        from scenes import obs_site_cablecar as scene
    shapes = SL.Shapes(Assets(args.jar, packs=(_pack(scene),)))
    own, own_entities, alone = station_cells()
    mine = {_stand(e) for e in own_entities}
    whose = lambda e: (part_of(tuple(int(math.floor(v)) for v in e[:3]))            # noqa: E731
                       if _stand(e) in mine else OTHERS)
    if scene is not None:
        canvas = scene.build()
        x0, z0, x1, z1 = S.CABLE_STATION
        inside = lambda p: (x0 - REACH <= p[0] <= x1 + REACH and z0 - REACH <= p[2] <= z1 + REACH   # noqa: E731
                            and p[1] >= S.STATION_GROUND - 1)
        cells = {p: s for p, s in canvas.b.items() if inside(p) or p in own}
        entities = [e for e in canvas.entities if inside(tuple(int(math.floor(v)) for v in e[:3]))]
        names = lambda cell: part_of(cell) if cell in own else OTHERS               # noqa: E731
        title = f"the test scene, within {REACH} cells of the station's box: {len(cells)} cells, {len(entities)} display entities"
        altered = sorted((p, s, canvas.b.get(p)) for p, s in own.items() if canvas.b.get(p) != s)
    else:
        lights.build(alone, (0, 0, 0))          # the sources of the station's own windows
        canvas, cells, entities, names = alone, own, own_entities, part_of
        title = f"site/cablecar alone: {len(cells)} cells, {len(entities)} display entities"
        altered = None
    light = block_light(canvas)
    sources = sorted((p, int(s.partition("level=")[2].rstrip("]"))) for p, s in canvas.b.items()
                     if p in light and s.startswith(B.LIGHT + "["))

    rows, parts, hits, disagree = [], {}, [], []
    boxes, unread = boxes_of(cells, entities, shapes, names, whose)
    for what, part, cell, lo, hi in boxes:
        m = measure(lo, hi)
        rows.append((what, part, cell, lo, hi, m))
        d = parts.setdefault(part, dict(boxes=0, in_a=0, in_b=0, a_low=None, a_side=None, b_low=None, b_side=None))
        d["boxes"] += 1
        if m["in_a"] or m["in_b"]:
            hits.append((what, part, cell, lo, hi, m))
            d["in_a"] += m["in_a"]
            d["in_b"] += m["in_b"]
        if by_skeleton(lo, hi) and not (m["in_a"] or m["in_b"]):
            disagree.append((what, cell))
        if not m["above"]:
            continue
        s0, s1 = m["span"]
        if m["a_low"] is not None and (d["a_low"] is None or m["a_low"] < d["a_low"][0]):
            d["a_low"] = (m["a_low"], what, cell, m["a_at"])
        if m["a_low"] is None:      # beside A: how far in bearing
            gap = NORTH - s1 if s1 < NORTH else s0 - SOUTH
            if d["a_side"] is None or gap < d["a_side"][0]:
                d["a_side"] = (gap, "north" if s1 < NORTH else "south", what, cell)
        if m["b_span"] is not None:
            low, up = m["b_span"]
            gap = low - TOP if low > TOP else COMET_LOW - up        # over the block, or under it
            if d["b_low"] is None or gap < d["b_low"][0]:
                d["b_low"] = (gap, "over" if low > TOP else "under", what, cell)
        elif s1 < COMET_NORTH or s0 > NORTH:
            gap = COMET_NORTH - s1 if s1 < COMET_NORTH else s0 - NORTH
            if d["b_side"] is None or gap < d["b_side"][0]:
                d["b_side"] = (gap, "north" if s1 < COMET_NORTH else "south", what, cell)

    print(f"V1's eye ({EYE[0]:g}, {EYE[1]:g}, {EYE[2]:g}); {title}; {len(rows)} boxes")
    print(f"  A  between the two ends of the main building: {_deg(NORTH)} to {_deg(SOUTH)} of west, "
          f"from the eye's level to {TOP:g} degrees up")
    print(f"  B  where the comet hangs: {_deg(COMET_NORTH)} to {_deg(NORTH)} of west, {COMET_LOW:g} to {TOP:g} degrees up")
    for part, d in sorted(parts.items()):
        words = [f"{d['boxes']} boxes", f"{d['in_a']} in A", f"{d['in_b']} in B"]
        if d["a_low"]:
            up, what, cell, at = d["a_low"]
            words.append(f"in A's bearings from {up:.2f} degrees up ({what} {cell}, at {tuple(at)})")
        if d["a_side"]:
            gap, side, what, cell = d["a_side"]
            words.append(f"beside A {gap:.2f} degrees {side} of it ({what} {cell})")
        if d["b_low"]:
            gap, side, what, cell = d["b_low"]
            words.append(f"in B's bearings {gap:.2f} degrees {side} it ({what} {cell})")
        if d["b_side"]:
            gap, side, what, cell = d["b_side"]
            words.append(f"beside B {gap:.2f} degrees {side} of it ({what} {cell})")
        print(f"  {part:15s} " + "; ".join(words))
    for what, part, cell, lo, hi, m in hits[:40]:
        where = " and ".join(k for k, v in (("A", m["in_a"]), ("B", m["in_b"])) if v)
        print(f"  IN {where}: {what} at {cell} ({part}), box {tuple(round(float(v), 3) for v in lo)} .. "
              f"{tuple(round(float(v), 3) for v in hi)}")
    if len(hits) > 40:
        print(f"  ... and {len(hits) - 40} more")
    if disagree:
        print(f"  skeleton.in_v1_clear() names {len(disagree)} boxes this measure lets through: {disagree[:6]}")
    if unread:
        print(f"  {len(unread)} display entities have no pieces to read; each is measured as its cell and one cell "
              f"round it: " + ", ".join(f"{what} {cell}" for what, cell in unread[:8])
              + (" ..." if len(unread) > 8 else ""))
    seen = picture(cells, entities, shapes, names, whose, light)
    print(f"V1's picture: {100 * seen['share']:.1f}% of it is what was measured")
    for part, d in sorted(seen["parts"].items(), key=lambda kv: -kv[1]["share"]):
        levels = ", ".join(f"{k}: {100 * v:.0f}%" for k, v in d["light"].items())
        print(f"  {part:15s} {100 * d['share']:5.2f}%  across {100 * d['left']:.0f}..{100 * d['right']:.0f}%, "
              f"down {100 * d['top']:.0f}..{100 * d['bottom']:.0f}%; block light {levels}")
    print(f"  the light is that of {len(sources)} sources round the station: "
          + ", ".join(f"{n} at {p}" for p, n in sources[:12]) + (" ..." if len(sources) > 12 else ""))
    frame = max(seen["parts"].get(FRAME, {}).get("light", {0: 1.0}))
    print(f"frame light: {'within' if frame <= FRAME_LIGHT else 'OVER'} {FRAME_LIGHT} "
          f"(at most {frame} on what V1 sees of the {FRAME})")
    read = None
    if args.picture:
        got, size = tones(args.picture, canvas, own, shapes)
        wall, blind, sky = got["wall"][0], got["blind"][0], got["sky"][0]
        apart = None if wall is None or sky is None else wall - sky
        over = [words for bad, words in (
            (apart is not None and abs(apart) > TONES["apart"], "the wall is too far from the sky"),
            (wall is not None and wall > TONES["wall"], "the wall is too bright"),
            (blind is not None and blind < TONES["blind"], "the shut windows are too dark")) if bad]
        print(f"V1's right edge in {os.path.basename(args.picture)} ({size[0]} x {size[1]}), the picture's "
              f"brightness 0 .. 1, medians: "
              + ", ".join(f"{label} {'not seen' if got[k][0] is None else format(got[k][0], '.3f')}"
                          f" ({got[k][1]} sight lines)" for k, label in (
                              ("wall", "wall"), ("blind", "shut windows"), ("roof", "roof"), ("sky", "the sky beside it"))))
        print(f"frame tones: {'OVER, ' + ', '.join(over) if over else 'within'} (the wall against the sky "
              f"{'not read' if apart is None else format(apart, '+.3f')}, {TONES['apart']} either way; the wall at most "
              f"{TONES['wall']}; the shut windows at least {TONES['blind']})")
        read = dict(picture=os.path.basename(args.picture), size=list(size), within=not over,
                    **{k: dict(median=v[0], lines=v[1]) for k, v in got.items()})
    if altered is not None:
        print(f"the station's cells in the scene: {len(own) - len(altered)} of {len(own)} as its package sets them"
              + "".join(f"\n  {part_of(p)} {p}: {was.partition('[')[0]} is {str(now).partition('[')[0]}"
                        for p, was, now in altered[:20])
              + (f"\n  ... and {len(altered) - 20} more" if len(altered) > 20 else ""))
    verdict = "CLEAR" if not hits and not disagree else "NOT CLEAR"
    print(f"result: {verdict} ({len(hits)} boxes in the view the station keeps clear)")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"eye": list(EYE), "what": title, "result": verdict, "boxes": len(rows),
                       "in": [dict(what=w, part=p, cell=list(c), a=bool(m["in_a"]), b=bool(m["in_b"]))
                              for w, p, c, _, _, m in hits],
                       "parts": {k: {kk: (list(vv) if isinstance(vv, tuple) else vv) for kk, vv in d.items()}
                                 for k, d in parts.items()},
                       "picture": seen, "frame_light": frame, "tones": read,
                       "unread": [dict(what=w, cell=list(c)) for w, c in unread],
                       "altered": None if altered is None else [dict(cell=list(p), set=was, stands=now)
                                                                for p, was, now in altered],
                       "sources": [dict(cell=list(p), level=n) for p, n in sources]}, fh, indent=1, default=str)
    sys.exit(0 if verdict == "CLEAR" else 1)


if __name__ == "__main__":
    main()
