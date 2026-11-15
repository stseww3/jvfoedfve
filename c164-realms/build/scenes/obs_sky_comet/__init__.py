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
the main bar, the drum and the great dome with its west slit open and the floor of the dome room,
the clock tower with the time-ball mast, the small dome, the radio mast on its pad.

The comet is always due west of the viewer, its head HEAD_ELEVATION up. It stands over the great
dome only for someone on the axis (V2, the lower platform); from the cable station (V1) due west
runs through the clock tower and the comet stands over the time-ball mast (A0 #19551). Both hero
views look up by about 22 degrees: as they were framed before, the top of the picture cut the comet
(V1: the head a tenth of the picture below its top edge, half of the tails outside).

In V1 the comet has two neighbours: the time-ball mast below its head and a little to the south,
and the radio mast to the north, whose beacon stands 6 degrees from the head and 3 degrees higher,
beside the lower part of the dust tail. around() measures both for the version shown.

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

# The observing slit as main/_dome builds it: its sill is the row y 25, it is open from the row
# above, and its last column eastwards is two past the apex. The head is being moved west of the
# apex (main/dome, A0's ruling that the dome keeps one apex on the axis); through_slit_head() says
# what each column costs the comet.
SLIT_SILL = S.DOME_SPRING + 1
SLIT_HEAD = S.DOME_CENTRE[0] + 2

# The two hero views look up by about 22 degrees, so that the whole comet is in the picture and the
# building takes the lower half (A0 #24227, 11-14): V1 keeps its place and looks at (8, 34, 0.5), V2
# stands at (58.5, 1.7, 0.5) and looks at (17, 19, 0.5). The skeleton is being changed to say so
# (S2); it is read here as soon as it does, until then the ruled numbers stand below.
V1 = S.V1 if S.V1["look_at"][1] >= 30 else dict(pos=S.V1["pos"], look_at=(8, 34, 0.5))
V2 = getattr(S, "V2", None) or dict(pos=(58.5, 1.7, 0.5), look_at=(17, 19, 0.5))

# name: (eye, look_at)
CAMERAS = {
    "v1": (V1["pos"], V1["look_at"]),                # from the cable station: the comet over the clock tower
    "v2": (V2["pos"], V2["look_at"]),                # on the axis in the forecourt: over the apex of the dome
    "axislow": ((82.5, S.LOWER_GROUND + S.EYE, 0.5), (4.5, 22.0, 0.5)),       # on the axis, lower platform
    "slit": ((8.5, S.PIER_TOP_Y + S.EYE, 0.5), (-29.5, 58.0, 0.5)),            # V8, out of the dome room
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


def _rotunda_and_dome(c, slit_head=None):
    slit_head = SLIT_HEAD if slit_head is None else slit_head
    cx, cz = S.DOME_CENTRE
    _ring(c, cx, cz, S.DOME_R, S.GROUND, S.DOME_SPRING - 1, STONE)
    _dome(c, cx, cz, S.DOME_SPRING, S.DOME_APEX, S.dome_profile, COPPER)
    for x in range(cx - S.DOME_R, cx + S.DOME_R + 1):       # the floor of the dome room
        for z in range(cz - S.DOME_R, cz + S.DOME_R + 1):
            if math.hypot(x - cx, z - cz) < S.DOME_R - 0.5:
                c.set(x, S.ROOF_FLOOR, z, STONE)
    # the west observing slit, SLIT_W wide on the axis, open above its sill as far as its head
    half = S.SLIT_W // 2
    z0, z1 = round(S.DOME_AXIS[1]) - half, round(S.DOME_AXIS[1]) + half
    c.carve(cx - S.DOME_R - 1, SLIT_SILL + 1, z0, slit_head, S.DOME_APEX + 1, z1)


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


def build(slit_head=None):
    c = Canvas()
    _ground(c)
    _main_bar(c)
    _rotunda_and_dome(c, slit_head)
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


def _square(n):
    """Directions through the centres of an n x n grid over the moon's square, as seen: row 0 is its
    top, column 0 its south side. The quad is flat, half-size 20 at distance 100 (SkyRenderer)."""
    th = math.radians(mood.MOON_ANGLE)
    centre = np.array([-math.sin(th), math.cos(th), 0.0])
    north, up = np.array([0.0, 0.0, -1.0]), np.array([math.cos(th), math.sin(th), 0.0])
    k = ((np.arange(n) + 0.5) / n * 2.0 - 1.0) * 0.2
    return centre + k[None, :, None] * north + (-k)[:, None, None] * up


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
    n = comet.SIZE
    d = _square(n)
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
    """The highest point of whatever reaches up towards the comet in the hero views."""
    fx, fz = S.RADIO_MAST["foot"]
    (x0, x1), (z0, z1) = S.CLOCK_SHAFT_X, S.CLOCK_SHAFT_Z
    return {
        "radio mast, beacon": (fx + 0.5, S.MAST_PAD["feet"] + S.RADIO_MAST["height"] - 0.5, fz + 0.5),
        "time-ball mast": ((x0 + x1) // 2 + 0.5, S.CLOCK_BALL_MAST + 1.0, (z0 + z1) // 2 + 0.5),
        "great dome, apex": (S.DOME_AXIS[0], S.DOME_APEX + 1.0, S.DOME_AXIS[1]),
    }


def around(style=None, cameras=("v1", "v2")):
    """The comet's neighbours in the hero views. For every camera and every top of _tops(): how far
    north of due west it stands and how high (degrees), how far it is from the comet's head, and
    how far from the nearest of the comet's light at its longest (look deep). A list of dicts."""
    style = style or STYLE
    lit = _square(comet.SIZE)[comet.luma(comet.comet(style, comet.STRENGTH["deep"], comet.TAIL["deep"])) >= comet.SEEN]
    lit = lit / np.linalg.norm(lit, axis=-1, keepdims=True)
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


SLIT_EYES = (-1.5, -1.0, -0.5, 0.0, 0.5, 1.5, 2.5, 3.0)       # z of an eye in the dome room, across the slit


def through_slit(style=None, canvas=None):
    """How much of the comet's light at its longest (look deep) an eye in the dome room sees through
    the slit, standing at the height and x of the camera 'slit' but off the axis: [(z, share seen,
    head seen)]. The slit is SLIT_W wide; the dust tail leans north, so the room is on the south."""
    style = style or STYLE
    solid = _solid(canvas or build())
    grey = comet.luma(comet.comet(style, comet.STRENGTH["deep"], comet.TAIL["deep"]))[::2, ::2]
    lit = grey >= comet.SEEN
    d, grey = _square(comet.SIZE)[::2, ::2][lit], grey[lit]
    head = _west(np.array(comet.HEAD_ELEVATION))[None]
    x, y, _ = CAMERAS["slit"][0]
    out = []
    for z in SLIT_EYES:
        eye = np.array([x, y, z])
        hidden = _hidden(solid, eye, d, reach=2.0 * S.DOME_R + 8.0)
        out.append((z, float(grey[~hidden].sum() / grey.sum()),
                    not bool(_hidden(solid, eye, head, reach=2.0 * S.DOME_R + 8.0)[0])))
    return out


SLIT_HEADS = (0, 1, 2, 3, SLIT_HEAD)       # last open column of the slit; the apex stands in column 4
ROOM_EYES = (8.5, 10.5, 12.5, 14.5)        # x of an eye in the dome room, from the pier to the east wall


def sky_in_slit(heads=SLIT_HEADS, eyes=ROOM_EYES):
    """How high the sky is seen through the slit, due west, by an eye on the axis at V8's height:
    {last open column of the slit: [highest elevation seen, for each x of eyes]}. The comet's tails
    end at comet.report()'s tip; a slit that stops short of the apex cuts them for an eye far east."""
    up = np.arange(comet.HEAD_ELEVATION, 90.0, 0.25)
    d = _west(up)
    _, y, z = CAMERAS["slit"][0]
    out = {}
    for head in heads:
        solid = _solid(build(slit_head=head))
        row = []
        for x in eyes:
            hidden = _hidden(solid, np.array([x, y, z]), d, step=0.1, reach=2.0 * S.DOME_R + 8.0)
            row.append(float(up[np.argmax(hidden)]) if hidden.any() else 90.0)
        out[head] = row
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
    for r in where(style):
        head = (f"{100 * r['head_x']:3.0f}%  {100 * r['head_y']:3.0f}%" + (" behind blocks" if r["head_hidden"] else "")
                if r["head_in"] else "outside the picture")
        print(f"{r['camera']:8s} {r['look']:5s}  {head:28s} {r['room']:5.1f} deg        "
              f"{100 * r['seen']:3.0f}% / {100 * r['hidden']:3.0f}% / {100 * r['cut']:3.0f}%"
              f"        {100 * r['bright']:.3f}%, {100 * r['lit']:.3f}%")
    print("the comet's neighbours   north of due west, up   from the head   from the comet's light (look deep)")
    for r in around(style):
        print(f"{r['camera']:8s} {r['name']:20s} {r['north']:6.1f}  {r['up']:5.1f} deg     {r['head']:5.1f} deg       {r['light']:5.1f} deg")
    print("through the slit, the eye off the axis (axis z 0.5; look deep): z of the eye, share of the comet's light seen")
    print("   " + "   ".join(f"{z:+.1f}: {100 * seen:3.0f}%" + ("" if head else " head hidden") for z, seen, head in through_slit(style)))
    tips = ", ".join(f"{r['look']} {r['tip']:.1f}" for r in comet.report(style))
    print(f"the sky in the slit, due west: the highest elevation seen (the tails end at {tips})")
    print("slit open as far as x     " + "".join(f"eye at x {x:<8g}" for x in ROOM_EYES))
    for head, row in sky_in_slit().items():
        print(f"{head:>12d}{' (now)' if head == SLIT_HEAD else '      '}        " + "".join(f"{e:5.1f} deg        " for e in row))
