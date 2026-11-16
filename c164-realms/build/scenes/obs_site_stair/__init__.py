"""Test scene of the work package site/stair (plan/packages/site/stair.md): the grand stair, the
retaining wall under the upper terrace, the floor and the edge of the lower platform.

The hill as it stands in the master scene: the site line whole (the terrain, the terraces, the court
and whatever stands on the lower platform by now), the main building above it, the props line's
lamps and the sky line's light sources last. The lines are built whole, in the master scene's
order, so the picture keeps up with them as their packages are merged.

The lamps of the way in. The package names where they stand (lowerplatform.LAMP_POINTS,
stair.LAMP_POINTS); the props line places them. Where props/lamps has its table of the site's
lamps the scene asks for it (lamps.dress). What that leaves out the scene stands itself, the way
the table does: a street lamp on the yard's six pads and on the two pedestals at the stair's foot;
on the two at its head the lip's low lamp, and nothing while there is no such lamp. A street lamp
at the head stands across a whole bay of the front in the arrival view, up to the cornice
(tools/check.py, sight).

The views: V1 as the skeleton fixes it (the arrival view the package is judged on: the wall is the
band under the building, the stair comes down on the left); the stair on its axis, from the block
where the axis begins on the yard's east edge (from there the yard's lamps stand whole in the
picture, two pairs before the stair, and the terrace's lip hides least of the front); the look
back down it from its head; the stair from its foot; the wall, a cheek and a foot pedestal from
near, and the wall's length from the yard's north end; the board's view of the power house (V6),
which stands on the stair's south half since A0's ruling of 11-16: the south cheek and its foot
pedestal with its lamp are that picture's foreground, the yard and the walk to the house's door
its floor; and three from above: from the north-east, where neither the power house nor its
chimney stands before the stair and the whole hill is in the picture; on the axis, the way a car
of the cableway comes in, the line from the yard's edge to the door; and the board's V12.

Two more scenes show the same hill with one thing left out, on the views that are judged
(JUDGED): obs_site_stair_noband without the walk's band on the treads (A0 #28839 chose on the
pictures: the band stays) and obs_site_stair_nolamps without the lamps of the way (c235's review).

    python -m scenes.obs_site_stair      writes shots.json for the three scenes
"""
import math

from artkit.canvas import Canvas

from scenes.obs import main, materials, props, site, sky
from scenes.obs.common import skeleton as S
from scenes.obs.props import lamps
from scenes.obs.site import lowerplatform, stair

BIOME = "obs_blue"
BIOME_MARGIN = 100
BIOME_MARGIN_Y = 150
LINES = (site, main, props, sky)
TIME = 14000
STREET_LEVEL = 13       # the lamps of the way are a step under the doorway (props/lamps)

# The board's views are the skeleton's: the arrival view (A0 #304 aims it at the comet over the dome),
# and the view of the power house, which stands on the tread of column x 66, three rows inside the
# south cheek (A0, 11-16; site/powerhouse's scene calls it stair_south).
V1, V6 = S.V1, S.V6
LOW = S.LOWER_GROUND + S.EYE        # -4.38: the eye of a person on the lower platform
HIGH = S.GROUND + S.EYE             # 1.62: on the upper terrace
VIEWS = [
    ("v1", V1["pos"], V1["look_at"]),
    ("stair_axis", (lowerplatform.START_X + 1.5, LOW, 0.5), (17, 12, 0.5)),
    ("stair_foot", (76.5, LOW, 3.5), (56, 3, 0.5)),
    ("look_back", (stair.EDGE_X + 0.5, HIGH, 0.5), (84, -9, 0.5)),
    ("wall_near", (70.5, LOW, -27.5), (62, -3.4, -15.5)),
    ("cheek_side", (75.5, LOW, -19.5), (65, -3, -8.5)),
    ("pedestal", (76.5, LOW, -12.5), (72.8, -3.6, -8.8)),
    ("yard_south", (72.5, LOW, -40.5), (62, -3.5, -4)),
    ("v6", V6["pos"], V6["look_at"]),
    ("aerial", (114, 42, -34), (58, 6, 2)),
    ("axis_high", (110, 16, 0.5), (40, -4, 0.5)),
    ("v12_aerial", (66, 72, 58), (8, -2, 0)),
    ("corner_nw", (68.5, LOW, -33.5), (60.5, -4.6, -40.5)),
    ("corner_sw", (65.5, LOW, 41.5), (60.5, -4.8, 40.5)),
    # the wall's arcade, the way the second round looks at detail (plan/fine.md 6): square on from
    # ten blocks, two bays between two buttresses; and one arch from two blocks
    ("wall_bay", (70.5, LOW, -17.5), (60, -3.8, -17.5)),
    ("wall_arch", (62.7, LOW, -18.6), (59.6, -4.1, -20.2)),
]
JUDGED = ("v1", "stair_axis", "look_back", "aerial", "axis_high")


def shots(names=None):
    """The shot list, or the views of it that are named."""
    return [{"name": name, "pos": [round(float(v), 2) for v in pos],
             "look_at": [round(float(v), 2) for v in look_at], "time": TIME}
            for name, pos, look_at in VIEWS if names is None or name in names]


def _way_lamps(c):
    """Stand the lamps of the way in that nobody has placed yet (see the module's text)."""
    for p in list(lowerplatform.LAMP_POINTS) + list(stair.LAMP_POINTS):
        if any(math.dist(p, e[:3]) < 0.5 for e in c.entities):
            continue
        if p[1] <= S.GROUND:
            lamps.place(c, "street", p, level=STREET_LEVEL)
        elif "post" in lamps.SPEC:
            lamps.place(c, "post", p)


def build(band=None, lit=True):
    """band: the walk's band on the stair's treads; None is the package's own switch (stair.BAND).
    lit: the lamps of the way in."""
    c = Canvas()
    if hasattr(lamps, "dress"):
        lamps.dress(c, lit)
    was = stair.BAND
    if band is not None:
        stair.BAND = bool(band)
    try:
        for line in LINES:
            if line is sky and lit:
                _way_lamps(c)       # before the sky line turns the offered lights into light
            line.build(c, (0, 0, 0))
    finally:
        stair.BAND = was
    return c


def build_models():
    out = {}
    for line in LINES:
        out.update(line.models() or {})
    return out


def write_pack(pack_dir):
    """The stair paints nothing itself; it stands on the repainted blocks as the materials line has
    them today (ashlar, cast iron). The sky's pack goes with them: the scene stands in the map's
    hour, and it is the sky's pack that puts the comet in the moon's place and blanks the game's own
    sun, which that hour leaves as a bright square on the open western horizon."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])
