"""Far ridges: the silhouettes of distant mountains on either side of the afterglow.

Card plan/packages/sky/ridges.md; plan/parts/sky.md section 5, sky-notes.md sections 4 and 8.

The cloud sea needs an end. Blocks cannot give it one: the game draws none beyond the view
distance (192 blocks at the 12 chunks the map is shown at). So the far shore is painted: four
upright sheets, each the cut-out picture of a jagged ridge, standing 360 to 446 blocks out in the
west half of the horizon. Two ranges, one to the north and one to the south of due west; due west
stays open, a notch between two capes where the afterglow is strongest and over which the comet
hangs.

How a sheet gets out there. The server sends an entity only to players near it, so the display
entities stand in the middle of the site (CENTRE), inside the rock. A sheet's model is three
blocks wide; its anchor lies in front of it, and the display's scale (SCALE) carries the sheet
out by SCALE times that distance. A display entity without a width is not culled, so it is drawn
whichever way the player looks. The game draws entities as far as four times the view distance.

What colour it has: none of its own. Everything beyond the fog's end is drawn in the fog's
colour, which is also the colour of the sky's lowest band. A sheet therefore shows only against
what lies behind and before it: it hides the afterglow's fan and the stars behind it (the fan
ends 6.7 degrees up due west in the blue hour, lower to either side: fan()), and the far cloud
layer, which thins out with the distance, ends against its foot. Where there is no afterglow,
towards the north and south, a ridge is a band without stars and little else: the ranges fade
out by themselves. The picture is painted in the darkest tone of night_glass, for a client that
draws without fog.

One pixel of the picture is one block out there (SCALE 128, 8 pixels to the model's unit): the
steps of the ridge line are the steps a mountain of blocks would show at that distance.

A range is given as it is seen from the site: elevations over bearings (RANGES). It reaches
HIGHEST degrees at most for an eye above CENTRE; nearer to it, at the west rail of the sunset
platform, the same peak stands a sixth higher (the card allows 6 degrees).

Where a ridge ends below. A ridge rises from the horizon: its shore lies behind the sea's far
edge. A sheet goes down to FOOT, a little under the lowest place a person can stand, so that for
every eye on the site it goes down under the horizon and no sky shows under it. What lies under
the horizon is the sea's business. The sky's shader (a2 and cloud, 11-16, group #67329) paints
a flat sea there and gives everything under the horizon the far sea's colour for its fog: the
sheet's lowest rows melt into the sea. Until that shader is in, the sky's lower half is the fog's
colour with the lower half of the afterglow, and those rows show as the ridge's flat base, a
degree or so under the horizon. The first sheets went down to the vanilla cloud layer, 4.7
degrees under the horizon; that layer is going (cloud), and their base stood out in the void.

DRESS is the switch for the whole of it: the far ridges change every view to the west, the
arrival view among them, and whether the game draws them well is only seen in the game. On, the
master scene carries them; off, nothing does. A test scene asks for them with dress(): the
sky's build() is also what a test scene of any line calls for its light sources (INTERFACE 4),
and no ridge is to come with those (the scene's pack would not even have the models). A canvas
carries no word of the scene it is built for, so build() asks its callers: see _master().

    python -m scenes.obs.sky.ridges     prints where the sheets stand and how high they reach
"""
import math
import sys

import numpy as np

from artkit import models as M

from ..common import palette as P
from ..common import skeleton as S
from . import mood

PREFIX = "sky_ridge_"
DRESS = True                # the master scene carries the far ridges; False takes them all out again

CENTRE = (30.5, 0.5)        # x, z where the entities stand: no place a person can reach is more than
#                             80 blocks from it, so every player on the site is sent them
ENTITY_Y = -2.5             # in the rock under the court's paving
VIEW = 6.0                  # view_range: shown to within 384 blocks of the entities at the default setting
SCALE = 128.0               # the display's scale
PX = 8                      # pixels to the model's unit: 16 * PX / SCALE pixels to the block, one
WIDTH, HEIGHT = 384, 48     # a sheet's picture in pixels, which is its size out there in blocks
FOOT = float(S.LOWER_PAVING_Y) - 1.0        # scene y of a sheet's lower edge: under the lowest eye on the site
EYE_Y = S.GROUND + S.EYE    # the eye the elevations are given for: a person on the upper terrace
HIGHEST = 4.0               # no ridge line stands higher than this, in degrees for that eye
SHORE = -1.6                # just under where a sheet's lower edge lies for that eye, in degrees
TONE = P.colour("night_glass", 0)

# The two ranges as the site sees them: the ridge line as points (degrees north of due west, degrees
# up for an eye at EYE_Y above CENTRE), from the horizon at the notch over peaks and saddles back
# under the horizon. Towards a peak the line is hollow: flat out of the saddle, steep under the top (FLANK);
# elsewhere the points are joined by straight lines. Then the line is broken up (JAG). The south
# range is not the north one mirrored: its bold headland stands next to the notch, its highest
# peak further out.
RANGES = {
    "north": dict(seed=3, line=(
        (9.0, SHORE), (10.5, 0.2), (15.5, 1.9), (18.5, 0.6), (25.0, 3.6), (30.0, 1.5), (35.5, 2.9), (40.5, 1.0),
        (46.0, 2.3), (51.5, 0.8), (57.0, 1.7), (63.0, 0.5), (69.0, 1.3), (75.0, 0.3), (80.0, 0.9), (88.0, -0.4),
        (94.0, SHORE))),
    "south": dict(seed=7, line=(
        (-8.5, SHORE), (-9.5, 0.4), (-13.5, 2.7), (-17.5, 0.9), (-23.0, 2.1), (-28.0, 1.2), (-37.0, 3.8),
        (-43.0, 1.4), (-48.5, 2.5), (-54.0, 0.7), (-59.5, 1.8), (-66.0, 0.4), (-71.0, 1.2), (-77.0, 0.2),
        (-82.0, 1.0), (-89.0, -0.4), (-94.0, SHORE))),
}
FLANK = 1.6
# the breaking up of a ridge line: (how many degrees one tooth is wide, how many degrees it stands high)
JAG = ((5.5, 0.30), (2.3, 0.27), (0.9, 0.16))

# The sheets: the range each shows, which way from CENTRE its middle lies (degrees north of due
# west) and how far out. A sheet spans atan(WIDTH / 2 / distance) to either side of its bearing.
# Two sheets to a range, the outer one further out, so far that it lies behind the inner one
# wherever the two overlap; there they show the same line to an eye at CENTRE. The card wants
# the picture 300 to 450 blocks out: the nearest point is 360, the furthest corner 446.
SHEETS = {
    "north": dict(range="north", bearing=34.0, distance=360.0),
    "north_far": dict(range="north", bearing=72.0, distance=402.0),
    "south": dict(range="south", bearing=-34.0, distance=360.0),
    "south_far": dict(range="south", bearing=-72.0, distance=402.0),
}


def _hash(i, seed):
    h = (int(i) * 374761393 + int(seed) * 668265263) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFFFF) / float(1 << 24)


def _teeth(bearing, seed):
    """The broken edge added to a ridge line at a bearing: sharp teeth of three sizes, in degrees."""
    out = 0.0
    for k, (wide, high) in enumerate(JAG):
        i = math.floor(bearing / wide)
        at = bearing / wide - i
        a, b = _hash(i, seed * 31 + k), _hash(i + 1, seed * 31 + k)
        out += high * ((a + (b - a) * at) * 2.0 - 1.0)
    return out


def line(name, bearing):
    """A range's ridge line at a bearing: degrees up for an eye at EYE_Y above CENTRE; SHORE and
    below where there is no ridge."""
    r = RANGES[name]
    pts = sorted(r["line"])
    if not pts[0][0] < bearing < pts[-1][0]:
        return SHORE - 1.0
    i = max(k for k in range(len(pts) - 1) if pts[k][0] <= bearing)
    (b0, h0), (b1, h1) = pts[i], pts[i + 1]
    t = (bearing - b0) / (b1 - b0)
    lo, hi = (i, i + 1) if h1 >= h0 else (i + 1, i)             # the segment's lower and higher end
    after = pts[hi + (hi - lo)][1] if 0 <= hi + (hi - lo) < len(pts) else SHORE
    if after < pts[hi][1]:                                      # the higher end is a peak: a hollow flank
        t = t if hi == i + 1 else 1.0 - t
        up = pts[lo][1] + (pts[hi][1] - pts[lo][1]) * t ** FLANK
    else:
        up = h0 + (h1 - h0) * t
    if up <= SHORE:
        return up
    # the teeth grow with the height: a low cape is calm, the peaks are broken
    return min(HIGHEST, up + _teeth(bearing, r["seed"]) * min(1.0, max(0.2, up / 3.5)))


def crest(name):
    """The ridge line of a sheet: for each of its WIDTH columns, from the left as the site sees
    it, the scene y where the ridge ends (whole blocks; FOOT and below where there is none)."""
    sheet = SHEETS[name]
    out = np.empty(WIDTH)
    for c in range(WIDTH):
        u = c + 0.5 - WIDTH / 2.0                               # blocks to the right of the sheet's middle
        bearing = sheet["bearing"] + math.degrees(math.atan2(u, sheet["distance"]))
        up = line(sheet["range"], bearing)
        out[c] = EYE_Y + math.hypot(u, sheet["distance"]) * math.tan(math.radians(up))
    return np.floor(out)


def picture(name):
    """A sheet's picture, HEIGHT by WIDTH, as the site sees it: the ridge in one tone, the sky clear."""
    rows = FOOT + HEIGHT - 1 - np.arange(HEIGHT)[:, None]       # the block each row of pixels shows
    solid = rows < crest(name)[None, :]
    out = np.zeros((HEIGHT, WIDTH, 4), dtype=np.uint8)
    out[solid, :3] = TONE
    out[solid, 3] = 255
    return out


class _Picture:
    """What artkit.models paints a face with: the sheet's picture, whatever size is asked for."""

    def __init__(self, name):
        self.name = PREFIX + name + "_picture"
        self.sheet = name

    def paint(self, w, h, grain="u", seed=0):
        if (w, h) == (WIDTH, HEIGHT):
            return picture(self.sheet)
        return np.zeros((h, w, 4), dtype=np.uint8)              # the sheet's edges: nothing


def models():
    out = {}
    for name, sheet in SHEETS.items():
        # the sheet stands upright across x, its face to +z; the anchor lies before it, where the
        # entity stands once the display's scale has carried the sheet out
        anchor = (0.0, (ENTITY_Y - FOOT) / SCALE * 16.0, sheet["distance"] / SCALE * 16.0)
        m = M.Model(PREFIX + name, px=PX, anchor=anchor)
        m.box((-WIDTH / PX / 2.0, 0.0, -0.05), (WIDTH / PX / 2.0, HEIGHT / PX, 0.0), _Picture(name),
              skip="newud", shade=False)
        out[m.name] = m
    return out


def _yaw(bearing):
    """The yaw that turns a model's -z (from its anchor to the sheet) to a bearing north of due west."""
    a = math.radians(bearing)
    return math.degrees(math.atan2(-math.cos(a), math.sin(a)))


def dress(canvas, on=True):
    """Put the far ridges on this canvas (or leave them off it), whatever the switch DRESS says:
    for a test scene. Call it before build()."""
    canvas.ridge_dress = bool(on)


def _master():
    """Is it the master scene that builds? Told as tools/check.py tells the master scene from a
    test scene: the module with LINES and _line, looked for among the callers."""
    frame = sys._getframe(1)
    while frame is not None:
        if "LINES" in frame.f_globals and "_line" in frame.f_globals:
            return True
        frame = frame.f_back
    return False


def build(canvas, origin=(0, 0, 0)):
    on = getattr(canvas, "ridge_dress", None)
    if on is None:
        on = DRESS and _master()
    if not on:
        return 0
    ox, oy, oz = origin
    made = models()
    for name, sheet in SHEETS.items():
        canvas.add_entity(CENTRE[0] + ox, ENTITY_Y + oy, CENTRE[1] + oz,
                          M.display(made[PREFIX + name], yaw=_yaw(sheet["bearing"]), scale=SCALE,
                                    brightness=(15, 0), view=VIEW))
    return len(SHEETS)


# ---- where the sheets stand, for the test scene and the card -------------------------------------
def corners(name, origin=(0, 0, 0)):
    """The four corners of a sheet in scene coordinates: lower left, lower right, upper left, upper
    right as the site sees it."""
    sheet = SHEETS[name]
    a = math.radians(sheet["bearing"])
    away = np.array([-math.cos(a), 0.0, -math.sin(a)])          # from CENTRE to the sheet's middle
    right = np.array([math.sin(a), 0.0, -math.cos(a)])          # to the right of someone who looks that way
    mid = np.array([CENTRE[0] + origin[0], FOOT + origin[1], CENTRE[1] + origin[2]]) + away * sheet["distance"]
    half, up = right * (WIDTH / 2.0), np.array([0.0, float(HEIGHT), 0.0])
    return [mid - half, mid + half, mid - half + up, mid + half + up]


def fan(bearing, up, alpha):
    """The share of the afterglow's colour the game lays over the sky in a direction (degrees from
    due west along the horizon, degrees up), for an afterglow of opacity alpha: 26.3 SkyRenderer,
    a fan from a vertex on the western horizon to a ring of 16 round the camera that is raised
    towards the west."""
    a, e = math.radians(bearing), math.radians(up)
    d = np.array([-math.cos(e) * math.cos(a), math.sin(e), math.cos(e) * math.sin(a)])
    west = np.array([-100.0, 0.0, 0.0])
    best = 0.0
    for j in range(16):
        ring = []
        for h in (j * math.pi / 8.0, (j + 1) * math.pi / 8.0):
            ring.append([-120.0 * math.cos(h), 40.0 * alpha * math.cos(h), 120.0 * math.sin(h)])
        m = np.column_stack([west, ring[0], ring[1]])
        if abs(np.linalg.det(m)) < 1e-9:
            continue
        k = np.linalg.solve(m, d)
        if (k >= -1e-9).all() and k.sum() > 1e-12:
            best = max(best, alpha * float(k[0] / k.sum()))
    return best


def report():
    alpha = mood.LOOKS[mood.DEFAULT]["glow_alpha"]
    lines = [f"{len(SHEETS)} sheets, {WIDTH} x {HEIGHT} blocks each, their lower edge at y {FOOT:g}; "
             f"elevations for an eye at y {EYE_Y} above the entities; afterglow opacity {alpha:g} (look {mood.DEFAULT})"]
    for name, sheet in SHEETS.items():
        ridge = crest(name)
        half = math.degrees(math.atan2(WIDTH / 2.0, sheet["distance"]))
        ups, fans = [], []
        for c in range(WIDTH):
            if ridge[c] <= FOOT:
                continue
            u = c + 0.5 - WIDTH / 2.0
            bearing = sheet["bearing"] + math.degrees(math.atan2(u, sheet["distance"]))
            ups.append(math.degrees(math.atan2(ridge[c] - EYE_Y, math.hypot(u, sheet["distance"]))))
            fans.append(fan(abs(bearing), max(ups[-1], 0.0), alpha))
        lines.append(f"{name:10s} {sheet['bearing'] - half:6.1f} to {sheet['bearing'] + half:6.1f} north of west, "
                     f"{sheet['distance']:.0f} to {math.hypot(WIDTH / 2.0, sheet['distance']):.0f} blocks out, "
                     f"ridge line up to {max(ups):.1f} degrees (y {ridge.max():.0f}), "
                     f"a ridge along {len(ups) / WIDTH * 100:.0f}% of the sheet; "
                     f"afterglow behind the ridge line {min(fans):.2f} to {max(fans):.2f}")
    return lines


if __name__ == "__main__":
    print("\n".join(report()))
