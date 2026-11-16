"""props/electrics -- the exposed electrics of the observatory (plan ART-PLAN 2, 7.3; part A6-props
2.4; card plan/packages/props/electrics-signs.md).

One motif for the family: white porcelain on cast iron, brass where a hand or a hammer touches it,
and the red flash of the voltage plates on what is live. A line has a start and an end and never
just stops (plan 2): it comes out of the wall in a conduit, is carried along the wall on
insulators and goes into a conduit again -- down to a junction box, into a lamp, or back into the
wall.

The pieces (16 texels to the block, px = scale; a wall piece is hung by a point of the wall's face,
its own +z out of the wall, +x to the right of whoever looks at it):

    insulator      a pin insulator on a wall bracket; the wire lies across its head, WIRE_UP over
                   the anchor and WIRE_OUT off the wall.
    lead_in        where the open wire ends: an iron fitting on a square flange, a porcelain nose
                   the wire runs into, WIRE_OUT off the wall, and a hub under it for the conduit.
    junction_box   a cast-iron box, the lid bolted on, the flash on an enamel label; a conduit
                   leaves it at the top and another at the bottom turns into the wall.
    elbow          a short conduit that turns into the wall: the end of a line with no box.
    clip           the collar that holds a conduit to the wall.
    bell           an electric bell: two coils, the armature and its hammer, a brass gong.
    wall_phone     a wall telephone in dark wood, a block wide and a block and a half tall: the
                   gong, the box with the mouthpiece, the receiver on its hook, the crank, a
                   writing shelf. Hung by the point of the wall behind the middle of its FOOT (as
                   props/instruments hangs its clocks), not by its middle.
    telegraph_key  a telegraph key for a table top; it stands (mount "floor": the anchor is the
                   middle of its foot) and its knob looks the way `facing` says, to the operator.
    cable, conduit drawn out between two points (models.between): the wire, the pipe.

For the other lines:

    from scenes.obs.props import electrics as E
    n += E.run(canvas, [(x, y, z0), (x, y, z1), (x, y, z2)], facing="east", origin=origin,
               ends=(("box", 3.75), ("feed", 4.4)))
    n += E.place(canvas, "bell", (x, y, z), facing="east", origin=origin)
    n += E.place(canvas, "wall_phone", (x, y_foot, z), facing="west", origin=origin)
    n += E.place(canvas, "telegraph_key", (x, y_table_top, z), facing="south", origin=origin)

run() strings one line: a lead-in at the first and the last point, an insulator at each point
between them, the wire from one to the next, and at each end what the wire comes from or goes to.
The points lie on the faces the supports are fixed to (pilasters, as a rule) at the height of the
wire. Where the wire passes a support nothing stands above it -- an insulator carries it on its
head -- and where something does stand above it, at a lead-in, the wire ends: seen against a wall
a line is a stroke with knobs under it and never a bar across an upright (plan red line 8).

Mounting, materials and rivets are _kit's. The test scene is build/scenes/obs_props_elecsign
(shared with props/signs).
"""
import functools

from artkit import models as M
from artkit.pixelart import Sprite

from ..common import palette as P
from . import _kit as K

PREFIX = "prop_elec_"
DRESS = False                   # build() dresses the master scene only when on (A0 #211)

IRON, IRON_D = K.IRON, K.IRON_D
BRASS, BRASS_D = K.BRASS, K.BRASS_D
PORC = P.mat("porcelain")
PORC_D = P.mat("porcelain", base=2)
COIL = P.mat("old_copper", base=1)
CABLE = K.flat("old_copper", 1)         # the wire: the tone of props/lamps' festoon cable
CONDUIT = K.flat("iron", 2)             # a conduit that is drawn out: one tone, nothing to smear
WOOD = P.mat("dark_wood")               # the telephone's boxes, the key's base: the three boards of
WOOD_L = P.mat("dark_wood", base=3)     # props/furniture and props/instruments
WOOD_D = P.mat("dark_wood", base=1)
SCREW = K.flat("brass", 4)              # a brass screw head in wood

# The line's measures, in blocks. Whoever hangs something on a line reads them from here.
WIRE_OUT = 4.0 / 16.0           # the wire runs this far off the face its supports are fixed to
WIRE_UP = 6.0 / 16.0            # ... and this far over the anchor of an insulator
AXIS_OUT = 1.0 / 16.0           # a conduit's axis off the wall (as _kit.wall_entry has it)
LEAD_DOWN = 4.5 / 16.0          # the conduit leaves a lead-in this far under its anchor
BOX_UP = 7.5 / 16.0             # ... and enters a junction box this far over its anchor
CLIP_EVERY = 1.0                # a riser is held by a clip to every so many blocks of its length
HUB = 1.1                       # texels: the radius of a hub or a collar on a conduit of 0.75. With the
                                # axis one texel off the wall its back still lies before the stone.

# the flash of the voltage plates (props/signs), on the white enamel label of a junction box
_FLASH = Sprite("elec_flash", ["wwwwww", "wwwrrw", "wwrrww", "wrrrrw", "wwrrww", "wrrwww", "wwwwww"],
                {"w": P.RAMPS["cream"][3], "r": P.RAMPS["signal"][2]})


# ---- the models ----------------------------------------------------------------------------------------
def _insulator():
    """A pin insulator on a wall bracket: a plate on the wall, an arm with a strut under it, and on
    the arm the porcelain -- a wide skirt, a waist, a shoulder, a groove and the head the wire
    lies across. Anchor: on the wall, at the top of the arm; the wire passes WIRE_UP over it and
    WIRE_OUT off the wall, along x. The plate's two rivets sit either side of the strut's foot,
    where someone who looks up at the line sees them."""
    m = M.Model(PREFIX + "insulator", px=1.0)
    m.box((-2.0, -4.0, 0.0), (2.0, 2.0, 1.0), IRON, grain="y")              # the plate on the wall
    for x in (-1.0, 1.0):
        K.rivet(m, (x, -3.0, 1.0))
    m.box((-1.0, -1.5, 1.0), (1.0, 0.0, 5.25), IRON, grain="z")             # the arm
    m.beam((0.0, -3.5, 1.0), (0.0, -1.5, 4.5), 1.0, 1.0, IRON_D)            # its strut
    c = (0.0, 4.0)
    m.tube("y", c, 0.0, 0.5, 1.0, IRON_D)                                   # the pin's collar
    m.taper("y", c, 0.5, 2.5, 2.75, 1.75, PORC, steps=2)                    # the skirt
    m.tube("y", c, 2.5, 3.25, 1.25, PORC_D)                                 # the waist
    m.taper("y", c, 3.25, 4.75, 2.0, 1.5, PORC, steps=2)                    # the shoulder
    m.tube("y", c, 4.75, 5.25, 1.0, PORC_D)                                 # the groove
    m.tube("y", c, 5.25, 6.0, 1.5, PORC)                                    # the head
    return m


def _lead_in():
    """Where the open wire goes into a conduit: a round iron fitting on a square flange bolted at
    its four corners, a porcelain nose in the middle of it that the wire runs into from either
    side, and under it the hub of the conduit. Anchor: on the wall, on the axis of the nose; the
    wire ends WIRE_OUT off the wall, the conduit leaves LEAD_DOWN under the anchor."""
    m = M.Model(PREFIX + "lead_in", px=1.0)
    m.box((-3.0, -3.0, 0.0), (3.0, 3.0, 1.0), IRON, grain="y")              # the flange on the wall
    for x in (-2.0, 2.0):
        for y in (-2.0, 2.0):
            K.rivet(m, (x, y, 1.0))
    m.tube("z", (0.0, 0.0), 1.0, 3.0, 2.0, IRON_D)                          # the fitting
    m.taper("z", (0.0, 0.0), 3.0, 5.0, 1.75, 1.25, PORC, steps=2)           # the nose
    m.tube("z", (0.0, 0.0), 5.0, 5.5, 0.75, PORC_D)
    m.tube("y", (0.0, 1.0), -4.5, -1.5, HUB, IRON)                          # the hub of the conduit
    return m


def _junction_box():
    """A cast-iron junction box: the lid bolted on at its four corners, on the lid a white enamel
    label with the flash; a hub on top for the conduit that comes down to it, and under it a
    conduit that turns into the wall. Anchor: on the wall, the middle of the box; the conduit from
    above enters BOX_UP over it."""
    m = M.Model(PREFIX + "junction_box", px=1.0)
    m.box((-6.0, -6.0, 0.0), (6.0, 6.0, 3.5), IRON, grain="y")              # the box
    m.box((-5.5, -5.5, 3.5), (5.5, 5.5, 4.25), IRON_D, grain="y")           # the lid
    for x in (-4.5, 4.5):
        for y in (-4.5, 4.5):
            K.rivet(m, (x, y, 4.25))
    m.box((-3.0, -3.5, 4.25), (3.0, 3.5, 4.5), K.flat("cream", 1), faces={"s": _FLASH}, skip="n")
    m.tube("y", (0.0, 1.0), 6.0, 7.5, HUB, IRON)                            # the hub on top
    m.tube("y", (0.0, 1.0), -7.0, -6.0, HUB, IRON)                          # the hub underneath
    m.tube("y", (0.0, 1.0), -10.5, -7.0, 0.75, IRON_D)                      # down and into the wall
    K.wall_entry(m, 0.0, -10.5)
    return m


def _elbow():
    """The end of a conduit that goes straight into the wall: a short length and the turn. Anchor:
    on the wall behind the conduit's axis, where the conduit from above ends."""
    m = M.Model(PREFIX + "elbow", px=1.0)
    m.tube("y", (0.0, 1.0), -3.0, 0.0, 0.75, IRON_D)
    K.wall_entry(m, 0.0, -3.0)
    return m


def _clip():
    """What holds a conduit to the wall: a foot and a collar round the pipe, barely wider than the
    pipe itself and taller than it is wide, so that it is a ring on the pipe and not a bar across
    it. Anchor: on the wall behind the conduit's axis."""
    m = M.Model(PREFIX + "clip", px=1.0)
    m.box((-1.0, -1.0, 0.0), (1.0, 1.0, 0.25), IRON)
    m.tube("y", (0.0, 1.0), -1.25, 1.25, HUB, IRON)
    return m


def _bell():
    """An electric bell on a cast back plate: two coils side by side under their yoke, the
    armature across their feet with the hammer at its end, and under them the brass gong. A
    conduit leaves the plate at the top and turns into the wall. Anchor: on the wall, the middle
    of the back plate."""
    m = M.Model(PREFIX + "bell", px=1.0)
    m.box((-4.0, -8.0, 0.0), (4.0, 8.0, 1.0), IRON_D, grain="y")            # the back plate
    for x in (-3.0, 3.0):
        for y in (-7.0, 7.0):
            K.rivet(m, (x, y, 1.0))
    with m.turned(("x", 90.0), about=(0.0, -3.5, 1.0)):                     # the gong bulges out of the wall
        m.ball((0.0, -3.5, 1.0), 3.5, BRASS, sides=12, layers=3, squash=0.6, part=(0.0, 1.0))
    m.tube("z", (0.0, -3.5), 2.9, 3.6, 0.75, BRASS_D)                       # the nut that holds it
    m.box((-3.0, 0.5, 1.75), (3.0, 1.25, 3.25), IRON, grain="x")            # the armature
    m.box((2.5, -0.25, 2.25), (3.0, 0.5, 2.75), IRON_D)                     # the hammer's stem
    m.tube("z", (2.75, -0.6), 1.9, 3.1, 0.75, IRON)                         # the hammer, at the gong's rim
    for x in (-1.75, 1.75):                                                 # the coils
        m.tube("y", (x, 2.5), 1.25, 1.75, 1.5, BRASS_D)
        m.tube("y", (x, 2.5), 1.75, 4.75, 1.25, COIL)
        m.tube("y", (x, 2.5), 4.75, 5.25, 1.5, BRASS_D)
    m.box((-3.25, 5.25, 1.0), (3.25, 6.0, 3.5), IRON, grain="x")            # the yoke
    m.tube("y", (0.0, 1.0), 8.0, 8.75, HUB, IRON)                           # the conduit: up and into the wall
    m.tube("y", (0.0, 1.0), 8.75, 11.0, 0.75, IRON_D)
    K.wall_entry(m, 0.0, 11.0)
    return m


def _wall_phone():
    """A wall telephone of the magneto kind: on a dark back board the bell's gong at the top with
    its hammer beside it, the box with the mouthpiece on its door, and under it the battery box
    whose lid is a writing shelf. The receiver hangs by its neck in the hook at the left, the
    crank of the generator hangs at the right, lower than the hook: the two are not a pair of
    arms. The cord runs from the receiver's tail into the side of the battery box, so nothing of
    it ends in the air. One gong and not the two side by side such telephones often have: two
    discs over the mouthpiece would be a face.
    Anchor: on the wall, behind the middle of the FOOT. 15.5 px wide (8 to the left of the anchor
    for whoever looks at it, 7.5 to the right), 23.5 px tall, 9 px off the wall."""
    m = M.Model(PREFIX + "wall_phone", px=1.0)
    m.box((-5.0, 0.0, 0.0), (5.0, 22.5, 1.0), WOOD_D, grain="y")            # the back board
    m.box((-3.0, 22.5, 0.0), (3.0, 23.5, 1.0), WOOD_D, grain="x")           # its crest
    for x in (-4.0, 4.0):
        for y in (1.0, 21.5):
            K.rivet(m, (x, y, 1.0), mat=SCREW)
    m.box((-4.5, 2.0, 1.0), (4.5, 5.5, 4.0), WOOD, grain="x")               # the battery box
    m.box((-5.0, 5.5, 1.0), (5.0, 6.25, 5.0), WOOD_L, grain="x")            # its lid: the writing shelf
    m.box((-4.0, 8.0, 1.0), (4.0, 16.0, 5.0), WOOD, grain="y")              # the box
    m.box((-3.0, 9.0, 5.0), (3.0, 15.0, 5.25), WOOD_L, grain="y")           # its door
    c = (0.0, 12.0)                                                         # the mouthpiece, on the door:
    m.tube("z", c, 5.25, 5.75, 2.25, BRASS)                                 # a brass rose,
    m.tube("z", c, 5.75, 6.75, 0.75, BRASS_D)                               # the neck,
    m.tube("z", c, 6.75, 7.75, 1.75, IRON_D)                                # the transmitter
    m.taper("z", c, 7.75, 9.0, 1.0, 1.5, IRON, steps=2)                     # and the horn one speaks into
    g = (0.0, 19.5, 1.0)
    with m.turned(("x", 90.0), about=g):                                    # the gong bulges out of the board
        m.ball(g, 2.5, BRASS, sides=12, layers=3, squash=0.6, part=(0.0, 1.0))
    m.tube("z", (0.0, 19.5), 2.4, 3.0, 0.6, BRASS_D)                        # the nut that holds it
    m.box((2.25, 16.0, 1.5), (2.75, 17.25, 2.0), IRON_D)                    # the hammer's stem, out of the box
    m.tube("z", (2.5, 17.6), 1.25, 2.25, 0.6, IRON)                         # the hammer, at the gong's rim
    r = (-6.0, 3.0)                                                         # the receiver's axis: x, z
    m.box((-5.5, 12.0, 2.5), (-4.0, 12.5, 3.5), BRASS_D, grain="x")         # the hook, out of the box's side
    m.tube("y", r, 12.75, 14.25, 1.75, IRON_D)                              # the receiver: the ear cap over the hook,
    m.tube("y", r, 12.0, 12.75, 0.75, IRON)                                 # the neck in it,
    m.taper("y", r, 8.0, 12.0, 0.9, 1.25, IRON_D, steps=2)                  # the handle hanging under it
    cord = [(-6.0, 8.0, 3.0), (-6.0, 4.75, 3.0), (-5.25, 3.75, 3.0), (-4.5, 3.75, 3.0)]
    m.hose(cord, 0.5, CABLE, sides=4)                                       # from its tail into the battery box
    m.tube("x", (11.0, 3.0), 4.0, 5.5, 0.5, BRASS_D)                        # the crank: its shaft,
    m.box((5.5, 8.5, 2.5), (6.25, 11.5, 3.5), BRASS, grain="y")             # the arm, hanging,
    m.tube("x", (9.0, 3.0), 6.25, 7.5, 0.75, WOOD_D)                        # and the wooden grip
    return m


def _telegraph_key():
    """A telegraph key for a table top: a wooden base, the brass lever between the two cheeks of
    its bearing, the knob at the end that looks to the operator, an anvil under that end and a
    stop under the other, and at the back two terminals whose leads go straight down into the
    table. The cheeks run along the lever, so that seen from above the key is three strokes side
    by side and never a bar across a bar; nothing stands through the lever either (plan red line
    8). Anchor: the middle of the foot; +z, the way `facing` says, is the operator's side. 6 px
    wide, 4.5 px to the front of the anchor and 4.75 px to the back, 4.25 px tall."""
    m = M.Model(PREFIX + "telegraph_key", px=1.0)
    m.box((-3.0, 0.0, -4.0), (3.0, 1.0, 4.0), WOOD, grain="z")              # the base
    for x in (-2.0, 1.0):
        m.box((x, 1.0, -2.0), (x + 1.0, 3.25, 1.0), BRASS, grain="z")       # the cheeks of the bearing
    m.box((-0.5, 2.25, -3.5), (0.5, 3.0, 3.75), BRASS, grain="z")           # the lever
    m.box((-0.5, 1.0, 1.5), (0.5, 2.25, 2.5), BRASS_D)                      # the anvil, under the knob's end
    m.box((-0.5, 1.0, -3.5), (0.5, 2.25, -2.5), BRASS_D)                    # the stop, under the other
    m.tube("y", (0.0, 3.0), 3.0, 3.5, 0.5, BRASS_D)                         # the knob's stem
    m.tube("y", (0.0, 3.0), 3.5, 4.25, 1.5, IRON_D)                         # the knob
    for x in (-2.0, 2.0):
        m.tube("y", (x, -3.25), 1.0, 2.0, 0.6, BRASS)                       # a terminal
        m.box((x - 0.25, 1.25, -4.75), (x + 0.25, 1.75, -3.25), CABLE)      # its lead: back off the base
        m.box((x - 0.25, 0.0, -4.75), (x + 0.25, 1.25, -4.25), CABLE)       # and down into the table
    return m


def _cable():
    """The wire: runs along +z from the anchor, 48 long, and is drawn out between two points. One
    flat tone, so drawing it out smears nothing."""
    m = M.Model(PREFIX + "cable", px=1.0)
    m.box((-0.5, -0.5, 0.0), (0.5, 0.5, 48.0), CABLE, grain="z")
    return m


def _conduit():
    """A conduit between two fittings: runs along +z from the anchor, 48 long, in flat tones, and
    is drawn out to the length wanted. Its axis is the line between the two points."""
    m = M.Model(PREFIX + "conduit", px=1.0)
    m.tube("z", (0.0, 0.0), 0.0, 48.0, 0.75, CONDUIT)
    return m


# ---- models and placing ------------------------------------------------------------------------------
SPEC = {
    "insulator": dict(build=_insulator, mount="wall"),
    "lead_in": dict(build=_lead_in, mount="wall"),
    "junction_box": dict(build=_junction_box, mount="wall"),
    "elbow": dict(build=_elbow, mount="wall"),
    "clip": dict(build=_clip, mount="wall"),
    "bell": dict(build=_bell, mount="wall"),
    "wall_phone": dict(build=_wall_phone, mount="wall"),
    "telegraph_key": dict(build=_telegraph_key, mount="floor"),
    "cable": dict(build=_cable, mount="floor"),
    "conduit": dict(build=_conduit, mount="floor"),
}
SCALE = {PREFIX + kind: 1.0 for kind in SPEC}
DRAWN = ("cable", "conduit")    # not placed by place(): drawn out between two points by run()
ENDS = ("box", "feed")


@functools.lru_cache(maxsize=None)
def _models():
    return {PREFIX + kind: spec["build"]() for kind, spec in SPEC.items()}


def models():
    return dict(_models())


def place(canvas, kind, pos, facing="south", origin=(0, 0, 0), yaw=None, **opts):
    """Put one fitting in its place; pos is where its anchor goes (scene coordinates). For a piece
    that hangs (all but the telegraph key) that is a point of the wall's face and `facing` the way
    the face looks; for the key, which stands, the middle of its foot on the table top and
    `facing` the way its knob looks. Returns the number of display entities (1)."""
    if kind in DRAWN:
        raise KeyError(f"a {kind} is drawn out between two points: electrics.run() strings it")
    spec = SPEC[kind]
    yaw = K.FACING[facing] if yaw is None else yaw
    return K.put(canvas, _models()[PREFIX + kind], pos, mount=spec["mount"], yaw=yaw, origin=origin, **opts)


def _draw(canvas, kind, a, b):
    """One length of wire or conduit from a to b (scene coordinates, the origin already added)."""
    canvas.add_entity(a[0], a[1], a[2], M.between(_models()[PREFIX + kind], a, b))
    return 1


def run(canvas, points, facing="east", origin=(0, 0, 0), ends=(None, None)):
    """String one line along a wall. Returns the number of display entities.

    points   where the wire is held, in order: points of the faces its supports are fixed to
             (scene coordinates), y the height of the wire. The first and the last are the line's
             ends and get a lead-in, the others an insulator. All the faces look the way `facing`
             says; they need not lie in one plane (a pilaster, then a wall).
    ends     what the conduit under each lead-in does, for the first and the last point:
             ("box", y)   it runs down to a junction box, the middle of the box at height y;
             ("feed", y)  it runs down to height y and ends there on the top of whatever it
                          feeds (a lamp's wall plate), which the caller has put there;
             None         it turns into the wall at once.
    A line is never left open: both of its ends go somewhere."""
    pts = [tuple(float(v) for v in p) for p in points]
    if len(pts) < 2:
        raise ValueError("a line has two ends: give it at least two points")
    yaw = K.FACING[facing]
    out = K.turn(yaw, (0.0, 0.0, 1.0))

    def off(p, far, down=0.0):
        """The point `far` off the wall in front of p and `down` under it, with the origin added."""
        return tuple(p[i] + out[i] * far + origin[i] - (down if i == 1 else 0.0) for i in range(3))

    n = 0
    for i, p in enumerate(pts):
        if i in (0, len(pts) - 1):
            n += place(canvas, "lead_in", p, facing=facing, origin=origin)
        else:
            n += place(canvas, "insulator", (p[0], p[1] - WIRE_UP, p[2]), facing=facing, origin=origin)
    for a, b in zip(pts, pts[1:]):
        n += _draw(canvas, "cable", off(a, WIRE_OUT), off(b, WIRE_OUT))
    for p, end in zip((pts[0], pts[-1]), ends):
        top = p[1] - LEAD_DOWN
        if end is None:
            n += place(canvas, "elbow", (p[0], top, p[2]), facing=facing, origin=origin)
            continue
        what, y = end
        if what not in ENDS:
            raise ValueError(f"the end of a line is one of {ENDS} or None, not {what!r}")
        foot = y + BOX_UP if what == "box" else float(y)
        if foot >= top:
            raise ValueError(f"the conduit of a lead-in at height {p[1]:g} cannot run down to {foot:g}")
        n += _draw(canvas, "conduit", off(p, AXIS_OUT, p[1] - foot), off(p, AXIS_OUT, p[1] - top))
        clips = int((top - foot) / CLIP_EVERY)
        for j in range(clips):
            at = foot + (top - foot) * (j + 1) / (clips + 1)
            n += place(canvas, "clip", (p[0], at, p[2]), facing=facing, origin=origin)
        if what == "box":
            n += place(canvas, "junction_box", (p[0], y, p[2]), facing=facing, origin=origin)
    return n


def build(canvas, origin=(0, 0, 0)):
    """What electrics place in the master scene: nothing. Where lines run on the real fronts is
    not settled (A0 #211: what is hung over the whole building stays off until it has passed on
    the real wall), and the line that builds a wall or a room strings its own with run()."""
    return 0
