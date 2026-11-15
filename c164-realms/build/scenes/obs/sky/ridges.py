"""sky/ridges -- the far hills.

The afterglow lies in the west (sky/mood.py paints it there). Two groups of hill ridges, one to
the north-west and one to the south-west, stand beyond the end of the fog and close the cloud sea
off; the west itself is left open so the afterglow and the comet are seen to the horizon. Each
ridge is a plane of display entities with a jagged, cut-out silhouette: only the hills themselves
are drawn, the sky showing through the gaps between the peaks.

Why they show only where the afterglow is: everything past the fog's end is plain fog colour, so a
panel with no light on it is invisible against that same colour. Where the afterglow fan lies
behind it, the fan's colour shows through the cut-out and the ridge reads as a darker shape
against it. That is the design of plan/parts/sky.md section 5; on the real machine (fog, the fan,
the clouds) it is what decides whether the idea stands at all.

How a panel gets 360 blocks out while its entity stands on the terrace: the server sends an entity
only to the players within 160 blocks of it, so the entity itself must stand where people walk.
The model is drawn with its picture already pushed out along the model's own normal by PUSH units
and the entity's uniform scale multiplies that offset along with the picture, so the panel lands
PUSH * k blocks away while standing W x k blocks wide. The two are one number, so the ratio of the
push to the picture's width is fixed by where the panel must stand and how much sky it covers:

    PUSH / WIDTH_UNITS == DISTANCE / WIDTH == 360 / 300

The entity's bounding box is emptied (width and height 0) so the game does not cull the picture
when the anchor leaves the screen, and view_range is raised so the terrace can see it.

The panels do not turn with the viewer: they are fixed, like any far hill, so walking about shifts
them against the nearer hills and the cloud sea as it should.
"""
import math

from artkit import models as M

from ..common import palette as P
from ..common import skeleton as S

PREFIX = "sky_ridge_"

# Where the ridges stand, in compass degrees (0 = north = +z, 90 = east = +x). The west, 270, is
# left empty on purpose: that is where the afterglow and the comet are seen.
BEARINGS = {"nw": 305.0, "sw": 233.0}
DISTANCE = 360.0                            # how far out the panels read, in blocks
WIDTH = 300.0                               # how much sky one panel covers, across, in blocks
TALL = 5.0                                  # the picture's height in the model's own units;
                                            # times SCALE that is the tallest peak, about 47 blocks
MAX_ANGLE = 6.0                             # the tallest peak's elevation, degrees (the card's ceiling)

# The model's own units. Its picture is WIDE units across and TALL units high, its foot at y 0.
WIDE = 32.0
PUSH = WIDE * DISTANCE / WIDTH               # 38.4: the ratio is fixed by distance and width above
SCALE = WIDTH / WIDE                         # 9.375: one number scales the picture and the push

# The silhouettes: (share of the width, share of the height) turning points of the skyline, left to
# right. Drawn as stepped shoulders, not straight lines, so the outline reads as rock.
SKYLINES = {
    "a": [(0.00, 0.10), (0.04, 0.16), (0.08, 0.13), (0.13, 0.34), (0.17, 0.30), (0.22, 0.46),
          (0.26, 0.42), (0.31, 0.66), (0.35, 0.58), (0.39, 0.72), (0.43, 0.55), (0.48, 0.40),
          (0.53, 0.44), (0.58, 0.30), (0.64, 0.26), (0.70, 0.20), (0.78, 0.16), (0.88, 0.12),
          (1.00, 0.08)],
    "b": [(0.00, 0.08), (0.06, 0.12), (0.11, 0.24), (0.15, 0.20), (0.20, 0.38), (0.24, 0.34),
          (0.29, 0.52), (0.33, 0.47), (0.38, 0.60), (0.43, 0.50), (0.49, 0.34), (0.55, 0.30),
          (0.61, 0.22), (0.68, 0.18), (0.76, 0.14), (0.86, 0.11), (1.00, 0.07)],
    "c": [(0.00, 0.12), (0.05, 0.20), (0.09, 0.17), (0.14, 0.40), (0.18, 0.36), (0.23, 0.55),
          (0.27, 0.50), (0.32, 0.44), (0.37, 0.30), (0.42, 0.26), (0.47, 0.32), (0.52, 0.22),
          (0.58, 0.18), (0.65, 0.15), (0.73, 0.12), (0.82, 0.10), (1.00, 0.06)],
}
# Which silhouette goes where, and what share of TALLEST its tallest point reaches.
PANELS = [("a", "nw", 1.00), ("b", "nw", 0.72), ("b", "sw", 0.90), ("c", "sw", 1.00)]

COLUMNS = 64                                # how finely the skyline is cut, across


def _mat():
    """The one colour the ridges are painted in: the darkest step of the dark glass ramp, which is
    the darkest thing the palette owns. Everything that far out is fog colour anyway; this only
    decides how dark the hill reads where the afterglow is behind it."""
    return P.mat("night_glass", kind="plain", noise=0.06, bevel=0, base=0)


def _skyline(key, columns):
    """The height in model units at each of the panel's `columns` columns."""
    pts = [(u * columns, v * TALL) for u, v in SKYLINES[key]]
    out = []
    for x in range(columns):
        i = 0
        while i + 1 < len(pts) and pts[i + 1][0] < x:
            i += 1
        (x0, y0), (x1, y1) = pts[i], pts[min(i + 1, len(pts) - 1)]
        t = 0.0 if x1 == x0 else (x - x0) / (x1 - x0)
        h = y0 + (y1 - y0) * t
        out.append(max(0.25, round(h * 4.0) / 4.0))       # quarter-unit steps: rock, not paper
    return out


def _panel(key):
    """One ridge panel: its foot at the model's y 0, its face at z = 0 looking towards +z (the way
    the entity is turned), the picture pushed PUSH units out along -z, away from the terrace."""
    m = M.Model(PREFIX + key, px=1.0, anchor=(WIDE / 2.0, 0.0, 0.0))
    mat = _mat()
    height = _skyline(key, COLUMNS)
    step = WIDE / COLUMNS
    z = -PUSH
    for i, top in enumerate(height):
        x0 = i * step
        x1 = x0 + step
        m.box((x0, 0.0, z), (x1, top, z + 0.25), mat)              # the hill, a quarter unit thick
        if i % 5 == 0 and top > TALL * 0.22:                       # a shoulder, a step behind
            m.box((x0, 0.0, z - 0.5), (x1, top * 0.72, z - 0.25), mat)
    # a foot band, so no ridge floats free of the haze
    m.box((0.0, 0.0, z), (WIDE, 0.30, z + 0.25), mat)
    return m


_CACHE = {}


def _models():
    if not _CACHE:
        for key in SKYLINES:
            _CACHE[PREFIX + key] = _panel(key)
    return _CACHE


def models():
    return dict(_models())


def _place(canvas, key, bearing, share, origin=(0, 0, 0)):
    """Stand one panel's anchor on the terrace and turn its face back towards the terrace centre."""
    b = math.radians(BEARINGS[bearing])
    cx, cz = S.WALL_E + 0.0, S.AXIS_Z
    x = origin[0] + cx + math.sin(b) * 6.0
    z = origin[2] + cz + math.cos(b) * 6.0
    y = origin[1] + S.GROUND
    m = _models()[PREFIX + key]
    k = SCALE * share                         # the height share too: TALLEST is set for share 1.0
    nbt = M.display(m, yaw=(BEARINGS[bearing] + 180.0) % 360.0, scale=k)
    nbt["width"] = 0.0                        # not culled: the picture outlives the anchor's screen
    nbt["height"] = 0.0
    nbt["view_range"] = 600.0
    canvas.add_entity(x, y, z, nbt)
    return 1


def build(canvas, origin=(0, 0, 0)):
    """Place the panels. Returns the number of display entities put down."""
    n = 0
    for key, bearing, share in PANELS:
        n += _place(canvas, key, bearing, share, origin)
    return n


def peaks():
    """For the checks: (silhouette, bearing, the tallest peak in world blocks, its elevation in
    degrees). The entity's scale is uniform, so a model unit is SCALE * share blocks tall, the
    same number that carries the push out to DISTANCE."""
    out = []
    for key, bearing, share in PANELS:
        tall = max(v for _, v in SKYLINES[key]) * TALL * SCALE * share
        out.append((key, BEARINGS[bearing], tall, math.degrees(math.atan(tall / DISTANCE))))
    return out
