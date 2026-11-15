"""Test scene of the work package machines/armillary (plan/packages/machines/armillary.md): version a.

The armillary where it stands in the master scene: the site line under it (the court with the
emblem roundel and the meridian), the main line behind it (the entrance and the dome it is seen
against), the props line's lamps, and the sky line's light sources last. The lines are built whole,
in the master scene's order, as in obs_site_court; of the machines line only the armillary is
placed. Version b stands on the same spot, so it has a scene of its own with the same shots,
obs_mach_armillary_b: the two are compared picture by picture. obs_mach_armillary_ah is version a
with the horizon ring it has lost, on five of these shots, until the director has ruled on it.

What lights the brass is A2's (sky/lights, props/lamps): four ground lamps on armillary.LAMP_CELLS
and a hidden light in the cell under armillary.LIGHT_CELL. A props line that has them (it then has
lamps.FEET_GLOW) is asked for that one group of the site's lamps, lamps.site(groups=("feet",)): its
switch lamps.DRESS is off in the master scene for now. Until the tree has such a props line the
scene stands the same in their place: the ground projector on each of armillary.lamp_feet(), and a
light of level GLOW.

    python -m scenes.obs_mach_armillary      writes shots.json
"""
from artkit.canvas import Canvas

from scenes.obs import main, materials, props, site, sky
from scenes.obs.common import skeleton as S
from scenes.obs.machines import armillary
from scenes.obs.props import _kit as K
from scenes.obs.props import lamps

VERSION = "a"
BIOME = "obs_blue"
BIOME_MARGIN = 80
BIOME_MARGIN_Y = 140
TIME = 14000
GLOW = 8                # the stand-in's level, A2's figure (c220, 11-15): the brass over it gets 7

# the two fixed cameras: the skeleton's once it has them (director, 11-14), until then the same numbers
V1 = S.V1 if hasattr(S, "V2") else dict(pos=S.V1["pos"], look_at=(8, 34, 0.5))
V2 = getattr(S, "V2", dict(pos=(58.5, 1.7, 0.5), look_at=(17, 19, 0.5)))


def _feet_lamps(c):
    """The four ground lamps and the light under the sphere. The brass has to stand on the canvas
    already: the props line gives that light only where the rings are."""
    if hasattr(lamps, "FEET_GLOW"):
        # a lamp is placed once: with lamps.DRESS on, props.build() has placed these and this adds nothing
        lamps.site(c, (0, 0, 0), groups=("feet",))
        return
    for foot, yaw in armillary.lamp_feet():
        lamps.place(c, "uplight", foot, yaw=yaw)
    x, y, z = armillary.LIGHT_CELL
    K.offer_lights(c, [((x, y - 1, z), GLOW)], "machines/armillary: stand-in for props/lamps")


def scene(version):
    c = Canvas()
    site.build(c, (0, 0, 0))
    main.build(c, (0, 0, 0))
    armillary.build(c, (0, 0, 0), version=version)
    props.build(c, (0, 0, 0))
    _feet_lamps(c)
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
    v2x, v2y, v2z = V2["pos"]

    def shot(name, pos, look_at):
        return {"name": name, "pos": [round(float(v), 3) for v in pos],
                "look_at": [round(float(v), 3) for v in look_at], "time": TIME}

    return [
        # the two pictures the versions are chosen on (director, 11-15). v2_entrance looks level at the
        # entrance, as the brief's V2 did; it stands one step in front of V2, because a shot on V2's own
        # spot looks where the skeleton says (tools/check.py, views)
        shot("v2_axis", V2["pos"], V2["look_at"]),
        shot("v2_entrance", (v2x - 1, v2y, v2z), (17, 11, 0.5)),
        shot("v1_arrival", V1["pos"], V1["look_at"]),
        shot("aerial", (46.0, 62.0, 30.0), (30.0, 0.0, 0.5)),                   # obs_site_court's bird's-eye view
        shot("plan", (cx, 17.0, cz + 9), (cx, 0.0, cz)),                        # obs_site_court's emblem_top, north up
        shot("oblique", (cx + 5.5, 1.7, cz + 5.5), (cx, cy - 0.5, cz)),         # on foot, from the south-east
        # along the brass meridian, the meridian ring on edge: is it a cross? (reviewer cr2 and
        # director, 11-15). Near, and from the south and the north edge of the court
        shot("meridian", (cx, 1.7, cz + 12), (cx, cy - 0.3, cz)),
        shot("south_edge", (cx, 1.7, 29.5), (cx, cy - 0.3, cz)),
        shot("north_edge", (cx, 1.7, -28.5), (cx, cy - 0.3, cz)),
        shot("rings", (cx + 3.1, cy + 0.2, cz + 2.9), (cx, cy - 0.1, cz)),      # the scales and the joints
        # stepping out of the entrance: against the sky. One step east of the skeleton's V7
        shot("door", (20.5, 1.62, cz), (cx, cy - 0.7, cz)),
    ]
