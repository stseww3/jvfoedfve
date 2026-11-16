"""Far ridges: the silhouettes of distant mountains on either side of the afterglow.

Card plan/packages/sky/ridges.md; plan/parts/sky.md section 5, sky-notes.md sections 4 and 8.

The cloud sea needs an end. Blocks cannot give it one: the game draws none beyond the view
distance (160 blocks at the 10 chunks a Realms server sends). So the far shore is painted, on the
sky itself: two ranges, one to the north and one to the south of due west. Due west stays open,
a notch between two capes where the afterglow is strongest and over which the comet hangs.

The carrier is the sky's own shader. The look is in the resource pack's core shaders
(sky/_shaders.py, card sky/safe-look: a Realms map takes no registry file), and the sky's
fragment shader paints every pixel by its direction. This package hands it a layer
(shader_layer()): below the ridge line of its bearing a direction shows the ridge and not the
sky, and the stars' shader draws no star there. Painted like this a ridge stands at no distance
at all. It does not shift when a person walks, as the horizon does not; RANGES is the ridge line
for every eye on the site; and from every height the ridge stands on the horizon.

What colour it has: none of its own. A ridge is so far off that the air has taken all of it: it
shows the horizon band of its bearing without the afterglow's fan, and is seen as far as the fan
glows behind it. Towards the north and south, where there is no afterglow, it is the colour of
the sky behind it, a band without stars and little else: the ranges fade out by themselves. At
its foot the mist on the sea hides it: over the lowest VEIL degrees it comes out of the glow that
lies on the horizon, so the sea's far edge shows no line.

The line is baked into a table of columns, STEP degrees of bearing each and whole steps of STEP
high: the ridge keeps the stepped outline of a mountain of blocks seen from afar (a block 230
blocks off is a quarter of a degree).

Nothing is built and the pack gets no model or picture from here: the layer is all there is.

The first carrier (11-15, 11-16) was four display entities with cut-out pictures, 360 to 446
blocks out. Two things ended it. At the Realms server's view distance the ridges were missing on
the real machine for someone who arrives at the west rail and looks west, and stood there after
a look back at the site (s1); the likeliest cause is that the game draws an entity only when the
chunk section it stands in has been built, which happens once that section has been in view.
And a sheet stands at a place: seen from above (V12) it was a dark band in the air beyond the
edge of the sea's disc, under the horizon (cr2). The shaders' fog would not have hidden it
either: by mood.fog_depth() a thing 400 blocks out keeps three quarters of its own paint, where
the old fog turned everything that far into the fog's colour. The card has the pictures.

    python -m scenes.obs.sky.ridges     prints where the ranges stand and how high they reach
"""
import math

import numpy as np

from . import mood

HIGHEST = 4.0               # no ridge line stands higher than this, in degrees
SHORE = -1.6                # where a range's line ends under the horizon, in degrees

# The two ranges as the site sees them: the ridge line as points (degrees north of due west, degrees
# up), from the horizon at the notch over peaks and saddles back under the horizon. Towards a peak
# the line is hollow: flat out of the saddle, steep under the top (FLANK); elsewhere the points are
# joined by straight lines. Then the line is broken up (JAG). The south range is not the north one
# mirrored: its bold headland stands next to the notch, its highest peak further out.
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
    """A range's ridge line at a bearing: degrees up; SHORE and below where there is no ridge."""
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


# ---- the layer on the sky ------------------------------------------------------------------------
STEP = 0.25                 # degrees to a column of the table, and to a step in height
FROM = -95.0                # the first column's bearing, degrees north of due west
COLUMNS = int(round(-2.0 * FROM / STEP))
VEIL = 0.5                  # degrees over the horizon at which a ridge has come out of the sea's mist


def baked():
    """The ridge line as the shader has it: for each column the whole number of steps the ridge
    stands over the horizon there (0: no ridge)."""
    out = np.zeros(COLUMNS, dtype=int)
    for c in range(COLUMNS):
        bearing = FROM + (c + 0.5) * STEP
        up = max(line(name, bearing) for name in RANGES)
        out[c] = max(0, int(math.floor(up / STEP + 0.5)))
    return out


def _crest_y():
    """For each column the y of the unit direction at the ridge line, -1 where there is none."""
    rows = baked()
    return np.where(rows > 0, np.sin(np.radians(rows * STEP)), -1.0)


SKYLINE_GLSL = """// sky/ridges.py: the far ridges. The ridge line, one entry to a column of {step} degrees of bearing
// from {start} degrees north of due west on: the y of the unit direction at the line, -1.0 where
// no ridge stands.
const float C164_RIDGE_FROM = {start};
const float C164_RIDGE_STEP = {step};
const int C164_RIDGE_COLUMNS = {columns};
const float C164_RIDGE_TOP = {top};        // no ridge stands higher
const float C164_RIDGE[{columns}] = float[{columns}](
{table}
);

float c164_skyline(vec3 d) {{
    if (d.y > C164_RIDGE_TOP || abs(d.x) + abs(d.z) < 1.0e-4) {{
        return -1.0;
    }}
    float column = floor((degrees(atan(-d.z, -d.x)) - C164_RIDGE_FROM) / C164_RIDGE_STEP);
    if (column < 0.0 || column > float(C164_RIDGE_COLUMNS - 1)) {{
        return -1.0;
    }}
    return C164_RIDGE[int(column)];
}}
"""

RIDGES_GLSL = """// sky/ridges.py: a far ridge has no colour of its own left: it is the horizon band of its bearing
// without the afterglow's fan, and at its foot it comes out of the glow that lies on the sea's edge.
const float C164_RIDGE_VEIL = {veil};

vec3 c164_ridges(vec3 colour, vec3 d) {{
    if (d.y < 0.0 || d.y >= c164_skyline(d)) {{
        return colour;
    }}
    vec3 level = vec3(d.x, 0.0, d.z) / length(d.xz);
    return mix(c164_band(level), c164_ring(level), smoothstep(0.0, C164_RIDGE_VEIL, d.y));
}}
"""


def _f(x):
    text = repr(round(float(x), 6))
    return text if ("." in text or "e" in text) else text + ".0"


def shader_layer(look=mood.DEFAULT):
    """What sky/_shaders.py lays on the sky for this package: dict(skyline=, ridges=), GLSL text.
    The colours are the look's through the functions of include/fog.glsl."""
    ys = _crest_y()
    table = ",\n".join("    " + ", ".join(_f(v) for v in ys[i:i + 10]) for i in range(0, COLUMNS, 10))
    top = math.sin(math.radians(HIGHEST + STEP))
    return dict(skyline=SKYLINE_GLSL.format(start=_f(FROM), step=_f(STEP), columns=COLUMNS, top=_f(top), table=table),
                ridges=RIDGES_GLSL.format(veil=_f(math.sin(math.radians(VEIL)))))


def skyline(d):
    """c164_skyline() in numpy: d is (n, 3) unit directions (x east, y up, z south)."""
    d = np.asarray(d, dtype=float)
    column = np.floor((np.degrees(np.arctan2(-d[:, 2], -d[:, 0])) - FROM) / STEP)
    inside = (column >= 0) & (column <= COLUMNS - 1) & (np.abs(d[:, 0]) + np.abs(d[:, 2]) >= 1e-4) \
        & (d[:, 1] <= math.sin(math.radians(HIGHEST + STEP)))
    return np.where(inside, _crest_y()[np.clip(column, 0, COLUMNS - 1).astype(int)], -1.0)


def painted(colour, d, twin):
    """c164_ridges() in numpy: colour is (n, 3), what the sky shows in directions d; twin is the
    look's sky/_shaders.Twin."""
    d = np.asarray(d, dtype=float)
    across = np.maximum(np.hypot(d[:, 0], d[:, 2]), 1e-9)
    level = np.stack([d[:, 0] / across, np.zeros(len(d)), d[:, 2] / across], axis=1)
    e = np.clip(d[:, 1] / math.sin(math.radians(VEIL)), 0.0, 1.0)
    out = twin._mix(twin.band(level), twin.ring(level), e * e * (3.0 - 2.0 * e))
    covered = (d[:, 1] >= 0.0) & (d[:, 1] < skyline(d))
    return np.where(covered[:, None], out, np.asarray(colour, dtype=float))


def report(look=mood.DEFAULT):
    """Where the ranges stand as the shader has them, and how much of the afterglow's fan glows
    behind the ridge line: that share of the glow's colour is all a ridge is seen by."""
    from . import _shaders
    twin = _shaders.Twin(look)
    up = baked() * STEP
    bearing = FROM + (np.arange(COLUMNS) + 0.5) * STEP
    lines = [f"the ridge line: {COLUMNS} columns of {STEP:g} degrees from {FROM:g} degrees north of due west, in steps of "
             f"{STEP:g} degrees up, the same for every eye; look {look}"]
    for name, side in (("north", bearing > 0.0), ("south", bearing < 0.0)):
        here = side & (up > 0.0)
        a, e = np.radians(bearing[here]), np.radians(up[here])
        glow = twin.fan(np.stack([-np.cos(a) * np.cos(e), np.sin(e), -np.sin(a) * np.cos(e)], axis=1))
        top = int(np.argmax(np.where(here, up, -1.0)))
        lines.append(f"{name:6s} {bearing[here].min():6.1f} to {bearing[here].max():6.1f} north of west, up to {up[top]:.2f} degrees "
                     f"at {bearing[top]:.1f}, a ridge in {int(here.sum())} of {int(side.sum())} columns; "
                     f"the afterglow behind the ridge line {glow.min():.2f} to {glow.max():.2f}")
    return lines


if __name__ == "__main__":
    print("\n".join(report()))
