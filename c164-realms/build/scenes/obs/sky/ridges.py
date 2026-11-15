"""Far ridges: the silhouettes of distant mountains on either side of the afterglow.

Card plan/packages/sky/ridges.md; plan/parts/sky.md section 5, sky-notes.md sections 4 and 8.

The cloud sea needs an end. Blocks cannot give it one: the game draws none beyond the view
distance (192 blocks at the 12 chunks the map is shown at). So the far shore is painted: a few
upright sheets, each the cut-out picture of a jagged ridge, standing 380 to 430 blocks out in the
west half of the horizon, to the north and to the south of due west. Due west stays open, a notch
between the two ranges where the afterglow is strongest and over which the comet hangs.

How a sheet gets out there. The server sends an entity only to players near it, so the display
entities stand in the middle of the site (CENTRE), inside the rock. A sheet's model is three
blocks wide; its anchor lies in front of it, and the display's scale (SCALE) carries the sheet
out by SCALE times that distance. A display entity without a width is not culled, so it is drawn
whichever way the player looks.

What colour it has: none of its own. Everything beyond the view distance is drawn in the fog's
colour, which is also the colour of the sky's lowest band. A sheet therefore shows only against
what lies behind and before it: it hides the afterglow's fan and the stars behind it (the fan
ends 6.7 degrees up due west in the blue hour, lower to either side: fan()), and the far cloud
layer ends against its foot. Where there is no afterglow, towards the north and south, a ridge is
a band without stars and little else: it fades out by itself. The picture is painted in the
darkest tone of night_glass, for a client whose view reaches further than the sheets stand.

One pixel of the picture is one block out there (SCALE 128, 8 pixels to the model's unit): the
steps of the ridge line are the steps a mountain of blocks would show at that distance.

Seen from the site, the ridge line of every sheet is given as elevations over bearings (CRESTS,
degrees up for an eye at EYE_Y, degrees north of due west) and reaches 4.5 degrees at most (the
card allows 6). The sheets go down to FOOT, far below the cloud layer's face, so that their
lower edge lies behind the near sea from wherever a person can stand.

    python -m scenes.obs.sky.ridges     prints where the sheets stand and how high they reach
"""
import math

import numpy as np

from artkit import models as M

from ..common import palette as P
from . import mood

PREFIX = "sky_ridge_"

CENTRE = (30.5, 0.5)        # x, z where the entities stand: no place a person can reach is more than
#                             80 blocks from it, so every player on the site is sent them
ENTITY_Y = -2.5             # in the rock under the court's paving
VIEW = 6.0                  # view_range: shown to within 384 blocks of the entities at the default setting
SCALE = 128.0               # the display's scale
PX = 8                      # pixels to the model's unit: 16 * PX / SCALE pixels to the block, one
WIDTH, HEIGHT = 384, 144    # a sheet's picture in pixels, which is its size out there in blocks
FOOT = -112.0               # scene y of a sheet's lower edge
EYE_Y = 1.62                # the eye the elevations are given for: a person on the upper terrace
HIGHEST = 4.5               # no ridge line stands higher than this, in degrees for that eye
TONE = P.colour("night_glass", 0)

# The sheets: which way from CENTRE the middle of each lies (degrees north of due west), how far out,
# and its ridge line as (bearing, elevation) points, joined by straight lines and then broken up
# (JAG). Where the line runs under the cloud layer's face the ridge has gone into the sea. A sheet
# spans atan(WIDTH / 2 / distance) to either side of its bearing; the points beyond that are not used.
SHEETS = {
    "north": dict(bearing=34.0, distance=380.0, seed=3, crest=(
        (6.0, -9.0), (8.5, -6.0), (11.0, 0.6), (14.0, 2.2), (18.5, 3.7), (22.0, 3.0), (26.0, 2.3),
        (31.5, 4.4), (35.0, 3.6), (40.0, 2.9), (44.0, 3.2), (49.0, 2.2), (55.0, 1.7), (62.0, 1.2))),
    "north_far": dict(bearing=72.0, distance=430.0, seed=5, crest=(
        (46.0, 1.2), (52.0, 1.6), (58.0, 2.3), (63.0, 1.5), (69.0, 1.3), (76.0, 1.9), (82.0, 1.1),
        (88.0, 0.4), (93.0, -3.0), (97.0, -9.0))),
    "south": dict(bearing=-34.0, distance=380.0, seed=7, crest=(
        (-6.0, -9.0), (-8.0, -6.0), (-10.5, 0.2), (-13.0, 2.4), (-16.5, 3.3), (-20.0, 2.1), (-25.0, 1.8),
        (-30.0, 3.1), (-34.0, 3.8), (-38.5, 4.2), (-43.0, 2.8), (-50.0, 2.1), (-56.0, 1.5), (-62.0, 1.1))),
    "south_far": dict(bearing=-72.0, distance=430.0, seed=11, crest=(
        (-46.0, 1.1), (-51.0, 1.7), (-57.0, 1.4), (-63.0, 2.4), (-68.0, 1.6), (-74.0, 1.2), (-80.0, 1.7),
        (-87.0, 0.5), (-92.0, -3.0), (-97.0, -9.0))),
}
# the breaking up of a ridge line: (how many degrees one tooth is wide, how many degrees it stands high)
JAG = ((5.5, 0.45), (2.3, 0.28), (0.9, 0.14))


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


def crest(name):
    """The ridge line of a sheet: for each of its WIDTH columns, from the left as the site sees
    it, the scene y where the ridge ends (whole blocks; under FOOT where there is none)."""
    sheet = SHEETS[name]
    bearings, heights = zip(*sorted(sheet["crest"]))
    out = np.empty(WIDTH)
    for c in range(WIDTH):
        u = c + 0.5 - WIDTH / 2.0                               # blocks to the right of the sheet's middle
        bearing = sheet["bearing"] + math.degrees(math.atan2(u, sheet["distance"]))
        up = float(np.interp(bearing, bearings, heights))
        if up > -2.0:                                           # a flank that dives into the sea stays smooth
            up = min(HIGHEST, up + _teeth(bearing, sheet["seed"]))
        out[c] = EYE_Y + math.hypot(u, sheet["distance"]) * math.tan(math.radians(up))
    return np.floor(out)


def picture(name):
    """A sheet's picture, HEIGHT by WIDTH, as the site sees it: the ridge in one tone, the sky clear."""
    top = FOOT + HEIGHT                                         # the scene y of the picture's upper edge
    rows = top - 1 - np.arange(HEIGHT)[:, None]                 # the block each row of pixels shows
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


def build(canvas, origin=(0, 0, 0)):
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
    lines = [f"{len(SHEETS)} sheets, {WIDTH} x {HEIGHT} blocks each, foot at y {FOOT:g}, "
             f"the cloud layer's face at y {mood.CLOUD_TOP}; elevations for an eye at y {EYE_Y}; "
             f"afterglow opacity {alpha:g} (look {mood.DEFAULT})"]
    for name, sheet in SHEETS.items():
        line = crest(name)
        half = math.degrees(math.atan2(WIDTH / 2.0, sheet["distance"]))
        ups, fans = [], []
        for c in range(WIDTH):
            u = c + 0.5 - WIDTH / 2.0
            bearing = sheet["bearing"] + math.degrees(math.atan2(u, sheet["distance"]))
            up = math.degrees(math.atan2(line[c] - EYE_Y, math.hypot(u, sheet["distance"])))
            ups.append(up)
            if line[c] > mood.CLOUD_TOP:
                fans.append(fan(abs(bearing), max(up, 0.0), alpha))
        over = [u for u, y in zip(ups, line) if y > mood.CLOUD_TOP]
        lines.append(f"{name:10s} {sheet['bearing'] - half:6.1f} to {sheet['bearing'] + half:6.1f} north of west, "
                     f"{sheet['distance']:.0f} to {math.hypot(WIDTH / 2.0, sheet['distance']):.0f} blocks out; "
                     f"ridge line up to {max(ups):.1f} degrees (y {line.max():.0f}), over the sea along "
                     f"{len(over) / WIDTH * 100:.0f}% of the sheet; afterglow behind the ridge line "
                     f"{min(fans):.2f} to {max(fans):.2f}")
    return lines


if __name__ == "__main__":
    print("\n".join(report()))
