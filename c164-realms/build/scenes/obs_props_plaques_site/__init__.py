"""Test scene of props/plaques for the site: the master scene as it stands in this tree, with the
plaques hung (plaques.dress) whatever the master scene's switch GUIDE says.

Every line is built whole, in the master scene's order. A plaque hangs only where the cell behind
its middle stands (plaques.site): what was left out is listed by
python -m scenes.obs_props_plaques_site --report  (a node's job: it builds the master scene),
with the plaques that hang in the open air before a camera of the board, nearer than the
distance they are drawn from.

One camera a plaque, 2.6 blocks before it at the height of the eye (HOW: nearer where the room
is shallower, higher where the plaque hangs low): where the real client's picture of its words
is taken from. The offline renderer draws no text display, so the kept pictures show the wall
the plaque hangs on and what stands round it.
"""
import importlib
import math

from artkit.canvas import Canvas

from scenes import obs
from scenes.obs.common import skeleton as S
from scenes.obs.props import _kit as K
from scenes.obs.props import plaques

BIOME = obs.BIOME
BIOME_MARGIN = obs.BIOME_MARGIN
BIOME_MARGIN_Y = obs.BIOME_MARGIN_Y

build_models = obs.build_models
write_pack = obs.write_pack

TIME = 14000
BEFORE = 2.6                    # blocks from a plaque to the camera that reads it
OVER = 0.1                      # and the camera over the plaque's middle: the eye, where a plaque hangs 1.5 over the floor
# (blocks before, over the middle) where that does not do: the vault's aisle before its plaque is
# two cells deep; the clock's hangs on the plinth, half a block over the floor
HOW = {"plate_vault": (1.7, 0.37), "master_clock": (BEFORE, 1.12)}
THIN = ("pressure_plate", "carpet", "rail", "trapdoor")    # a block of these lies on the floor: who stands on it stands in its cell
CLEAR = ("glass", "pane", "bars", "fence", "chain", "rail", "ladder")  # and these do not hide what is behind them
BOARD = [name for name in (f"V{i}" for i in range(1, 13)) if hasattr(S, name)]
REACH = plaques.VIEW * 64.0     # blocks a plaque is drawn from, at the game's own entity distance


def build():
    c = Canvas()
    plaques.dress(c)
    counts = {}
    for name in obs.LINES:
        line = importlib.import_module(f"scenes.obs.{name}")
        counts[name] = int(line.build(c, obs.ORIGIN) or 0)
    c.entity_counts = counts
    return c


def _yaw(spec):
    return K.FACING[spec.get("facing", "south")] if spec.get("yaw") is None else float(spec["yaw"])


def shots():
    """A camera before every plaque of the tables; the arrival view alone while there is none."""
    out = []
    for key, spec in plaques.site_plaques().items():
        x, y, z = spec["pos"]
        before, over = HOW.get(key, (BEFORE, OVER))
        dx, _, dz = K.turn(_yaw(spec), (0.3, 0.0, before))
        out.append({"name": key, "pos": [round(x + dx, 2), round(y + over, 2), round(z + dz, 2)],
                    "look_at": [round(float(x), 2), round(float(y), 2), round(float(z), 2)], "time": TIME})
    if not out:
        out.append({"name": "v1", "pos": list(S.V1["pos"]), "look_at": list(S.V1["look_at"]), "time": TIME})
    return out


def _cell(point, yaw, off):
    """The cell `off` (across, up, out of the wall) from a point, as the plaque is turned."""
    dx, dy, dz = K.turn(yaw, off)
    return (math.floor(point[0] + dx), math.floor(point[1] + dy), math.floor(point[2] + dz))


def _what(c, x, y, z):
    """The name of what stands in a cell, "" for air and for a light block."""
    name = (c.name(x, y, z) or "").split(":")[-1]
    return "" if name in ("air", "cave_air", "light") else name


def _stops(c, x, y, z):
    """Whether a walker cannot be in this cell: something stands in it that is not laid on the floor."""
    name = _what(c, x, y, z)
    return bool(name) and not any(word in name for word in THIN)


def _seen(c, eye, point):
    """Whether no block stands between an eye and a point. The line is walked a tenth of a block at
    a time; what is laid on the floor (THIN) and what one sees through (CLEAR) hides nothing, and
    neither does a model: this errs towards seen."""
    to = [p - e for p, e in zip(point, eye)]
    far = math.sqrt(sum(v * v for v in to))
    first = tuple(math.floor(v) for v in eye)
    for i in range(1, int(far / 0.1)):
        at = tuple(math.floor(e + d * (i * 0.1 / far)) for e, d in zip(eye, to))
        name = _what(c, *at)
        if at != first and name and not any(word in name for word in THIN + CLEAR):
            return False
    return True


def faults(c):
    """What is wrong with where the plaques hang on the canvas of build(), [(key, words)]: a corner
    of the plate with nothing behind it or inside a block, no place to stand and read it in the
    three cells before it, its middle far from the reader's eye, more than one other plaque seen
    from where it is read. A plaque with nothing behind its middle does not hang at all and is not
    looked at."""
    table = plaques.site_plaques()
    left = set(getattr(c, "plaques_left_out", []))
    inset = 0.02                                            # a corner on the edge of a cell belongs to the plate's side of it
    out = []
    for key, spec in table.items():
        if key in left:
            continue
        yaw, pos = _yaw(spec), spec["pos"]
        bare, sunk = [], []
        for across in (-1.0, 1.0):
            for up in (-1.0, 1.0):
                at = (across * (plaques.WIDE / 2.0 - inset), up * (plaques.HIGH / 2.0 - inset))
                behind, before = _cell(pos, yaw, (at[0], at[1], -0.25)), _cell(pos, yaw, (at[0], at[1], 0.25))
                if not c.has(*behind) and behind not in bare:
                    bare.append(behind)
                if c.has(*before) and before not in sunk:
                    sunk.append(before)
        if bare:
            out.append((key, f"the plate hangs over the edge of what it hangs on: nothing stands at {bare}"))
        if sunk:
            out.append((key, f"the plate is inside a block: {[(cell, c.get(*cell)) for cell in sunk]}"))
        stands = []                                         # (blocks before the plaque, the y the feet are at)
        for far in (0.5, 1.5, 2.5):                         # the three cells before the wall
            x, _, z = _cell(pos, yaw, (0.0, 0.0, far))
            for feet in range(math.floor(pos[1]) + 1, math.floor(pos[1]) - 4, -1):
                if _stops(c, x, feet - 1, z) and not _stops(c, x, feet, z) and not _stops(c, x, feet + 1, z):
                    stands.append((far, feet))
                    break
        if not stands:
            out.append((key, "nobody can stand and read it: no floor with two cells of air in the three cells before it"))
            eye = tuple(p + d for p, d in zip(pos, K.turn(yaw, (0.0, OVER, BEFORE))))
        else:
            far, feet = min(stands, key=lambda s: (abs(s[1] + S.EYE - pos[1]), -s[0]))
            off = abs(feet + S.EYE - pos[1])
            if off > 0.75:
                out.append((key, f"its middle is {off:.2f} from the eye of who stands before it "
                                 f"(feet at y {sorted({feet for _, feet in stands})})"))
            eye = tuple(p + d for p, d in zip(pos, K.turn(yaw, (0.0, feet + S.EYE - pos[1], far))))
        others = []
        for other, o in table.items():
            if other == key or other in left:
                continue
            front = K.turn(_yaw(o), (0.0, 0.0, 1.0))
            to = tuple(a - b for a, b in zip(eye, o["pos"]))
            near = math.sqrt(sum(v * v for v in to))
            if near < 64.0 * o.get("view", plaques.VIEW) and sum(a * b for a, b in zip(to, front)) > 0.0 \
                    and _seen(c, eye, tuple(p + 0.05 * f for p, f in zip(o["pos"], front))):
                others.append(f"{other} ({near:.1f} blocks)")
        if len(others) > 1:
            out.append((key, f"who reads it sees {len(others)} more plaques by turning his head: {', '.join(others)}"))
    return out


def in_board():
    """The plaques a camera of the board could show: [(key, view, blocks from the camera)] for every
    plaque nearer to a locked camera than it is drawn from, on the side it is read from."""
    out = []
    for key, spec in plaques.site_plaques().items():
        reach = 64.0 * spec.get("view", plaques.VIEW)
        front = K.turn(_yaw(spec), (0.0, 0.0, 1.0))
        for view in BOARD:
            eye = getattr(S, view)["pos"]
            to = tuple(e - p for e, p in zip(eye, spec["pos"]))
            far = math.sqrt(sum(v * v for v in to))
            if far < reach and sum(a * b for a, b in zip(to, front)) > 0.0:
                out.append((key, view, far))
    return out
