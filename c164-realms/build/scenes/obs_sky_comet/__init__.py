"""Test scene for the card sky/comet: what the comet is seen against, as a white model.

    python -m scenes.obs_sky_comet      writes shots.json and prints where the comet stands in
                                        every picture (the same for the scenes of versions b and c)

The moon's slot holds one picture per light, so the three versions cannot hang in one sky. They are
compared picture by picture: this scene shows version a, obs_sky_comet_b and obs_sky_comet_c show
the other two over the same blocks with the same shots, each under all three lights. This scene
takes one shot more, sky_card: the test card in the moon's slot, to see which way up the game
draws the picture.

White models in plain vanilla blocks of the occupancy table, enough to judge where the comet stands
and what hides it: the two terraces and the station platform (so that the eye stands somewhere),
the main bar, the drum and the great dome (its skin, crown and west slit by main/dome's numbers)
with the floor of the dome room, the clock tower with the time-ball mast, the small dome, the radio
mast on its stone foot.

The comet is always due west of the viewer, its head HEAD_ELEVATION up. It stands over the great
dome only for someone on the axis (V2, the lower platform); from the cable station (V1) due west
runs through the clock tower and the comet stands over the time-ball mast (A0 #19551). Both hero
views look up by about 22 degrees: as they were framed before, the top of the picture cut the comet
(V1: the head a tenth of the picture below its top edge, half of the tails outside).

In V1 the comet has two neighbours: the time-ball mast below its head and a little to the south,
and the radio mast to the north, whose beacon stands 6 degrees from the head and 3 degrees higher,
beside the lower part of the dust tail. around() measures both for the version shown. From V2 the
top line of the great dome is its near shoulder, not its apex; under_head() measures how far below
the comet's head the blocks end in both views.

The offline pictures prove position and what hides the comet; its colour and brightness against the
real sky are judged on the pictures from the game.
"""
import json
import math
import os

import numpy as np

from artkit.canvas import Canvas
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.sky import comet, mood

BIOME = "obs_blue"
BIOME_MARGIN = 120          # the look has to reach the far cameras, not only the blocks
BIOME_MARGIN_Y = 150

STYLE = "a"                 # the version this scene shows; the _b and _c scenes set their own

STONE = B.TUFF_SMOOTH.block          # the white model's stone
COPPER = B.VERDIGRIS                 # the dome shells, the time ball, the radio mast's beacon
DARK = B.SLATE_SMOOTH.block          # the ground, darker than the walls, and the two masts

FOV = 77.0                  # what the pictures are taken at: the option's 70, a tenth wider because
ASPECT = 16.0 / 9.0         # the camera player is flying (render.py, tools/shoot.py)

# The great dome as main/dome builds it (c222, group 11-15). Its skin is a half-ellipse 13.5 wide at
# the foot and 14 high over the centre cell. The observing slit takes z -2..2 and every column as
# far east as x 2; its sill is the row y 25, it is open from the row above. Over the nine columns
# about the axis lies the crown: a cover half a block thick in the row y 38 and, on the axis cell,
# the one block that stands highest on the whole dome (top face 39.0). Under the cover the nine
# columns are open, so the slit's head, seen from the room, is the western edge of the cover.
SLIT_SILL = S.DOME_SPRING + 1
SLIT_HEAD = 2
CROWN_Y = S.DOME_APEX + 1
CROWN_COVER = B.VERDIGRIS_CUT.slab + "[type=bottom]"

# The two hero views look up by about 22 degrees, so that the whole comet is in the picture and the
# building takes the lower half (A0 #24227, 11-14). They are the skeleton's locked cameras, read
# from it: tools/check.py names a shot that stands at one of them and looks elsewhere.
V1, V2 = S.V1, S.V2

# V8 looks out of the dome room through the slit. Its camera stands at the back of the observing
# floor beside the tube and looks due west, 25 degrees up (interiors/domeroom, c178, group 11-15):
# at z 2.2, south of a tube that lies on the axis; its other place, for a tube that hangs south of
# the axis, is z 0.2. The white model has no telescope, the shot shows what the slit lets through.
V8 = getattr(S, "V8", None) or dict(pos=(11.8, S.PIER_TOP_Y + S.EYE, 2.2), look_at=(-6.3, 28.06, 2.2))

# name: (eye, look_at)
CAMERAS = {
    "v1": (V1["pos"], V1["look_at"]),                # from the cable station: the comet over the clock tower
    "v2": (V2["pos"], V2["look_at"]),                # on the axis in the forecourt: over the great dome
    "axislow": ((82.5, S.LOWER_GROUND + S.EYE, 0.5), (4.5, 22.0, 0.5)),       # on the axis, lower platform
    "slit": (V8["pos"], V8["look_at"]),                                        # V8, out of the dome room
    "sky": ((-30.0, S.GROUND + S.EYE, 0.5), (-130.0, 110.0, 0.5)),             # the comet alone
}


def write_pack(pack_dir):
    """Only the comet's pictures: the white model is plain vanilla blocks, nothing repainted."""
    return comet.pack(pack_dir, STYLE)


def shots(card=True):
    """Every camera under every light. With card, the west close-up once more at the tick of the test
    card (mood.TRIALS): which way up the game draws the moon's picture is read off it. The card is
    the same in the three versions, so only this scene takes it."""
    out = [dict(name=f"{name}_{look}", pos=list(pos), look_at=list(at), time=mood.tick(look))
           for name, (pos, at) in CAMERAS.items() for look in mood.LOOKS]
    if card:
        pos, at = CAMERAS["sky"]
        out.append(dict(name="sky_card", pos=list(pos), look_at=list(at), time=mood.TRIALS["card"]["tick"]))
    return out


def _walls(c, x0, z0, x1, z1, y0, y1, block):
    """A one-block-thick wall around the rectangle."""
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            c.set(x, y, z0, block)
            c.set(x, y, z1, block)
        for z in range(z0, z1 + 1):
            c.set(x0, y, z, block)
            c.set(x1, y, z, block)


def _slab(c, box, y, block):
    x0, z0, x1, z1 = box
    c.box(x0, y, z0, x1, y, z1, block)


def _ring(c, cx, cz, r, y0, y1, block):
    cells = set()
    for a in range(0, 360, 2):
        cells.add((int(round(cx + r * math.cos(math.radians(a)))),
                   int(round(cz + r * math.sin(math.radians(a))))))
    for y in range(y0, y1 + 1):
        for x, z in cells:
            c.set(x, y, z, block)


def _dome(c, cx, cz, y0, y1, radius_at, block):
    """A shell one block thick and closed at the top: at every level the cells within that level's
    radius that the level above does not cover."""
    for y in range(y0, y1 + 1):
        r = radius_at(y) or 0.0
        above = (radius_at(y + 1) or 0.0) if y < y1 else -1.0
        reach = int(math.ceil(r)) + 1
        for x in range(int(math.floor(cx)) - reach, int(math.ceil(cx)) + reach + 1):
            for z in range(int(math.floor(cz)) - reach, int(math.ceil(cz)) + reach + 1):
                if above - 0.5 < math.hypot(x - cx, z - cz) <= r + 0.5:
                    c.set(x, y, z, block)


def _ground(c):
    _slab(c, S.UPPER_TERRACE, S.GROUND - 1, DARK)
    _slab(c, S.LOWER_PLATFORM, S.LOWER_GROUND - 1, DARK)
    x0, z0, x1, z1 = S.CABLE_STATION
    c.box(x0, S.LOWER_GROUND, z0, x1, S.STATION_GROUND - 1, z1, DARK)
    x0, z0, x1, z1 = S.LOWER_PLATFORM                      # the retaining wall under the terrace's edge
    c.box(x0 - 1, S.LOWER_GROUND - 1, z0, x0 - 1, S.GROUND - 1, z1, DARK)


def _main_bar(c):
    _walls(c, S.WALL_W, S.Z_NORTH, S.WALL_E, S.Z_SOUTH, S.GROUND, S.CORNICE, STONE)
    for j in range(1, S.N_BAYS + 1):
        xe = S.east_wall_x(j)
        for z in range(S.pilaster_z(j - 1), S.pilaster_z(j) + 1):
            for y in range(S.GROUND, S.CORNICE + 1):
                c.set(xe, y, z, STONE)
    _slab(c, (S.WALL_W, S.Z_NORTH, S.WALL_E, S.Z_SOUTH), S.ROOF_FLOOR, STONE)


def _great_dome(c):
    """The shell of the great dome in whole blocks, one block thick: every column reaches up to the
    skin (to the nearer side) and down to the top of its lowest neighbour. Then the crown and the
    west observing slit, SLIT_W wide on the axis, open above its sill as far as its head."""
    cx, cz = S.DOME_CENTRE
    foot, r, rise = S.DOME_SPRING, S.DOME_R + 0.5, S.DOME_APEX + 1.0 - S.DOME_SPRING
    tops = {}
    for x in range(cx - S.DOME_R - 1, cx + S.DOME_R + 2):
        for z in range(cz - S.DOME_R - 1, cz + S.DOME_R + 2):
            d = math.hypot(x - cx, z - cz)
            if d < r:
                tops[(x, z)] = int(math.floor(foot + rise * math.sqrt(1.0 - (d / r) ** 2) - 0.5))
    for (x, z), top in tops.items():
        if max(abs(x - cx), abs(z - cz)) <= 1:              # open under the crown
            continue
        lows = [tops.get(n, foot - 1) for n in ((x - 1, z), (x + 1, z), (x, z - 1), (x, z + 1))]
        for y in range(max(foot, min(top, min(lows) + 1)), top + 1):
            c.set(x, y, z, COPPER)
    for x in range(cx - 1, cx + 2):
        for z in range(cz - 1, cz + 2):
            c.set(x, CROWN_Y, z, COPPER if (x, z) == (cx, cz) else CROWN_COVER)
    half = S.SLIT_W // 2
    c.carve(cx - S.DOME_R - 1, SLIT_SILL + 1, cz - half, SLIT_HEAD, CROWN_Y, cz + half)


def _rotunda_and_dome(c):
    cx, cz = S.DOME_CENTRE
    _ring(c, cx, cz, S.DOME_R, S.GROUND, S.DOME_SPRING - 1, STONE)
    for x in range(cx - S.DOME_R, cx + S.DOME_R + 1):       # the floor of the dome room
        for z in range(cz - S.DOME_R, cz + S.DOME_R + 1):
            if math.hypot(x - cx, z - cz) < S.DOME_R - 0.5:
                c.set(x, S.ROOF_FLOOR, z, STONE)
    _great_dome(c)


def _clock_tower(c):
    x0, x1 = S.CLOCK_SHAFT_X
    z0, z1 = S.CLOCK_SHAFT_Z
    _walls(c, x0, z0, x1, z1, S.GROUND, S.CLOCK_TOP, STONE)
    _slab(c, (x0, z0, x1, z1), S.CLOCK_TOP, STONE)
    mx, mz = (x0 + x1) // 2, (z0 + z1) // 2       # the time-ball mast, which the comet stands over in V1
    for y in range(S.CLOCK_TOP + 1, S.CLOCK_BALL_MAST + 1):
        c.set(mx, y, mz, DARK)
    c.box(mx - 1, S.CLOCK_BALL_MAST - 2, mz, mx + 1, S.CLOCK_BALL_MAST - 2, mz, COPPER)    # the time ball


def _small_dome(c):
    cx = (S.SMALL_DOME_X[0] + S.SMALL_DOME_X[1]) / 2.0
    cz = (S.SMALL_DOME_Z[0] + S.SMALL_DOME_Z[1]) / 2.0

    def profile(y):
        t = (y - S.SMALL_DRUM_BASE) / float(S.SMALL_DOME_APEX - S.SMALL_DRUM_BASE)
        return S.SMALL_DOME_R * math.sqrt(max(0.0, 1.0 - t * t))

    _dome(c, cx, cz, S.SMALL_DRUM_BASE, S.SMALL_DOME_APEX, profile, COPPER)


def _radio_mast(c):
    """The radio mast (machines/radiomast) as its four legs with a belt every six blocks, the needle
    and the beacon, on the two steps of its stone foot (site/mastbase: centred on the skeleton's
    foot cell, the legs on the corners of the upper step, from y 2). From V1 it stands a little
    north of due west and reaches as high as the comet's head, so it is the comet's neighbour in
    that picture. The real legs are thinner and the lattice between them is open; whatever these
    blocks leave free, the real mast does too."""
    x0, z0, x1, z1 = S.MAST_PAD["box"]
    feet = S.MAST_PAD["feet"]
    c.box(x0, S.LOWER_GROUND - 1, z0, x1, feet - 1, z1, DARK)
    fx, fz = S.RADIO_MAST["foot"]
    c.box(fx - 2, feet, fz - 2, fx + 2, feet, fz + 2, DARK)
    c.box(fx - 1, feet + 1, fz - 1, fx + 1, feet + 1, fz + 1, DARK)
    foot, top = feet + 2, feet + S.RADIO_MAST["height"]
    for y in range(foot, top - 2):
        for x in (fx - 1, fx + 1):
            for z in (fz - 1, fz + 1):
                c.set(x, y, z, DARK)
        if (y - foot) % 6 == 0 and y > foot:
            c.box(fx - 1, y, fz - 1, fx + 1, y, fz + 1, DARK)
    c.set(fx, top - 2, fz, DARK)                   # the needle
    c.set(fx, top - 1, fz, COPPER)                 # the beacon


def build():
    c = Canvas()
    _ground(c)
    _main_bar(c)
    _rotunda_and_dome(c)
    _clock_tower(c)
    _small_dome(c)
    _radio_mast(c)
    c.entity_counts = {}
    return c


# --- where the comet stands in a picture: position and what hides it, without drawing anything ------

def _camera(pos, look_at):
    """Eye, forward, right, up: the camera of artkit.gamescene.Scene.camera."""
    pos = np.array(pos, dtype=float)
    f = np.array(look_at, dtype=float) - pos
    f /= np.linalg.norm(f)
    r = np.cross(f, (0.0, 1.0, 0.0))
    r /= np.linalg.norm(r)
    return pos, f, r, np.cross(r, f)


def _on_screen(cam, d):
    """Directions (..., 3) -> (right, up) in -1..1 across the picture, and whether in the picture."""
    _, f, r, u = cam
    half = math.tan(math.radians(FOV) / 2.0)
    along = d @ f
    safe = np.where(along > 1e-6, along, 1.0)
    sx, sy = (d @ r) / safe / (half * ASPECT), (d @ u) / safe / half
    return sx, sy, (along > 1e-6) & (np.abs(sx) < 1.0) & (np.abs(sy) < 1.0)


def _west(elevation):
    e = np.radians(elevation)
    return np.stack([-np.cos(e), np.sin(e), np.zeros_like(e)], axis=-1)


def _solid(c):
    (x0, y0, z0), (x1, y1, z1) = c.bounds()
    lo = np.array([x0, y0, z0])
    grid = np.zeros((x1 - x0 + 1, y1 - y0 + 1, z1 - z0 + 1), dtype=bool)
    for (x, y, z) in c.b:
        grid[x - x0, y - y0, z - z0] = True
    return lo, grid


def _hidden(solid, eye, d, step=0.2, reach=None):
    """True where a block stands on the way from the eye along the directions d (..., 3), as far as
    reach (everything the scene holds when it is not given)."""
    lo, grid = solid
    shape = np.array(grid.shape)
    d = d / np.linalg.norm(d, axis=-1, keepdims=True)
    hit = np.zeros(d.shape[:-1], dtype=bool)
    if reach is None:
        reach = float(np.linalg.norm(shape)) + float(np.linalg.norm(np.maximum(lo - eye, 0.0))) + 8.0
    for t in np.arange(0.5, reach, step):
        cell = np.floor(eye + d * t).astype(int) - lo
        inside = ((cell >= 0) & (cell < shape)).all(axis=-1)
        at = np.where(inside[..., None], cell, 0)
        hit |= inside & grid[at[..., 0], at[..., 1], at[..., 2]]
    return hit


def where(style=None, canvas=None):
    """For every camera and light: where the head is in the picture, how much sky the picture has
    above it, what share of the comet's light is in the picture, hidden by blocks, or cut off by
    the picture's edge, and how much of the picture its bright part and the whole of it take
    (comet.report() says what counts as bright; towards the picture's edge the wide angle stretches
    everything, the comet with it). A list of dicts; nothing is drawn."""
    style = style or STYLE
    solid = _solid(canvas or build())
    d = comet.directions()
    head = _west(np.array(comet.HEAD_ELEVATION))
    above = _west(comet.HEAD_ELEVATION + np.arange(0.0, 30.0, 0.05))
    out = []
    for name, (pos, at) in CAMERAS.items():
        cam = _camera(pos, at)
        sx, sy, inside = _on_screen(cam, d)
        hidden = _hidden(solid, cam[0], d[::4, ::4]).repeat(4, axis=0).repeat(4, axis=1)
        hx, hy, head_in = _on_screen(cam, head)
        _, _, sky_in = _on_screen(cam, above)
        room = float(np.argmin(sky_in) * 0.05) if not sky_in.all() else 30.0
        # the share of the picture one pixel of the square covers
        area = np.abs(np.gradient(sx, axis=1) * np.gradient(sy, axis=0)
                      - np.gradient(sx, axis=0) * np.gradient(sy, axis=1)) / 4.0
        for look in mood.LOOKS:
            grey = comet.luma(comet.comet(style, comet.STRENGTH[look], comet.TAIL[look]))
            total = float(grey.sum())
            seen = inside & ~hidden
            out.append(dict(
                camera=name, look=look, head_in=bool(head_in), head_x=float((hx + 1.0) / 2.0),
                head_y=float((1.0 - hy) / 2.0), head_hidden=bool(_hidden(solid, cam[0], head[None])[0]),
                room=room, seen=float(grey[seen].sum() / total), hidden=float(grey[inside & hidden].sum() / total),
                cut=float(grey[~inside].sum() / total),
                bright=float(area[seen & (grey + comet.sky_behind(look) >= comet.WASHED)].sum()),
                lit=float(area[seen & (grey >= comet.SEEN)].sum())))
    return out


def _tops():
    """The tops of the two masts that reach up towards the comet in V1."""
    fx, fz = S.RADIO_MAST["foot"]
    (x0, x1), (z0, z1) = S.CLOCK_SHAFT_X, S.CLOCK_SHAFT_Z
    return {
        "radio mast, beacon": (fx + 0.5, S.MAST_PAD["feet"] + S.RADIO_MAST["height"] - 0.5, fz + 0.5),
        "time-ball mast": ((x0 + x1) // 2 + 0.5, S.CLOCK_BALL_MAST + 1.0, (z0 + z1) // 2 + 0.5),
    }


def under_head(canvas=None, cameras=("v1", "v2")):
    """How high the blocks reach right under the comet's head in the hero views: {camera: the
    highest elevation, due west of the eye, at which a block stands; None when there is none}. A
    dome seen from below shows its near shoulder as its top, not its apex: from V2 the comet
    stands over that line, and the crown on the axis is out of sight behind it."""
    solid = _solid(canvas or build())
    up = np.arange(0.0, comet.HEAD_ELEVATION, 0.1)
    out = {}
    for camera in cameras:
        hidden = _hidden(solid, np.array(CAMERAS[camera][0], dtype=float), _west(up), step=0.1)
        out[camera] = float(up[hidden][-1]) if hidden.any() else None
    return out


def around(style=None, cameras=("v1",)):
    """The comet's neighbours in a hero view. For every camera and every top of _tops(): how far
    north of due west it stands and how high (degrees), how far it is from the comet's head, and
    how far from the nearest of the comet's light at its longest (look deep). A list of dicts."""
    style = style or STYLE
    lit, _ = comet.light(style)
    head = _west(np.array(comet.HEAD_ELEVATION))
    out = []
    for camera in cameras:
        eye = np.array(CAMERAS[camera][0], dtype=float)
        for name, point in _tops().items():
            d = np.array(point, dtype=float) - eye
            d /= np.linalg.norm(d)
            out.append(dict(
                camera=camera, name=name, north=math.degrees(math.atan2(-d[2], -d[0])),
                up=math.degrees(math.asin(d[1])),
                head=math.degrees(math.acos(min(1.0, float(d @ head)))),
                light=math.degrees(math.acos(min(1.0, float((lit @ d).max()))))))
    return out


# z of an eye in the dome room, across the slit; 2.2 and 0.2 are the two places of the V8 camera
SLIT_EYES = (-1.5, -1.0, -0.5, 0.2, 0.5, 1.5, 2.2, 2.5, 3.0)
ROOM_EYES = (8.5, 10.5, 12.5, 14.5)        # x of an eye in the dome room, from the pier to the east wall
ROOM_REACH = 2.0 * S.DOME_R + 8.0          # from an eye in the room, nothing farther hides the sky


def _longest(style):
    """The comet at its longest (look deep), every second pixel: directions and grey of the lit ones."""
    grey = comet.luma(comet.comet(style, comet.STRENGTH["deep"], comet.TAIL["deep"]))[::2, ::2]
    lit = grey >= comet.SEEN
    return comet.directions()[::2, ::2][lit], grey[lit]


def _from_room(solid, eye, d, grey):
    """(share of the comet's light seen, head seen) for an eye in the dome room."""
    hidden = _hidden(solid, eye, d, reach=ROOM_REACH)
    head = _west(np.array(comet.HEAD_ELEVATION))[None]
    return float(grey[~hidden].sum() / grey.sum()), not bool(_hidden(solid, eye, head, reach=ROOM_REACH)[0])


def through_slit(style=None, canvas=None):
    """How much of the comet's light at its longest (look deep) an eye in the dome room sees through
    the slit, standing at the height and x of the camera 'slit', anywhere across the slit: [(z,
    share seen, head seen)]. The slit is SLIT_W wide about the axis (z 0.5); the dust tail leans
    north, so the room is on the south."""
    solid = _solid(canvas or build())
    d, grey = _longest(style or STYLE)
    x, y, _ = CAMERAS["slit"][0]
    return [(z,) + _from_room(solid, np.array([x, y, z]), d, grey) for z in SLIT_EYES]


def sky_in_slit(eyes=ROOM_EYES, canvas=None):
    """How high the sky is seen through the slit, due west, by an eye on the axis at V8's height:
    [highest elevation seen, for each x of eyes]. The comet's tails end at comet.report()'s tip; a
    slit whose head stood lower would cut them for an eye far east in the room."""
    solid = _solid(canvas or build())
    up = np.arange(comet.HEAD_ELEVATION, 90.0, 0.25)
    d = _west(up)
    y, z = CAMERAS["slit"][0][1], S.DOME_AXIS[1]
    out = []
    for x in eyes:
        hidden = _hidden(solid, np.array([x, y, z]), d, step=0.1, reach=ROOM_REACH)
        out.append(float(up[np.argmax(hidden)]) if hidden.any() else 90.0)
    return out


def tell(style, folder, shots=shots):
    """What python -m <scene> does: write the scene's shots.json and print where the comet stands."""
    path = os.path.join(folder, "shots.json")
    with open(path, "w") as fh:
        fh.write("[\n" + ",\n".join(" " + json.dumps(s) for s in shots()) + "\n]\n")
    print(f"{len(shots())} shots -> {path}")
    print(f"version {style}; head {comet.HEAD_ELEVATION:.2f} degrees up, due west; pictures at fov {FOV:g}")
    print("camera   light  head: from left, from top    sky above the head   light: seen / hidden / cut off"
          "   bright part, whole comet (share of the picture)")
    canvas = build()
    for r in where(style, canvas):
        head = (f"{100 * r['head_x']:3.0f}%  {100 * r['head_y']:3.0f}%" + (" behind blocks" if r["head_hidden"] else "")
                if r["head_in"] else "outside the picture")
        print(f"{r['camera']:8s} {r['look']:5s}  {head:28s} {r['room']:5.1f} deg        "
              f"{100 * r['seen']:3.0f}% / {100 * r['hidden']:3.0f}% / {100 * r['cut']:3.0f}%"
              f"        {100 * r['bright']:.3f}%, {100 * r['lit']:.3f}%")
    print("the comet's neighbours   north of due west, up   from the head   from the comet's light (look deep)")
    for r in around(style):
        print(f"{r['camera']:8s} {r['name']:20s} {r['north']:6.1f}  {r['up']:5.1f} deg     {r['head']:5.1f} deg       {r['light']:5.1f} deg")
    low = comet.reach(style)[2]
    for camera, top in under_head(canvas).items():
        print(f"{camera:8s} under the head, due west, blocks reach up to " + ("nothing" if top is None else
              f"{top:.1f} deg: the head stands {comet.HEAD_ELEVATION - top:.1f} above them, the comet's light begins {low - top:.1f} above"))
    print(f"through the slit, the eye at x {CAMERAS['slit'][0][0]:g} (axis z 0.5; look deep): z of the eye, share of the comet's light seen")
    print("   " + "   ".join(f"{z:+.1f}: {100 * seen:3.0f}%" + ("" if head else " head hidden")
                             for z, seen, head in through_slit(style, canvas)))
    tips = ", ".join(f"{r['look']} {r['tip']:.1f}" for r in comet.report(style))
    print(f"the sky in the slit (open as far as x {SLIT_HEAD}), due west, from the axis: the highest elevation seen "
          f"(the tails end at {tips})")
    print("   " + "   ".join(f"eye at x {x:g}: {e:.1f} deg" for x, e in zip(ROOM_EYES, sky_in_slit(canvas=canvas))))
