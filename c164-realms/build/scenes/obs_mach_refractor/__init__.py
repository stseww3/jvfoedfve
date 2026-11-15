"""Test scene of the work package machines/refractor: the great refractor in the dome room
(plan/packages/machines/refractor.md), both versions side by side for the review to choose.

The room is the master scene's own, built whole: main's drum, dome and slit, the telescope pier and
its cap, the dome-room floor, the rail and the ring stair. The two mountings stand at the scene's
true coordinates, one copy of the room each, the second copy moved 400 blocks south so the two can
be photographed from identical cameras (the scenes obs_mach_domegear and obs_main_shell do the
same):

    z 0      version a, the German equatorial: the tube 1.5 blocks off the axes, a weight opposite
    z 400    version b, the English cradle: the tube on the dome axis, heavy rings, no weight

What each shot is for (card's acceptance points):
    v8, v8_north, v8_glow    the room's own view of the machine, the tube in the slit, the sky and
                             the comet behind it, in the default light and in the afterglow
    axis                     down the tube's axis from outside the pier, the eyepiece at the far
                             end: what a visitor standing at the eye sees, the map's last view
    tube_near                the barrel from three blocks: the courses, the rivets, the hoops
    eye_near                 the eyepiece end, the focuser, the finder, the one red lamp
    mount                    the head from the room's south-east: the polar axle, the circles, the
                             fork or the weight
    driver                   the driving clock and the governor against the pedestal
    from_east, from_south     the machine's outline across the room, as the stair exit and the
                             gallery give it
    weight (a only)          version a's counterweight, clear of the floor
The pair is compared picture by picture; obs_mach_refractor_b is the same scene with b as its
default version, so the two can be laid side by side in either order.

    python -m scenes.obs_mach_refractor      writes shots.json from the numbers below
"""
from artkit.canvas import Canvas

from scenes.obs import main, materials, sky
from scenes.obs.common import skeleton as S
from scenes.obs.machines import scope

BIOME = "obs_blue"
CATEGORY = "machines"
BIOME_MARGIN = 64
BIOME_MARGIN_Y = 64
TIME = 14000                    # light version A, the default (INTERFACE: 18000 is B, 12900 is C)
GLOW = 12900                    # light version C: the most sky light the room ever gets

FIRST = "a"                     # the version in the room at z 0
SECOND = "b"                    # the one in the copy 400 south
SHIFT = 400                     # how far the second copy stands from the first, in z
VERSIONS = {FIRST: 0, SECOND: SHIFT}

AX, AZ = S.DOME_AXIS            # (4.5, 0.5)
STAND = S.ROOF_STAND            # 18: feet on the dome-room floor
EYE = STAND + S.EYE             # 19.62: the eye of a person standing in the room
CX, CZ = S.DOME_CENTRE


def _room(c, origin, version):
    """One copy of the room and one telescope: the building's own shells, then the machine, in the
    master scene's order (machines before the sky's light sources)."""
    main.build(c, origin)
    n = scope.build(c, origin, version=version)
    return n


def build():
    c = Canvas()
    counts = {}
    for version, dz in VERSIONS.items():
        counts[version] = _room(c, (0, 0, dz), version)
    sky.build(c, (0, 0, 0))     # the light line's sources go in last, both rooms' at once
    c.entity_counts = {"machines": sum(counts.values())}
    return c


def build_models():
    out = {}
    out.update(main.models() or {})
    out.update(scope.models() or {})
    return out


def write_pack(pack_dir):
    """The sky's pictures -- the comet stands in the slit -- and the repainted stone, copper and
    iron the machine is judged against."""
    return list(sky.pack(pack_dir) or []) + list(materials.pack(pack_dir) or [])


def shots():
    """The cameras, written once for version a's room and repeated 400 south for version b: the
    pair are compared shot by shot, so the names and the aims are the same."""
    out = []

    def shot(name, pos, look_at, time=TIME, dz=0):
        """One camera, and with `dz` the same camera 400 south: both the stand and the aim move, so
        the pair are photographed from the same place in their own room."""
        out.append({"name": name, "pos": [round(v, 2) for v in (pos[0], pos[1], pos[2] + dz)],
                    "look_at": [round(v, 2) for v in (look_at[0], look_at[1], look_at[2] + dz)],
                    "time": time})

    eye_a, eye_b = scope.eyepiece("a"), scope.eyepiece("b")
    obj_a, obj_b = scope.objective("a"), scope.objective("b")
    piv_a, piv_b = scope.pivot("a"), scope.pivot("b")

    # the room's own view: the domegear scene's stand and aim, so the pictures can be laid together
    v8 = getattr(S, "V8", None) or dict(pos=(11.8, EYE, 2.2), look_at=(0.0, 25.2, 0.9))
    shot("v8", v8["pos"], v8["look_at"])
    shot("v8_north", (v8["pos"][0], v8["pos"][1], v8["pos"][2] - 2.0), v8["look_at"])
    shot("v8_glow", v8["pos"], v8["look_at"], GLOW)

    # down the tube's axis from east of the eyepiece, at the eye of a standing person: the map's
    # last view. Version a's tube runs in z 1.40 and its eyepiece end is lower, so its camera moves
    shot("axis_a", (eye_a[0] + 1.2, eye_a[1], eye_a[2]), (obj_a[0], obj_a[1], obj_a[2]))
    shot("axis_b", (eye_b[0] + 1.2, eye_b[1], eye_b[2]), (obj_b[0], obj_b[1], obj_b[2]),
         dz=SHIFT)

    # the barrel from three blocks off its middle, above and south of it
    mids = [tuple((eyepiece[i] + objective[i]) / 2.0 for i in range(3))
            for eyepiece, objective in ((eye_a, obj_a), (eye_b, obj_b))]
    shot("tube_near_a", (mids[0][0] + 1.6, mids[0][1] + 2.2, mids[0][2] + 2.6), mids[0])
    shot("tube_near_b", (mids[1][0] + 1.6, mids[1][1] + 2.2, mids[1][2] + 2.6), mids[1], dz=SHIFT)

    # the eyepiece end: the drawtube, the focuser, the finder and the one red lamp, from the room
    shot("eye_near_a", (eye_a[0] + 1.4, eye_a[1] + 0.9, eye_a[2] + 1.6),
         (eye_a[0], eye_a[1], eye_a[2]))
    shot("eye_near_b", (eye_b[0] + 1.4, eye_b[1] + 0.9, eye_b[2] + 1.6),
         (eye_b[0], eye_b[1], eye_b[2]), dz=SHIFT)

    # the head, from the room's south-east, where the gallery and the stair leave the floor clear
    shot("mount_a", (piv_a[0] + 3.2, STAND + 2.6, piv_a[2] + 3.6), (piv_a[0], piv_a[1], piv_a[2]))
    shot("mount_b", (piv_b[0] + 3.2, STAND + 2.6, piv_b[2] + 3.6), (piv_b[0], piv_b[1], piv_b[2]),
         dz=SHIFT)

    # the driving clock and its governor, at the pedestal's south face
    for version, dz, piv in (("a", 0, piv_a), ("b", SHIFT, piv_b)):
        shot("driver_" + version, (piv[0] + 1.1, STAND + 1.5, piv[2] + 3.4),
             (piv[0], STAND + 1.6, piv[2] + 1.2), dz=dz if version == "b" else 0)

    # the outline across the room, from due east and from due south: the two bars of version a, the
    # centred cradle of version b
    for version, dz, piv in (("a", 0, piv_a), ("b", SHIFT, piv_b)):
        shot("from_east_" + version, (CX + 9.0, EYE, AZ), (piv[0], piv[1], piv[2]),
             dz=dz if version == "b" else 0)
        shot("from_south_" + version, (CX, EYE, AZ + 9.0), (piv[0], piv[1], piv[2]),
             dz=dz if version == "b" else 0)

    # version a's weight, down the declination axis from the axes, seen from the north-west floor
    shot("weight_a", (AX - 3.0, EYE, AZ - 3.2), (AX - 0.9, 22.2, AZ - 1.1))
    return out
