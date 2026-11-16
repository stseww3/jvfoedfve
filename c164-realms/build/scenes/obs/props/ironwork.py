"""props/ironwork -- the door and window ironwork of the observatory (plan ART-PLAN 7.3, part A6,
card plan/packages/props/ironwork.md).

All cast and riveted iron on the common palette, 16 texels to the block (px = scale):

    window_arch, _2      the iron frame of a great arched window, three or two blocks wide. Iron only:
                         it is pressed on A1's glazed pane and stands where that pane's 8 px net
                         runs. Jambs 2 px on the glass and 6 px deep in the stone reveal, a riveted
                         plate over the bottom row of lights, a transom on the 4.0 line, a half
                         round head, riveted sheet in the spandrels.
    window_grille, _2    the barred grille of a base-storey window: a bar on every upright muntin.
    door_frame, fanlight the entrance doorway's frame (the window's, without the foot plate) with an
                         iron fan in its head, and the amber glass behind that fan.
    door_leaf            one leaf of the entrance door: riveted plate, kick plate, two ledges, a
                         brass pull and a glazed porthole; both faces alike. leaves() hangs a pair
                         open against the reveals, so a player walks through.
    gate                 a side arch of the entrance, shut: the same frame, an open fan, barred leaves.
                         doors() gives it the collision a model has not: a barrier behind the leaves.
    glazed_leaf          one leaf of the west door: riveted below, dark glass above. leaves() hangs a
                         pair open like the entrance's: the door leads to the sunset terrace.
    canopy, canopy_lamp  the glazed canopy over the middle arch on two quarter-round braces, and the
                         opal lamp under it (canopy_lamp_in, _left, _right: the quarters of its globe
                         that look at the wall and along it; canopy_lamp_under: what of it looks down).
    railing_panel        a cast scroll panel for the terrace balustrade, between two posts.
    ladder, ladder_cage  a three-block length of the inspection ladder, bare and caged; they stack.
    vent_cowl            a roof vent: a flanged pipe, a bent neck and a bell mouth.
    grate_hatch          a floor grating with a ring pull.

Everything is placed through _kit (mounting, materials, rivets, glowing glass). windows() and
doors() dress a wall from the tables main/_plan gives; build() does that for the main building.
Glass that glows is a piece of its own, drawn in a tilted frame (TILT): only so does a face that
looks out of an east wall show its picture as painted. What looks down needs more than a tilt, a
frame whose level planes are slid over each other (SLIDE).

The look is judged on texture and on style, so the test scene is build/scenes/obs_props_ironwork.
"""
import contextlib
import functools
import math

import numpy as np

from artkit import models as M
from artkit.nbtw import Float

from ..common import blocks as B
from ..common import palette as P
from . import _kit as K

PREFIX = "prop_iron_"
DRESS = True                     # build() dresses the master scene only when on. On from the merge on
                                 # (the fast lane, COMMON 0.10); review looks at it on the real wall

IRON, IRON_D = K.IRON, K.IRON_D
BRASS, BRASS_D = K.BRASS, K.BRASS_D
GLASS_HOT, GLASS_MID, GLASS_DIM = K.GLOW_HOT, K.GLOW_MID, K.GLOW_DIM     # amber glass that glows
GLASS_AMBER = K.flat("glow", 0)                                         # the same glass with no light behind it
GLASS_COOL = K.flat("opal", 2)                                          # frosted canopy glass, not lit

# ---- glass that glows: the tilted frame ---------------------------------------------------------------
# The game lights every item by two lamps fixed in the world, whatever the item emits (the item
# shader's minecraft_mix_light; artkit.gamescene draws the same): a face that looks up shows its
# picture as painted, one that looks north or south 0.74 of it, one that looks east or west 0.50, one
# that looks down 0.40. The front of the observatory looks east, so a lamp's globe and a fanlight were
# seen from the court at half their tones, greyer than any lit window (those are blocks, which can
# switch the shading off: A2 #14980; an item cannot, shade_direction_override is read for blocks only).
# But a face is lit as if it looked along the axis of its model that lies nearest to its normal
# (FaceBakery.calculateFacing), and that axis is turned with the display (VertexConsumer.putBakedQuad).
# So a piece that glows is drawn in a frame tilted about the wall's own line, and its display turns it
# back: it stands where it stood, and a face that looks out of the wall is lit as one that looks 40
# degrees up -- 1.00. Up stays 1.00, along the wall 0.74, down 0.40; into the wall falls to 0.40.
# A flat piece on the wall needs no more (the back of a fanlight is seen from the hall, against the
# night: 0.40 is right for it). A round one that is seen from all sides -- the lamp's globe -- is
# drawn in four pieces, each in the frame tilted for the faces that look its way: out of the wall,
# into it, and along it to the right and to the left (about the line that runs out of the wall).
TILT = 40.0
# the way the faces of a piece look -> (the turn of its frame, that way in the model: x along the wall, z out of it)
WAYS = {"out": (("x", TILT), (0.0, 0.0, 1.0)), "in": (("x", -TILT), (0.0, 0.0, -1.0)),
        "right": (("z", -TILT), (1.0, 0.0, 0.0)), "left": (("z", TILT), (-1.0, 0.0, 0.0))}


def _tilted(m, way="out"):
    """`with _tilted(m, way):` draws in the frame tilted for the faces that look `way`; the piece
    is placed with turns=_turns(way)."""
    return m.turned(WAYS[way][0])


def _turns(way="out"):
    axis, angle = WAYS[way][0]
    return ((axis, -angle),)


def _facing(m, first, way="out"):
    """Of the parts drawn since `first` in the frame tilted for `way`, keep the faces that look
    more that way than any other of the four; those that look straight up stay with "out", and
    those that look straight down are left to the piece in the slid frame (SLIDE). So the four
    quarters of a round thing, each in its own frame, make it whole without a face drawn twice."""
    turn = M.quat(*WAYS[way][0])
    ways = {name: M._qrot(turn, d) for name, (_, d) in WAYS.items()}
    up = M._qrot(turn, (0.0, 1.0, 0.0))
    for part in m.parts[first:]:
        q = part["rot"][0] if part["rot"] else M.IDENT
        for letter, normal in M.NORMAL.items():
            n = M._qrot(q, normal)
            along = {name: round(sum(a * b for a, b in zip(n, d)), 9) for name, d in ways.items()}
            best = max(along, key=along.get)                # of equals the first: "out" before "in" ...
            if along[best] > 1e-6:
                keep = best == way
            else:                                           # a level face
                keep = way == "out" and sum(a * b for a, b in zip(n, up)) > 0.0
            if not keep:
                part["skip"].add(letter)
    m.parts[first:] = [part for part in m.parts[first:] if len(part["skip"]) < 6]


# ---- glass that glows and looks down: the slid frame ------------------------------------------------
# No tilt helps a face that looks straight down. It is lit by the axis of its model nearest to its
# normal, which lies within 55 degrees of that normal however the model is turned -- under the
# horizon still: 0.41 at the best -- and to show its picture as painted a face has to be lit as one
# that looks some 40 degrees up. So the underside of the lamp's globe was a dark disc to everyone
# who walked in under it. But the game lights by the display's whole transformation, not by its
# turn alone (PoseStack.Pose.mulPose: the normals of a matrix that is more than a turn go by its
# inverse transpose; artkit.gamescene draws the same), and a transformation need not keep angles.
# What looks down is therefore a piece of its own, the level faces alone: drawn in the frame tilted
# for "out" with every level plane moved along the wall's normal by SLIDE times its height, and
# shown by a display that slides the planes back (frame, _slid_display). A level face is moved in
# its own plane, so it stays the rectangle it was and lies where it lay, 16 px to the block; it is
# lit as one that looks 50 degrees up: 1.00. Only level faces can be drawn so -- a box in that
# frame leans. (tools/check.py reads the scale of such a display as a model that is not 16 px to
# the block; obs_props_ironwork/fit.py measures the faces themselves, rule 8.)
SLIDE = 2.4


@contextlib.contextmanager
def _slid(m, height):
    """`with _slid(m, h):` draws the level faces at height h in the frame of what looks down; the
    piece is shown by _slid_display."""
    with _tilted(m), m.moved((0.0, 0.0, SLIDE * height)):
        yield


def _ball_under(m, centre, radius, bands, sides=8, squash=1.0, emit=15):
    """What looks down of a ball of K.glass_ball (the same arguments, the bands from the bottom up):
    the foot of every layer that is wider than the layer under it -- the steps of the lower half --
    as the polygons Model.ball draws, each in the slid frame of its height."""
    hw = math.tan(math.pi / sides)
    under = 0.0
    for t0, t1, layers, mat in bands:
        for i in range(layers):
            a, b = t0 + (t1 - t0) * i / layers, t0 + (t1 - t0) * (i + 1) / layers
            r = radius * math.sqrt(max(0.0, 1.0 - ((a + b) / 2.0) ** 2))
            y = centre[1] + radius * squash * a
            seed = None
            for s in range(sides // 2 if r > under + 1e-9 else 0):
                angle = 360.0 * s / sides
                with _slid(m, y):
                    m.box((centre[0] - r * hw, y, centre[2] - r), (centre[0] + r * hw, y + 0.5, centre[2] + r), mat,
                          rot=("y", angle, tuple(centre)) if angle else None, skip="nsewu", faces={"d": mat},
                          grain="x", seed=seed, emit=emit, shade=not emit)
                seed = m.parts[-1]["seed"]
            under = r
    return m


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


def _sheet(m, hw, cx, r_out, r_in, top, mat=PLATE):
    """Riveted sheet over all that lies outside the arch ring, up to `top`: rows of boxes whose inner
    ends lie under the ring, so no light is left between the iron and the stone above the springing
    and the glass keeps the clean half round. The ring turns about x = cx; r_in is the widest its
    soffit gets."""
    m._n += 1
    seed, gap, y = m._n, r_out * r_out - r_in * r_in, 0.0
    while y < r_in:
        h = 0.5
        while (y + h + 0.5) ** 2 - y * y <= gap and y + h < r_in:
            h += 0.5
        inner = (math.sqrt(max(0.0, r_in * r_in - y * y)) + math.sqrt(max(0.0, r_out * r_out - (y + h) ** 2))) / 2.0
        for a, b in ((-hw, cx - inner), (cx + inner, hw)):
            if b - a >= 0.5:
                m.box((a, SPRING + y, 0.0), (b, SPRING + y + h, SHEET), mat, seed=seed, grain="x")
        y += h
    m.box((-hw, SPRING + y, 0.0), (hw, top, SHEET), mat, seed=seed, grain="x")


# The stone head over the iron (A3, main/_order.arch): a stair hung in each top corner narrows the
# opening by half a block either side at 5.0 blocks, and at 5.5 blocks it is shut -- a slab hung
# between the two stairs of a three-wide head (facade.CROWN, the director's ruling of 11-15), the
# two stairs themselves in a two-wide one. So the iron ends at 5.5 blocks: nothing of it is made to
# hide behind stone, and the ring's crown stands right under the stone's.
SHUT = 44.0
# rivets on the spandrel sheet where the stone head leaves it in sight, in the corners beside the
# ring (x, y in units)
SHEET_RIVETS = {
    3: [(-7.0, 43.0), (7.0, 43.0), (-11.0, 39.0), (11.0, 39.0)],
    2: [(-2.5, 42.0), (0.0, 42.0), (2.5, 42.0), (-6.5, 38.5), (6.5, 38.5)],
}


def _head(m, width, jambs):
    """The round head the windows and the doorways share: a half ring, 6 px deep, that springs from
    the 4.0 line and carries on the inner edges of the two jambs, and riveted sheet in the spandrels
    up to where the stone head is shut.
    So the round of glass is centred on what the jambs leave: with a window's unequal jambs that is
    the middle of the pane's net, half a pixel beside the middle of the stone, and the lights the
    ring cuts come out the same left and right. The ring is as wide as the wider jamb; beside the
    narrower one the rest of it runs into the stone of the reveal. Returns the soffit radius."""
    hw = width * 4.0
    left, right = jambs
    cx, r, wide = (left - right) / 2.0, hw - (left + right) / 2.0, max(left, right)
    sides = 32 if width >= 3 else 24
    m.ring("z", (cx, SPRING, DEEP / 2.0), r + wide / 2.0, wide, DEEP, IRON, sides=sides, arc=(0.0, 180.0))
    _sheet(m, hw, cx, r + wide, r / math.cos(math.pi / sides), SHUT)
    for x, y in SHEET_RIVETS[width]:
        K.rivet(m, (x, y, SHEET))
    return r


def _frame(m, width, foot=True, jambs=JAMBS):
    """Jambs, transom and head of a `width`-block arched opening six blocks high; with `foot`, the
    riveted plate over the bottom row of lights, its top edge on the pane's first level muntin.
    A window's rivets sit where the pane's muntins meet the iron, a pixel beside the middle like the
    net itself; a doorway has no pane behind it and its rivets are spaced about its own middle."""
    hw = width * 4.0
    left, right = jambs
    m.box((-hw, 0.0, 0.0), (-hw + left, SPRING, DEEP), IRON, grain="y")
    m.box((hw - right, 0.0, 0.0), (hw, SPRING, DEEP), IRON, grain="y")
    m.box((-hw, SPRING - 1.0, 0.0), (hw, SPRING + 1.0, DEEP), IRON, grain="x")
    if foot:
        m.box((-hw + left, 0.0, 0.0), (hw - right, 4.0, SILL), IRON_D, grain="x")
    on_net = 0.5 if foot else 0.0
    for x in _muntins(hw):
        K.rivet(m, (x + on_net, SPRING, DEEP))
        if foot:
            K.rivet(m, (x + on_net, 2.0, SILL))
    for y in (7.5, 15.5, 23.5):                              # the reveal faces of the jambs, on the block lines
        K.rivet(m, (-hw + left, y, DEEP / 2.0), out="x")
        K.rivet(m, (hw - right, y, DEEP / 2.0), out="-x")
    return _head(m, width, jambs)


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


def _fan(m, r, rays, wide, hub=3.5, arc=7.0):
    """What fills the half round over a doorway: an iron fan -- a hub on the transom (its radius
    `hub`), rays from it to the ring and one arc between (its middle radius `arc`)."""
    z = (0.5, 1.5)
    for i in range(1, rays + 1):
        _ray(m, 180.0 * i / (rays + 1), hub - 0.5, r + 0.25, wide, z, IRON_D)
    m.ring("z", (0.0, SPRING, 1.0), arc, wide, 1.0, IRON_D, sides=24, arc=(0.0, 180.0))
    m.ring("z", (0.0, SPRING, 1.25), hub / 2.0, hub, 1.5, IRON, sides=12 if hub < 4.0 else 16, arc=(0.0, 180.0))
    K.rivet(m, (0.0, SPRING + math.floor(hub + 1.0) / 2.0, 2.0))     # in the middle of what shows over the transom


DOOR_JAMBS = (1.0, 1.0)         # a doorway's jambs: 2 px either side, no pane to stand on


def _door_frame(width=3):
    """The iron frame of the entrance doorway and the fan in its head, at scale 2 (anchor: the foot
    centre of the doorway, on the plane the glass of a window would stand in). The glass behind the
    fan is the piece `fanlight`."""
    m = M.Model(PREFIX + "door_frame", px=2.0)
    _fan(m, _frame(m, width, foot=False, jambs=DOOR_JAMBS), rays=5, wide=0.5)
    return m


def _fanlight(width=3):
    """The amber glass of the doorway's fanlight, at scale 2 (anchor as door_frame): it fills the
    half round behind the iron fan, runs in a pixel under the ring and is drawn as one-pixel rows in
    three tones, hot round the hub. It glows -- with the lamp under the canopy it is all the light
    the family has of its own -- so it is drawn in the tilted frame."""
    m = M.Model(PREFIX + "fanlight", px=2.0)
    rg = width * 4.0 - sum(DOOR_JAMBS) / 2.0 + 0.5
    with _tilted(m):
        m._n += 1
        seed, y = m._n, 1.0
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
    return m


LEAF_W, LEAF_T = 12.0, 1.5      # a leaf: 1.5 blocks wide, a 3 px plate; what is fixed on it stands 1 px proud
LEAF_ANCHOR = (0.5, 0.0, 0.0)   # a leaf's anchor: its foot, a pixel in from the hinge edge (x = 0), so that the
                                # entity of a shut leaf stands in the doorway and not in the jamb (leaves())
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


def _pull(m, x, proud, y=7.5):
    """A brass bar to pull a leaf by, on both faces, half a block long from y up: 1.0 to 1.4 blocks
    above the floor."""
    for s in (1.0, -1.0):
        z0 = s * (LEAF_T / 2.0 + proud)
        for foot in (y, y + 3.0):
            m.box((x, foot, s * LEAF_T / 2.0), (x + 1.0, foot + 1.0, z0 + s * 1.0), BRASS_D)
        m.box((x, y, z0 + s * 0.5), (x + 1.0, y + 4.0, z0 + s * 1.0), BRASS, grain="y")


def _door_leaf():
    """One leaf of the entrance door: riveted plate, a kick plate, two ledges, a brass pull and a
    glazed porthole high up like a ship's, at scale 2 (the hinge edge is x = 0 and the leaf runs
    along +x; anchor: LEAF_ANCHOR). Both faces are the same. The porthole's amber glass does not
    glow: the leaves stand open against the stone of the reveals, and glass with a wall behind it
    has no light of its own (c219, pre-review P9); it takes the light of the lamp under the canopy
    like the iron."""
    m = M.Model(PREFIX + "door_leaf", px=2.0, anchor=LEAF_ANCHOR)
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
    K.glass_prism(m, "z", (cx, cy), -t - 0.25, t + 0.25, 2.6, GLASS_AMBER, emit=0)
    _pull(m, 9.5, 0.5)
    _hinges(m, ((2.0, 4.5), LOCK, top))
    return m


def _gate(width=3):
    """A side arch of the entrance, closed: the door's frame, an open iron fan in the head and a pair
    of barred leaves that repeat the door's kick plate and ledges, at scale 2 (anchor as door_frame).
    The lower third of the leaves, up to the lock rail, is shut by a sheet behind the bars, as the
    door's leaf is plate there: a gate reads as a gate by what is solid below, the bars above it and
    the light behind them (c164 #21988, #22558).
    The fan has an even number of rays, none on the middle: the upright line of the two meeting
    stiles ends at the transom and does not run on to the crown, where transom and upright would
    stand against the light as a cross (c219, pre-review P9). Six rays from a hub 9 px in radius:
    no opening between them is narrower than 2 px (eight from the fanlight's small hub left slits
    of half a pixel round it, a smear in the pictures).
    The leaves hang at the back of the frame and nothing on them stands more than 3.5 px out of
    the glass face: who walks into the gate is stopped by the barriers behind it (doors()) with
    his eye 4.8 px out, and the game draws nothing nearer to the eye than 0.8 px (GATE_REACH)."""
    m = M.Model(PREFIX + "gate", px=2.0)
    _fan(m, _frame(m, width, foot=False, jambs=DOOR_JAMBS), rays=6, wide=1.0, hub=4.5, arc=7.5)
    hw, z, zr, top = width * 4.0, (0.0, 1.0), (0.25, 0.75), LEAF_H      # no slit of light under the transom
    for sx in (-1.0, 1.0):
        def span(x0, x1, y0, y1, mat, zz=z, **kw):
            a, b = sorted((sx * x0, sx * x1))
            m.box((a, y0, zz[0]), (b, y1, zz[1]), mat, **kw)
        span(hw - 2.0, hw - 1.0, 0.0, top, IRON, grain="y")                               # the hanging stile
        span(0.0, 1.0, 0.0, top, IRON, grain="y")                                         # the meeting stile
        for x in (2.5, 5.0, 7.5):                                                         # bars 2 px, lights 3 px
            span(x, x + 1.0, KICK, top - 1.0, IRON, grain="y")
        span(1.0, hw - 2.0, 0.0, KICK, IRON_D, zr, grain="x")                             # the kick plate
        span(1.0, hw - 2.0, KICK - 0.25, LOCK[0] + 0.25, IRON, (zr[0] + 0.125, zr[1] - 0.125), grain="y")  # the sheet
        for y0, y1 in (LOCK, WAIST, (top - 1.0, top)):
            span(1.0, hw - 2.0, y0, y1, IRON_D, zr, grain="x")
        for x in (3.0, 5.5, 8.0):
            K.rivet(m, (sx * x, KICK - 1.0, zr[1]))
            K.rivet(m, (sx * x, 9.5, z[1]))
            K.rivet(m, (sx * x, 15.5, z[1]))
    m.box((-1.5, 8.0, z[1]), (1.5, 11.0, z[1] + 0.5), IRON_D)                             # the lock case
    m.tube("z", (0.0, 9.5), z[1] + 0.5, z[1] + 0.75, 0.75, BRASS, sides=8)                # and its brass boss
    return m


NIGHT = [K.flat("night_glass", i) for i in range(4)]
# the lights of a glazed leaf, top row first: mostly one tone of the sky, now and then a darker or a
# lighter pane, as A1 paints its dark windows
_PANES = ("121", "111", "101", "112", "111")


def _glazed_leaf():
    """One leaf of the west door: a riveted plate in the lower third, dark glass in 6 x 7 px lights
    above it, at scale 2 (the hinge edge is x = 0 and the leaf runs along +x, 1.5 blocks by 4;
    anchor: LEAF_ANCHOR). Both faces are the same."""
    m = M.Model(PREFIX + "glazed_leaf", px=2.0, anchor=LEAF_ANCHOR)
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
    _studs(m, [(1.5, 6.0), (10.5, 6.0)])
    _pull(m, 9.5, 0.5, y=sill - 4.0)                    # both its feet on the plate, none on the glass
    _hinges(m, ((2.0, 4.5), (14.0, 16.5), (27.0, 29.5)))
    return m


# ---- the glazed entrance canopy and its lamp ----------------------------------------------------------
def _canopy(width=5, depth=3):
    """The glazed canopy over the middle arch of the entrance, at scale 2. Anchor: the middle of its
    back edge on the face of the two pilasters it hangs from, at its underside -- the top of the
    string course, on which it lies (c164 #21442). Between the pilasters the roof runs one block
    further back, to the wall. Five lights across and two deep; a riveted valance in front and at
    the sides; under each end a quarter-round brace that springs from the pilaster three blocks
    down and meets the front edge (_brace). The middle of the underside is left free: canopy_lamp
    hangs there."""
    m = M.Model(PREFIX + "canopy", px=2.0)
    hw, out, back, pil = width * 4.0, depth * 8.0, -8.0, 8.0
    bay = hw - pil                                           # half the width between the pilasters
    rim = 1.5                                                # the frame: channel iron 3 px high
    m.box((-hw, 0.0, out - 1.0), (hw, rim, out), IRON, grain="x")
    m.box((-bay, 0.0, back), (bay, rim, back + 1.0), IRON, grain="x")
    for sx in (-1.0, 1.0):
        for x0, x1, z0, z1, grain in ((hw - 1.0, hw, 0.0, out - 1.0, "z"), (bay, hw - 1.0, 0.0, 1.0, "x"),
                                      (bay - 1.0, bay, back + 1.0, 1.0, "z")):     # the return, up to the glass
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
        _brace(m, sx * (hw - pil / 2.0), out - 1.0, pil)
    return m


RIB = 3.0           # a brace's rib is 6 px deep: a plate between two flanges of 1 px, riveted down its middle


def _brace(m, x, r, top):
    """A brace of the canopy, on the middle of a pilaster (at x): a riveted plate rib bent to a
    quarter round -- the family's riveted plate and its round head in one piece, and iron enough
    under a roof of five blocks by three (a bar of 2 px read as a wire there). The rib's back, of
    radius r, leaves the wall plate upright and meets the canopy's underside behind the front
    valance, whose rail it carries. The wall plate ends under the string course, `top` below the
    canopy; in the corner under that course a ring, the family's small scroll, and under the shoe
    the rib stands in the plate's foot curls forward."""
    cy, cz = -r, r + 0.5                                     # the rib turns about this point
    web = r - RIB / 2.0
    m.box((x - 1.5, cy - 2.5, 0.0), (x + 1.5, -top, 0.5), IRON_D, grain="y")              # the wall plate
    m.ring("x", (x, cy, cz), web, RIB - 1.0, 1.0, IRON, sides=48, arc=(270.0, 360.0))
    for q in (r - 0.25, r - RIB + 0.25):                                                  # the flanges
        m.ring("x", (x, cy, cz), q, 0.5, 2.0, IRON_D, sides=48, arc=(270.0, 360.0))
    for k in range(1, 9):
        t = math.radians(270.0 + 10.0 * k)
        y, z = cy + web * math.cos(t), cz + web * math.sin(t)
        K.rivet(m, (x + 0.5, y, z), out="x")
        K.rivet(m, (x - 0.5, y, z), out="-x")
    m.box((x - 1.5, cy - 1.0, 0.5), (x + 1.5, cy, RIB + 1.0), IRON_D, grain="z")           # the shoe
    m.ring("x", (x, cy - 2.25, 2.25), 1.25, 1.0, 1.0, IRON, sides=12, arc=(90.0, 360.0))   # the foot's curl
    m.ring("x", (x, -top - 2.0, 2.5), 1.5, 1.0, 1.0, IRON, sides=12)                      # the scroll
    for y in (-top - 2.0, -top - 6.5):                       # the plate's rivets, either side of the rib
        for side in (-1.0, 1.0):
            K.rivet(m, (x + side, y, 0.5))


OPAL = [K.flat("opal", i) for i in range(len(P.RAMPS["opal"]))]
LAMP_QUARTERS = ("in", "left", "right")       # the pieces of the lamp that are glass alone (_canopy_lamp):
LAMP_PIECES = ["canopy_lamp"] + ["canopy_lamp_" + way for way in LAMP_QUARTERS + ("under",)]      # ... and all of it


def _canopy_lamp(way="out"):
    """The lamp under the canopy, the brightest point of the entrance (c164 #21442): an opal globe in
    an iron cage on a rod, at scale 1. Anchor: the point under the canopy it hangs from; the foot of
    the lamp is 28.5 px below it. The lamp is five pieces, so the globe shows its tones as painted
    from wherever one comes: four (WAYS), each drawn in the frame tilted for its quarter of the
    globe -- the one that looks out of the wall has the iron as well, the other three are glass
    alone -- and "under", the steps of the globe's lower half, which look down (SLIDE)."""
    m = M.Model(PREFIX + "canopy_lamp" + ("" if way == "out" else "_" + way), px=1.0)
    bands = [(-1.0, -0.75, 1, OPAL[0]), (-0.75, -0.5, 1, OPAL[1]), (-0.5, -0.25, 1, OPAL[2]),
             (-0.25, 0.25, 1, OPAL[4]), (0.25, 0.5, 1, OPAL[3]), (0.5, 0.75, 1, OPAL[2]), (0.75, 1.0, 1, OPAL[1])]
    globe = dict(centre=(0.0, -21.0, 0.0), radius=5.0, bands=bands, sides=12, squash=1.0)
    if way == "under":
        return _ball_under(m, **globe)
    with _tilted(m, way):
        K.glass_ball(m, **globe)
        _facing(m, 0, way)
        if way != "out":
            return m
        m.tube("y", (0.0, 0.0), -1.0, 0.0, 2.5, IRON_D)
        m.tube("y", (0.0, 0.0), -12.0, -1.0, 0.5, IRON, sides=4)
        m.tube("y", (0.0, 0.0), -7.0, -6.0, 1.0, IRON_D, sides=4)
        m.taper("y", (0.0, 0.0), -12.0, -15.0, 1.5, 5.0, IRON, sides=8, steps=3)              # the hood
        m.tube("y", (0.0, 0.0), -16.0, -15.0, 6.0, IRON_D, sides=8)
        for angle in (45.0, 135.0, 225.0, 315.0):       # the cage: no bar before the middle of the globe,
            m.box((5.5, -26.0, -0.5), (6.5, -16.0, 0.5), IRON, rot=("y", angle, (0.0, 0.0, 0.0)), grain="y")   # front or side
        m.ring("y", (0.0, -26.5, 0.0), 5.75, 1.0, 1.0, IRON_D, sides=8)
        m.tube("y", (0.0, 0.0), -28.5, -25.5, 1.0, IRON, sides=4)
    return m


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
    "fanlight": dict(build=_fanlight, mount="wall", scale=2.0, light=None, turns=_turns()),
    "door_leaf": dict(build=_door_leaf, mount="floor", scale=2.0, light=None),
    "gate": dict(build=_gate, mount="wall", scale=2.0, light=None),
    "glazed_leaf": dict(build=_glazed_leaf, mount="floor", scale=2.0, light=None),
    "canopy": dict(build=_canopy, mount="wall", scale=2.0, light=None),
    "canopy_lamp": dict(build=_canopy_lamp, mount="ceiling", scale=1.0, light=(0.0, -1.3, 0.0), level=13,
                        turns=_turns()),
    **{"canopy_lamp_" + way: dict(build=lambda way=way: _canopy_lamp(way), mount="ceiling", scale=1.0,
                                  light=None, turns=_turns(way)) for way in LAMP_QUARTERS},
    "canopy_lamp_under": dict(build=lambda: _canopy_lamp("under"), mount="ceiling", scale=1.0, light=None,
                              turns=_turns(), slide=SLIDE),
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


def frame(kind):
    """What the display of a piece of SPEC does to its model, scale apart: the rows of the matrix
    that takes the model's own frame to the wall's (x along the wall, y up, z out of it). A turn
    for a piece drawn in a tilted frame; for one drawn in the slid frame the turn and then the
    slide back, every level plane along the wall's normal by -SLIDE times its height."""
    spec = SPEC[kind]
    q = M.IDENT
    for axis, deg in spec.get("turns", ()):
        q = M._qmul(M.quat(axis, deg), q)
    x, y, z = zip(*(M._qrot(q, axis) for axis in ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))))
    slide = spec.get("slide", 0.0)
    return x, y, tuple(c - slide * b for b, c in zip(y, z))


def _quat_of(turn):
    """The quaternion (x, y, z, w) of a turn given as a matrix."""
    m = [[float(v) for v in row] for row in turn]
    k = max(range(3), key=lambda i: m[i][i])
    if m[0][0] + m[1][1] + m[2][2] > 0.0:
        w = math.sqrt(1.0 + m[0][0] + m[1][1] + m[2][2]) / 2.0
        return ((m[2][1] - m[1][2]) / (4.0 * w), (m[0][2] - m[2][0]) / (4.0 * w), (m[1][0] - m[0][1]) / (4.0 * w), w)
    i, j = (k + 1) % 3, (k + 2) % 3
    v = [0.0, 0.0, 0.0]
    v[k] = math.sqrt(1.0 + m[k][k] - m[i][i] - m[j][j]) / 2.0
    v[i], v[j] = (m[i][k] + m[k][i]) / (4.0 * v[k]), (m[j][k] + m[k][j]) / (4.0 * v[k])
    return (v[0], v[1], v[2], (m[j][i] - m[i][j]) / (4.0 * v[k]))


def _slid_display(model, kind):
    """The transformation of the display that shows a piece in frame(kind), for one drawn in the
    slid frame: artkit.models.display gives a turn and a scale, and a slide is neither. A display
    takes any matrix as a turn, a scale along the axes and a turn again (left_rotation, scale,
    right_rotation: its singular values and vectors), here in the half-turned frame the item
    renderer draws in; the translation brings the model's anchor to the entity, as display's does."""
    half = np.diag([-1.0, 1.0, -1.0])
    g = half @ (np.array(frame(kind)) * SPEC[kind]["scale"]) @ half
    left, scale, right = np.linalg.svd(g)
    for i in range(3):                                  # of the two ways to sign a pair of vectors, one always
        if left[np.argmax(np.abs(left[:, i])), i] < 0.0:
            left[:, i], right[i, :] = -left[:, i], -right[i, :]
    if np.linalg.det(left) < 0.0:                       # two turns: the matrix mirrors nothing, so if one of
        left[:, 2], right[2, :] = -left[:, 2], -right[2, :]         # them does, so does the other
    shift = model.shift()
    anchor = np.array([(model.anchor[i] + shift[i] - 8.0) / 16.0 for i in range(3)])
    return {
        "left_rotation": [Float(round(v, 7)) for v in _quat_of(left)],
        "right_rotation": [Float(round(v, 7)) for v in _quat_of(right)],
        "scale": [Float(round(float(v), 7)) for v in scale],
        "translation": [Float(round(float(v), 7)) for v in -g @ half @ anchor],
    }


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
    if spec.get("turns"):                               # a piece drawn in the tilted frame is turned back
        opts.setdefault("turns", spec["turns"])
    model = _models()[PREFIX + key]
    n = K.put(canvas, model, pos, mount=spec["mount"], facing=facing, yaw=yaw, scale=spec["scale"],
              origin=origin, **opts)
    if spec.get("slide"):                               # ... and one drawn in the slid frame is slid back
        canvas.entities[-1][3]["transformation"] = _slid_display(model, key)
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
GRILLES = "model"       # the base-storey windows: this family's grille on the glass ("model") or A3's bars
                        # in the wall plane ("blocks"). Only one layer stays, and side by side on the real
                        # wall it is the model: the blocks stand a block in front of the glass, their bars
                        # miss the pane's muntins and slide over them as one walks -- two nets


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


EYE, NEAR = 0.3, 0.05   # a player's eye keeps half his width from a wall or a barrier; the game draws nothing
                        # that is nearer to the eye than NEAR. A model has no collision of its own, so a
                        # piece he can walk up to lies within EYE - NEAR of what stops him, or he looks into it
GATE_REACH = EYE - NEAR             # a shut gate's leaves, from the barriers behind them (the glass face)
LEAF_OFF = 0.14         # an open leaf lies this far off the reveal, its middle plane: the face of its plate is
                        # 0.234 off, within EYE - NEAR; what is fixed on the face it turns to the stone goes in
LEAF_OUT = 7.0 / 16.0   # the hinge line of the entrance leaves: just in front of the frame's 6 px
WEST_OUT = 0.30         # the hinge line of the west door's leaves, which have no frame: this far into the reveal
WALK = 2                # the rows of a doorway a player fills: what stands in them stops him or lets him by
BARRIER = B.BARRIER     # the collision of a shut gate, which a model has not: doors()
CANOPY_LAMP = 1.5       # the lamp hangs this far in front of the pilasters, under the middle glazing bar


def leaves(canvas, kind, pos, facing="east", origin=(0, 0, 0), swing=90.0, inset=None, out=LEAF_OUT):
    """Hang a pair of leaves (`kind`: "door_leaf" or "glazed_leaf") in a three-wide doorway. pos is
    the foot centre of the doorway on the plane the leaves close in, `facing` the way it looks.
    swing: 0 is shut, 90 is open outwards with each leaf along its reveal, `inset` off it (left
    out: as far as the leaf has swung towards the reveal, LEAF_OFF when it lies along it and
    nothing when it is shut, so that a shut pair meets in the middle); the hinge line stands `out`
    in front of pos. Both leaves show the same face. Returns the entity count.
    A leaf is lit by the cell its entity stands in. A shut leaf's hinge foot lies on the face of
    the jamb, and on one side of the doorway that point counts to the jamb's stone -- a black
    leaf; so the entity stands where the leaf's anchor is, a pixel along the leaf (LEAF_ANCHOR)."""
    base = K.FACING[facing]
    tan = K.turn(base, (1.0, 0.0, 0.0))                 # along the doorway, to the right of who looks at it
    fwd = K.turn(base, (0.0, 0.0, 1.0))
    model, scale = _models()[PREFIX + kind], SPEC[kind]["scale"]
    if inset is None:
        inset = LEAF_OFF * abs(math.sin(math.radians(swing)))
    for side, yaw in ((-1.0, base + swing), (1.0, base + 180.0 - swing)):
        reach = side * (1.5 - inset)
        along = K.turn(yaw, (model.anchor[0] * scale / 16.0, 0.0, 0.0))
        at = tuple(pos[k] + origin[k] + reach * tan[k] + out * fwd[k] + along[k] for k in range(3))
        canvas.add_entity(at[0], at[1], at[2], M.display(model, yaw=yaw, scale=scale))
    return 2


def doors(canvas, table, origin=(0, 0, 0), west_swing=90.0):
    """Dress the doorways of a table as main/_plan.doors() gives it -- [dict(front, bay, cells,
    inward, y, arch, kind)], cells the columns of the wall line; the iron stands one step inward,
    where a window's glass would. An arched doorway six high: kind "door" gets the frame with its
    fanlight, a pair of riveted leaves open against the reveals, and -- where a pilaster stands on
    either side -- the canopy and its lamp; kind "gate" gets the barred gate, shut. A flat-headed
    doorway four high (the west door) gets a pair of glazed leaves, open against the reveals like
    the entrance's (west_swing: 90; 0 would shut them). Returns the entity count.

    A door people are to walk through stands open, and a shut one is a wall (c164 #522): the
    entrance and the west door, which leads to the sunset terrace, are hung open. A gate is shut,
    but a model stops nobody; so whatever stands in the plane behind its leaves is cleared (A3's
    stand-in bars) and the bottom two rows of that plane are filled with barriers, as wide as the
    leaves and no wider (the director's desk, 11-16 05:07: a barrier may stand in a shut model
    door or gate, and nowhere else). They fill the wall's inner layer under the arch: who comes
    from the court walks into the reveal and stands against the bars, who comes from the hall
    cannot step into the recess."""
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
                for x, z in cells:
                    for y in range(y0, y0 + WALK):
                        canvas.set(origin[0] + x, origin[1] + y, origin[2] + z, BARRIER)
                n += place(canvas, "gate", pos, facing=facing, origin=origin)
                continue
            n += place(canvas, "door_frame", pos, facing=facing, origin=origin)
            n += place(canvas, "fanlight", pos, facing=facing, origin=origin)
            n += leaves(canvas, "door_leaf", pos, facing=facing, origin=origin)
            n += canopy(canvas, pos, y1 + 2.0, facing=facing, origin=origin)
        elif not d.get("arch") and y1 - y0 == 3:
            n += leaves(canvas, "glazed_leaf", pos, facing=facing, origin=origin, swing=west_swing, out=WEST_OUT)
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
    for kind in LAMP_PIECES:
        n += place(canvas, kind, (lamp[0], y, lamp[2]), facing=facing, origin=origin)
    return n


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
