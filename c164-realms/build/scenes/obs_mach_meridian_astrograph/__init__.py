"""Test scene of the work package machines/meridian-astrograph
(plan/packages/machines/meridian-astrograph.md): the transit circle and the astrograph, each in
the room it is made for and once more on a bench.

  the hut     the meridian hut at its place on the court, the transit circle inside. The hut is
              site/outbuildings' own once that package is in the tree: its shells are built on a
              canvas apart and the hut's box is taken over cell for cell. Until then a stand-in is
              laid from the numbers that module gives (its head 69b57fe8: the room clear from wall
              to wall, 3.5 high, a slot one block wide over the meridian from the door in the
              south gable to the north gable). Round it a patch of the court's paving.
  the dome    the small dome as main/smalldome builds it, the astrograph inside, on a stand-in of
              the south pavilion's flat roof: the deck, and of it the terrace west of the dome,
              where one stands before the slit.
  the bench   both instruments again, free on a plain floor before a plain wall, east of the rest
              and drawn at noon: the pieces themselves, with no room in the way.

    python -m scenes.obs_mach_meridian_astrograph      writes shots.json from the numbers below
"""
import importlib
import importlib.util

from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.machines import astro, meridian
from scenes.obs.main import smalldome
from scenes.obs.site import _kit as SK

BIOME = "obs_blue"
CATEGORY = "machines"
BIOME_MARGIN = 32
BIOME_MARGIN_Y = 32
TIME = 14000                                    # look A, the blue hour
DAY = "noon"

HUT_X, HUT_Z = S.MERIDIAN_HUT["centre"]         # (35, -30)
HUT_HALF = S.MERIDIAN_HUT["size"] // 2          # 4: the hut is x 31..39, z -34..-26
HUT_BOX = (HUT_X - HUT_HALF, S.PAVING_Y, HUT_Z - HUT_HALF, HUT_X + HUT_HALF, S.GROUND + 5, HUT_Z + HUT_HALF)
COURT = (HUT_X - 10, HUT_Z - 10, HUT_X + 10, HUT_Z + 18)        # the patch of paving: x 25..45, z -40..-12

DECK_Y = S.ROOF_FLOOR                           # 17: the pavilion's flat roof, the dome room's floor
DECK = (0, S.SMALL_DOME_Z[0] - 2, S.SMALL_DOME_X[1] + 1, S.SMALL_DOME_Z[1] + 2)     # x 0..17, z 24..36

BENCH = (72, 0, -30)                            # the bench: the middle of its floor
BENCH_HALF = (10, 6)                            # half its size along x and z
BENCH_WALL = 6                                  # the wall behind it, on the north side
BENCH_LIGHT = (15, 0)                           # the pieces on the bench are shown in the day's light
MERIDIAN_AT = (BENCH[0] - 5.0, BENCH[2] - 0.5)  # where each instrument's middle stands on the bench (x, z)
ASTRO_AT = (BENCH[0] + 5.0, BENCH[2] + 0.5)


def _outbuildings():
    """site/outbuildings, or None while that package is not in the tree."""
    name = "scenes.obs.site.outbuildings"
    return importlib.import_module(name) if importlib.util.find_spec(name) else None


def _hut_stand_in(c):
    """The hut's shell from the numbers of site/outbuildings: a slate plinth and two courses of
    banded ashlar, two dark windows in each long wall, dressed jambs with the emblem either side of
    the slot, a flat roof of old copper half a block over its eaves course, the two iron shutters
    lying open on it; inside, the court's paving with the meridian's brass in the middle."""
    x0, x1, z0, z1 = HUT_X - HUT_HALF, HUT_X + HUT_HALF, HUT_Z - HUT_HALF, HUT_Z + HUT_HALF
    door_x, door_z = S.MERIDIAN_HUT["door"]
    mx, on, eave = S.MERIDIAN_X, S.GROUND, S.GROUND + 3
    wall, plinth, copper = B.ASHLAR_ROUGH.block, B.SLATE_BRICK.block, B.OLD_COPPER_CUT.slab
    ring = [(x, z) for x in range(x0, x1 + 1) for z in range(z0, z1 + 1) if x in (x0, x1) or z in (z0, z1)]
    for x, z in ring:
        if (x, z) == (door_x, door_z):
            continue
        c.set(x, on, z, plinth)
        if x != mx:
            c.set(x, on + 1, z, wall)
            c.set(x, on + 2, z, wall)
    for x in (x0, x1):
        for z in (HUT_Z - 2, HUT_Z + 2):
            c.set(x, on + 2, z, B.WINDOW_DARK.pane)
    for z in range(z0, z1 + 1):
        gable = z in (z0, z1)
        for x in range(x0, x1 + 1):
            d = abs(x - mx)
            if d == 0:
                continue
            if gable and d == 1:
                c.set(x, on + 1, z, B.ASHLAR_FINE.block)
                c.set(x, on + 2, z, B.ASHLAR_FINE.block)
                c.set(x, eave, z, B.ASHLAR_EMBLEM)
                c.set(x, eave + 1, z, f"{B.ASHLAR_PANEL.slab}[type=bottom]")
            elif gable:
                c.set(x, eave, z, f"{B.ASHLAR_ROUGH.slab}[type=bottom]" if d == HUT_HALF else wall)
            else:
                c.set(x, eave, z, f"{copper}[type={'bottom' if d == HUT_HALF else 'top'}]")
                if d == 1:
                    c.set(x, eave + 1, z, f"{B.IRON_HATCH}[facing={'east' if x < mx else 'west'},half=bottom,open=false]")


def _hut(c):
    """The hut on its patch of the court. Returns what it is: "site/outbuildings" or "stand-in"."""
    x0, z0, x1, z1 = COURT
    mx = S.MERIDIAN_X
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            c.set(x, S.PAVING_Y, z, SK.STRIP if abs(x - mx) <= 1 else SK.FIELD)
    brass = (B.BRASS_LINE + "[shape=north_south]") if hasattr(B, "BRASS_LINE") else B.BRASS_INLAY
    for z in range(HUT_Z - HUT_HALF + 1, z1 + 1):
        c.set(mx, S.GROUND, z, brass)
    theirs = _outbuildings()
    if theirs is None:
        _hut_stand_in(c)
        return "stand-in"
    apart = Canvas()
    theirs.build(apart, (0, 0, 0))
    bx0, by0, bz0, bx1, by1, bz1 = HUT_BOX
    for x in range(bx0, bx1 + 1):
        for y in range(by0, by1 + 1):
            for z in range(bz0, bz1 + 1):
                if apart.has(x, y, z):
                    c.set(x, y, z, apart.get(x, y, z))
    return "site/outbuildings"


def _dome(c):
    """The pavilion's flat roof as main/facade lays it, the iron plate main/roof lays before the
    dome's door, and the small dome itself."""
    x0, z0, x1, z1 = DECK
    c.box(x0, DECK_Y, z0, x1, DECK_Y, z1, B.SLATE_SMOOTH.block)
    door = smalldome.door_cells()[0]
    c.set(door[0] - 1, DECK_Y, door[2], B.IRON_RIVETED.block)
    smalldome.build(c, (0, 0, 0))


def _bench_origin(at, model_middle, floor):
    """The origin that stands an instrument's middle (x, z) on the bench's `at`, its floor on the bench's."""
    return (at[0] - model_middle[0], BENCH[1] - floor, at[1] - model_middle[1])


def bench_origins():
    """(the transit circle's origin, the astrograph's) on the bench."""
    a = meridian.axis()
    return (_bench_origin(MERIDIAN_AT, (a[0], a[2]), float(S.GROUND)),
            _bench_origin(ASTRO_AT, astro.DOME_AXIS, astro.FLOOR))


def _bench(c):
    bx, by, bz = BENCH
    hx, hz = BENCH_HALF
    c.box(bx - hx, by - 1, bz - hz, bx + hx, by - 1, bz + hz, B.TUFF_SMOOTH.block)
    c.box(bx - hx, by, bz - hz - 1, bx + hx, by + BENCH_WALL - 1, bz - hz - 1, B.ASHLAR_FINE.block)
    at_meridian, at_astro = bench_origins()
    n = meridian.build(c, at_meridian, lamp=False, brightness=BENCH_LIGHT)
    n += astro.build(c, at_astro, brightness=BENCH_LIGHT)
    return n


def build():
    c = Canvas()
    c.hut = _hut(c)
    _dome(c)
    n = meridian.build(c, (0, 0, 0))
    n += astro.build(c, (0, 0, 0))
    n += _bench(c)
    sky.build(c, (0, 0, 0))         # the light line's sources go in last, when every piece is in place
    c.entity_counts = {"machines": n}
    return c


def write_pack(pack_dir):
    """The repainted blocks the rooms are built of, and the sky line's pictures: the scene stands
    in the map's hour (mood.py)."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])


def shots():
    """The cameras.

    The hut (the eye of a standing person unless said):
      hut_door      in the doorway, north along the meridian: the instrument end on
      hut_east      from the south-east corner: the tube, the east circle and its pier
      hut_west      from the south-west corner: the lantern on the west pier
      hut_north     from the north-west corner, back at the object glass
      hut_circle    close, over the east pier's shoulder: the east circle's divided limb and the two
                    microscopes that read it
      hut_eye       close: the eye end, the micrometer and the two finding circles
      hut_sight     from outside, down the tube's own line through the slot into the object glass
      hut_court     from the court, due south of the door: the hut and what shows in its slot

    The dome:
      dome_door     a step inside the west door (its leaf is shut) and a step to the south, the eye on
                    the pivot: the tube overhead and its hoops, the column and the head beneath it
      dome_south    from the south wall: the tube side on, the mount behind it
      dome_north    from the north wall: the head, the declination circle, the counterweights
      dome_plate    close, by the east wall: the camera back and the plate holder
      dome_up       from the south-east of the room, up along the tube to the slit
      slit          from outside, beside the tube's line: the object glass in the slit
      terrace       from the terrace west of the dome, as one walks up to its door
      west_high     from the west and above, as from the tower: the slit and the glass in it

    The bench, at noon:
      bench_meridian, bench_meridian_side   the transit circle from the south-west; along its axis
      bench_astro, bench_astro_north        the astrograph from the south; from the north-east
      bench                                  both, from the south
    """
    out = []

    def shot(name, pos, look_at, time=TIME):
        out.append({"name": name, "pos": [round(v, 2) for v in pos],
                    "look_at": [round(v, 2) for v in look_at], "time": time})

    def off(p, dx=0.0, dy=0.0, dz=0.0):
        return (p[0] + dx, p[1] + dy, p[2] + dz)

    eye = S.EYE
    # the hut
    a = meridian.axis()
    east_pier = meridian.piers()[1]
    door_x, door_z = S.MERIDIAN_HUT["door"]
    lo, hi = HUT_Z - HUT_HALF + 1, HUT_Z + HUT_HALF            # the room: z -33 .. -26
    west, east = HUT_X - HUT_HALF + 1, HUT_X + HUT_HALF         # x 32 .. 39
    shot("hut_door", (door_x + 0.5, S.GROUND + eye, door_z + 0.35), off(a, dy=-0.2))
    shot("hut_east", (east - 0.35, S.GROUND + eye, hi - 0.35), off(a, dx=-0.2, dy=-0.1))
    shot("hut_west", (west + 0.35, S.GROUND + eye, hi - 0.35), off(a, dx=0.2, dy=-0.1))
    shot("hut_north", (west + 0.4, S.GROUND + 2.3, lo + 0.4), off(a, dy=0.3, dz=-0.4))
    limb = a[0] + meridian.CIRCLE_OFF / 16.0
    shot("hut_circle", (east_pier[0] + 1.05, S.GROUND + 2.75, a[2] + 1.3), (limb + 0.1, a[1] + 0.9, a[2] + 0.2))
    e = meridian.eyepiece()
    shot("hut_eye", (e[0] + 1.15, e[1] + 0.45, e[2] + 1.25), off(e, dy=0.25, dz=-0.35))
    o = meridian.objective()
    far = tuple(o[i] + meridian.SIGHT[i] * 7.5 for i in range(3))
    shot("hut_sight", (far[0] + 0.9, far[1] + 0.3, far[2]), o)
    shot("hut_court", (door_x + 0.5, S.GROUND + eye, door_z + 11.5), (door_x + 0.5, S.GROUND + 2.2, HUT_Z + 0.5))

    # the dome
    p = astro.pivot()
    floor = astro.FLOOR
    door = smalldome.door_cells()[0]
    h = astro.head()
    shot("dome_door", (door[0] + 1.2, floor + eye, door[2] + 1.85), p)
    shot("dome_south", (p[0] + 0.3, floor + eye, p[2] + 2.2), off(p, dx=-0.4, dy=0.2))
    shot("dome_north", (p[0] + 0.7, floor + eye, p[2] - 2.1), off(h, dx=-0.2, dy=-0.2))
    back = astro.plate()
    shot("dome_plate", (back[0] + 0.55, back[1] + 0.55, back[2] - 1.35), off(back, dx=-0.3, dy=0.1))
    g = astro.objective()
    shot("dome_up", (p[0] + 1.8, floor + eye, p[2] + 1.4), (g[0] + 1.0, g[1] - 0.8, g[2]))
    out_there = tuple(g[i] + astro.SIGHT[i] * 4.5 for i in range(3))
    shot("slit", (out_there[0], out_there[1] + 0.5, out_there[2] + 1.2), g)
    shot("terrace", (DECK[0] + 2.5, DECK_Y + 1 + eye, p[2] + 1.2), (g[0], g[1] - 0.6, g[2]))
    shot("west_high", (DECK[0] - 2.5, g[1] + 4.5, p[2] + 3.0), (g[0], g[1] - 0.5, g[2]))

    # the bench
    om, oa = bench_origins()
    m = off(a, *om)
    q = off(p, *oa)
    shot("bench_meridian", (m[0] - 3.6, BENCH[1] + 2.6, m[2] + 4.2), off(m, dy=-0.2), DAY)
    shot("bench_meridian_side", (m[0] + 5.2, BENCH[1] + 2.1, m[2] + 0.6), off(m, dy=-0.1), DAY)
    shot("bench_astro", (q[0] - 0.6, BENCH[1] + 2.4, q[2] + 5.6), off(q, dx=-0.5, dy=-0.2), DAY)
    shot("bench_astro_north", (q[0] + 2.6, BENCH[1] + 2.6, q[2] - 4.4), off(q, dx=-0.4, dy=-0.4), DAY)
    shot("bench", (BENCH[0], BENCH[1] + 3.2, BENCH[2] + 9.5), (BENCH[0], BENCH[1] + 1.6, BENCH[2]), DAY)
    return out
