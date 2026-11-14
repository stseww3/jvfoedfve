"""props/ironwork -- the door and window ironwork of the observatory (plan ART-PLAN 7.3, part A6,
card plan/packages/props/ironwork.md).

All cast and riveted iron on the common palette, 16 texels to the block (px = scale):

    window_arch, _2      the iron frame of a great arched window, three or two blocks wide. Iron only:
                         it is pressed on A1's glazed pane and stands where that pane's 8 px net
                         runs. Jambs 2 px on the glass and 6 px deep in the stone reveal, a riveted
                         plate over the bottom row of lights, a transom on the 4.0 line, a half
                         round head, riveted sheet in the spandrels.
    window_grille, _2    the barred grille of a base-storey window: a bar on every upright muntin.
    door_frame           the entrance doorway's frame (the window's, without the foot plate) and its
                         fanlight: an iron fan over amber glass.
    door_leaf            one leaf of the entrance door: riveted plate, kick plate, two ledges, a
                         brass pull and a glazed porthole; both faces alike. leaves() hangs a pair
                         open against the reveals, so a player walks through.
    gate                 a side arch of the entrance, shut: the same frame, an open fan, barred leaves.
    glazed_leaf          one leaf of the west door: riveted below, dark glass above.
    canopy, canopy_lamp  the glazed canopy over the middle arch on two quarter-round braces, and the
                         opal lamp under it.
    railing_panel        a cast scroll panel for the terrace balustrade, between two posts.
    ladder, ladder_cage  a three-block length of the inspection ladder, bare and caged; they stack.
    vent_cowl            a roof vent: a flanged pipe, a bent neck and a bell mouth.
    grate_hatch          a floor grating with a ring pull.

Everything is placed through _kit (mounting, materials, rivets, glowing glass). windows() and
doors() dress a wall from the tables main/_plan gives; build() does that for the main building.

The look is judged on texture and on style, so the test scene is build/scenes/obs_props_ironwork.
"""
import functools
import math

from artkit import models as M

from ..common import blocks as B
from ..common import palette as P
from . import _kit as K

PREFIX = "prop_iron_"
DRESS = False                    # build() dresses the master scene only when on: off until the family
                                 # has passed review on the real wall (the test scene shows it meanwhile)

IRON, IRON_D = K.IRON, K.IRON_D
BRASS, BRASS_D = K.BRASS, K.BRASS_D
GLASS_HOT, GLASS_MID, GLASS_DIM = K.GLOW_HOT, K.GLOW_MID, K.GLOW_DIM     # amber glass that glows
GLASS_COOL = K.flat("opal", 2)                                          # frosted canopy glass, not lit


# ---- the arched window frame ------------------------------------------------------------------------
# A1's glass is drawn on an 8 px net: seen from outside, an upright muntin in the first pixel column of
# every half block (none on the right edge) and a level one in the top row of every half block (none
# at the foot). The iron presses on that net and starts no net of its own (c205 #20557, c219 #20858):
# a member covers two pixels of glass at most or a whole light, and it stands where a muntin runs.
DEEP = 3.0          # the frame stands 6 px proud of the glass, inside the stone reveal (units of 2 px)
SILL = 1.5          # the riveted plate at the foot: 3 px proud
SHEET = 1.0         # the riveted sheet in the spandrels: 2 px
SPRING = 32.0       # the middle of the transom, on the 4.0 block line: the arch springs from it
JAMBS = (1.5, 1.0)  # left, right: 3 px over the pane's edge muntin and 2 px of glass; both end lights keep 5
PLATE = P.mat("iron_dark", bevel=0)     # sheet made of several boxes: no edge is drawn where two meet


def _muntins(hw):
    """x of the pane's upright muntins between the jambs, in units of 2 px from the middle."""
    return [-hw + 4.0 * k for k in range(1, int(hw) // 2)]


def _sheet(m, hw, r_out, r_in, top, mat=PLATE):
    """Riveted sheet over all that lies outside the arch ring, up to `top`: rows of boxes whose inner
    ends lie under the ring, so no light is left between the iron and the stone above the springing
    and the glass keeps the clean half round. r_in is the widest the ring's soffit gets."""
    m._n += 1
    seed, gap, y = m._n, r_out * r_out - r_in * r_in, 0.0
    while y < r_in:
        h = 0.5
        while (y + h + 0.5) ** 2 - y * y <= gap and y + h < r_in:
            h += 0.5
        inner = (math.sqrt(max(0.0, r_in * r_in - y * y)) + math.sqrt(max(0.0, r_out * r_out - (y + h) ** 2))) / 2.0
        if hw - inner >= 0.5:
            for sx in (-1.0, 1.0):
                a, b = sorted((sx * inner, sx * hw))
                m.box((a, SPRING + y, 0.0), (b, SPRING + y + h, SHEET), mat, seed=seed, grain="x")
        y += h
    m.box((-hw, SPRING + y, 0.0), (hw, top, SHEET), mat, seed=seed, grain="x")


# rivets on the spandrel sheet, where the stone head leaves it in sight: the slot under the crown and
# the corners beside the ring (x, y in units; the stone head steps in at 5.0 and at 5.5 blocks)
SHEET_RIVETS = {
    3: [(-3.0, 46.0), (0.0, 46.0), (3.0, 46.0), (-7.0, 43.0), (7.0, 43.0), (-11.0, 39.0), (11.0, 39.0)],
    2: [(-2.5, 42.0), (0.0, 42.0), (2.5, 42.0), (-6.5, 38.5), (6.5, 38.5)],
}


def _head(m, width, top=48.0):
    """The round head the windows and the doorways share: a half ring that springs from the 4.0 line,
    2 px on the glass and 6 px deep, and riveted sheet in the spandrels. Returns the soffit radius."""
    hw = width * 4.0
    sides = 32 if width >= 3 else 24
    m.ring("z", (0.0, SPRING, DEEP / 2.0), hw - 0.5, 1.0, DEEP, IRON, sides=sides, arc=(0.0, 180.0))
    _sheet(m, hw, hw, (hw - 1.0) / math.cos(math.pi / sides), top)
    for x, y in SHEET_RIVETS[width]:
        K.rivet(m, (x, y, SHEET))
    return hw - 1.0


def _frame(m, width, foot=True, jambs=JAMBS):
    """Jambs, transom and head of a `width`-block arched opening six blocks high; with `foot`, the
    riveted plate over the bottom row of lights, its top edge on the pane's first level muntin."""
    hw = width * 4.0
    left, right = jambs
    m.box((-hw, 0.0, 0.0), (-hw + left, SPRING, DEEP), IRON, grain="y")
    m.box((hw - right, 0.0, 0.0), (hw, SPRING, DEEP), IRON, grain="y")
    m.box((-hw, SPRING - 1.0, 0.0), (hw, SPRING + 1.0, DEEP), IRON, grain="x")
    if foot:
        m.box((-hw + left, 0.0, 0.0), (hw - right, 4.0, SILL), IRON_D, grain="x")
    for x in _muntins(hw):                                   # a rivet where a muntin meets the iron
        K.rivet(m, (x + 0.5, SPRING, DEEP))
        if foot:
            K.rivet(m, (x + 0.5, 2.0, SILL))
    for y in (7.5, 15.5, 23.5):                              # the reveal faces of the jambs, on the block lines
        K.rivet(m, (-hw + left, y, DEEP / 2.0), out="x")
        K.rivet(m, (hw - right, y, DEEP / 2.0), out="-x")
    return _head(m, width)


def _window_arch(width=3):
    """The iron frame of a great window, `width` blocks by six, at scale 2 (anchor: the foot centre
    of the glass, on its outer face). A1 draws the glass and its muntins behind it."""
    m = M.Model(PREFIX + _sized("window_arch", width), px=2.0)
    _frame(m, width)
    return m


# ---- the base-storey grille -----------------------------------------------------------------------
def _window_grille(width=3):
    """The barred grille of a base-storey window, `width` blocks by two, at scale 1 (anchor: the foot
    centre of the glass, on its outer face). It lies on the glass like the frames: a bar rides on
    every upright muntin (one pixel of glass either side), a rail on the middle and on the top one,
    so the iron thickens A1's net and from no side shows a second one. Every light keeps 5 px."""
    m = M.Model(PREFIX + _sized("window_grille", width), px=1.0)
    hw, h = width * 8.0, 32.0
    m.box((-hw, 0.0, 0.0), (-hw + 2.0, h, 2.0), IRON, grain="y")
    m.box((hw - 1.0, 0.0, 0.0), (hw, h, 2.0), IRON, grain="y")
    rails = ((0.0, 2.0), (14.0, 17.0), (30.0, 32.0))
    for y0, y1 in rails:
        m.box((-hw, y0, 0.0), (hw, y1, 2.0), IRON_D, grain="x")
    for k in range(1, 2 * width):
        x = -hw + 8.0 * k                                    # the muntin is the pixel column x .. x + 1
        m.box((x - 1.0, 0.0, 0.0), (x + 2.0, h, 3.0), IRON, grain="y")
        for y0, y1 in rails:
            K.rivet(m, (x + 0.5, math.floor((y0 + y1) / 2.0) + 0.5, 3.0))
    return m


# ---- the entrance: door frame and fanlight, leaves, gates ---------------------------------------------
# A doorway of the entrance is the great window's opening standing on the ground (c206 #21393): three
# wide, six high, the same stone head. So its iron is the window's frame without the foot plate, and
# the leaves hang under the transom on the 4.0 line.
def _ray(m, angle, r0, r1, wide, z, mat):
    """A flat bar from r0 to r1 on the line that leaves the middle of the springing at `angle`."""
    m.box((r0, SPRING - wide / 2.0, z[0]), (r1, SPRING + wide / 2.0, z[1]), mat,
          rot=("z", angle, (0.0, SPRING, 0.0)) if angle else None, grain="x")


def _fan(m, r, rays, wide, glass):
    """What fills the half round over a doorway: an iron fan -- a hub on the transom, rays to the ring
    and one arc half way out -- and with `glass` the amber glass behind it, which runs in under the
    ring and is drawn as one-pixel rows in three tones, hot round the hub (the fanlight)."""
    if glass:
        m._n += 1
        seed, rg, y = m._n, r + 0.5, 1.0
        while y < rg:
            mid, hot = (math.floor(2.0 * math.sqrt(max(0.0, q * q - y * y))) / 2.0 for q in (9.0, 6.0))
            edge = math.sqrt(rg * rg - y * y)
            spans = [(-edge, -mid, GLASS_DIM), (-mid, -hot, GLASS_MID), (-hot, hot, GLASS_HOT),
                     (hot, mid, GLASS_MID), (mid, edge, GLASS_DIM)]
            for x0, x1, mat in spans:
                if x1 - x0 > 1e-6:
                    m.box((x0, SPRING + y, 0.0), (x1, SPRING + y + 0.5, 0.5), mat, emit=15, shade=False,
                          grain="x", seed=seed)
            y += 0.5
    z = (0.5, 1.5)
    for i in range(1, rays + 1):
        _ray(m, 180.0 * i / (rays + 1), 3.0, r + 0.25, wide, z, IRON_D)
    m.ring("z", (0.0, SPRING, 1.0), 7.0, wide, 1.0, IRON_D, sides=24, arc=(0.0, 180.0))
    m.ring("z", (0.0, SPRING, 1.25), 1.75, 3.5, 1.5, IRON, sides=12, arc=(0.0, 180.0))       # the hub
    K.rivet(m, (0.0, SPRING + 2.0, 2.0))


def _door_frame(width=3):
    """The iron frame of the entrance doorway with its fanlight, at scale 2 (anchor: the foot centre
    of the doorway, on the plane the glass of a window would stand in). The glass glows: with the
    portholes it is the only lit iron of the family."""
    m = M.Model(PREFIX + "door_frame", px=2.0)
    _fan(m, _frame(m, width, foot=False, jambs=(1.0, 1.0)), rays=5, wide=0.5, glass=True)
    return m


LEAF_W, LEAF_T = 12.0, 1.5      # a leaf: 1.5 blocks wide, a 3 px plate; what is fixed on it stands 1 px proud
LEAF_H = SPRING - 1.0           # up to the underside of the transom
KICK = 5.0                      # the kick plate
LOCK = (8.5, 10.5)              # the lock rail: 0.30 of the height; the pull sits on it, 1.0 to 1.4 blocks up
WAIST = (14.5, 16.5)            # the second ledge: 0.50 of the height


def _both(m, a, b, mat, proud=0.5, base=LEAF_T / 2.0, **kw):
    """The same raised piece on both faces of a leaf, from (x, y) a to b: a leaf reads alike from
    either side, so the two of a pair match whichever face each one shows."""
    m.box((a[0], a[1], base), (b[0], b[1], base + proud), mat, **kw)
    m.box((a[0], a[1], -base - proud), (b[0], b[1], -base), mat, **kw)


def _studs(m, spots, z=LEAF_T / 2.0):
    for x, y in spots:
        K.rivet(m, (x, y, z), out="z")
        K.rivet(m, (x, y, -z), out="-z")


def _hinges(m, rows):
    """The knuckles of a leaf's hinges, on its hinge edge (x = 0)."""
    for y0, y1 in rows:
        m.tube("y", (-0.5, 0.0), y0, y1, 0.9, IRON_D, sides=8)


def _pull(m, x, proud):
    """A brass bar to pull a leaf by, on both faces: 1.0 to 1.4 blocks above the floor."""
    for s in (1.0, -1.0):
        z0 = s * (LEAF_T / 2.0 + proud)
        for y in (7.5, 10.5):
            m.box((x, y, s * LEAF_T / 2.0), (x + 1.0, y + 1.0, z0 + s * 1.0), BRASS_D)
        m.box((x, 7.5, z0 + s * 0.5), (x + 1.0, 11.5, z0 + s * 1.0), BRASS, grain="y")


def _door_leaf():
    """One leaf of the entrance door: riveted plate, a kick plate, two ledges, a brass pull and a
    glazed porthole high up like a ship's, at scale 2 (anchor: the foot of the hinge edge; the leaf
    runs along +x). Both faces are the same."""
    m = M.Model(PREFIX + "door_leaf", px=2.0)
    w, h, t = LEAF_W, LEAF_H, LEAF_T / 2.0
    m.box((0.0, 0.0, -t), (w, h, t), IRON, grain="y")
    top = (h - 3.0, h - 1.0)
    for y0, y1 in ((0.0, KICK), LOCK, WAIST, top):
        _both(m, (0.0, y0), (w, y1), IRON_D, grain="x")
    across = (1.5, 4.5, 7.5, 10.5)
    _studs(m, [(x, KICK - 1.0) for x in across] + [(1.5, 1.0), (10.5, 1.0)]
           + [(x, 9.5) for x in across[:3]] + [(x, 15.5) for x in across] + [(x, h - 2.0) for x in across], t + 0.5)
    _studs(m, [(x, y) for x in (1.5, 10.5) for y in (7.0, 12.5, 19.0, 22.5, 26.0)])
    cx, cy = w / 2.0, 22.5
    m.ring("z", (cx, cy, 0.0), 3.0, 1.0, LEAF_T + 1.5, BRASS, sides=16)                   # the porthole's rim
    K.glass_prism(m, "z", (cx, cy), -t - 0.25, t + 0.25, 2.6, GLASS_MID, cap=GLASS_DIM, emit=15)
    _pull(m, 9.5, 0.5)
    _hinges(m, ((2.0, 4.5), LOCK, top))
    return m


def _gate(width=3):
    """A side arch of the entrance, closed: the door's frame, an open iron fan in the head and a pair
    of barred leaves that repeat the door's kick plate and ledges, at scale 2 (anchor as door_frame)."""
    m = M.Model(PREFIX + "gate", px=2.0)
    _fan(m, _frame(m, width, foot=False, jambs=(1.0, 1.0)), rays=7, wide=1.0, glass=False)
    hw, z, zr, top = width * 4.0, (0.75, 1.75), (1.0, 1.5), LEAF_H - 1.0
    for sx in (-1.0, 1.0):
        def span(x0, x1, y0, y1, mat, zz=z, **kw):
            a, b = sorted((sx * x0, sx * x1))
            m.box((a, y0, zz[0]), (b, y1, zz[1]), mat, **kw)
        span(hw - 2.0, hw - 1.0, 0.0, top, IRON, grain="y")                               # the hanging stile
        span(0.0, 1.0, 0.0, top, IRON, grain="y")                                         # the meeting stile
        for x in (2.5, 5.0, 7.5):                                                         # bars 2 px, lights 3 px
            span(x, x + 1.0, KICK, top - 1.0, IRON, grain="y")
        span(1.0, hw - 2.0, 0.0, KICK, IRON_D, zr, grain="x")                             # the kick plate
        for y0, y1 in (LOCK, WAIST, (top - 1.0, top)):
            span(1.0, hw - 2.0, y0, y1, IRON_D, zr, grain="x")
        for x in (3.0, 5.5, 8.0):
            K.rivet(m, (sx * x, KICK - 1.0, zr[1]))
            K.rivet(m, (sx * x, 9.5, z[1]))
            K.rivet(m, (sx * x, 15.5, z[1]))
    m.box((-1.5, 8.0, z[1]), (1.5, 11.0, z[1] + 0.5), IRON_D)                             # the lock case
    m.tube("z", (0.0, 9.5), z[1] + 0.5, z[1] + 1.25, 0.75, BRASS, sides=8)
    return m


NIGHT = [K.flat("night_glass", i) for i in range(4)]
# the lights of a glazed leaf, top row first: mostly one tone of the sky, now and then a darker or a
# lighter pane, as A1 paints its dark windows
_PANES = ("121", "111", "101", "112", "111")


def _glazed_leaf():
    """One leaf of the west door: a riveted plate in the lower third, dark glass in 6 x 7 px lights
    above it, at scale 2 (anchor: the foot of the hinge edge; the leaf runs along +x, 1.5 blocks
    by 4). Both faces are the same."""
    m = M.Model(PREFIX + "glazed_leaf", px=2.0)
    w, h, t = LEAF_W, 32.0, LEAF_T / 2.0
    sill, head = 11.0, h - 1.5
    m.box((0.0, 0.0, -t), (w, sill, t), IRON, grain="y")
    m.box((0.0, sill, -t), (1.0, h, t), IRON, grain="y")
    m.box((w - 1.0, sill, -t), (w, h, t), IRON, grain="y")
    m.box((1.0, head, -t), (w - 1.0, h, t), IRON, grain="x")
    for j, row in enumerate(_PANES):
        y1 = head - 4.0 * j
        for i, tone in enumerate(row):
            x0 = 1.0 + 3.5 * i
            m.box((x0, y1 - 3.5, -0.25), (x0 + 3.0, y1, 0.25), NIGHT[int(tone)], grain="x")
        if j:
            m.box((1.0, y1, -0.5), (w - 1.0, y1 + 0.5, 0.5), IRON_D, grain="x")           # a glazing bar, 1 px
    for x in (4.0, 7.5):
        m.box((x, sill, -0.5), (x + 0.5, head, 0.5), IRON_D, grain="y")
    for y0, y1 in ((0.0, KICK), (sill - 2.0, sill)):
        _both(m, (0.0, y0), (w, y1), IRON_D, grain="x")
    across = (1.5, 4.5, 7.5, 10.5)
    _studs(m, [(x, KICK - 1.0) for x in across] + [(1.5, 1.0), (10.5, 1.0)] + [(x, sill - 1.0) for x in across[:3]], t + 0.5)
    _studs(m, [(1.5, 7.0), (10.5, 7.0)])
    _pull(m, 9.5, 0.5)
    _hinges(m, ((2.0, 4.5), (14.0, 16.5), (27.0, 29.5)))
    return m


# ---- the glazed entrance canopy and its lamp ----------------------------------------------------------
def _canopy(width=5, depth=3):
    """The glazed canopy over the middle arch of the entrance, at scale 2. Anchor: the middle of its
    back edge on the face of the two pilasters it hangs from, at its underside -- the top of the
    string course, on which it lies (c164 #21442). Between the pilasters the roof runs one block
    further back, to the wall. Five lights across and two deep; a riveted valance in front and at
    the sides; under each end a quarter-round brace that springs from the pilaster three blocks
    down and meets the front edge, a small scroll in its corner. The middle of the underside is
    left free: canopy_lamp hangs there."""
    m = M.Model(PREFIX + "canopy", px=2.0)
    hw, out, back, pil = width * 4.0, depth * 8.0, -8.0, 8.0
    bay = hw - pil                                           # half the width between the pilasters
    rim = 1.5                                                # the frame: channel iron 3 px high
    m.box((-hw, 0.0, out - 1.0), (hw, rim, out), IRON, grain="x")
    m.box((-bay, 0.0, back), (bay, rim, back + 1.0), IRON, grain="x")
    for sx in (-1.0, 1.0):
        for x0, x1, z0, z1, grain in ((hw - 1.0, hw, 0.0, out - 1.0, "z"), (bay, hw - 1.0, 0.0, 1.0, "x"),
                                      (bay - 1.0, bay, back + 1.0, 0.0, "z")):
            a, b = sorted((sx * x0, sx * x1))
            m.box((a, 0.0, z0), (b, rim, z1), IRON, grain=grain)
    glass = dict(emit=0, grain="x")
    m.box((-hw + 1.0, 1.0, 1.0), (hw - 1.0, 1.5, out - 1.0), GLASS_COOL, **glass)
    m.box((-bay + 1.0, 1.0, back + 1.0), (bay - 1.0, 1.5, 1.0), GLASS_COOL, **glass)
    for x in (-bay, -4.0, 4.0, bay):                         # glazing bars under the glass, a batten over it
        z0 = back + 1.0 if abs(x) < bay else 1.0
        m.box((x - 0.25, 0.0, z0), (x + 0.25, 1.0, out - 1.0), IRON_D, grain="z")
        m.box((x - 0.5, 1.5, z0), (x + 0.5, 2.0, out - 1.0), IRON, grain="z")
    mid = out / 2.0
    m.box((-hw + 1.0, 0.0, mid - 0.25), (hw - 1.0, 1.0, mid + 0.25), IRON_D, grain="x")
    m.box((-hw + 1.0, 1.5, mid - 0.5), (hw - 1.0, 2.0, mid + 0.5), IRON, grain="x")
    m.box((-hw, -3.0, out - 0.5), (hw, 0.0, out), IRON_D, grain="x")                      # the valance
    for i in range(-4, 5):
        K.rivet(m, (4.0 * i, -1.5, out))
    for sx in (-1.0, 1.0):
        a, b = sorted((sx * (hw - 0.5), sx * hw))
        m.box((a, -3.0, pil), (b, 0.0, out - 0.5), IRON_D, grain="z")
        for z in (12.0, 16.0, 20.0):
            K.rivet(m, (sx * hw, -1.5, z), out="x" if sx > 0 else "-x")
        x, r = sx * (hw - pil / 2.0), out                    # the brace, on the middle of the pilaster
        m.box((x - 1.0, -r - 1.5, 0.0), (x + 1.0, -pil, 0.5), IRON_D, grain="y")           # its wall plate
        # the arc's outer edge leaves the wall plate upright and meets the underside at the front edge
        m.ring("x", (x, -r + 0.5, out), r - 1.0, 1.0, 1.0, IRON, sides=48, arc=(270.0, 360.0))
        m.box((x - 0.5, -1.0, pil), (x + 0.5, 0.0, out - 1.0), IRON, grain="z")
        m.ring("x", (x, -pil - 2.0, 2.5), 1.75, 0.5, 1.0, IRON, sides=12)                 # the scroll
        m.ring("x", (x, -r - 1.5, 1.5), 1.0, 0.5, 1.0, IRON, sides=12, arc=(90.0, 360.0))  # the foot's curl
        K.rivet(m, (x, -r + 2.0, 0.5))
        K.rivet(m, (x, -pil - 5.0, 0.5))
    return m


OPAL = [K.flat("opal", i) for i in range(len(P.RAMPS["opal"]))]


def _canopy_lamp():
    """The lamp under the canopy, the brightest point of the entrance (c164 #21442): an opal globe in
    an iron cage on a rod, at scale 1. Anchor: the point under the canopy it hangs from; the foot of
    the lamp is 28.5 px below it."""
    m = M.Model(PREFIX + "canopy_lamp", px=1.0)
    m.tube("y", (0.0, 0.0), -1.0, 0.0, 2.5, IRON_D)
    m.tube("y", (0.0, 0.0), -12.0, -1.0, 0.5, IRON, sides=4)
    m.tube("y", (0.0, 0.0), -7.0, -6.0, 1.0, IRON_D, sides=4)
    m.taper("y", (0.0, 0.0), -12.0, -15.0, 1.5, 5.0, IRON, sides=8, steps=3)              # the hood
    m.tube("y", (0.0, 0.0), -16.0, -15.0, 6.0, IRON_D, sides=8)
    bands = [(-1.0, -0.75, 1, OPAL[0]), (-0.75, -0.5, 1, OPAL[1]), (-0.5, -0.25, 1, OPAL[2]),
             (-0.25, 0.25, 1, OPAL[4]), (0.25, 0.5, 1, OPAL[3]), (0.5, 0.75, 1, OPAL[2]), (0.75, 1.0, 1, OPAL[1])]
    K.glass_ball(m, (0.0, -21.0, 0.0), 5.0, bands, sides=12, squash=1.0)
    for angle in (0.0, 90.0, 180.0, 270.0):                                               # the cage
        m.box((5.5, -26.0, -0.5), (6.5, -16.0, 0.5), IRON, rot=("y", angle, (0.0, 0.0, 0.0)) if angle else None, grain="y")
    m.ring("y", (0.0, -26.5, 0.0), 5.75, 1.0, 1.0, IRON_D, sides=8)
    m.tube("y", (0.0, 0.0), -28.5, -25.5, 1.0, IRON, sides=4)
    return m


# ---- the terrace balustrade scroll panel ----------------------------------------------------------
def _railing_panel(width=2, height=1):
    """A cast scroll panel between two posts, at scale 1 (anchor: the foot centre, it stands on the
    floor)."""
    m = M.Model(PREFIX + "railing_panel", px=1.0)
    w, h, dz = width * 16.0, height * 16.0, 2.0
    hw = w / 2.0
    for sx in (-1.0, 1.0):                                                        # posts
        m.box((sx * hw - 1.5, 0.0, 0.0), (sx * hw + 1.5, h, dz), IRON, grain="y")
    m.box((-hw, h - 2.0, 0.0), (hw, h, dz), IRON, grain="x")                      # top rail
    m.box((-hw, 0.0, 0.0), (hw, 2.0, dz), IRON, grain="x")                        # bottom rail
    zc = dz / 2.0
    for sx in (-1.0, 1.0):                                                        # a pair of C-scrolls
        cx = sx * hw * 0.5
        m.ring("z", (cx, h * 0.5, zc), h * 0.28, 1.2, dz, IRON_D, sides=16, arc=(200.0, 520.0))
        m.ring("z", (sx * hw * 0.25, h * 0.42, zc), h * 0.14, 1.0, dz, IRON_D, sides=12, arc=(0.0, 300.0))
    K.rivet(m, (0.0, 2.0, dz))
    K.rivet(m, (0.0, h - 2.0, dz))
    return m


# ---- the inspection ladder ------------------------------------------------------------------------
LADDER_H = 48.0     # three blocks to a length; rungs every 8 px and hoops every 16, so lengths stack


def _ladder(caged=False):
    """A three-block length of the inspection ladder, at scale 1 (anchor: the foot centre on the
    wall; it stands 4 px off the wall on +z). Lengths stack without a break. `caged` is the length
    above head height: round hoops every block and five straps down them, a cage a block and an
    eighth wide, so from in front it is a cage about the ladder and not three short lines."""
    m = M.Model(PREFIX + ("ladder_cage" if caged else "ladder"), px=1.0)
    rail, stand = 4.5, 4.0
    for sx in (-1.0, 1.0):
        m.box((sx * rail - 1.0, 0.0, stand - 1.0), (sx * rail + 1.0, LADDER_H, stand + 1.0), IRON, grain="y")
        for y in (8.0, 40.0):                                                    # the stays to the wall
            m.box((sx * rail - 0.5, y - 1.0, 0.0), (sx * rail + 0.5, y + 1.0, stand - 1.0), IRON_D, grain="z")
    for i in range(6):
        m.tube("x", (4.0 + 8.0 * i, stand), -rail, rail, 0.8, IRON_D, sides=8)   # a rung
    if caged:
        centre, r = stand + 1.0, 9.0
        for y in (8.0, 24.0, 40.0):
            m.ring("y", (0.0, y, centre), r, 1.0, 2.0, IRON, sides=16, arc=(180.0, 360.0))
            for sx in (-1.0, 1.0):                                               # the hoop's lugs, back to the rails
                a, b = sorted((sx * (rail + 1.0), sx * (r + 0.5)))
                m.box((a, y - 1.0, centre - 1.0), (b, y + 1.0, centre), IRON, grain="x")
        for angle in (200.0, 235.0, 270.0, 305.0, 340.0):
            m.box((r - 0.5, 0.0, centre - 0.5), (r + 0.5, LADDER_H, centre + 0.5), IRON_D,
                  rot=("y", angle, (0.0, 0.0, centre)), grain="y")
    return m


# ---- the roof vent cowl ---------------------------------------------------------------------------
HOLLOW = K.flat("iron", 0)


def _vent_cowl():
    """A ship's cowl ventilator, at scale 1 (anchor: the foot centre, it stands on the roof): a
    flanged pipe, a quarter bend for a neck and a bell mouth that looks along +z, dark inside."""
    m = M.Model(PREFIX + "vent_cowl", px=1.0)
    r, bend, neck = 4.0, 6.0, 12.0
    m.tube("y", (0.0, 0.0), 0.0, 1.5, r + 2.0, IRON_D, sides=12)                 # the base flange
    m.tube("y", (0.0, 0.0), 1.5, neck, r, IRON, sides=12)
    m.ring("y", (0.0, neck - 0.5, 0.0), r + 0.5, 1.0, 1.0, IRON_D, sides=12)     # the collar under the bend
    points = [(0.0, neck + bend * math.sin(math.radians(t)), bend - bend * math.cos(math.radians(t)))
              for t in (0.0, 22.5, 45.0, 67.5, 90.0)]
    m.hose(points, r, IRON, sides=12)
    top = neck + bend
    m.taper("z", (0.0, top), bend, bend + 4.0, r, r + 3.0, IRON, sides=12)       # the bell
    m.ring("z", (0.0, top, bend + 4.5), r + 3.0, 1.0, 1.0, IRON_D, sides=12)     # its rolled rim
    m.tube("z", (0.0, top), bend + 4.0, bend + 4.1, r + 2.4, HOLLOW, sides=12, cap=HOLLOW)
    return m


# ---- the floor grating / louvre hatch -------------------------------------------------------------
def _grate_hatch(width=1):
    """A square floor grating with a ring pull, at scale 1 (anchor: the foot centre, it lies flat on
    the floor)."""
    m = M.Model(PREFIX + "grate_hatch", px=1.0)
    s = width * 16.0 / 2.0
    for sx in (-1.0, 1.0):
        m.box((sx * s - 1.5, 0.0, -s), (sx * s + 1.5, 2.0, s), IRON, grain="z")
        m.box((-s, 0.0, sx * s - 1.5), (s, 2.0, sx * s + 1.5), IRON, grain="x")
    for i in range(int(2 * s // 3) - 1):                                         # grating bars
        z = -s + 3.0 * (i + 1)
        m.tube("x", (1.0, z), -s + 1.5, s - 1.5, 0.6, IRON_D, sides=6)
    m.box((-s, 0.0, -s + 0.5), (-s + 1.5, 1.0, -s + 2.5), IRON_D)                # a hinge
    m.ring("y", (s - 3.0, 1.5, 0.0), 2.0, 0.8, 0.8, BRASS, sides=12)            # ring pull
    return m


# ---- the family's models, placement and dressing --------------------------------------------------
def _sized(kind, width):
    """The name of a piece that comes in more than one width: the three-wide one has the plain name."""
    return kind if width in (None, 3) else f"{kind}_{width}"


SPEC = {
    "window_arch": dict(build=_window_arch, mount="wall", scale=2.0, light=None),
    "window_arch_2": dict(build=lambda: _window_arch(2), mount="wall", scale=2.0, light=None),
    "window_grille": dict(build=_window_grille, mount="wall", scale=1.0, light=None),
    "window_grille_2": dict(build=lambda: _window_grille(2), mount="wall", scale=1.0, light=None),
    "door_frame": dict(build=_door_frame, mount="wall", scale=2.0, light=(0.0, 4.6, 0.3), level=9),
    "door_leaf": dict(build=_door_leaf, mount="floor", scale=2.0, light=None),
    "gate": dict(build=_gate, mount="wall", scale=2.0, light=None),
    "glazed_leaf": dict(build=_glazed_leaf, mount="floor", scale=2.0, light=None),
    "canopy": dict(build=_canopy, mount="wall", scale=2.0, light=None),
    "canopy_lamp": dict(build=_canopy_lamp, mount="ceiling", scale=1.0, light=(0.0, -1.3, 0.0), level=13),
    "railing_panel": dict(build=_railing_panel, mount="floor", scale=1.0, light=None),
    "ladder": dict(build=_ladder, mount="wall", scale=1.0, light=None),
    "ladder_cage": dict(build=lambda: _ladder(True), mount="wall", scale=1.0, light=None),
    "vent_cowl": dict(build=_vent_cowl, mount="floor", scale=1.0, light=None),
    "grate_hatch": dict(build=_grate_hatch, mount="floor", scale=1.0, light=None),
}
SCALE = {PREFIX + name: spec["scale"] for name, spec in SPEC.items()}


@functools.lru_cache(maxsize=None)
def _models():
    return {PREFIX + name: spec["build"]() for name, spec in SPEC.items()}


def models():
    return dict(_models())


def place(canvas, kind, pos, facing="south", origin=(0, 0, 0), width=None, light=True, level=None,
          yaw=None, **opts):
    """Place one piece and, if it is a lit one, offer its light to A2. Returns the entity count.

    kind     a key of SPEC; "window_arch" and "window_grille" take `width` (3, the default, or 2).
    pos      scene coordinates. A wall piece: the point on the face it is fixed to, `facing` the way
             that face looks. A floor piece: the centre of its foot (`yaw` turns it). The lamp: the
             point it hangs from.
    opts     go to artkit.models.display (brightness, view)."""
    key = _sized(kind, width)
    spec = SPEC[key]
    n = K.put(canvas, _models()[PREFIX + key], pos, mount=spec["mount"], facing=facing, yaw=yaw,
              scale=spec["scale"], origin=origin, **opts)
    if light and spec.get("light") is not None:
        y = yaw if yaw is not None else K.FACING[facing]
        cell = K.light_cell(pos, y, spec["light"], origin)
        K.offer_lights(canvas, [(cell, level if level is not None else spec.get("level", 9))],
                       f"props/ironwork:{key}")
    return n


def ladder(canvas, pos, lengths, facing="south", origin=(0, 0, 0), plain=1):
    """A ladder of `lengths` three-block lengths up a wall from pos (the foot centre on the wall);
    the first `plain` of them are bare, so one can step on, the rest are caged."""
    n = 0
    for i in range(lengths):
        at = (pos[0], pos[1] + 3.0 * i, pos[2])
        n += place(canvas, "ladder" if i < plain else "ladder_cage", at, facing=facing, origin=origin)
    return n


OUT = {(1, 0): "east", (-1, 0): "west", (0, 1): "south", (0, -1): "north"}
GRILLES = "blocks"      # the base-storey windows: A3's bars in the wall plane ("blocks") or this family's
                        # grille on the glass ("model"); only one layer stays, the review says which


def _face(cells, inward, y):
    """Where a piece pressed on the outer face of the glass in `cells` is anchored: the foot centre
    of that face (cells -> a point) and the way it looks. cells are (x, z) columns in a straight run."""
    out = (-inward[0], -inward[1])
    n = float(len(cells))
    x = sum(c[0] + 0.5 for c in cells) / n + 0.5 * out[0]
    z = sum(c[1] + 0.5 for c in cells) / n + 0.5 * out[1]
    return (x, float(y), z), OUT[out]


def _empty(canvas, cells, y0, y1, origin, only=None):
    """Clear the columns `cells` from row y0 to y1; with `only`, just the blocks of that name."""
    for x, z in cells:
        for y in range(y0, y1 + 1):
            at = (origin[0] + x, origin[1] + y, origin[2] + z)
            state = canvas.get(*at)
            if state is not None and (only is None or state.partition("[")[0].split(":")[-1] == only):
                canvas.clear(*at)


def windows(canvas, table, origin=(0, 0, 0), grilles=None):
    """Dress the windows of a table as main/_plan.windows() gives it -- [dict(front, bay, storey,
    cells, inward, y)], cells the glass columns: an arch frame on every great window (three or two
    wide, six high), and on the base-storey windows (two high) what `grilles` says: "blocks" leaves
    A3's bars in the wall plane, "model" takes them out and lays this family's grille on the glass;
    a function of the window answers for each one. Left out, GRILLES. Returns the entity count."""
    grilles = GRILLES if grilles is None else grilles
    n = 0
    for w in table:
        inward = tuple(w["inward"])
        cells, (y0, y1) = list(w["cells"]), w["y"]
        if w.get("blind") or (-inward[0], -inward[1]) not in OUT or len(cells) not in (2, 3):
            continue
        pos, facing = _face(cells, inward, y0)
        if w["storey"] == "main" and y1 - y0 == 5:
            n += place(canvas, "window_arch", pos, facing=facing, origin=origin, width=len(cells))
        elif w["storey"] == "base" and y1 - y0 == 1:
            if (grilles(w) if callable(grilles) else grilles == "model"):
                _empty(canvas, [(x - inward[0], z - inward[1]) for x, z in cells], y0, y1, origin, only=B.IRON_BARS)
                n += place(canvas, "window_grille", pos, facing=facing, origin=origin, width=len(cells))
    return n


LEAF_OFF = 0.30         # an open leaf stands this far off the reveal: its ledges and its pull are between
LEAF_OUT = 7.0 / 16.0   # the hinge line of the entrance leaves: just in front of the frame's 6 px
CANOPY_LAMP = 1.5       # the lamp hangs this far in front of the pilasters, under the middle glazing bar


def leaves(canvas, kind, pos, facing="east", origin=(0, 0, 0), swing=90.0, inset=LEAF_OFF, out=LEAF_OUT):
    """Hang a pair of leaves (`kind`: "door_leaf" or "glazed_leaf") in a three-wide doorway. pos is
    the foot centre of the doorway on the plane the leaves close in, `facing` the way it looks.
    swing: 0 is shut, 90 is open outwards with each leaf along its reveal, `inset` off it; the hinge
    line stands `out` in front of pos. Both leaves show the same face. Returns the entity count."""
    base = K.FACING[facing]
    tan = K.turn(base, (1.0, 0.0, 0.0))                 # along the doorway, to the right of who looks at it
    fwd = K.turn(base, (0.0, 0.0, 1.0))
    model, scale = _models()[PREFIX + kind], SPEC[kind]["scale"]
    for side, yaw in ((-1.0, base + swing), (1.0, base + 180.0 - swing)):
        reach = side * (1.5 - inset)
        at = tuple(pos[k] + origin[k] + reach * tan[k] + out * fwd[k] for k in range(3))
        canvas.add_entity(at[0], at[1], at[2], M.display(model, yaw=yaw, scale=scale))
    return 2


def doors(canvas, table, origin=(0, 0, 0), west_swing=0.0):
    """Dress the doorways of a table as main/_plan.doors() gives it -- [dict(front, bay, cells,
    inward, y, arch, kind)], cells the columns of the wall line; the iron stands one step inward,
    where a window's glass would. An arched doorway six high: kind "door" gets the frame with its
    fanlight, a pair of riveted leaves open against the reveals, and -- where a pilaster stands on
    either side -- the canopy and its lamp; kind "gate" gets the barred gate, shut, and whatever
    stands in its plane is cleared first (A3's stand-in bars). A flat-headed doorway four high (the
    west door) gets a pair of glazed leaves, shut unless west_swing opens them. Returns the count."""
    n = 0
    for d in table:
        inward = tuple(d["inward"])
        if (-inward[0], -inward[1]) not in OUT or len(d["cells"]) != 3:
            continue
        cells = [(x + inward[0], z + inward[1]) for x, z in d["cells"]]
        (y0, y1), kind = d["y"], d.get("kind", "door")
        pos, facing = _face(cells, inward, y0)
        if d.get("arch") and y1 - y0 == 5:
            if kind == "gate":
                _empty(canvas, cells, y0, y1, origin)
                n += place(canvas, "gate", pos, facing=facing, origin=origin)
                continue
            n += place(canvas, "door_frame", pos, facing=facing, origin=origin)
            n += leaves(canvas, "door_leaf", pos, facing=facing, origin=origin)
            n += canopy(canvas, pos, y1 + 2.0, facing=facing, origin=origin)
        elif not d.get("arch") and y1 - y0 == 3:
            n += leaves(canvas, "glazed_leaf", pos, facing=facing, origin=origin, swing=west_swing,
                        inset=0.0, out=LEAF_OFF)
    return n


def canopy(canvas, pos, y, facing="east", origin=(0, 0, 0)):
    """The canopy and its lamp over a doorway whose foot centre, on the plane its iron stands in, is
    pos: the canopy lies at height y (the top of the string course) on the faces of the pilasters
    either side of the doorway, two blocks in front of pos. Places nothing where those pilasters
    are not built. Returns the entity count."""
    base = K.FACING[facing]
    tan = K.turn(base, (1.0, 0.0, 0.0))
    fwd = K.turn(base, (0.0, 0.0, 1.0))
    for side in (-2.0, 2.0):                            # the cell of each pilaster, a block under the canopy
        at = [pos[k] + origin[k] + side * tan[k] + 1.5 * fwd[k] for k in range(3)]
        if not canvas.has(int(math.floor(at[0])), int(math.floor(y + origin[1] - 2.0)), int(math.floor(at[2]))):
            return 0
    face = tuple(pos[k] + 2.0 * fwd[k] for k in range(3))
    n = place(canvas, "canopy", (face[0], y, face[2]), facing=facing, origin=origin)
    lamp = tuple(face[k] + CANOPY_LAMP * fwd[k] for k in range(3))
    return n + place(canvas, "canopy_lamp", (lamp[0], y, lamp[2]), facing=facing, origin=origin)


def _plan():
    """A3's plan of the main building when it is in the tree, else None."""
    try:
        from ..main import _plan as plan
    except ImportError:
        return None
    return plan


def build(canvas, origin=(0, 0, 0)):
    """Dress the main building A3 has built, from its own tables: windows() on main/_plan.windows(),
    doors() on main/_plan.doors() once the plan has one. Places nothing until the plan is in the
    tree, so the master scene always generates.
    While DRESS is off it places nothing and does not read A3's tables at all, so a card that is being
    reworked neither shows in the master scene nor can stop it from generating."""
    if not DRESS:
        return 0
    plan = _plan()
    if plan is None:
        return 0
    n = windows(canvas, getattr(plan, "windows", list)(), origin)
    table = getattr(plan, "doors", None)
    if table is not None:
        n += doors(canvas, table(), origin)
    return n
