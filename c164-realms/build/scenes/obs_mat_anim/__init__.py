"""Moving pictures: the proof that they run in the game, and three samples to copy from.

A picture can change with time without a command and without an entity: its frames are stacked in
one file and a .mcmeta beside it tells the game how long each is shown (plan/parts/materials.md,
section 2 D). For a block's picture that is known to work (the panels do it). This scene is where
it is shown for the sheet of a display entity's model, which artkit.models writes since 11-16 when
a face of the model has a material of pixelart.Frames.

On a slate floor before a wall of fine stone, from the west, each at eye height:

    card    a plate with a test card: eight cells in a row, and in every frame another one is lit
            (eight frames of ten ticks, so the light takes four seconds to cross the plate)
    still   the same plate with the first frame only: what the offline pictures show of `card`
    panel   a block whose picture moves (the oscilloscope panel of materials/panels): the case that
            is known to work, to tell "nothing moves in this client" from "models do not move"
    oil     an oil lamp: the flame in its chimney (pixelart.flame)
    gas     a gas burner: the flat fishtail flame (pixelart.flame, fan=True)
    fire    a fire door ajar: the bed of coal behind it (pixelart.shimmer over a drawn picture)

The shots `proof_0` to `proof_5` are one camera six times. In the game they are taken one after
the other, a second or more apart: when the sheets move, the lit cell of `card` stands in different
places in them and the flames differ, while `still` is the same in all six. The offline renderer
draws the first frame, so there all six are alike. `near_*` are the samples one by one.

    python -m scenes.obs_mat_anim      writes shots.json
"""
import numpy as np

from artkit import models as M
from artkit import pixelart as PX
from artkit.blocks import st
from artkit.canvas import Canvas

from scenes.obs import sky
from scenes.obs.common import blocks as B
from scenes.obs.common import palette as P
from scenes.obs.materials import _kit as K

BIOME = "obs_blue"
TIME = 14000                    # light version A
VERSIONS = {}

FLOOR = B.SLATE_SMOOTH.block
WALL = B.ASHLAR_FINE.block
PREFIX = "mat_anim_"
STEP = 3                        # blocks from one thing to the next
ORDER = ("card", "still", "panel", "oil", "gas", "fire")
EYE = 1.5                       # the height of each thing's middle above the floor
LAMP = 12                       # an invisible light before the wall, so the stills are not black

GLOW = [P.colour("glow", n) for n in range(len(P.RAMPS["glow"]))]
IRON = P.mat("iron")
BRASS = P.mat("brass")
DARK = P.colour("iron", 0)

CELLS = 8                       # the test card's cells, one lit in each frame
CARD_TICKS = 10


def _card_frame(lit):
    """The test card, 32 by 8 pixels: eight cells of dark iron in a brass line, one of them lit."""
    px = np.zeros((8, 4 * CELLS, 4), dtype=np.uint8)
    px[..., :3] = P.colour("brass", 2)
    px[..., 3] = 255
    for n in range(CELLS):
        px[1:7, 4 * n + 1:4 * n + 4, :3] = GLOW[3] if n == lit else DARK
    return px


def _card(name, moving):
    m = M.Model(PREFIX + name)
    frames = [PX.Picture(f"{PREFIX}{name}_{n}", _card_frame(n)) for n in range(CELLS)]
    face = PX.Frames(PREFIX + name + "_face", frames, frametime=CARD_TICKS) if moving else frames[0]
    m.box((-16, -4, 0), (16, 4, 1), IRON, faces={"s": face}, emit=15, shade=False)
    return m


def _oil():
    """An oil lamp: a brass font, the burner, the flame, a glass chimney drawn as four thin posts."""
    m = M.Model(PREFIX + "oil")
    m.tube("y", (0, 0), -8, -4, 3.0, BRASS, sides=8)
    m.tube("y", (0, 0), -4, -2, 1.5, BRASS, sides=8)
    flame = PX.flame(PREFIX + "oil_flame", GLOW[1:4], 5, 9, frames=8, frametime=2, seed=1)
    for turn in (0.0, 90.0):        # two crossed plates, so the flame shows from every side
        with m.turned(("y", turn)):
            m.box((-2.5, -2, 0), (2.5, 7, 0), IRON, faces={"s": flame, "n": flame}, skip="ewud", emit=15, shade=False)
    return m


def _gas():
    """A gas burner: an iron pipe, the brass tip, the fishtail flame across the line of sight."""
    m = M.Model(PREFIX + "gas")
    m.tube("y", (0, 0), -8, -3, 1.0, IRON, sides=8)
    m.tube("y", (0, 0), -3, -2, 1.5, BRASS, sides=8)
    flame = PX.flame(PREFIX + "gas_flame", GLOW[1:4], 9, 7, frames=8, frametime=2, seed=2, fan=True)
    m.box((-4.5, -2, 0), (4.5, 5, 0), IRON, faces={"s": flame, "n": flame}, skip="ewud", emit=15, shade=False)
    return m


_COALS = (
    "kkkkkkkkkkkk",
    "kk11111111kk",
    "k1122222211k",
    "k1223333221k",
    "k1233443321k",
    "k1223333221k",
    "k1122122211k",
    "kk12k11k21kk",
    "kkkkkkkkkkkk",
)


def _coals():
    """A bed of coal seen through a fire door: soot round it, the glare in the middle."""
    tone = {"k": DARK, "1": GLOW[0], "2": GLOW[1], "3": GLOW[2], "4": GLOW[3]}
    px = np.zeros((len(_COALS), len(_COALS[0]), 4), dtype=np.uint8)
    for y, row in enumerate(_COALS):
        for x, ch in enumerate(row):
            px[y, x, :3] = tone[ch]
            px[y, x, 3] = 255
    return px


def _fire():
    """A fire door's frame of cast iron and, a little behind it, the coals."""
    m = M.Model(PREFIX + "fire")
    m.box((-8, -6.5, -1), (8, 6.5, 0), IRON)
    coals = PX.shimmer(PREFIX + "fire_coals", _coals(), GLOW[:4], frames=6, frametime=4, share=0.35, seed=4)
    m.box((-6, -4.5, 0), (6, 4.5, 0.25), IRON, faces={"s": coals}, emit=15, shade=False)
    return m


def build_models():
    models = [_card("card", True), _card("still", False), _oil(), _gas(), _fire()]
    return {m.name: m for m in models}


def _x(name):
    return STEP * ORDER.index(name) + 1.5


def build():
    c = Canvas()
    length = STEP * len(ORDER)
    c.box(-2, -1, -3, length + 1, -1, 8, FLOOR)
    c.box(-2, 0, -3, length + 1, 3, -3, WALL)
    models = build_models()
    n = 0
    for name in ORDER:
        x = _x(name)
        if name == "panel":
            c.set(int(x), 1, -2, st(B.PANELS["scope"], facing="south"))
            c.set(int(x), 0, -2, WALL)
            continue
        c.add_entity(x, EYE, -1.5, M.display(models[PREFIX + name], scale=1.0, brightness=(15, 15)))
        n += 1
    for name in ORDER[::2]:
        c.set(int(_x(name)) + 1, 2, 1, st(B.LIGHT, level=LAMP))
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

    mid = STEP * len(ORDER) / 2.0
    for k in range(6):
        shot(f"proof_{k}", (mid, 2.2, 9.5), (mid, 1.4, -1.5))
    for name in ORDER:
        shot(f"near_{name}", (_x(name), 1.7, 1.6), (_x(name), EYE, -1.5))
    return out
