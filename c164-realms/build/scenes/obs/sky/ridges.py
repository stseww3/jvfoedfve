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

How a panel gets out to DISTANCE while its entity stands on the terrace: the server sends an
entity only to the players within 160 blocks, so the anchor must stand where people walk. The
picture is a flat model at the anchor; the entity's own `transformation.translation` carries it out
along the bearing. The world matrix the game uses is

    centre = anchor + Rotation @ translation

so the local translation that lands the picture W blocks out in a given world direction d is
`translation = rot_y(-yaw) @ (d * DISTANCE)`. The translation is applied in the model's frame, so
it is NOT scaled by `scale`, which keeps the two independent: the model's scale sets the picture's
size, the translation sets where it stands.

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
MAX_ANGLE = 6.0                             # the tallest peak's elevation, degrees (the card's ceiling)

# The model's own units: the exporter writes a model unit as 1/32 of a block (a 16-pixel element
# comes out 0.5 blocks wide), so the model's picture is WIDE units = WIDE/32 blocks across before
# the entity's scale. WIDE is chosen so the unscaled picture is exactly one block: then the
# entity's scale IS the panel's width in blocks.
WIDE, TALL = 32.0, 5.0                      # model units: 1.0 block across, 0.156 blocks high
SCALE = WIDTH / (WIDE / 32.0)               # 300: the width in blocks over the model's own width

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
# Which silhouette goes where, and what share of the tallest height its tallest point reaches.
PANELS = [("a", "nw", 1.00), ("b", "nw", 0.72), ("b", "sw", 0.90), ("c", "sw", 1.00)]

COLUMNS = 64                                # how finely the skyline is cut, across


def _mat():
    """The one colour the ridges are painted in.

    Painted for where they stand: the fog law the sky lead (a2) set has the ground fog end at 768,
    so a panel at 360 carries 360/768 = 47% fog. Mixing the palette's darkest step with the look's
    fog colour by that share comes out (43, 47, 93), which is `night_glass` 2 -- (39, 51, 95) --
    to within a few parts of a level. So the palette already owns the colour this needs: the
    palette's own step is used, and nothing new is defined (COMMON 4: no colours of one's own).
    The hill then reads as a darker shape where the afterglow is behind it and fades into the fog
    where there is none -- which is the design on the card.
    """
    return P.mat("night_glass", kind="plain", noise=0.06, bevel=0, base=2)


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
    """One ridge panel: a flat picture standing at the model's own z 0, its foot at y 0, facing
    +z. Its span along z is tiny on purpose -- the panel is carried out by the entity's
    translation, so the model never comes near the 48-unit span limit."""
    m = M.Model(PREFIX + key, px=1.0, anchor=(WIDE / 2.0, 0.0, 0.0))
    mat = _mat()
    height = _skyline(key, COLUMNS)
    step = WIDE / COLUMNS
    for i, top in enumerate(height):
        x0 = i * step
        x1 = x0 + step
        m.box((x0, 0.0, 0.0), (x1, top, 0.25), mat)                # the hill, a quarter unit thick
        if i % 5 == 0 and top > TALL * 0.22:                       # a shoulder, a step behind
            m.box((x0, 0.0, -0.25), (x1, top * 0.72, 0.0), mat)
    m.box((0.0, 0.0, 0.0), (WIDE, 0.30, 0.25), mat)                # a foot band, no ridge floats
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
    """Stand one panel's anchor on the terrace, its face turned back towards the terrace centre,
    and carry the picture DISTANCE blocks out along that face's own normal."""
    b = math.radians(BEARINGS[bearing])
    cx, cz = S.WALL_E + 0.0, S.AXIS_Z
    # the anchor stands a few cells off the centre on the bearing: on the terrace, in plain sight,
    # so the server sends the entity to whoever walks there
    x = origin[0] + cx + math.sin(b) * 6.0
    z = origin[2] + cz + math.cos(b) * 6.0
    y = origin[1] + S.GROUND
    m = _models()[PREFIX + key]
    k = SCALE * share
    yaw = (BEARINGS[bearing] + 180.0) % 360.0          # the face looks back at the terrace
    nbt = M.display(m, yaw=yaw, scale=k)
    # the world offset we want, and its expression in the model's own frame. The renderer and the
    # game put the picture's centre at  centre = anchor + turn @ translation  with
    # turn = rot_y(-R), R being the NBT Rotation (180 + the yaw the face looks). A rotation's
    # transpose is its inverse, so translation = turn^T @ offset.
    d = math.radians(BEARINGS[bearing])
    off_x, off_z = math.sin(d) * DISTANCE, math.cos(d) * DISTANCE
    R = (180.0 + yaw) % 360.0
    r = math.radians(R)
    # turn = rot_y(-R) = [[c, 0, -s], [0, 1, 0], [s, 0, c]]; its transpose is [[c, 0, s], [0, 1, 0], [-s, 0, c]]
    tx = math.cos(r) * off_x + math.sin(r) * off_z
    tz = -math.sin(r) * off_x + math.cos(r) * off_z
    nbt["transformation"]["translation"] = [M.Float(tx), M.Float(0.0), M.Float(tz)]
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
    degrees). A model unit is 1/32 of a block, so the height in blocks is TALL/32 * SCALE * share."""
    out = []
    for key, bearing, share in PANELS:
        tall = max(v for _, v in SKYLINES[key]) * (TALL / 32.0) * SCALE * share
        out.append((key, BEARINGS[bearing], tall, math.degrees(math.atan(tall / DISTANCE))))
    return out
