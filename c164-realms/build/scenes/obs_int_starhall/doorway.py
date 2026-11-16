"""The first look through the open door, in numbers (A0 #83714, review #83800 and #85249, cr3
#87129): what the board's picture from the forecourt (V4) and the hall's own (V7) read in the boxes
the reviewers measure, with the hall's lamps as they are and with other levels beside them.
No picture is written: the two frames are traced in memory and only the boxes are read.

    env PYTHONPATH=build python -m scenes.obs_int_starhall.doorway [variant ...]      (from c164-realms/, on a worker node)

A variant is a comma separated list of the levels it sets, name=level; "now" (or nothing) is the
hall as it is delivered. Names:

  foot    starhall.STAIR_FOOT_LEVEL       the two lamps at the foot of the flights
  under   _starhall_ways.CORNER_UNDER     the sources before the first steps are this far under them
  east    _starhall_ways.DOOR_EAST_LEVEL  the floor's pair nearer the door (0: none)
  west    _starhall_ways.DOOR_WEST_LEVEL  the floor's pair nearer the arcade
  pier    _starhall_ways.PIER_SIDE_LEVEL  the pair beside the clock's dial
  upper   _starhall_ways.PIER_UPPER_LEVEL the pair two rows over it
  pool    starhall.SUN_POOL               the source over the roundel's middle

    ... doorway now foot=11,under=5,east=0,west=0,pier=0        the delivered hall beside the hall of the 12:00 save

The boxes are the reviewers', on a picture of 1280 by 720; a box reads the median of the Rec. 601
luma, and "warm" is the median of red less the median of blue (sky/_tones.py reads the same way).
The lines are at the end of each variant: what holds and what does not.
"""
import atexit
import importlib
import shutil
import sys
import tempfile
import time

import numpy as np

import makepack
import render as RD                 # build/render.py: the game's timelines, the jar's place, the hour of look A
from artkit import gamelook, gamescene, water
from artkit.gameassets import Assets

from scenes.obs.common import skeleton as S
from scenes.obs.interiors import _starhall_ways as W
from scenes.obs.interiors import starhall
from scenes.obs.sky import _lightkit as L
from scenes.obs.sky import lights

SCENE = "scenes.obs_int_starhall"
SIZE = (1280, 720)
FOV = 77.0                          # what tools/shoot.py gets
V4 = {"pos": (27.5, 1.62, 3.5), "look_at": (17.5, 4.5, 0.5)}        # tools/boardshots.py: the entrance from the forecourt

NAMES = {"foot": (starhall, "STAIR_FOOT_LEVEL"), "pool": (starhall, "SUN_POOL"), "under": (W, "CORNER_UNDER"),
         "east": (W, "DOOR_EAST_LEVEL"), "west": (W, "DOOR_WEST_LEVEL"), "pier": (W, "PIER_SIDE_LEVEL"),
         "upper": (W, "PIER_UPPER_LEVEL")}

# (x0, y0, x1, y1), the far edges left out
V4_BOXES = (("half", (602, 394, 640, 545)), ("over", (602, 406, 640, 425)), ("flight", (602, 425, 640, 510)),
            ("floor", (602, 510, 640, 545)), ("paving", (600, 566, 690, 600)))
V7_BOXES = (("pier N", (676, 450, 692, 580)), ("pier S", (588, 450, 606, 580)), ("over clock", (600, 340, 670, 420)),
            ("dial", (626, 452, 654, 480)), ("arch N", (700, 470, 780, 600)), ("arch S", (500, 470, 580, 600)),
            ("lining L", (0, 125, 150, 562)), ("lining R", (1125, 125, 1280, 562)), ("foot", (560, 650, 720, 700)),
            ("globe", (440, 590, 495, 635)), ("board", (795, 515, 870, 665)))

# the rows of the half, from its top: the girder, the arch's crown, under the crown, the flight's steps 5 to 3, 2 and 1,
# the first step, the floor before the flight, the roundel, the floor inside the door
ROWS = (394, 406, 416, 425, 447, 478, 496, 510, 524, 540, 545)

HALF, WARM = 0.22, 0.03             # the board's picture: the half of the doorway, and how much redder than blue
PIER = (0.255, 0.26)                # the hall's picture: the pier's face beside the clock
ARCH, ALIKE = 0.235, 0.02           # the flights behind the side arches, and how far the two may differ
LINING = 0.12

# cells whose block light is told: the pier's outer columns before its face, the doorway's linings,
# the cells before the risers of the north flight's first five steps and of the south flight's
CELLS = (
    ("pier N y2..5", [(6, y, -1) for y in range(2, 6)]), ("pier S", [(6, y, 1) for y in range(2, 6)]),
    ("lining", [(16, 1, -1), (17, 1, -1), (16, 1, 1), (17, 1, 1)]),
    ("risers N 0..4", [(2 - i, i, -4) for i in range(5)]), ("risers S", [(2 - i, i, 4) for i in range(5)]),
    ("floor x14..7", [(14, 0, 0), (13, 0, -1), (12, 0, -1), (10, 0, -1), (9, 0, -1), (8, 0, -3), (7, 0, -2)]),
    ("middle", [(11, 1, 0), (12, 0, 0)]),
)


def read(img, box):
    """(median luma, median red less median blue) of a box of an 8-bit picture."""
    x0, y0, x1, y1 = box
    part = img[y0:y1, x0:x1].astype(np.float64) / 255.0
    luma = 0.299 * part[..., 0] + 0.587 * part[..., 1] + 0.114 * part[..., 2]
    return float(np.median(luma)), float(np.median(part[..., 0]) - np.median(part[..., 2]))


def variant(text):
    """{name: level} of one argument."""
    out = {}
    if text in ("", "now"):
        return out
    for item in text.split(","):
        name, _, value = item.partition("=")
        if name not in NAMES:
            raise SystemExit(f"{name!r}: a variant sets {', '.join(sorted(NAMES))}")
        out[name] = int(value)
    return out


class Hall:
    """The game's files, read once; a variant is built, lit and traced on them."""

    def __init__(self):
        self.scene = importlib.import_module(SCENE)
        pack = tempfile.mkdtemp(prefix="c164pack-")
        atexit.register(shutil.rmtree, pack, ignore_errors=True)
        makepack.write(SCENE.split(".", 1)[1], pack)
        self.assets = Assets(RD.ROOT + "/client26/versions/26.3/26.3.jar", [pack])
        mood = importlib.import_module(SCENE + ".mood")
        biome = mood.BIOMES[getattr(self.scene, "BIOME", sorted(mood.BIOMES)[0])]
        dimension = self.assets.json(f"{RD.DATA}dimension_type/overworld.json")
        lines = RD.timelines(self.assets) + [mood.TIMELINES[k] for k in sorted(getattr(mood, "TIMELINES", {}))]
        self.look = lambda tick: gamelook.Look(tick, dimension, biome, lines)

    def frames(self, canvas):
        """The two pictures as render.py would draw them, kept in memory."""
        cells = dict(canvas.b)
        floor = min(k[1] for k in cells) - 1

        class _Canvas:
            b = cells

        flow = water.run(_Canvas, floor)
        for cell, amount in flow.w.items():
            cells[cell] = "water[level=8]" if amount == water.FALLING else f"water[level={8 - amount}]"
        for cell in flow.src:
            cells.setdefault(cell, "water")
        world = gamescene.Scene(self.assets, cells, canvas.entities, self.look(6000), place=[0, 200, 0])
        out = []
        for shot in (V4, S.V7):
            cam = world.camera(shot["pos"], shot["look_at"], 0.0, 0.0, FOV)
            out.append(world.picture(self.look(RD.DEFAULT_TIME), cam, SIZE, 1, FOV))
        return out


def measure(hall, levels):
    """Build the hall with these levels and say what the boxes read; returns the lines that fail."""
    t0 = time.time()
    kept = {name: getattr(*NAMES[name]) for name in levels}
    for name, level in levels.items():
        setattr(*NAMES[name], level)
    try:
        canvas = hall.scene.build()
        said = (f"foot {starhall.STAIR_FOOT_LEVEL} corner {W.corner_level()} east {W.DOOR_EAST_LEVEL} west {W.DOOR_WEST_LEVEL} "
                f"pier {W.PIER_SIDE_LEVEL} upper {W.PIER_UPPER_LEVEL} pool {starhall.SUN_POOL}")
        asked = {cell: (level, f"{W.WHY}:way {what}") for cell, level, what in W.sources()}
    finally:
        for name, level in kept.items():
            setattr(*NAMES[name], level)
    r = lights.report(canvas)
    odd = [f"{cell} asked {want[0]} got {r['placed'].get(cell)}" for cell, want in sorted(asked.items())
           if r["placed"].get(cell) != want]
    light = L.levels(canvas, (-9, -2, -7), (18, 15, 7))
    v4, v7 = hall.frames(canvas)
    got = {name: read(v4, box) for name, box in V4_BOXES}
    got.update({name: read(v7, box) for name, box in V7_BOXES})
    print(f"== {said}  ({time.time() - t0:.0f} s)")
    print("V4 " + "  ".join(f"{name} {got[name][0]:.3f} ({got[name][1]:+.3f})" for name, _ in V4_BOXES))
    print("V7 " + "  ".join(f"{name} {got[name][0]:.3f}" for name, _ in V7_BOXES))
    x0, _, x1, _ = V4_BOXES[0][1]
    print("V4 rows " + "  ".join(f"{a}-{b} {read(v4, (x0, a, x1, b))[0]:.3f}" for a, b in zip(ROWS, ROWS[1:])))
    print("light " + " | ".join(f"{name} " + " ".join(str(light.get(c, 0)) for c in cells) for name, cells in CELLS))
    fails = []
    if odd:
        fails.append("sources not placed as asked: " + "; ".join(odd))
    half, warm = got["half"]
    if half < HALF or warm < WARM:
        fails.append(f"the half of the doorway {half:.3f} ({warm:+.3f}); the line is {HALF} and +{WARM}")
    for name in ("pier N", "pier S"):
        if not PIER[0] <= got[name][0] <= PIER[1]:
            fails.append(f"{name} {got[name][0]:.3f}, not {PIER[0]} to {PIER[1]}")
    arches = [got["arch N"][0], got["arch S"][0]]
    if max(arches) > ARCH or abs(arches[0] - arches[1]) > ALIKE:
        fails.append(f"the flights {arches[0]:.3f} and {arches[1]:.3f}; {ARCH} at most and within {ALIKE} of each other")
    if max(arches) >= min(got["pier N"][0], got["pier S"][0]):
        fails.append("a flight is as light as the pier's face")
    if max(got["pier N"][0], got["pier S"][0]) >= got["dial"][0]:
        fails.append("the pier's face is as light as the dial")
    for name in ("lining L", "lining R"):
        if got[name][0] > LINING:
            fails.append(f"{name} {got[name][0]:.3f}, over {LINING}")
    print("lines: " + ("all hold" if not fails else "; ".join(fails)))
    sys.stdout.flush()
    return fails


def main(argv):
    hall = Hall()
    first = None
    for text in argv or ["now"]:
        fails = measure(hall, variant(text))
        first = fails if first is None else first
    print("doorway: " + ("PASS" if not first else "FAIL") + " (the first variant)")
    return 0 if not first else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
