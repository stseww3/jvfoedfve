"""Test scene of the work package machines/armillary (plan/packages/machines/armillary.md): version a.

The armillary where it stands in the master scene: the site line under it (the court with the
emblem roundel and the meridian), the main line behind it (the entrance and the dome it is seen
against), the props line's lamps, and the sky line's light sources last. The lines are built whole,
in the master scene's order, as in obs_site_court; of the machines line only the armillary is
placed. Version b stands on the same spot, so it has a scene of its own with the same shots,
obs_mach_armillary_b: the two are compared picture by picture.

Until A2's table places the four ground lamps at the foot of the base, the scene stands a stand-in
of the props line's ground projector on each of armillary.lamp_feet() (LAMP_STANDINS).

    python -m scenes.obs_mach_armillary      writes shots.json
"""
from artkit.canvas import Canvas

from scenes.obs import main, materials, props, site, sky
from scenes.obs.common import skeleton as S
from scenes.obs.machines import armillary
from scenes.obs.props import lamps

VERSION = "a"
BIOME = "obs_blue"
BIOME_MARGIN = 80
BIOME_MARGIN_Y = 140
TIME = 14000
LAMP_STANDINS = True

# the two fixed cameras: the skeleton's once it has them (director, 11-14), until then the same numbers
V1 = S.V1 if hasattr(S, "V2") else dict(pos=S.V1["pos"], look_at=(8, 34, 0.5))
V2 = getattr(S, "V2", dict(pos=(58.5, 1.7, 0.5), look_at=(17, 19, 0.5)))


def scene(version):
    c = Canvas()
    site.build(c, (0, 0, 0))
    main.build(c, (0, 0, 0))
    armillary.build(c, (0, 0, 0), version=version)
    props.build(c, (0, 0, 0))
    if LAMP_STANDINS:
        for foot, yaw in armillary.lamp_feet():
            lamps.place(c, "uplight", foot, yaw=yaw)
    sky.build(c, (0, 0, 0))
    return c


def build():
    return scene(VERSION)


def build_models():
    out = {}
    for line in (site, main, props, sky):
        out.update(line.models() or {})
    out.update(armillary.models())
    return out


def write_pack(pack_dir):
    """The armillary paints no block; it stands on the repainted blocks as the materials line has
    them today."""
    return materials.pack(pack_dir)


def shots():
    cx, cy, cz = S.mid(armillary.CX), armillary.CENTRE_Y, S.mid(armillary.CZ)

    def shot(name, pos, look_at):
        return {"name": name, "pos": [float(v) for v in pos], "look_at": [float(v) for v in look_at], "time": TIME}

    return [
        shot("v2_axis", V2["pos"], V2["look_at"]),                              # the view it is made for
        shot("v2_entrance", V2["pos"], (17, 11, 0.5)),                          # the same eye, level with the brief
        shot("axis_near", (cx + 12, 1.7, cz), (17, 8, 0.5)),                    # half way: the entrance through the rings
        shot("v1_arrival", V1["pos"], V1["look_at"]),
        shot("aerial", (46.0, 62.0, 30.0), (30.0, 0.0, 0.5)),                   # obs_site_court's bird's-eye view
        shot("plan", (cx, 26.0, cz), (cx, 0.0, cz)),                            # straight down: ring and meridian
        shot("oblique", (cx + 5.5, 1.7, cz + 5.5), (cx, cy - 0.5, cz)),         # on foot, from the south-east
        shot("meridian", (cx, 1.7, cz + 12), (cx, cy - 0.3, cz)),               # due south: the meridian ring on edge
        shot("rings", (cx + 3.1, cy + 0.2, cz + 2.9), (cx, cy - 0.1, cz)),      # the scales and the joints
        shot("door", (19.5, 1.62, 0.5), (cx, cy - 0.7, cz)),                    # stepping out of the entrance
    ]
