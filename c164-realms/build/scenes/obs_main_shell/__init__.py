"""Test scene of the work package main/shell (plan/packages/main/shell.md).

The main line built whole (walls, drum and dome, the shell inside them) seven times over:

  at z 0      as it stands, with a few invisible lights inside so the rooms can be seen (they are
              this scene's only: the rooms get their lamps and their light from the interiors and
              the light line);
  at z 100    cut off above y 4, under the heads of the arches: the ground floor from above -- the
              hall, the west arcade as its piers and three openings, the two flights, the way to
              the west door, the foot of the pier;
  at z 200    cut off above y 13: the main floor -- galleries, mezzanine, the well, the wing rooms,
              the first turn of the ring stair;
  at z 300    cut off above y 19: the dome-room floor, the opening round the pier, the stair's top;
  at z 400    whole and lit like the first, with plain blocks standing in for what other lines
              bring: the two things the hall is the background of, the orrery hung from the
              ceiling and the mother clock on the pier, and the lamp the light line stands on each
              post of the ring stair. The board's view of the star hall (V7, from outside the door)
              is taken here, and the two views of the stair's mouths (stair_foot, stair_top);
  at z 500    cut off east of x 2, between the pier and the arcade: the cross section, looking
              west -- the three arches side by side as no one standing in the hall sees them (the
              pier stands before the middle one), a flight in each of the outer two, the cross
              gallery on them, the ring stair's west run hung over it, the galleries and the
              wing rooms cut through;
  at z 600    cut off south of z 1: the long section, looking north -- entrance, hall, pier and
              the stair winding up round it, arcade, the way to the west door under the
              mezzanine, the apse, and the dome room on top.

Each cut keeps the lights of what it shows, so the plans and sections read by the same light as
the rooms and not by the sky's alone. A slab of paving lies under each so the cuts do not look
into the void. The facade's stand-in behind the entrance (a pale wall across the hall, until the
hall is fitted out) is left out: the scene shows the hall as it is without it.
"""
from artkit import arch
from artkit.canvas import Canvas

from scenes.obs import main, materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.main import shell

BIOME = "obs_blue"
BIOME_MARGIN = 60
CUTS = {"ground": (100, 4), "main": (200, 13), "dome": (300, 19)}       # name: (z of the copy, last row kept)
DRESSED = 400                                                           # z of the copy with the stand-ins
SECTIONS = {"cross": (500, 0, 2), "long": (600, 2, 1)}                  # name: (z of the copy, axis cut across (0 x, 2 z),
#                                                                         last column kept): east of x 2 and south of z 1 are gone
GROUND = (S.WALL_W - 14, S.Z_NORTH - 6, S.WALL_E + 24, S.Z_SOUTH + 6)  # x -14..39, z -40..40: the view through
#                                                                         the door stands on it, 19 before the wall
LIGHTS = [
    (9, 4, -3), (9, 4, 3), (13, 4, 0), (10, 11, 0), (13, 10, -3), (13, 10, 3),      # the hall
    (-3, 3, 0), (-4, 10, 0), (-3, 10, -4), (-3, 10, 4), (-1, 9, 0),                 # the stair hall
    (7, 10, -11), (7, 10, -20), (7, 10, 11), (7, 10, 20),                           # the wing rooms
    (11, 20, 5), (11, 20, -5), (-3, 20, 5), (-3, 20, -5), (6, 15, 2),               # the dome room, the stair's shaft
]
LIGHT_LEVEL = 14                                                        # the light line's top level; never 15
FLIGHT_LIGHTS = [(1, 4, -4), (1, 4, 4)]                                 # under the head of each side arch, where the star hall
FLIGHT_LIGHT_LEVEL = 11                                                 # hangs a lamp at the foot of each flight: dimmer than the hall
LIGHT_OVER_CUT = 2                                                      # a cut keeps the lights up to this far beyond its last row or column
CLOCK_HIGH = 4                                                          # the mother clock on its plinth (A0, 11-15)


def stand_ins(c, dz):
    """Plain blocks for what the hall is the background of, after the star hall's own stand-ins
    (interiors/_stubs.py). The orrery (machines/orrery) as its envelope: an orbit five across round
    a pale sun at the ring's height, a rod up to the beam it hangs from. The mother clock
    (machines/clocks): a dark case with its dial, on the star hall's plinth before the pier's east
    face. And what the shell leaves a cell free for: a lantern on each post of the ring stair
    (sky/lights; review 16 looks at the two mouths with their lamps)."""
    cx, cz = S.ORRERY_CENTRE
    x, z, ring_y = int(cx - 0.5), int(cz - 0.5), int(S.ORRERY_RING_Y)
    for ox, oz in arch.outline(cx, cz, S.ORRERY_R):
        c.set(ox, ring_y, oz + dz, B.BRASS_RAIL)
    c.set(x, ring_y, z + dz, B.WINDOW_FROSTED.block)
    for y in range(ring_y + 1, S.STAR_HALL_CEIL):
        c.set(x, y, z + dz, f"{B.IRON_PIPE}[axis=y]")
    x, y0 = int(S.MOTHER_CLOCK["back_x"]), int(S.MOTHER_CLOCK["y"][0])
    for side in (-1, 0, 1):
        c.set(x, S.GROUND, z + side + dz, B.SLATE_BRICK.block)
    for y in range(y0, y0 + CLOCK_HIGH):
        c.set(x, y, z + dz, B.DARK_WOOD.block)
    c.set(x, y0 + CLOCK_HIGH - 2, z + dz, f"{B.PANELS['dial']}[facing=east]")
    for x, y, z in shell.stair_posts():
        c.set(x, y + 1, z + dz, B.IRON_LANTERN)


def copies():
    """Every copy of the building as (z of the copy, axis, last kept): what lies beyond `last kept`
    along that axis (0 x, 1 y, 2 z) is left out; axis None is the building whole."""
    return ([(0, None, None), (DRESSED, None, None)] + [(dz, 1, top) for dz, top in CUTS.values()]
            + list(SECTIONS.values()))


def build():
    whole = Canvas()
    with shell.hall_open():
        main.build(whole, (0, 0, 0))
    c = Canvas()
    x0, z0, x1, z1 = GROUND
    lights = [(cell, LIGHT_LEVEL) for cell in LIGHTS] + [(cell, FLIGHT_LIGHT_LEVEL) for cell in FLIGHT_LIGHTS]
    for dz, axis, last in copies():
        c.box(x0, S.PAVING_Y, z0 + dz, x1, S.PAVING_Y, z1 + dz, B.SLATE_SMOOTH.block)
        for cell, state in whole.b.items():
            if axis is None or cell[axis] <= last:
                c.set(cell[0], cell[1], cell[2] + dz, state)
    stand_ins(c, DRESSED)
    for dz, axis, last in copies():
        for cell, level in lights:
            if axis is None or cell[axis] <= last + LIGHT_OVER_CUT:
                c.set(cell[0], cell[1], cell[2] + dz, f"{B.LIGHT}[level={level}]", keep=True)
    return c


def build_models():
    return main.models() or {}


def write_pack(pack_dir):
    """The shell paints nothing; it stands on the repainted blocks as the materials line has them,
    under the sky line's sky: the scene takes the map's hour, and without the sky's pictures the
    game's own sun lies on the western horizon in every shot that sees the open sky."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])
