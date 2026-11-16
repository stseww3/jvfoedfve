"""machines/train: the train that brings the visitor up the mountain (plan/round2.md, the card
machines/train; the director's ruling on its size, 11-16 12:50). One rack engine pushes one coach:
the coach leads uphill, the engine is at the downhill end. This module is the train's table: the
frame its vehicles are drawn in, the coach's measures, its seats, and where the loose things in
the coach hang. The coach's models are machines/coach, the engine is machines/locomotive (m1), the
loose things in the coach are machines/coachfittings (a3). The line is site/_rail (a4), the
moving is motion/_kit's travel (a2).

The vehicle frame. Every model that rides the rails is drawn in it and every point below is given
in it, in texels (sixteen to a block; PX turns them into blocks):

  origin   on the track's centre line, on the upper face of the rails, at the middle of the
           vehicle's length
  +x       down the line, the way a4 counts the distance s: east when the train stands in the
           station. The coach's door end is at -x (uphill, where the riders look), the engine
           couples on at +x.
  +y       up from the rails
  +z       to the right of one who looks down the line: south in the station. A rider, who looks
           uphill, has +z on his left: the side the mountain is on while the train runs along
           the far straight of the viaduct.

At home (the train standing in the station, the place travel() is told as home=RAIL.STOP) the
coach's origin is the Point RAIL.pose(RAIL.STOP, COACH_BASE); spot() turns a point of the coach's
frame into the scene's coordinates there, and turn() says how M.display stands a model of that
frame on it:

    canvas.add_entity(*T.spot(p), M.display(model, brightness=T.INSIDE, view=M.FAR, **T.turn()))
    coach.carry(canvas)         # the travelling coach, handed to the one who places (travel.md, section 3)

A model whose own origin is the point p it hangs on (a lamp on its hook, a case on its foot) is
drawn with the frame's axes and placed like this; nothing of the train is placed with a yaw of
its own, because the coach does not stand square to the station (the line bends under it).

The coach, 5 blocks long, 3 wide over its eaves and 3 high (all numbers texels in its frame):

  the body      x -40..40, z -22..22 (the eaves reach -24..24), from the frame at y 6 to the
                eaves at 41; the clerestory's top is at 48
  the room      clear between x -37.5 and 37.5, z -19.5 and 19.5, from the floor boards at 9.5 to
                the ceiling at 40.5; under the clerestory (z -11..11) the well goes up to 46.5
  the windows   y 21..36 all round: the whole door end is glass, a glazed door in its middle
                (z -5..5); four big lights a side, one beside each row of seats
  the seats     four benches across, all looking uphill, their tops at 14.5: the backs of the
                rows are at x -18, -2, 14, 30. On the left (+z) a bench for two from z 1.5 to
                19.5, on the right a single seat from -19.5 to -8.5, the aisle between them.
  the racks     a brass rack along either side over the windows: its slats' upper face at 37,
                from the wall (19.5) 5 into the room, x -30..30; what lies on it may be 3 high
  the stand     the luggage stand across the engine end behind the last row: x 31..37, the floor
                at 9.5, things on it up to y 20.5 (the sill of the end windows is at 21). The
                hand brake's column stands in its middle (z -3..3).

Light. A display entity takes the light of the place it stands on, and the train runs through the
cloud, where that place is inside a block and dark: every piece of the train says its own
brightness. OUTSIDE is for what is seen from without, INSIDE for what stands in the lit room.
"""
import math

from ..site import _rail as RAIL

PX = 1.0 / 16.0                         # one texel, in blocks

# --- the consist ----------------------------------------------------------------------------------------
NAME = "train"                          # travel's name of it: its functions are <ns>:<scene>-motion/train/...
COACH_HALF = 40.0                       # half the coach's length
COACH_BASE = 3.5                        # blocks from bogie to bogie: travel's axles=(-1.75, 1.75)
COACH_BOGIES = (-28.0, 28.0)            # the bogies' middles
COACH_AXLES = (-34.0, -22.0, 22.0, 34.0)        # the four wheelsets: 6 either side of a bogie's middle
COACH_WHEEL = 4.0                       # a coach wheel's radius over the tyre
ENGINE_AT = 4.25                        # blocks from the coach's middle down the line to the engine's
ENGINE_BASE = 2.0                       # blocks between the engine's two axles, until machines/locomotive says its own
COUPLING = (COACH_HALF, 10.0, 0.0)      # the middle of the coach's buffer face at the engine end

OUTSIDE = (15, 7)                       # brightness (sky, block) of what is seen from without
INSIDE = (15, 12)                       # ... of what stands in the lit room

# --- the room ---------------------------------------------------------------------------------------------
FLOOR, CEILING, WELL = 9.5, 40.5, 46.5
ROOM = dict(x=(-37.5, 37.5), y=(FLOOR, CEILING), z=(-19.5, 19.5), well=dict(z=(-11.0, 11.0), y=WELL))
SILL, HEAD = 21.0, 36.0                 # the windows, all round
BENCH_TOP = 14.5
ROWS = (-22.0, -6.0, 10.0, 26.0)        # the middle of each row's seat; its back is 4 behind (+x)
ACROSS = (15.0, -14.0, 6.0)             # a row's seats in the order they are taken: left window, right, left aisle
# The seats, in the order the riders take them: from the front row back (the director: whoever
# comes first sits in front). A seat is the point a rider sits on, on the bench's top; his eye is
# 1.02 blocks over it.
SEATS = [(x, BENCH_TOP, z) for x in ROWS for z in ACROSS]

# --- where the loose things hang (machines/coachfittings) -------------------------------------------------
# Two lamps hang in the clerestory's well, over the aisle side of the benches: the hook, on the
# well's ceiling. A lamp hangs no lower than LAMP_LOW (heads pass under it) and is no wider than 6.
LAMP_HOOKS = [(-14.0, WELL, 0.0), (18.0, WELL, 0.0)]
LAMP_LOW = 38.5
# The racks: the upper face of the slats, and the box a thing on them stays in (x, y, z ranges).
RACK_TOP = 37.0
RACKS = {
    "left": dict(x=(-30.0, 30.0), y=(RACK_TOP, CEILING - 0.25), z=(14.5, 19.5)),
    "right": dict(x=(-30.0, 30.0), y=(RACK_TOP, CEILING - 0.25), z=(-19.5, -14.5)),
}
# The stand behind the last row, either side of the hand brake: trunks and instrument cases.
STAND = {
    "left": dict(x=(31.0, 37.0), y=(FLOOR, SILL - 0.5), z=(4.0, 19.0)),
    "right": dict(x=(31.0, 37.0), y=(FLOOR, SILL - 0.5), z=(-19.0, -4.0)),
}
# The timetable: on the solid panel beside the door, right of one who comes in (the wall's face
# is z -19.5 and looks into the room, +z). The middle of the sheet, and the most it may measure
# along the wall, in height, and off the wall.
TIMETABLE = dict(point=(-34.5, 29.0, -19.5), facing="+z", most=(6.0, 10.0, 0.75))
# The enamel number plate on the door's lower panel, outside (the face is x -40 and looks up the
# line, -x): seen from the platform by who turns round at the spawn. Middle and most (across, high, off).
DOOR_PLATE = dict(point=(-40.0, 15.0, 0.0), facing="-x", most=(6.0, 4.0, 0.5))
COACH_NO = 2                            # the engine is No. 1 (the director); the numbers' table is a6's


def home():
    """The coach's origin when the train stands in the station: a Point of the line (x, y, z, the
    heading hx, hz in plan, the slope)."""
    return RAIL.pose(RAIL.STOP, COACH_BASE)


def spot(p, at=None):
    """(x, y, z) in the scene of the point p of a vehicle's frame (texels), the vehicle's origin
    being the Point `at` (the coach at home when it is not given). The frame is tilted with the
    line: its +x is the Point's heading with its slope, its +y square to that."""
    o = at or home()
    run = (1.0 + o.slope * o.slope) ** 0.5
    ax, ay, az = o.hx / run, o.slope / run, o.hz / run              # +x of the frame
    ux, uy, uz = -o.slope * o.hx / run, 1.0 / run, -o.slope * o.hz / run        # +y
    rx, rz = -o.hz, o.hx                                            # +z: level, to the right
    x, y, z = (v * PX for v in p)
    return (o.x + ax * x + ux * y + rx * z, o.y + ay * x + uy * y, o.z + az * x + uz * y + rz * z)


def turn(at=None):
    """How M.display stands a model drawn in the vehicle frame on the Point `at` (the coach at home
    when it is not given): dict(yaw=, turns=), the model tipped to the line's slope about its own
    z and then turned to the line's heading."""
    o = at or home()
    tip = math.degrees(math.atan(o.slope))
    return dict(yaw=math.degrees(math.atan2(o.hz, o.hx)), turns=(("z", tip),) if abs(tip) > 1e-9 else ())


def seats():
    """The seats in the scene, the train at home: what travel's seat() is given."""
    return [spot(p) for p in SEATS]
