"""Test scene of the work package machines/refractor (plan/packages/machines/refractor.md).

The two mounts side by side, each in a dome room of its own, STAGE blocks apart from north to
south: version a (the director's pick, what machines/scope brings to the map) under the northern
dome, version b under the southern one. Every camera stands the same way in both rooms and its
two pictures carry the same name with the version behind it, so the two can be looked at blind.

What other packages bring is stood in for with the skeleton's numbers: the drum and the dome
(main/dome once it is in the tree, until then the massing of main/_dome), the floor of boards, the
opening round the pier with its curb and railing, the pier's cap (main/shell). The room itself
(interiors/domeroom) is left out: the instrument is judged against the bare shell.

    python -m scenes.obs_mach_refractor      writes shots.json from the numbers below
"""
import importlib

from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.machines import scope
from scenes.obs.main import _dome
from scenes.obs.main import _order as O

BIOME = "obs_blue"
CATEGORY = "machines"
BIOME_MARGIN = 32
BIOME_MARGIN_Y = 32

STAGE = {"a": (0, 0, 0), "b": (0, 0, 40)}       # where each version's dome room stands
FLOOR_Y = S.ROOF_FLOOR
UNDER_Y = S.DRUM_BASE - 4                        # the box's bottom: the pier's opening looks down on it
TIME = 14000                                     # look A, the blue hour


def _rotunda(c, origin):
    """The drum and the dome: main/dome in its default version once that package is in the
    tree, else the massing the master scene has today."""
    try:
        dome = importlib.import_module("scenes.obs.main.dome")
    except ImportError:
        dome = None
    if dome is not None:
        dome.build(c, origin)
    else:
        _dome.build(c, origin)


def _room(c, origin):
    """What main/shell lays in the dome room: the floor of boards, the iron curb round the pier's
    opening with the railing on it, the pier's cap. Under it the box is closed in dark stone."""
    ox, oy, oz = origin
    cx, cz = S.DOME_CENTRE
    whole = O.disc(cx, cz, S.DOME_R)
    inside = O.shrink(O.shrink(whole))
    hole = O.box(*S.PIER_ENVELOPE)
    curb = O.ring(hole)
    exit_cell = (cx, S.PIER_ENVELOPE[1] - 1)     # where the ring stair comes out, on the north side
    for x, z in inside - hole:
        c.set(ox + x, oy + FLOOR_Y, oz + z, B.IRON_RIVETED.block if (x, z) in curb else B.FLOOR_WOOD.block)
    for x, z in O.box(*S.PIER_CAP):
        for y in range(UNDER_Y + 1, FLOOR_Y + 1):
            c.set(ox + x, oy + y, oz + z, B.ASHLAR_FINE.block)
    for x, z in curb - {exit_cell}:
        c.set(ox + x, oy + FLOOR_Y + 1, oz + z, B.IRON_BARS)
    for x, z in whole:
        c.set(ox + x, oy + UNDER_Y, oz + z, B.SLATE_SMOOTH.block)
        if (x, z) not in inside:
            for y in range(UNDER_Y + 1, S.DRUM_BASE):
                c.set(ox + x, oy + y, oz + z, B.SLATE_BRICK.block)


def build():
    c = Canvas()
    n = 0
    for version, origin in STAGE.items():
        _rotunda(c, origin)
        _room(c, origin)
        n += scope.build(c, origin, version=version)
    sky.build(c, (0, 0, 0))         # the light line's sources go in last, when every piece is in place
    c.entity_counts = {"machines": n}
    return c


def build_models():
    return {name: model for version in STAGE for name, model in scope.models(version).items()}


def write_pack(pack_dir):
    """The comet in the slit is the sky line's picture, the blocks are repainted as the materials
    line has them today."""
    return list(sky.pack(pack_dir) or []) + list(materials.pack(pack_dir) or [])


def shots():
    """The cameras, each once for either version. All but the last two stand inside the room, at
    the height of a standing eye where the floor allows it.

    v8      the billboard's view, scope.v8(): a standing eye at the east edge of the observing
            floor, north of the tube of version a, up along it at the slit
    v8_south  the same from south of the dome's axis, where version b shows best (scope.V8["b"])
    eye     beside the observer, looking up the tube
    south   the whole instrument side on, from the south wall; north the same from the north
    east    from the east wall, the tube coming at the camera
    mount   the mount from the south, close; mount_north from the north
    tail    the tailpiece, the finder and the red lamp's back, close
    circle  the hour circle, the worm and the driving clock, from under the tube
    lamp    the red lamp's glass, from the west and below: the one camera that stands on the
            side each version hangs its lamp on
    top     from under the dome's crown, down on the instrument
    slit    from outside, down the tube's own line through the slit at the objective
    """
    out = []
    eye_y = S.ROOF_STAND + S.EYE
    for v, origin in STAGE.items():
        def shot(name, pos, look_at, o=origin, v=v):
            out.append({"name": f"{name}_{v}",
                        "pos": [round(pos[i] + o[i], 2) for i in range(3)],
                        "look_at": [round(look_at[i] + o[i], 2) for i in range(3)], "time": TIME})

        cross, eyepiece, objective = scope.crossing(v), scope.eyepiece(v), scope.objective(v)
        mid = tuple((eyepiece[i] + objective[i]) / 2.0 for i in range(3))
        shot("v8", *scope.v8("a"))
        shot("v8_south", *scope.v8("b"))
        shot("eye", (eyepiece[0] + 1.0, eye_y, eyepiece[2] + 1.8),
             (eyepiece[0] - 7.5, eye_y + 6.6, eyepiece[2] - 0.1))
        shot("south", (5.5, eye_y + 1.0, 11.3), (mid[0], cross[1] + 0.3, 0.5))
        shot("north", (5.5, eye_y + 1.0, -10.3), (mid[0], cross[1] + 0.3, 0.5))
        shot("east", (13.6, eye_y, -1.2), (2.0, cross[1] + 1.5, 0.8))
        shot("mount", (7.6, eye_y + 0.8, 7.2), (4.5, cross[1] - 1.0, 0.7))
        shot("mount_north", (7.6, eye_y + 0.8, -6.2), (4.5, cross[1] - 1.0, 0.3))
        shot("tail", (eyepiece[0] + 1.3, eyepiece[1] + 0.25, eyepiece[2] + 2.3),
             (eyepiece[0] - 1.1, eyepiece[1] + 0.75, eyepiece[2] + 0.1))
        shot("circle", (7.9, eye_y + 0.6, 5.4), (4.8, cross[1] - 2.1, 1.9))
        lamp, side = scope._lamp_at(v)[0], scope._SPEC[v]["show"]
        shot("lamp", (lamp[0] - 1.3, lamp[1] - 0.45, lamp[2] + side * 0.4),
             (lamp[0] + 0.3, lamp[1] + 0.1, lamp[2] - side * 0.1))
        shot("top", (7.5, 34.5, 3.0), (3.6, cross[1], 0.6))
        out_there = tuple(objective[i] + scope.SIGHT[i] * 11.0 for i in range(3))
        shot("slit", (out_there[0], out_there[1] + 1.2, out_there[2] + 1.6), objective)
    return out
