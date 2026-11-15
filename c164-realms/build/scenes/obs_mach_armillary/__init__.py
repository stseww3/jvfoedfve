"""Test scene of the work package machines/armillary (plan/packages/machines/armillary.md): version a.

The armillary where it stands in the master scene: the site line under it (the court with the
emblem roundel and the meridian), the main line behind it (the entrance and the dome it is seen
against), the props line's lamps, and the sky line's light sources last. The lines are built whole,
in the master scene's order, as in obs_site_court; of the machines line only the armillary is
placed. Version b stands on the same spot, so it has a scene of its own with the same shots,
obs_mach_armillary_b: the two are compared picture by picture. obs_mach_armillary_ah is version a
with the horizon ring it has lost, on five of these shots, until the director has ruled on it.

What lights the brass is the props line's (props/lamps, the group "feet" of the site's lamps): four
ground lamps on armillary.LAMP_CELLS and a hidden light in the cell under armillary.LIGHT_CELL.
props.build() places them with the rest of the site's lamps. The brass has to stand on the canvas
before that: the props line gives the hidden light only where the rings are.

    python -m scenes.obs_mach_armillary      writes shots.json
"""
from artkit.canvas import Canvas

from scenes.obs import main, materials, props, site, sky
from scenes.obs.common import skeleton as S
from scenes.obs.machines import armillary

VERSION = "a"
BIOME = "obs_blue"
BIOME_MARGIN = 80
BIOME_MARGIN_Y = 140
TIME = 14000

V1, V2 = S.V1, S.V2


def scene(version):
    c = Canvas()
    site.build(c, (0, 0, 0))
    main.build(c, (0, 0, 0))
    armillary.build(c, (0, 0, 0), version=version)
    props.build(c, (0, 0, 0))
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
    them today, under the map's sky: V2 looks west, and without the sky's pack the game's own sun
    would stand over the dome."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])


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
        # director, 11-15). Near, from the south edge of the court, and from the north, stepping out of
        # the meridian hut's door (the hut stands over the court's north edge)
        shot("meridian", (cx, 1.7, cz + 12), (cx, cy - 0.3, cz)),
        shot("south_edge", (cx, 1.7, 29.5), (cx, cy - 0.3, cz)),
        shot("north_edge", (cx, 1.7, S.MERIDIAN_HUT["door"][1] + 1.5), (cx, cy - 0.3, cz)),
        # the scales and the joints, from the north-east and a little below: there the ecliptic turns
        # the rim with its scale to the camera in both versions (from the south-east it showed none)
        shot("rings", (cx + 3.5, cy - 1.15, cz - 2.7), (cx, cy, cz)),
        # stepping out of the entrance: against the sky. One step east of the skeleton's V7
        shot("door", (20.5, 1.62, cz), (cx, cy - 0.7, cz)),
    ]
