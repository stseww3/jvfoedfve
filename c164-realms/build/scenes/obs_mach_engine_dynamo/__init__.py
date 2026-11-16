"""Test scene of machines/engine-dynamo (plan/packages/machines/engine-dynamo.md): the steam engine,
its flywheel, the belt and the dynamo where they stand in the master scene, in the shell of the
power house as site/powerhouse builds it.

Round the shell there is a slab of the lower platform and nothing else. The room is empty but for
the set: the boilers, the switchboard, the gratings and rails round the pit, the pipes and the
lamps are other packages'. The floor is a stand-in for the room's (interiors/powerhouse), and the
light is a stand-in as well: rows of invisible sources four blocks over the floor on either side
of the engine, so that the models can be judged, and one source over each of the four cells the
set takes its light from (engine.LIT_BY), so that all its pieces are lit alike, as the room is
asked to light them; the room's own lamps and the boilers' fire come with the interior and the
sky line.

The house's glass is painted opaque, so the skeleton's V6, which looks at the house from the grand
stair, sees nothing of the engine; what the yard does see is the slice of the room behind the open
wicket, and `wicket` stands there.

The loop is not run for the pictures: every part stands in its rest pose, the dead centre.

    python -m scenes.obs_mach_engine_dynamo        # writes shots.json from the numbers below
"""
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.machines import engine
from scenes.obs.site import powerhouse

BIOME = "obs_blue"
BIOME_MARGIN = 24
BIOME_MARGIN_Y = 24

X0, Z0, X1, Z1 = S.POWER_HOUSE["box"]
SLAB = (X0 - 6, Z0 - 6, X1 + 3, Z1 + 3)         # the piece of the lower platform the house stands on
PAVING_Y = S.LOWER_PAVING_Y                     # -7
FLOOR = B.TUFF_SMOOTH.block                     # stands in for the room's floor and the yard's paving
ROCK = B.TUFF.block                             # under it: what the pit is dug into
LIGHT_Y = int(engine.FLOOR) + 4                 # over the dynamo's terminals and clear of the flywheel's cell
LIGHTS = ([(x, 32) for x in (71, 74, 77, 80, 83, 86)]
          + [(x, 39) for x in (71, 74, 77, 80, 83, 86)])
OVER = sorted({(x, z) for x, _y, z in engine.LIT_BY})      # a source over each cell the pieces are lit by
LIGHT_LEVEL = 15
TIME = 14000                                    # light version A, the default

EYE = S.EYE


def build():
    c = Canvas()
    c.box(SLAB[0], PAVING_Y - 3, SLAB[1], SLAB[2], PAVING_Y - 1, SLAB[3], ROCK)
    c.box(SLAB[0], PAVING_Y, SLAB[1], SLAB[2], PAVING_Y, SLAB[3], FLOOR)
    shell = powerhouse.build(c, (0, 0, 0))          # its own entities: the lamp over the wicket
    n = engine.build(c, (0, 0, 0))
    for x, z in LIGHTS + OVER:
        c.set(x, LIGHT_Y, z, f"{B.LIGHT}[level={LIGHT_LEVEL}]", keep=True)
    c.entity_counts = {"machines": n, "site": int(shell or 0)}
    return c


def build_models():
    out = dict(engine.models())
    try:
        from scenes.obs.props import lamps          # the shell hangs the props line's lamp over its wicket
    except ImportError:
        lamps = None
    if lamps is not None:
        out.update(lamps.models() or {})
    return out


def write_pack(pack_dir):
    """The repainted tuff, iron and glass of the house the set stands in, and the sky's own sun."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])


def shots():
    """The cameras. Three are the card's: the whole set, the flywheel and the rods close, and what
    is seen of it from outside. The others walk round the set."""
    fy = engine.FLOOR
    sx, lz, wz = engine.SHAFT_X, engine.LINE_Z, engine.WHEEL_Z
    h = fy + engine.H
    dx, dz = sx + engine.DYN_X, lz + engine.DYN_Z
    out = []

    def shot(name, pos, look_at):
        out.append({"name": name, "pos": [round(float(v), 2) for v in pos],
                    "look_at": [round(float(v), 2) for v in look_at], "time": TIME})

    shot("door", (74.5, fy + EYE, 23.2), (sx, h, wz))                       # a step inside the wicket
    shot("whole", (sx + 1.0, fy + 2.6, lz - 8.5), (sx + 1.0, h - 0.2, lz))  # the set in elevation
    shot("flywheel", (sx + 3.6, fy + EYE, lz - 3.6), (sx + 0.3, h, lz + 0.6))
    shot("rods", (sx + 6.6, fy + 2.3, lz - 2.6), (sx + 2.6, h, lz))
    shot("cylinder", (sx + 9.6, fy + EYE, lz - 3.2), (sx + 6.6, h, lz - 0.3))
    shot("dynamo", (dx + 2.2, fy + EYE, wz - 3.4), (dx, fy + engine.DYN_H + 0.5, dz - 0.4))
    shot("belt", (dx - 1.6, fy + EYE, wz - 2.2), (sx - 1.2, h + 0.3, wz))   # along the belt, from the pulley's end
    shot("south", (sx + 2.4, fy + EYE, wz + 3.9), (sx, h, wz))              # the wheel's far side, the outboard bearing
    shot("valve", (sx + 5.4, fy + EYE + 0.4, lz + 4.8), (sx + 6.4, h + 0.4, lz + 0.9))      # chest, governor, eccentric rod
    shot("brushes", (dx + 2.0, fy + EYE, dz + 2.6), (dx, fy + engine.DYN_H + 0.4, dz + 0.4))        # the commutator's end
    shot("above", (sx - 1.0, fy + 7.5, lz - 5.0), (sx - 0.5, fy, lz + 0.8))
    shot("wicket", (73.9, fy + EYE, 18.2), (76.9, h, wz))                   # from the yard, through the open wicket
    return out
