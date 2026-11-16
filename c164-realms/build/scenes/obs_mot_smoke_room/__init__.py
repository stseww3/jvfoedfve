"""Second test scene of the work package motion/smoke: what breathes inside the power house.

The machines stand where they do in the master scene, in the shell of the power house as
site/powerhouse builds it: the two boilers and the switchboard (machines/boiler, machines/board)
and the engine with its dynamo (machines/engine). So motion/smoke finds each machine on the canvas
and registers its puffs exactly as it does in the master scene; the chimney is the real one too.
Round the shell there is a slab of the lower platform and nothing else; the floor is a stand-in
for the room's, and the light is the machines' own (the fire doors, the board's lamps, the pilot
lamp), placed by the sky line.

Particles are not drawn offline: the offline pictures show the machines at rest, and what they
breathe is for the real machine to say. Every camera is in the shot list twice, the second time
as <name>_again. The game must not be frozen while the pictures are taken. The safety valve blows
for a second and a half of every eight (smoke.VALVE) and its steam is gone two to three seconds
later: of a pair of pictures taken seven seconds apart one may well show nothing, which is why
two cameras look at the valve.

The cameras
    room        a step inside the wicket: does the steam show to somebody who comes in
    valve       from the firing floor, before boiler No. 2: up at its safety valve
    valve_side  a little over the valve, from the west and nearly square to the wind: the wisps
                lean right
    fire        the firing floor, north-west of No. 2's fire door: into the gap of the leaf that
                stands ajar, where the sparks come out
    flange      the engine's steam flange from the north-west, a little over it: the leak
    brushes     the dynamo's commutator from the east, square to it: the two brushes
    switch      the knife switch that stands open, from the east

The sparks live half a second to two and there are seven in eight seconds; a flash at a brush or
at the switch lives a tenth of a second and there are eight in eight seconds: a single picture
seldom has one. Whoever takes the pictures on the real machine takes a handful of each.

    python -m scenes.obs_mot_smoke_room      (in build/) writes shots.json
"""
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.machines import board, boiler, engine
from scenes.obs.motion import smoke
from scenes.obs.site import powerhouse

BIOME = "obs_blue"
BIOME_MARGIN = 24
BIOME_MARGIN_Y = 24

X0, Z0, X1, Z1 = S.POWER_HOUSE["box"]
SLAB = (X0 - 6, Z0 - 6, X1 + 3, Z1 + 3)         # the piece of the lower platform the house stands on
PAVING_Y = S.LOWER_PAVING_Y                     # -7
FLOOR = B.TUFF_SMOOTH.block                     # stands in for the room's floor and the yard's paving
ROCK = B.TUFF.block                             # under it: what the engine's pit is dug into
FY = boiler.FLOOR
EYE = S.EYE
TIME = 14000


def _views():
    vx, vy, vz = boiler.SAFETY_VALVES[-1]
    dx, dy, dz = boiler.FIRE_DOORS[-1]
    fx, fy, fz = engine.STEAM_IN
    bx, by, bz = engine.SHAFT_X + engine.DYN_X, FY + engine.DYN_H, engine.LINE_Z + sum(engine.COMM) / 2.0
    sx, sy, sz = board.OPEN_SWITCH
    return [
        ("room", (74.5, FY + EYE, 23.2), (77.5, FY + 1.4, 36.5)),
        ("valve", (vx - 3.55, FY + EYE, vz + 2.1), (vx, vy + 0.6, vz + 0.1)),
        # south of the boiler's axis: on the axis the pressure gauge stands before the valve
        ("valve_side", (vx - 2.85, vy + 0.9, vz + 1.6), (vx, vy + 0.7, vz + 0.15)),
        ("fire", (dx - 1.85, FY + EYE, dz - 1.6), (dx - 0.05, dy + 0.2, dz - 0.2)),
        # over the cylinder: from the floor its top hides all of the flange but the rim
        ("flange", (fx - 1.6, fy + 0.6, fz - 2.4), (fx, fy + 0.15, fz - 0.05)),
        # square to the commutator, clear of the bearing south of it
        ("brushes", (bx + 1.9, FY + EYE, bz + 0.5), (bx, by, bz)),
        ("switch", (sx + 1.95, sy - 0.6, sz + 0.95), (sx, sy, sz)),
    ]


def shots():
    out = []
    for again in ("", "_again"):
        for name, pos, look_at in _views():
            out.append({"name": name + again, "pos": [round(float(v), 2) for v in pos],
                        "look_at": [round(float(v), 2) for v in look_at], "time": TIME})
    return out


def build():
    c = Canvas()
    c.box(SLAB[0], PAVING_Y - 3, SLAB[1], SLAB[2], PAVING_Y - 1, SLAB[3], ROCK)
    c.box(SLAB[0], PAVING_Y, SLAB[1], SLAB[2], PAVING_Y, SLAB[3], FLOOR)
    shell = powerhouse.build(c, (0, 0, 0))          # its own entities: the lamp over the wicket
    n = boiler.build(c, (0, 0, 0)) + board.build(c, (0, 0, 0)) + engine.build(c, (0, 0, 0))
    smoke.build(c, (0, 0, 0))
    c.entity_counts = {"machines": n, "site": int(shell or 0), "motion": 0}
    sky.build(c, (0, 0, 0))                         # the sky line's light sources go in last
    return c


def build_models():
    out = dict(boiler.models())
    out.update(board.models())
    out.update(engine.models())
    try:
        from scenes.obs.props import lamps          # the shell hangs the props line's lamp over its wicket
    except ImportError:
        lamps = None
    if lamps is not None:
        out.update(lamps.models() or {})
    return out


def write_pack(pack_dir):
    """The repainted tuff, iron, glass and panels of the house the machines stand in, and the sky's sun."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])
