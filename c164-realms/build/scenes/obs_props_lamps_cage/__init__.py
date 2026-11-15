"""The hoops of the caged wall lamp, three ways, for the review to pick from: the card keeps three
fallbacks and the choice is a6's model, not this line's (A0 #549 left it open, c219 group #33010).

Nothing here is in the master scene or in any delivery: the delivery's cage A is unchanged, and so
are obs_props_lamps and obs_props_lamps_site. This scene exists to put the three on one wall under
one camera, so the "pause sign" question is settled from pictures instead of prose.

    python -m scenes.obs_props_lamps_cage          writes shots.json, prints the models
    tools/selfshots.py obs_props_lamps_cage --out /tmp/c164_lamps/cage

  as now   the two hoops either side of the glass's middle, close in (the delivered cage_a)
  wide     the same two moved out to the glass's edge (x +-2.25, the card's second fallback)
  three    three hoops a third of the way round (the card's first fallback)
"""
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.props import lamps

BIOME = "obs_blue"
BIOME_MARGIN = 32
BIOME_MARGIN_Y = 32

STONE, PLATE = B.ASHLAR_FINE.block, B.IRON_PLATE
WALL_H = 8
BAY = 6                                                  # how far apart the three hang
CHOICES = (("as_now", "two"), ("wide", "two_wide"), ("three", "three"))
TIME = 14000


def _models():
    """The delivered family plus the two fallbacks, under their own names."""
    out = dict(lamps.models())
    for name, choice in CHOICES[1:]:
        out[f"{lamps.PREFIX}cage_a_{name}"] = lamps._cage_a(lamps.cage_hoops(choice),
                                                            name=f"{lamps.PREFIX}cage_a_{name}")
    return out


def build_models():
    return _models()


def _wall(c, x0):
    """A stretch of dressed stone with an iron plate where the lamp hangs, as the gallery has it.
    The wall's face is one row north of the lamp bay, so that the lamp hangs south of it."""
    c.box(x0, 0, -1, x0 + BAY - 1, WALL_H - 1, -1, STONE)
    c.box(x0 + 2, 0, -1, x0 + 2, WALL_H - 1, -1, PLATE)


def build():
    c = Canvas()
    models = _models()
    c.box(-2, -1, -1, BAY * len(CHOICES) + 2, -1, 8, B.TUFF_SMOOTH.block)
    n = 0
    for i, (name, _) in enumerate(CHOICES):
        x0 = BAY * i
        _wall(c, x0)
        model = models[f"{lamps.PREFIX}cage_a" if name == "as_now" else f"{lamps.PREFIX}cage_a_{name}"]
        from artkit import models as M
        c.add_entity(x0 + 2.5, 3.5, -0.01, M.display(model))       # on the wall's south face, no turn
        n += 1
    sky.build(c, (0, 0, 0))
    c.entity_counts = {"props": n}
    return c


def write_pack(pack_dir):
    return materials.pack(pack_dir)


def shots():
    """Dead on (where the pause sign shows), and from three cells off at eye height."""
    out = []

    def shot(name, pos, look_at):
        out.append({"name": name, "pos": [round(v, 2) for v in pos], "look_at": [round(v, 2) for v in look_at],
                    "time": TIME})

    for i, (name, _) in enumerate(CHOICES):
        x = BAY * i + 2.5
        shot(f"{name}_dead", (x, 3.5, 4.0), (x, 3.5, 0.0))
        shot(f"{name}_eyelevel", (x + 3.0, 1.62, 4.4), (x, 3.6, 0.0))
    mid = BAY * (len(CHOICES) - 1) / 2.0 + 2.5
    shot("all_three", (mid, 3.6, 13.0), (mid, 3.4, 0.0))
    return out
