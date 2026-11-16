"""site/outbuildings: the four small ancillary buildings on the hilltop (plan/ART-PLAN.md 4, 5.3,
card plan/packages/site/outbuildings.md). Shells and platforms, of blocks:

  - the meridian hut: a low stone hut over the brass meridian (skeleton MERIDIAN_HUT, centre (35,-30),
    9x9). The meridian cuts it in two: an open slot one block wide runs through the south gable (the
    door), along the ridge and through the north gable, so the transit instrument (A5) sweeps the sky
    from horizon to horizon and the brass line runs out of the door into the court. A low roof of old
    copper, flat but for its eaves course; the two iron shutters lie slid open on it either side of
    the slot. It stands on the V1 sight line to the foot of the clock tower, so it is kept low: the
    roof is at y 4, the heads of the slot's jambs at 4.5, and the top course of the base storey and
    all of the great windows show over it.
  - the water tower: four riveted legs on slate pads with one girt and knee braces, a thin gallery
    with an iron rail, a round riveted tank under a cone of old copper, a riser pipe with its valve
    and gauges and a ladder; north-west shoulder (S.WATER_TOWER). Its top stays a block under the
    cornice.
  - the weather station: a fenced instrument enclosure on the north slope (S.WEATHER_STATION) with a
    louvred shelter (a Stevenson screen), a wind mast, a rain gauge and a free pedestal.
  - the south lookout: a stone terrace with a prow toward the cloud sea (S.SOUTH_LOOKOUT), the site's
    rail round it and a brass ring in the floor where a tripod telescope stands; V11 (the look back)
    is taken from here, so nothing on it stands in that picture's middle.
  - the three ways down from the upper terrace to the shelves.

One family with the main building and plainer than it: its slate plinth and its riveted iron, the
site's rail on every edge, one lamp at a door and no more, and to each of the three that has a roof
or a vessel one piece of the old copper of the main cornice's gutter: the hut's roof, the tank's
cone, the rain gauge. The pale ashlar is the main building's alone: the hut's walls are of the
power house's tuff brick, its jambs of polished tuff (see the materials below).

The instruments themselves -- the meridian circle, the thermometer screen, the tripod telescope and
the benches -- belong to the machines and props lines; this card leaves the shells, the sockets and
the clear spots for them. Three of them are set on their spots from here, as the props line asks of
whoever builds a terrace (props/instruments places nothing itself): the tripod telescope on the
lookout's stand, the thermometer screen and the sunshine recorder on the weather platform. While
that package is not in the tree the stand and the pedestal are empty and a shelter of pale boards
stands in for the screen.

Three small things of the weather station are this card's own display models (models(), 16 pixels to
the block): the head of the wind mast with its vane, the cup wheel beside it and the rain gauge. The
vane's tail points where the skeleton's wind blows to (S.WIND, A0 #569: one wind for the whole site).
The cup wheel is the one thing here that moves: it is registered with the motion kit (motion/_kit,
a turn about its own upright axis in MK.ANEMOMETER_REV ticks) and stands as placed while no loop runs.

What the other cards read from this module (points are (x, y, z) in scene coordinates):
  LAMP_POINTS   where a lamp may hang, one to a building (props/lamps)
  HUT_AXIS      the middle of the transit circle: where its east-west axis crosses the meridian
  HUT_PIERS     the two floor cells either side of the meridian where its piers stand
  SCREEN        where the thermometer screen stands on the weather platform, the middle of its foot
  PEDESTAL_TOP  the top of the pedestal on the weather platform, where the sunshine recorder stands
  SCOPE_STAND   where the tripod telescope stands on the lookout, the middle of its foot
  MAST_HEAD     the top of the wind mast's pole, where the vane's spindle stands

The terrain card lays each shelf's flat rock and the neck that leads to it; these shells stand on the
foot levels it gives (S.*["feet"], the stone block one below) and bring a short footing of their own,
laid into air only, so nothing floats before the terrain is merged. Terrace edges use the site's one
rail (site/_kit.rail).
"""
import functools
import importlib.util
import math

from artkit import models as M
from artkit.canvas import Mix

from . import _kit as K
from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S
from ..motion import _kit as MK

ORDER = 70      # after the terrain (10) and the court paving (60); the shells go on the finished ground
# How far this card's display entities are drawn (artkit.models; INTERFACE 7): the far band, as
# everything out of doors that counts in a silhouette -- the wind engine over the water tower, the
# vane and the cups on the wind mast -- so the module sets no VIEW (it would take the props line's
# instruments down with it). Only the small things, a pixel or two from afar, are given less
# where they are placed: the rain gauge the middle band, the parts under the tower's deck the near
# one.
INSTRUMENTS = True      # stand the props line's instruments on their spots (see _place)

# --- materials (occupancy-table roles only) -------------------------------------------------------
# The hut's stone is the power house's and not the main building's (A0 #82484, 11-16): the pale
# ashlar is kept for the main building alone. A south wall gets eight tenths of the light and an
# east one six, so the hut's south gable, of the base storey's ashlar, stood brighter in V5 (0.30
# to 0.32) than the face of the clock tower behind it (0.22), whatever its lamp was set to. On
# the materials board in that light a south wall of tuff brick or polished tuff is 0.22 where the
# rough ashlar is 0.36 and the dressed 0.40 (c324 #82960): the gable comes to about 0.17, under
# the tower. Slate brick (0.16) would run into the plinth and the retaining walls
WALL = B.TUFF_BRICK.block               # tuff brick, as the power house: the hut's walls
RAKE = B.TUFF_BRICK.slab                # the raking stones of the hut's gables
JAMB = B.TUFF_SMOOTH.block              # the dressed stone of that family: the jambs of the meridian slot, and their heads
JAMB_COPE = B.TUFF_SMOOTH.slab          # the coping stone on each jamb
COPE = B.ASHLAR_PANEL.slab              # a grey-white slab: the cap of the weather station's pedestal
PLINTH = B.SLATE_BRICK.block            # dark plinths, footings, the steps' landings
POST = B.SLATE_BRICK.wall               # a slate post
COPPER = B.OLD_COPPER_CUT.block         # old copper in sheets, as in the gutter of the main cornice
COPPER_SLAB = B.OLD_COPPER_CUT.slab     # the hut's roof
COPPER_STAIR = B.OLD_COPPER_CUT.stairs  # the cone over the tank
BOARD = B.PALE_WOOD.block               # pale boards: the stand-in thermometer screen
BOARD_SLAB = B.PALE_WOOD.slab
GAUGES = B.PANELS["gauges"]             # a pair of pressure gauges on a casing: the riser's valve box
BRASS_RING = getattr(B, "BRASS_LINE", None)     # the thin inlaid brass line of the court, any shape
# the meridian in the floor: the thin inlaid line of the court once the occupancy table has it
# (BRASS_LINE, A0 #255 / c194 #273), the whole-cell inlay until then
BRASS = (B.BRASS_LINE + "[shape=north_south]") if hasattr(B, "BRASS_LINE") else B.BRASS_INLAY
IRON = B.IRON_RIVETED.block             # riveted plate: legs, bands, decks
IRON_SLAB = B.IRON_RIVETED.slab
IRON_STAIR = B.IRON_RIVETED.stairs
PLATE = B.IRON_PLATE                    # plain plate: the tank
BARS = B.IRON_BARS                      # ladders and trestles of iron (stone edges: K.rail)
HATCH = B.IRON_HATCH                    # hatch, shutter: the riveted leaves on the hut's ridge (c198 #36725)
ROD = B.IRON_ROD                        # thin rod: finials, the wind mast
PIPE = B.IRON_PIPE                      # thin pipe: the riser

# a dark broken mix for the shelves' own floors so none reads as one flat sheet
FOOTING = Mix({B.SLATE_BRICK.block: 10, B.SLATE_TILE.block: 3, B.SLATE_SMOOTH.block: 3}, seed=2292)
STEP = B.SLATE_BRICK.stairs             # the steps down to the shelves: the terrace's small dark stone

# The ways down from the upper terrace, agreed with the terrain card (c221 #21052): the terrain
# leaves its railing open in these cells and stands a gate pier either side; the steps are here.
LOOKOUT_WAY = (44, 46)      # x, through the terrace's south edge, on the lookout's middle line
WEATHER_WAY = (2, 4)        # x, through the north edge
TOWER_WAY = (-33, -31)      # z, through the west edge


# --- where things stand, for the other cards (all from the skeleton) -------------------------------
def _middle(box):
    x0, z0, x1, z1 = box
    return (x0 + x1) // 2, (z0 + z1) // 2


def _lamp_points():
    door_x, door_z = S.MERIDIAN_HUT["door"]
    cx, cz = _middle(S.WATER_TOWER["box"])
    return {
        # the south gable, east of the slot, facing south: (37.5, 2.5, -25.0)
        "hut_door": (door_x + 2.5, S.GROUND + 2.5, door_z + 1.0),
        # the north-east leg's south face, under the girt, by the ladder: (-14.5, 1.5, -32.0)
        "tower_foot": (cx + 2.5, S.WATER_TOWER["feet"] + 3.5, cz - 1.0),
    }


# Where a lamp may hang, one to a building and no more (A0 #22568: the small buildings on the hill
# keep dark but for one lamp at the door). Points on a wall face, for the lamps card to dress
# (props/lamps reads this table). A wall lamp hangs in the cell in front of its point, so that cell
# is kept free: the tower's lamp hangs under the girt, in the cell below it (c220 #32102). The
# lookout has none on purpose: V11 is taken from it and wants a dark foreground; the weather station
# has none either, its instruments are read by the moon.
LAMP_POINTS = _lamp_points()

# For the transit circle (machines/meridian-astrograph): the middle of the hut at the height of the
# instrument's east-west axis, and the two floor cells either side of the meridian for its piers.
# The room is clear from wall to wall (x 32..38, z -33..-27): 3.5 high under the roof, open to the
# sky over the meridian's own column. The slot is one block wide.
_HUT_X, _HUT_Z = S.MERIDIAN_HUT["centre"]
HUT_AXIS = (_HUT_X + 0.5, S.GROUND + 2.0, _HUT_Z + 0.5)                         # (35.5, 2.0, -29.5)
HUT_PIERS = [(_HUT_X - 2, S.GROUND, _HUT_Z), (_HUT_X + 2, S.GROUND, _HUT_Z)]    # (33, 0, -30), (37, 0, -30)


def _station_spots():
    """The cells (x, z) of what stands on the weather platform: the screen (the west one of the two
    cells its stand-in of blocks takes), the wind mast, the rain gauge and the free pedestal."""
    x0, z0, x1, z1 = S.WEATHER_STATION["box"]           # -2,-49,8,-43
    return dict(screen=(x0 + 2, z0 + 3), mast=(x1 - 2, z0 + 2), gauge=(x1 - 2, z1 - 2),
                pedestal=((x0 + x1) // 2, z0 + 2))


def _scope_cell():
    """The cell (x, z) of the telescope stand: on the lookout's middle line, in the prow."""
    x0, z0, x1, z1 = S.SOUTH_LOOKOUT["box"]             # 40,48,50,56
    return (x0 + x1) // 2, z1 - 2


_SPOTS = _station_spots()
# the screen stands on the joint of its two cells, the pedestal's top is a slab over a post
SCREEN = (_SPOTS["screen"][0] + 1.0, float(S.WEATHER_STATION["feet"]),
          _SPOTS["screen"][1] + 0.5)                                            # (1.0, -4.0, -45.5)
PEDESTAL_TOP = (_SPOTS["pedestal"][0] + 0.5, S.WEATHER_STATION["feet"] + 1.5,
                _SPOTS["pedestal"][1] + 0.5)                                    # (3.5, -2.5, -46.5)
SCOPE_STAND = (_scope_cell()[0] + 0.5, float(S.SOUTH_LOOKOUT["feet"]),
               _scope_cell()[1] + 0.5)                                          # (45.5, -5.0, 54.5)
MAST_RODS = 8                           # the wind mast: eight rods on a slate post
MAST_HEAD = (_SPOTS["mast"][0] + 0.5, S.WEATHER_STATION["feet"] + 1.0 + MAST_RODS,
             _SPOTS["mast"][1] + 0.5)                                           # (6.5, 5.0, -46.5)
GAUGE = (_SPOTS["gauge"][0] + 0.5, float(S.WEATHER_STATION["feet"]),
         _SPOTS["gauge"][1] + 0.5)                                              # (6.5, -4.0, -44.5)


# --- the weather station's own display models (16 pixels to the block) ----------------------------
MODEL_HEAD = "site_weather_head"        # the head of the wind mast: collar, cup arm, spindle and vane
MODEL_CUPS = "site_weather_cups"        # the cup wheel, a piece of its own so that it can turn
MODEL_GAUGE = "site_weather_gauge"      # the rain gauge
CUPS_ARM = 10.0                         # pixels west of the pole's axis: where the cup wheel's spindle stands
CUPS_UP = 2.5                           # pixels over the top of the pole: the middle of the wheel's hub
CUPS_AT = (MAST_HEAD[0] - CUPS_ARM / 16.0, MAST_HEAD[1] + CUPS_UP / 16.0, MAST_HEAD[2])     # (5.875, 5.156, -46.5)


@functools.lru_cache(maxsize=None)
def _models():
    dark, iron = P.mat("iron_dark"), P.mat("iron")
    copper, brass = P.mat("old_copper"), P.mat("brass")
    on = (0.0, 0.0)

    # The head of the wind mast, in pixels from the top of the pole (the rod's knob is the 4 px under
    # it). One arm, to the west and under the top, carries the cup wheel; the vane turns on a spindle
    # over the top. Seen from the east or the west the vane lies on top of the pole like the bar of a
    # T with unequal ends and nothing stands over it; seen along the wind the arm is one-sided: from
    # no side is it a cross.
    m = M.Model(MODEL_HEAD)
    m.tube("y", on, -4.5, 0.5, 2.75, iron)                              # a collar over the pole's knob
    m.box((-CUPS_ARM - 0.5, -2.75, -0.5), (-2.0, -1.25, 0.5), dark, grain="x")      # the arm, west
    m.tube("y", (-CUPS_ARM, 0.0), -3.25, CUPS_UP - 1.0, 0.5, dark, sides=4)         # the cups' spindle
    m.tube("y", on, 0.5, 13.0, 0.5, dark, sides=4)                      # the vane's spindle
    m.ball((0.0, 13.75, 0.0), 1.25, brass, sides=8, layers=4)           # and the ball that keeps it on
    m.tube("y", on, 8.0, 11.0, 1.25, iron)                              # the vane's sleeve
    # the vane itself lies along the wind: the arrow's point into it, the copper tail down it
    wx, wz = float(S.WIND[0]), float(S.WIND[2])
    with m.aimed((0.0, 9.5, 0.0), (wx, 9.5, wz), "z"):
        m.box((-0.5, -0.5, -7.0), (0.5, 0.5, 6.0), dark, grain="z")                 # the shaft
        m.taper("z", on, -7.0, -10.5, 1.5, 0.25, brass, sides=4, steps=3)           # the point
        m.box((-0.25, -2.5, 5.0), (0.25, 2.5, 8.5), copper, grain="z")              # the tail: a swallow's,
        m.box((-0.25, 0.75, 8.5), (0.25, 2.5, 12.5), copper, grain="z")             # two tongues
        m.box((-0.25, -2.5, 8.5), (0.25, -0.75, 12.5), copper, grain="z")

    # The cup wheel, in pixels about its hub: three arms, never four. It turns about y through the
    # anchor.
    w = M.Model(MODEL_CUPS)
    w.tube("y", on, -1.0, 1.0, 1.0, dark)
    for k in range(3):
        a = math.radians(90.0 + 120.0 * k)
        ux, uz = math.cos(a), -math.sin(a)
        w.beam((ux, 0.0, uz), (4.0 * ux, 0.0, 4.0 * uz), 0.75, 0.75, dark)
        w.tube("y", (5.0 * ux, 5.0 * uz), -1.5, 1.5, 1.75, copper, sides=6)

    # The rain gauge, in pixels from the floor: a copper can on an iron foot, a brass rim round its
    # dark mouth.
    g = M.Model(MODEL_GAUGE)
    g.tube("y", on, 0.0, 1.0, 3.25, dark)
    g.tube("y", on, 1.0, 9.0, 2.5, copper)
    g.tube("y", on, 9.0, 10.0, 3.0, brass, cap=dark)
    return {m.name: m, w.name: w, g.name: g}


# --- the wind engine on the water tower (the card's own display models; it turns) ------------------
# A sail wheel on a short lattice mast on the point of the tank's cone, where a finial rod stood:
# the wind fills the tank. The wheel stands before the mast, into the wind, its tail down the wind
# (S.WIND, as the vane of the weather station); its shaft works a pump rod that goes down through the
# tank and comes out under the deck, beside the riser, into the pump on the valve box: the box is
# the pump's chest, the riser its rising main. The wheel is three blocks and a quarter across: it
# clears the cone under it, and its top stays under the roof terrace's floor (S.ROOF_FLOOR). From
# the court the main building hides it; from the roofs, the west terrace and the north slope it is
# the thing that turns.
#
# What it is made of, as the machines' reviewer asked (cr3, #89688): a wheel that reads as a ring
# and not as spokes, eighteen sails of plate between an inner and an outer hoop, the inner third
# open; a tail that is one broad riveted plate; all of it dark iron, no lighter than the tank's
# hoops; a guide for the pump rod every two blocks.
MODEL_WIND_MAST = "site_windpump_mast"      # the lattice mast on the cone's point and the head on it: turntable,
#                                             gear case and shaft (one piece: neither moves)
MODEL_WIND_TAIL = "site_windpump_tail"      # the tail on its hinge, a piece of its own: it hunts in the wind
MODEL_WIND_WHEEL = "site_windpump_wheel"    # the sail wheel, a piece of its own: it turns
MODEL_WIND_ROD = "site_windpump_rod"        # the pump rod under the deck, a piece of its own: it rises and falls
MODEL_WIND_PUMP = "site_windpump_pump"      # the pump barrel on the valve box, which the rod works in
MODEL_WIND_GUIDE = "site_windpump_guide"    # a guide of the rod, clipped to the riser, and the riser's blue band
WHEEL_R = 1.625                         # blocks: the wheel's radius
WHEEL_SAILS = 18
WHEEL_PITCH = 18.0                      # degrees a sail is turned out of the wheel's plane
WHEEL_REV = 60                          # ticks a turn: twenty turns a minute, a light wind
WHEEL_OUT = 12.0                        # pixels the wheel's middle stands before the mast's axis, into the wind
MAST_UP = 36.0                          # pixels from the cone's point to the wheel's shaft
TAIL_HINGE = 4.0                        # pixels the tail's hinge pin stands behind the mast's axis, down the wind
TAIL_HUNT = (6.0, 160)                  # degrees to either side, ticks there and back
ROD_STROKE = 3.0                        # pixels the pump rod rises and falls, once a turn
ROD_OFF = 4.5                           # pixels the rod stands off the riser's axis, into the wind
ROD_GUIDES = (3.25, 5.25, 7.25)         # blocks above the tower's feet: a guide holds the rod every two blocks
WIND_NUMBER = 31                        # the machine's number, on its plate (plan/fine.md 4; a6 #90826)
_TANK_POINT = S.WATER_TOWER["feet"] + 15.0                          # 13.0: the top of the cone's last copper block
_TANK_AXIS = tuple(v + 0.5 for v in _middle(S.WATER_TOWER["box"]))  # (-16.5, -30.5)
_WIND = (float(S.WIND[0]), float(S.WIND[2]))
_WIND = tuple(v / math.hypot(*_WIND) for v in _WIND)                # the way the wind blows to, one block of it
# the wheel's middle, on its shaft: (-16.5, 15.25, -31.25). For the lines that add sound or steam.
WIND_WHEEL = (_TANK_AXIS[0] - _WIND[0] * WHEEL_OUT / 16.0, _TANK_POINT + MAST_UP / 16.0,
              _TANK_AXIS[1] - _WIND[1] * WHEEL_OUT / 16.0)


@functools.lru_cache(maxsize=None)
def _wind_models():
    dark, iron = P.mat("iron_dark"), P.mat("iron")
    brass, blue = P.mat("brass_dark"), P.mat("enamel")
    on = (0.0, 0.0)

    # The mast, in pixels from the cone's point: four legs that stand on the corners of the cone's
    # last block and lean in to the turntable, each in a shoe; two rounds of girts with a gusset at
    # every joint; the pump rod's pipe up the middle; rungs up the lee side, to oil the gear by.
    t = M.Model(MODEL_WIND_MAST)
    foot, head, top = 7.0, 2.5, MAST_UP - 3.0
    lean = (foot - head) / top
    girts = (top * 0.36, top * 0.70)
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            t.beam((sx * foot, 0.0, sz * foot), (sx * head, top, sz * head), 1.5, 1.5, iron)
            t.box((sx * foot - 1.25, 0.0, sz * foot - 1.25), (sx * foot + 1.25, 0.75, sz * foot + 1.25), dark)  # a shoe
    for y in girts:
        d = foot - lean * y
        for a, b in (((-d, -d), (d, -d)), ((d, -d), (d, d)), ((d, d), (-d, d)), ((-d, d), (-d, -d))):
            t.beam((a[0], y, a[1]), (b[0], y, b[1]), 1.0, 1.0, dark)
        for sx in (-1.0, 1.0):
            for sz in (-1.0, 1.0):
                t.box((sx * d - 1.0, y - 1.0, sz * d - 1.0), (sx * d + 1.0, y + 1.0, sz * d + 1.0), iron)   # a gusset
    for k in range(12):                                                 # the rungs, on the lee side
        y = 2.5 + 2.5 * k
        if min(abs(y - g) for g in girts) < 1.25:
            continue                                                    # a girt is the rung there
        d = foot - lean * y
        t.box((-d, y - 0.25, d - 0.25), (d, y + 0.25, d + 0.25), dark, grain="x")
    t.tube("y", on, 0.0, top, 0.75, dark, sides=4)
    t.tube("y", on, top - 1.0, top, head + 1.5, iron)                   # the cap plate the turntable rides on

    # The head, drawn into the mast's model (nothing of it moves, and every display entity over
    # the tank is counted in half the board's views): in pixels about the point where the wheel's
    # shaft crosses the mast's axis, +z down the wind. A turntable, the gear case over it with its
    # lid bolted on and an oil cup, the shaft to the wheel in its bearing.
    with t.aimed((0.0, MAST_UP, 0.0), (_WIND[0], MAST_UP, _WIND[1]), "z"):
        t.tube("y", on, -3.0, -1.5, 3.5, dark)                          # the turntable
        t.box((-2.0, -1.5, -4.0), (2.0, 2.5, TAIL_HINGE - 1.0), iron, grain="z")        # the gear case
        t.box((-2.25, 2.5, -4.25), (2.25, 3.25, TAIL_HINGE - 0.75), dark, grain="z")    # ... its lid
        for bx in (-1.75, 1.75):
            for bz in (-3.5, TAIL_HINGE - 1.5):
                t.box((bx - 0.4, 3.25, bz - 0.4), (bx + 0.4, 3.75, bz + 0.4), iron)    # the lid's bolts
        t.tube("y", on, 3.25, 5.0, 0.6, brass, sides=4)                 # the oil cup's stalk
        t.tube("y", on, 5.0, 6.25, 1.1, brass)                          # ... and the cup
        t.tube("z", on, -6.0, -4.0, 1.6, dark)                          # the bearing
        t.tube("z", on, -WHEEL_OUT, -6.0, 0.9, iron)                    # the shaft

    # The tail, in pixels about its hinge pin behind the gear case; +z is down the wind. It is
    # hinged, as such a tail is to be folded out of a gale, and hunts a little from side to side.
    # One broad plate that widens to its end, riveted to a boom and a stay, with a stiffening rim
    # and the maker's plate.
    v = M.Model(MODEL_WIND_TAIL)
    v.tube("y", on, -1.5, 4.5, 0.75, dark, sides=4)                     # the hinge pin
    v.box((-0.5, -0.5, 0.0), (0.5, 0.5, 12.0), dark, grain="z")         # the boom
    v.beam((0.0, 4.25, 0.0), (0.0, 3.0, 10.0), 0.5, 0.5, dark)          # its stay
    for z0, z1, half in ((9.0, 16.0, 4.0), (16.0, 23.0, 5.5), (23.0, 30.0, 7.0)):
        v.box((-0.375, -half, z0), (0.375, half, z1), iron, grain="z")  # the plate, in three widths
        for z in (z0 + 1.75, z1 - 1.75):
            for y in (-half + 1.25, half - 1.25):
                v.box((-0.6, y - 0.4, z - 0.4), (0.6, y + 0.4, z + 0.4), dark)      # a rivet, through
    v.box((-0.6, -7.5, 29.5), (0.6, 7.5, 30.5), dark, grain="y")        # the rim at its end
    v.box((-0.55, -1.0, 17.0), (0.55, 1.0, 22.0), brass, grain="z")     # the maker's plate, an oval
    v.box((-0.55, -1.5, 17.75), (0.55, 1.5, 21.25), brass, grain="z")

    # The wheel, in eighths of a block about its middle (shown at scale 2: 16 pixels to the block);
    # its axis is z, the wind comes from -z. Two hoops on six arms; between the hoops the sails,
    # each a plate in three widths that widens to the rim, with a slit between it and the next:
    # from afar a ring. They are turned out of the wheel's plane the way that makes the wind drive
    # the wheel right-handed about +z.
    w = M.Model(MODEL_WIND_WHEEL, px=2.0)
    r_out, r_in = WHEEL_R * 8.0, 4.5
    w.tube("z", on, -2.0, 2.0, 1.75, dark)                              # the hub
    w.tube("z", on, -3.0, -2.0, 1.0, iron)                              # ... and the nut before it
    w.ring("z", (0.0, 0.0, 0.0), r_in, 0.75, 1.0, iron, sides=16)
    w.ring("z", (0.0, 0.0, 0.0), r_out - 0.375, 0.75, 1.0, iron, sides=24)
    for k in range(6):                                                  # the arms, each behind a slit
        w.box((1.5, -0.3, 0.5), (r_out - 0.75, 0.3, 1.1), iron, rot=("z", 60.0 * k, (0.0, 0.0, 0.0)), grain="x")
    for k in range(WHEEL_SAILS):
        with w.turned(("z", (k + 0.5) * 360.0 / WHEEL_SAILS)):
            for n, (a0, a1, half) in enumerate(((5.0, 7.5, 0.75), (7.5, 10.0, 1.2), (10.0, 12.5, 1.65))):
                w.box((a0, -half, -0.25), (a1, half, 0.25), dark, grain="x", seed=7001 + n,
                      rot=("x", -WHEEL_PITCH, ((a0 + a1) / 2.0, 0.0, 0.0)))

    # The pump rod, in eighths of a block from its foot (scale 2): six blocks of rod, from inside
    # the pump barrel up into the deck.
    rod = M.Model(MODEL_WIND_ROD, px=2.0)
    rod.tube("y", on, 0.0, 48.0, 0.5, iron, sides=4)
    # its couplings, the lowest of brass: a plain rod that slides along itself is not seen to move.
    # Each keeps clear of the guides (ROD_GUIDES) through the stroke
    for at, mat in ((4.5, brass), (18.0, dark), (34.0, dark)):
        rod.tube("y", on, at, at + 1.25, 1.0, mat)

    # The pump, in pixels from the top of the valve box, about the rod's axis; +z is down the wind,
    # where the riser stands. A flanged barrel in two lengths, bolted down; a gland with its brass
    # nut on top, in which the rod's foot is never seen to end; an oil cup on the gland and a drain
    # cock at the foot.
    pump = M.Model(MODEL_WIND_PUMP)
    pump.tube("y", on, 0.0, 1.25, 2.75, dark)                           # the foot flange
    for k in range(4):
        with pump.turned(("y", 45.0 + 90.0 * k)):
            pump.box((1.75, 1.25, -0.4), (2.55, 1.75, 0.4), iron)       # its bolts
    pump.tube("y", on, 1.25, 8.0, 2.0, iron)                            # the barrel
    pump.tube("y", on, 8.0, 9.0, 2.6, dark)                             # the joint
    pump.tube("y", on, 9.0, 16.5, 2.0, iron)
    pump.tube("y", on, 16.5, 17.75, 2.6, dark)                          # the gland
    pump.tube("y", on, 17.75, 21.0, 1.25, brass)                        # ... and its nut
    pump.box((-2.9, 15.0, -0.4), (-2.0, 15.6, 0.4), brass)              # the oil cup's arm
    pump.tube("y", (-3.1, 0.0), 15.0, 17.0, 0.75, brass, sides=4)       # ... and the cup
    pump.box((-0.4, 3.0, -3.4), (0.4, 3.8, -2.0), brass)                # the drain cock
    pump.box((-0.9, 3.8, -3.2), (0.9, 4.2, -2.8), dark)                 # ... and its key

    # A guide of the rod, in pixels about the riser's axis at the guide's own height; +z is down
    # the wind, the rod stands at -ROD_OFF. A clip of two halves bolted round the riser, an arm, an
    # eye the rod runs through; under the clip the band that says what the riser carries: blue,
    # water (plan/fine.md 3).
    g = M.Model(MODEL_WIND_GUIDE)
    g.tube("y", on, -0.75, 0.75, 2.5, dark)                             # the clip
    g.box((-3.5, -0.4, -0.4), (-2.25, 0.4, 0.4), iron)                  # its two bolts
    g.box((2.25, -0.4, -0.4), (3.5, 0.4, 0.4), iron)
    g.box((-0.5, -0.5, -ROD_OFF + 1.5), (0.5, 0.5, -2.25), dark, grain="z")         # the arm
    g.tube("y", (0.0, -ROD_OFF), -1.0, 1.0, 1.75, iron)                 # the eye
    g.tube("y", on, -3.5, -1.5, 1.9, blue)                              # the band
    return {x.name: x for x in (t, v, w, rod, pump, g)}


def models():
    return {**_models(), **_wind_models()}


# --- small helpers --------------------------------------------------------------------------------
def _put(c, o, x, y, z, state, keep=False):
    c.set(o[0] + x, o[1] + y, o[2] + z, state, keep=keep)


def _fill(c, o, x0, y0, z0, x1, y1, z1, state, keep=False):
    for x in range(min(x0, x1), max(x0, x1) + 1):
        for y in range(min(y0, y1), max(y0, y1) + 1):
            for z in range(min(z0, z1), max(z0, z1) + 1):
                c.set(o[0] + x, o[1] + y, o[2] + z, state, keep=keep)


def _place(c, o, kind, pos, facing):
    """Stand one of the props line's instruments on its spot (props/instruments.place, the card
    plan/packages/props/instruments.md). Returns the number of display entities: 0 while that
    package or that piece is not in the tree, or with INSTRUMENTS off. A package that is in the
    tree and does not load is an error and is not passed over."""
    if not INSTRUMENTS:
        return 0
    name = __package__.rpartition(".")[0] + ".props.instruments"       # scenes.obs.props.instruments
    if importlib.util.find_spec(name) is None:
        return 0
    instruments = importlib.import_module(name)
    if kind not in getattr(instruments, "SPEC", {}):
        return 0
    return int(instruments.place(c, kind, pos, facing=facing, origin=o) or 0)


_FACING = {(0, -1): "north", (0, 1): "south", (-1, 0): "west", (1, 0): "east"}


def _plate(c, o, number, pos, facing):
    """Hang a machine's number plate (props/nameplates.plate, a6's piece: an oval brass plate with
    the emblem and No. and two digits, plan/fine.md 4) with its middle at `pos`, on the face that
    looks to `facing`. Returns the number of display entities: 0 while that module is not in the
    tree. A module that is in the tree and does not load is an error and is not passed over."""
    name = __package__.rpartition(".")[0] + ".props.nameplates"        # scenes.obs.props.nameplates
    if importlib.util.find_spec(name) is None:
        return 0
    nameplates = importlib.import_module(name)
    return int(nameplates.plate(c, number, pos, facing=facing, origin=o) or 0)


def _ring(x0, z0, x1, z1):
    """The perimeter cells of a rectangle, each once."""
    cells = []
    for x in range(x0, x1 + 1):
        cells.append((x, z0))
        if z1 != z0:
            cells.append((x, z1))
    for z in range(z0 + 1, z1):
        cells.append((x0, z))
        if x1 != x0:
            cells.append((x1, z))
    return cells


def _round(cx, cz, r):
    """The cells of a round plan 2r + 1 across: a square with its corners cut off (r 3: an octagon
    with sides of three cells; r 0: the one cell in the middle)."""
    return [(x, z) for x in range(cx - r, cx + r + 1) for z in range(cz - r, cz + r + 1)
            if abs(x - cx) + abs(z - cz) <= r + 1]


def _flight(c, o, rows, drop, facing):
    """A way down over `rows` (each the cells across the way, the first row next to the terrace):
    `drop` stair blocks spread evenly along it, level steps between them. The first stair lies in
    the terrace's paving course. Every step brings two blocks of footing (into air only) and clears
    its own headroom, so the way holds whatever the slope under it is."""
    n = len(rows)
    at = {int(round(i * (n - 1) / float(max(1, drop - 1)))) for i in range(drop)}
    y = S.PAVING_Y
    for i, row in enumerate(rows):
        for x, z in row:
            _put(c, o, x, y, z, STEP + f"[facing={facing},half=bottom]" if i in at else PLINTH)
            for d in (1, 2):
                _put(c, o, x, y - d, z, PLINTH, keep=True)
            for d in (1, 2, 3):
                c.clear(o[0] + x, o[1] + y + d, o[2] + z)
        if i in at:
            y -= 1


def _ways_down(c, o):
    tx0, tz0, tx1, tz1 = S.UPPER_TERRACE
    lz0 = S.SOUTH_LOOKOUT["box"][1]
    rows = [[(x, z) for x in range(LOOKOUT_WAY[0], LOOKOUT_WAY[1] + 1)] for z in range(tz1 + 1, lz0)]
    _flight(c, o, rows, S.GROUND - S.SOUTH_LOOKOUT["feet"], "north")      # a step, a landing, five times
    wz1 = S.WEATHER_STATION["box"][3]
    rows = [[(x, z) for x in range(WEATHER_WAY[0], WEATHER_WAY[1] + 1)] for z in range(tz0 - 1, wz1, -1)]
    _flight(c, o, rows, S.GROUND - S.WEATHER_STATION["feet"], "south")    # a straight flight of four
    wx1 = S.WATER_TOWER["box"][2]
    rows = [[(x, z) for z in range(TOWER_WAY[0], TOWER_WAY[1] + 1)] for x in range(tx0 - 1, wx1, -1)]
    _flight(c, o, rows, S.GROUND - S.WATER_TOWER["feet"], "east")         # two steps


# --- the meridian hut (skeleton MERIDIAN_HUT) -----------------------------------------------------
def _meridian_hut(c, o):
    cx, cz = S.MERIDIAN_HUT["centre"]
    h = S.MERIDIAN_HUT["size"] // 2
    x0, x1, z0, z1 = cx - h, cx + h, cz - h, cz + h     # x 31..39, z -34..-26
    dx, dz = S.MERIDIAN_HUT["door"]                     # (35, -26): the south end of the slot
    mx = S.MERIDIAN_X                                   # 35
    floor, on = S.PAVING_Y, S.GROUND                    # -1 the paving block, 0 the standing level
    eave = on + 3                                       # the roof course: a plinth and two courses under it

    # the floor: the terrace's own stones, the meridian's column in the middle tone, the brass on it
    for x in range(x0 + 1, x1):
        for z in range(z0 + 1, z1):
            _put(c, o, x, floor, z, K.STRIP if abs(x - mx) <= 1 else K.FIELD)
    _put(c, o, dx, floor, dz, K.STRIP)
    for z in range(z0 + 1, dz + 1):
        _put(c, o, mx, on, z, BRASS)

    # the walls: a slate plinth and two courses of tuff brick; the slot stands on the plinth in
    # the north gable and comes down to the floor in the south one
    for x, z in _ring(x0, z0, x1, z1):
        if (x, z) == (dx, dz):
            continue
        _put(c, o, x, on, z, PLINTH)
        if x != mx:
            _put(c, o, x, on + 1, z, WALL)
            _put(c, o, x, on + 2, z, WALL)
    for wx in (x0, x1):                                 # two small dark windows in each long wall
        for wz in (cz - 2, cz + 2):
            _put(c, o, wx, on + 2, wz, B.WINDOW_DARK.pane)

    # The roof, of old copper in sheets (slate was a black bar before the lit front in V1; the copper
    # is the main cornice's gutter come down to a small roof): a course on each long wall and a flat
    # a half block over it. The two iron shutters lie slid open on the flat either side of the slot.
    # The gables are of stone to the roof's own line; the slot's jambs are dressed, three stones
    # under a coping stone, a little over the roof. (The head of a jamb was the emblem block; the
    # emblem is cut in the pale stone only, and no pale stone is left on the hut.)
    # The hut stands before the base storey in V1 and check.py's sight counts how much of that is
    # out of sight (the posts of the east edge take a third, half is the limit). From the eye, a top
    # edge at height h and x hides the front up to -2.38 + (h + 2.38) * 72.5 / (88.5 - x): the eaves
    # (3.5 at x 40) to y 6.4, the flat (4.0 at x 39) to 7.0, the east shutter (4.19 at x 37) to 6.9.
    # So the top course of the base storey (the samples at y 7.25 and 7.75) shows over the roof, and
    # a kerb or a ridge half a block higher would take it away: the roof stays as flat as this.
    lines = {4: "bottom", 3: "top", 2: "top", 1: "top"}
    for z in range(z0, z1 + 1):
        gable = z in (z0, z1)
        for x in range(x0, x1 + 1):
            d = abs(x - mx)
            if d == 0:
                continue
            if gable and d == 1:                        # a jamb: three dressed stones and a coping
                _put(c, o, x, on + 1, z, JAMB)
                _put(c, o, x, on + 2, z, JAMB)
                _put(c, o, x, eave, z, JAMB)
                _put(c, o, x, eave + 1, z, JAMB_COPE + "[type=bottom]")
            elif gable:
                _put(c, o, x, eave, z, RAKE + "[type=bottom]" if lines[d] == "bottom" else WALL)
            else:
                _put(c, o, x, eave, z, COPPER_SLAB + f"[type={lines[d]}]")
                if d == 1:
                    _put(c, o, x, eave + 1, z, HATCH + f"[facing={'east' if x < mx else 'west'},half=bottom,open=false]")


# --- the water tower (S.WATER_TOWER, north-west shoulder) -----------------------------------------
def _water_tower(c, o):
    x0, z0, x1, z1 = S.WATER_TOWER["box"]               # -21,-35,-13,-27
    foot = S.WATER_TOWER["feet"]                        # -2, where the legs stand
    cx, cz = (x0 + x1) // 2, (z0 + z1) // 2             # -17, -31
    legs = [(cx + sx * 2, cz + sz * 2) for sx in (-1, 1) for sz in (-1, 1)]
    deck_y = foot + 8                                   # 6
    tank_lo, tank_hi = deck_y + 1, deck_y + 4           # 7..10; the cone ends at 13, the rod at 14

    # until the terrain card's shelf is merged the shelf is a flat slab laid only where there is
    # nothing yet; the site's rail on the three sides over the drop, the uphill (east) side open
    _fill(c, o, x0, foot - 1, z0, x1, foot - 1, z1, FOOTING, keep=True)
    _fill(c, o, x0, foot - 2, z0, x1, foot - 3, z1, PLINTH, keep=True)
    edge = [(x, z) for x, z in _ring(x0, z0, x1, z1) if not (x == x1 and z0 < z < z1)]
    piers = {(x, bz) for bz in (z0, z1) for x in K.spaced([x0, x1])} | {(x0, z) for z in K.spaced([z0, z1])}
    K.rail(c, o, edge, piers, y=foot, kerb=True)

    # four riveted legs, each on a slate pad; one thin girt half-way up; a knee brace under the deck
    # either side of every leg
    for lx, lz in legs:
        _put(c, o, lx, foot - 1, lz, PLINTH)
        _put(c, o, lx, foot - 2, lz, PLINTH, keep=True)
        _put(c, o, lx, foot, lz, PLINTH)
        _fill(c, o, lx, foot + 1, lz, lx, deck_y - 1, lz, IRON)
        tx, tz = (1 if lx < cx else -1), (1 if lz < cz else -1)
        _put(c, o, lx + tx, deck_y - 1, lz, IRON_STAIR + f"[facing={'west' if tx > 0 else 'east'},half=top]")
        _put(c, o, lx, deck_y - 1, lz + tz, IRON_STAIR + f"[facing={'north' if tz > 0 else 'south'},half=top]")
    for x, z in _ring(cx - 2, cz - 2, cx + 2, cz + 2):
        if (x, z) not in legs:
            _put(c, o, x, foot + 4, z, IRON_SLAB + "[type=top]")

    # the deck: a riveted floor on the legs' heads, and round it a thin gallery with an iron rail,
    # its four corners cut off like the tank's
    for x in range(cx - 3, cx + 4):
        for z in range(cz - 3, cz + 4):
            if max(abs(x - cx), abs(z - cz)) < 3:
                _put(c, o, x, deck_y, z, IRON)
            elif abs(x - cx) != abs(z - cz):
                _put(c, o, x, deck_y, z, IRON_SLAB + "[type=top]")
                _put(c, o, x, deck_y + 1, z, BARS)

    # The tank: a round riveted drum five across and four high, a riveted band at its foot and at
    # its head, plain plate between. Its cap is a cone of old copper, two rings of steps and a rod
    # on the point.
    for y in range(tank_lo, tank_hi + 1):
        for x, z in _round(cx, cz, 2):
            _put(c, o, x, y, z, IRON if y in (tank_lo, tank_hi) else PLATE)
    for r in (2, 1):
        y = tank_hi + 3 - r
        for x, z in _round(cx, cz, r):
            ddx, ddz = x - cx, z - cz
            if max(abs(ddx), abs(ddz)) < r:
                _put(c, o, x, y, z, COPPER)             # the filling under the next ring, the point
            else:                                       # a step that rises towards the middle
                facing = ("south" if ddz < 0 else "north") if abs(ddz) == r else ("east" if ddx < 0 else "west")
                _put(c, o, x, y, z, COPPER_STAIR + f"[facing={facing},half=bottom]")

    # the riser from its valve box on the ground (a pair of gauges on the side the steps arrive at)
    # up into the tank, and a ladder up the north-east leg, where the way down from the terrace
    # arrives, to a hatch in the gallery
    _put(c, o, cx, foot, cz, GAUGES + "[facing=east]")
    for y in range(foot + 1, deck_y):
        _put(c, o, cx, y, cz, PIPE + "[axis=y]")
    lx, lz = cx + 2, cz - 2
    for y in range(foot, deck_y):
        _put(c, o, lx + 1, y, lz, BARS)
    _put(c, o, lx + 1, deck_y, lz, HATCH + "[facing=west,half=top,open=true]")

    # The wind engine on the cone's point, where a finial rod stood (see _wind_models): the mast,
    # the head with its tail down the wind, the wheel before it, turning. Under the deck the pump
    # on the valve box and the rod that works in it, once up and down to a turn of the wheel: the
    # rod stands beside the riser, in the riser's own cell, held to it by a guide every two blocks,
    # and ends in the deck. What stands over the tank is seen from across the site and keeps the
    # far band: three pieces, the mast with the head, the tail, the wheel. What is under the deck
    # is small detail, a pixel or two from beyond the shelf, and has the near one.
    kit = _wind_models()
    yaw = math.degrees(math.atan2(-_WIND[0], _WIND[1]))                 # a model's +z goes down the wind
    ax, az = _TANK_AXIS
    c.add_entity(o[0] + ax, o[1] + _TANK_POINT, o[2] + az, M.display(kit[MODEL_WIND_MAST], view=M.FAR))
    c.add_entity(o[0] + ax + _WIND[0] * TAIL_HINGE / 16.0, o[1] + WIND_WHEEL[1], o[2] + az + _WIND[1] * TAIL_HINGE / 16.0,
                 M.display(kit[MODEL_WIND_TAIL], yaw=yaw, view=M.FAR))
    MK.swing(c, "y", *TAIL_HUNT)
    c.add_entity(o[0] + WIND_WHEEL[0], o[1] + WIND_WHEEL[1], o[2] + WIND_WHEEL[2],
                 M.display(kit[MODEL_WIND_WHEEL], yaw=yaw, scale=2.0, view=M.FAR))
    MK.spin(c, "z", WHEEL_REV)
    rx, rz = ax - _WIND[0] * ROD_OFF / 16.0, az - _WIND[1] * ROD_OFF / 16.0
    c.add_entity(o[0] + rx, o[1] + foot + 1.0, o[2] + rz, M.display(kit[MODEL_WIND_PUMP], yaw=yaw, view=M.NEAR))
    c.add_entity(o[0] + rx, o[1] + foot + 2.0, o[2] + rz, M.display(kit[MODEL_WIND_ROD], scale=2.0, view=M.NEAR))
    half = WHEEL_REV // 2
    MK.slide(c, "y", [(0, ROD_STROKE / 16.0, half), (half, 0.0, half)], WHEEL_REV)
    for up in ROD_GUIDES:
        c.add_entity(o[0] + ax, o[1] + foot + up, o[2] + az, M.display(kit[MODEL_WIND_GUIDE], yaw=yaw, view=M.NEAR))
    # the machine's number plate on the pump's chest, on the face the wind comes to: the side one
    # walks round to from the steps (the gauges are on the east face)
    wx, wz = (cx + 0.5, cz + 0.5)
    face = (wx - _WIND[0] * 0.5, foot + 0.5, wz - _WIND[1] * 0.5)
    n = _plate(c, o, WIND_NUMBER, face, _FACING[(-round(_WIND[0]), -round(_WIND[1]))])
    return 5 + len(ROD_GUIDES) + n


# --- the weather station (S.WEATHER_STATION, north slope) -----------------------------------------
def _weather_station(c, o):
    x0, z0, x1, z1 = S.WEATHER_STATION["box"]           # -2,-49,8,-43
    foot = S.WEATHER_STATION["feet"]                    # -4
    pave = foot - 1                                     # -5, the paving block

    # a small paved platform footed a little into the slope, a landing in the middle stone where the
    # steps arrive; the site's rail on the three sides over the drop (a fenced instrument enclosure),
    # the uphill (south) side open
    _fill(c, o, x0, pave, z0, x1, pave, z1, FOOTING)
    _fill(c, o, WEATHER_WAY[0], pave, z1 - 1, WEATHER_WAY[1], pave, z1, K.STRIP)
    _fill(c, o, x0, pave - 1, z0, x1, pave - 3, z1, PLINTH, keep=True)
    edge = [(x, z) for x, z in _ring(x0, z0, x1, z1) if not (z == z1 and x0 < x < x1)]
    piers = {(x, z0) for x in K.spaced([x0, x1])} | {(bx, z) for bx in (x0, x1) for z in K.spaced([z0, z1])}
    K.rail(c, o, edge, piers, y=foot, kerb=True)

    # the thermometer screen (a Stevenson screen): the props line's white louvred box on its four
    # legs, the door to the north, as a screen's door is hung. Until that piece is in the tree a
    # shelter of blocks stands in for it on the same spot: a box of pale boards two cells long on
    # an iron trestle, under a lid of the same boards
    n = _place(c, o, "louvre_box", SCREEN, "north")
    if not n:
        sx, sz = _SPOTS["screen"]                       # (0, -46) and the cell east of it
        for x in (sx, sx + 1):
            _put(c, o, x, foot, sz, BARS)
            _put(c, o, x, foot + 1, sz, BOARD)
            _put(c, o, x, foot + 2, sz, BOARD_SLAB + "[type=bottom]")

    # the wind mast: a thin rod eight blocks up, stepped in a slate post; its head, the vane and the
    # cup wheel are this card's models (see _models). The one arm is to the west and under the top:
    # an upright with an arm across it reads as a cross from afar, which the project does not allow.
    wx, wz = _SPOTS["mast"]                             # (6, -47)
    _put(c, o, wx, foot, wz, POST)
    for y in range(foot + 1, foot + 1 + MAST_RODS):
        _put(c, o, wx, y, wz, ROD + "[facing=up]")
    kit = _models()
    c.add_entity(o[0] + MAST_HEAD[0], o[1] + MAST_HEAD[1], o[2] + MAST_HEAD[2], M.display(kit[MODEL_HEAD]))
    c.add_entity(o[0] + CUPS_AT[0], o[1] + CUPS_AT[1], o[2] + CUPS_AT[2], M.display(kit[MODEL_CUPS]))
    MK.spin(c, "y", MK.ANEMOMETER_REV)                  # the cups go round in the wind

    # the rain gauge, a copper can on the floor (this card's model too), and a stone pedestal for
    # the sunshine recorder
    c.add_entity(o[0] + GAUGE[0], o[1] + GAUGE[1], o[2] + GAUGE[2], M.display(kit[MODEL_GAUGE], view=M.MID))
    n += 3
    px, pz = _SPOTS["pedestal"]                         # (3, -47)
    _put(c, o, px, foot, pz, POST)
    _put(c, o, px, foot + 1, pz, COPE + "[type=bottom]")
    # the props line's sunshine recorder on the pedestal, its glass ball to the south (c199 #34880)
    n += _place(c, o, "sunshine_recorder", PEDESTAL_TOP, "south")
    return n


# --- the south lookout (S.SOUTH_LOOKOUT, south ridge; V11) ----------------------------------------
def _south_lookout(c, o):
    x0, z0, x1, z1 = S.SOUTH_LOOKOUT["box"]             # 40,48,50,56
    foot = S.SOUTH_LOOKOUT["feet"]                      # -5, where a person stands (V11)
    pave = foot - 1                                     # -6, the floor block
    cut = 3                                             # the two south corners are cut off: a prow
    cells = [(x, z) for x in range(x0, x1 + 1) for z in range(z0, z1 + 1)
             if min(x - x0, x1 - x) + (z1 - z) >= cut]
    wx0, wx1 = LOOKOUT_WAY
    tx, tz = _scope_cell()                              # (45, 54): the telescope stand, in the prow

    # the floor: dark slate, a walk in the middle stone from the steps to a round stand in the prow,
    # where a ring of the court's thin brass line is let in round the tripod telescope's place: two
    # blocks across, through the middles of the eight cells about it; a footing into the slope
    for x, z in cells:
        walk = wx0 <= x <= wx1 and z < tz
        stand = abs(x - tx) + abs(z - tz) <= 2
        _put(c, o, x, pave, z, K.STRIP if walk or stand else FOOTING)
        for d in (1, 2, 3):
            _put(c, o, x, pave - d, z, PLINTH, keep=True)
    if BRASS_RING:
        # every cell takes the shape that joins its two neighbours in the ring (see B.BRASS_LINE)
        turn = {(-1, -1): "south_east", (1, -1): "south_west", (-1, 1): "north_east", (1, 1): "north_west"}
        for ddx in (-1, 0, 1):
            for ddz in (-1, 0, 1):
                if (ddx, ddz) != (0, 0):
                    shape = turn.get((ddx, ddz), "east_west" if ddx == 0 else "north_south")
                    _put(c, o, tx + ddx, foot, tz + ddz, BRASS_RING + f"[shape={shape}]")

    # the site's rail round the whole edge (the neck that leads here is three wide, so the north
    # edge hangs free too), open where the steps arrive. Piers at the four knuckles of the prow, and
    # one on the north edge: the rail's end east of the steps' foot, capped like the two at the
    # terrace's gap; the lamps line stands a lamp on it (A4, 11-16 10:30). The end west of the steps
    # stays a rail: V11 looks north-west over the north edge, and a pier there stands in the middle
    # of the picture.
    edge = [p for p in K.outline(cells) if not (p[1] == z0 and wx0 <= p[0] <= wx1)]
    piers = {(x0, z1 - cut), (x1, z1 - cut), (x0 + cut, z1), (x1 - cut, z1), (wx1 + 1, z0)}
    K.rail(c, o, edge, piers, y=foot, kerb=True)
    # That pier's cap is half a block over the high half of the steps' last tread, and the tread
    # ends half a block short of it: whoever came down along the east side was lifted on to the
    # cap, into the lamp, and could walk on round the terrace on top of the rail (walk-out, A7).
    # One barrier in the cell north of the cap, beside the tread and at the lamp's foot, a block
    # over the tread: on to the cap takes a jump again, as on to any rail. Nothing seen is changed
    # (A0 #84088); the pier, its cap and the lamp's cell over it stay as the lamps line found them
    _put(c, o, wx1 + 1, foot + 1, z0 - 1, B.BARRIER)

    # the props line's tripod telescope on the stand, turned to the cloud sea. V11 is taken two
    # blocks north of it, looking north-west: the telescope is behind that picture's back
    return _place(c, o, "tripod_scope", SCOPE_STAND, "south")


def build(canvas, origin=(0, 0, 0)):
    """Places the four shells and the ways down; returns the number of display entities: this
    card's three on the weather platform (mast head, cup wheel, rain gauge), the wind engine's on
    the water tower (five, a guide of the rod every two blocks, its number plate when the props
    line's nameplates are in the tree), and the props line's three instruments when that package
    is in the tree."""
    _meridian_hut(canvas, origin)
    n = _water_tower(canvas, origin)
    n += _weather_station(canvas, origin)
    n += _south_lookout(canvas, origin)
    _ways_down(canvas, origin)
    return n
