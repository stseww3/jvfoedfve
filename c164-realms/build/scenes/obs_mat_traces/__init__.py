"""Traces: every kind on the large materials, as decals and worked into pictures.

The sample card of materials/traces (plan/parts/materials.md, section 2 F), and the place where it
is shown that a display entity's plate with a half clear ink is drawn over a wall as a stain.

Six bays stand in a row from the west, each a wall four blocks wide and four high with the floor
that goes with it: fine stone, rough stone, tuff brick, slate brick, iron plate, dark wood. Every
bay carries the same decals at the same places (T.decal), so the kinds can be told from bay to bay:

    on the wall   water and rust hang from its head (left, and beside it); soot rises in the
                  middle; a crack and a chalk mark on the right; a rubbed patch and a blot of oil
                  below them; damp along the foot, four decals side by side that join
    on the floor  oil, coal dust and a worn patch near the wall; a crack, a chalk mark and more
                  coal a step out

East of the bays, on a wall of smooth slate, the swatches: plates of twelve pixels whose own
picture carries the trace (T.stain, T.worn; no entity is spent on the trace). One row to a
material, from the top iron, brass, dark wood, stone, verdigris, porcelain; in every row, from the
west, the plain plate, then water, rust, soot, damp, oil, coal, crack, chalk, worn about the
middle, worn along the edges.

    python -m scenes.obs_mat_traces      writes shots.json
"""
from artkit import models as M
from artkit.blocks import st
from artkit.canvas import Canvas

from scenes.obs import sky
from scenes.obs.common import blocks as B
from scenes.obs.common import palette as P
from scenes.obs.materials import _kit as K
from scenes.obs.materials import traces as T

BIOME = "obs_blue"
TIME = 14000                    # light version A
VERSIONS = {}

PREFIX = "mat_trace_swatch_"
BAYS = (("fine", B.ASHLAR_FINE.block, B.SLATE_SMOOTH.block),
        ("rough", B.ASHLAR_ROUGH.block, B.SLATE_SMOOTH.block),
        ("tuff", B.TUFF_BRICK.block, B.TUFF_SMOOTH.block),
        ("slate", B.SLATE_BRICK.block, B.SLATE_TILE.block),
        ("iron", B.IRON_PLATE, B.IRON_RIVETED.block),
        ("wood", B.DARK_WOOD.block, B.FLOOR_WOOD.block))
BAY = 5                         # blocks from one bay to the next
WIDE, HIGH = 4, 4               # a bay's wall
FACE = -2.0                     # the walls stand in z -3; their faces look south from here
DEPTH = 7                       # the floor runs this far south of the walls
LAMP = 13                       # invisible lights before the walls, so the night does not hide the card

MATS = (("iron", P.mat("iron")), ("brass", P.mat("brass")), ("wood", P.mat("dark_wood")),
        ("stone", P.mat("ashlar")), ("verdigris", P.mat("verdigris")), ("porcelain", P.mat("porcelain")))
COLUMNS = ("plain",) + T.KINDS + ("edges",)
PITCH = 0.9                     # blocks from one swatch to the next
SWATCH = 12                     # pixels square
SWATCH_X = BAY * len(BAYS) + 1  # where the swatch wall begins
SWATCH_WIDE = int(PITCH * len(COLUMNS)) + 1
SWATCH_HIGH = int(PITCH * len(MATS)) + 1


def _swatch(mat_name, mat, column):
    m = M.Model(f"{PREFIX}{mat_name}_{column}")
    if column == "plain":
        face = mat
    elif column == "edges":
        face = T.worn(mat)
    elif column == "worn":
        face = T.worn(mat, "middle", look=1)
    else:
        face = T.stain(mat, column, look=COLUMNS.index(column) % T.LOOKS)
    m.box((-SWATCH / 2.0, -SWATCH / 2.0, 0), (SWATCH / 2.0, SWATCH / 2.0, 2), mat, faces={"s": face}, seed=1)
    return m


def build_models():
    models = dict(T.models())
    for mat_name, mat in MATS:
        for column in COLUMNS:
            m = _swatch(mat_name, mat, column)
            models[m.name] = m
    return models


def _bay(c, x0, look):
    """The decals of one bay, the same in every bay but for the drawing of each kind."""
    n = 0
    top = float(HIGH)
    n += T.decal(c, (x0 + 0.5, top, FACE), "south", "water", look=look)
    n += T.decal(c, (x0 + 1.5, top, FACE), "south", "rust", look=look)
    n += T.decal(c, (x0 + 2.5, 2.25, FACE), "south", "soot", look=look)
    n += T.decal(c, (x0 + 3.5, 3.4, FACE), "south", "crack", look=look)
    n += T.decal(c, (x0 + 3.5, 2.3, FACE), "south", "chalk", look=look)
    n += T.decal(c, (x0 + 1.0, 1.6, FACE), "south", "worn", look=look)
    n += T.decal(c, (x0 + 2.5, 1.4, FACE), "south", "oil", look=look)
    for k in range(WIDE):
        n += T.decal(c, (x0 + k + 0.5, 0.0, FACE), "south", "damp", look=(look + k) % T.LOOKS)
    n += T.decal(c, (x0 + 0.6, 0.0, -1.2), "up", "oil", look=look)
    n += T.decal(c, (x0 + 1.8, 0.0, -1.2), "up", "coal", look=look)
    n += T.decal(c, (x0 + 3.0, 0.0, -1.2), "up", "worn", look=look)
    n += T.decal(c, (x0 + 1.0, 0.0, 0.0), "up", "crack", look=look)
    n += T.decal(c, (x0 + 2.4, 0.0, 0.0), "up", "chalk", look=look)
    n += T.decal(c, (x0 + 3.4, 0.0, 0.2), "up", "coal", look=(look + 2) % T.LOOKS, turn=90.0)
    return n


def _swatch_at(row, column):
    return (SWATCH_X + 0.6 + PITCH * column, SWATCH_HIGH - 0.55 - PITCH * row, FACE)


def build():
    c = Canvas()
    east = SWATCH_X + SWATCH_WIDE
    c.box(-2, -1, -3, east + 1, -1, DEPTH, B.SLATE_SMOOTH.block)
    n = 0
    for i, (_name, wall, floor) in enumerate(BAYS):
        x0 = BAY * i
        c.box(x0, 0, -3, x0 + WIDE - 1, HIGH - 1, -3, wall)
        c.box(x0, -1, -2, x0 + WIDE - 1, -1, 1, floor)
        n += _bay(c, x0, i % T.LOOKS)
    c.box(SWATCH_X, 0, -3, east, SWATCH_HIGH, -3, B.SLATE_SMOOTH.block)
    models = build_models()
    for row, (mat_name, _mat) in enumerate(MATS):
        for column, name in enumerate(COLUMNS):
            x, y, z = _swatch_at(row, column)
            c.add_entity(x, y, z + 0.01, M.display(models[f"{PREFIX}{mat_name}_{name}"], view=M.NEAR))
            n += 1
    for x in range(0, east + 1, 3):
        c.set(x, 3, 1, st(B.LIGHT, level=LAMP))
        c.set(x, 1, 3, st(B.LIGHT, level=LAMP))
    sky.build(c, (0, 0, 0))
    c.entity_counts = {"materials": n}
    return c


def write_pack(pack_dir):
    return list(K.pack_with(pack_dir, **VERSIONS) or []) + list(sky.pack(pack_dir) or [])


def shots():
    out = []

    def shot(name, pos, look_at):
        out.append({"name": name, "pos": [round(v, 2) for v in pos], "look_at": [round(v, 2) for v in look_at],
                    "time": TIME})

    for half, first in (("west", 0), ("east", 3)):
        mid = BAY * first + (BAY * 2 + WIDE) / 2.0
        shot(f"bays_{half}", (mid, 2.6, 6.8), (mid, 1.7, FACE))
    for i, (name, _wall, _floor) in enumerate(BAYS):
        x = BAY * i + WIDE / 2.0
        shot(f"bay_{name}", (x, 2.2, 2.4), (x, 1.9, FACE))
    for name in ("fine", "iron"):
        x = BAY * [b[0] for b in BAYS].index(name)
        shot(f"near_{name}", (x + 1.2, 3.0, 0.3), (x + 1.2, 3.1, FACE))
        shot(f"foot_{name}", (x + 2.0, 1.5, 0.6), (x + 2.0, 0.3, FACE))
    for name in ("fine", "tuff", "wood"):
        x = BAY * [b[0] for b in BAYS].index(name) + WIDE / 2.0
        shot(f"floor_{name}", (x, 2.3, 1.7), (x, 0.0, -0.8))
    mid = SWATCH_X + SWATCH_WIDE / 2.0
    shot("swatches", (mid, SWATCH_HIGH / 2.0, 4.6), (mid, SWATCH_HIGH / 2.0, FACE))
    shot("swatches_near", (SWATCH_X + 2.6, SWATCH_HIGH - 1.2, 0.6), (SWATCH_X + 2.6, SWATCH_HIGH - 1.4, FACE))
    return out
