"""Test scene of the work package materials/iron (plan/packages/materials/iron.md).

What it is for: to see the cast iron of every oxidized_* copper block that has no waxed_ twin, and
to see that the waxed_oxidized_* twin beside it stays verdigris. The twin stations set each repainted
block next to the vanilla block it shares its model and texture files with -- cast iron beside
verdigris, old copper beside exposed copper -- in every shape the family has, so a glance confirms
the split, and the two lamps (the caged bulb, the lantern) show their glow. Two eight-by-eight walls,
the riveted plate (with its stairs and slabs at the foot) and the plain plate, are there to be read
close for the rivets and seams and from twenty blocks for stripes (c190's pre-review, point 3): a
bolted run must not tile into continuous diagonal lines or evenly spaced bars, and the plate face
must keep enough light and dark.

The gallery shows the thin pieces at work, the way the dome's gallery uses them: a wall of riveted
plate with a door in it, a floor of gratings in front, a railing round the floor, thin pipes and
rods. It is there for what the second delivery changed and only a picture can settle: whether the
railing is of one tone with the plates behind it, whether a floor of gratings reads as one mesh
with the ground seen through it, whether the door's porthole meets the eye of someone standing in
front of it, and whether pipe, rod and railing can still be made out from twenty blocks.

The balustrade shows the hatch a run at a time, the way the buildings use it: on edge as the panels
of a balustrade, lying one above the other as the blades of a louvre. It is there to see that every
panel and every blade is the same lid, and that a standing one is lit from above like the plate it
stands on.

    python -m scenes.obs_mat_iron        writes shots.json from the layout below
"""
from artkit.blocks import st
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.materials import _board

BIOME = "obs_blue"
Z = 0
TIME = 14000        # the default light version (sky line)


def walls(c, x, z):
    """Two eight-by-eight walls for the stripe check: the riveted plate (with its stairs and slabs at
    the foot) and the plain plate, a gap between them."""
    _board.wall(c, B.IRON_RIVETED, x, 0, z)             # x..x+7, its stairs and slabs at z+1
    _board.wall(c, B.IRON_PLATE, x + 10, 0, z)          # x+10..x+17
    _board.stage(c, x, x + 17, z, height=9)
    return x + 19


GALLERY_WIDE = 9        # the wall behind the gallery: x .. x + 8
GALLERY_TOP = 6         # ... and y 0 .. 6
GALLERY_Y = 2           # the gratings' y; one stands on y = 3
GALLERY_DEEP = 4        # the floor of gratings: z + 1 .. z + 4, the railing on its outer blocks
EYE = 1.62              # a player's eye above the block stood on


def gallery(c, x, z):
    """A wall of riveted plate with a door, a window of bars two high, a band of cast plates and a
    vent in it; before it a floor of gratings with a railing on three sides, standing on two thin
    pipes; a thin pipe up the whole wall and two rods on its top."""
    x1 = x + GALLERY_WIDE - 1
    walk = GALLERY_Y + 1                                # the y one stands on: the door's, the railing's
    door_x = x + GALLERY_WIDE // 2
    _board.stage(c, x, x1, z, height=GALLERY_TOP + 1)
    c.box(x, 0, z, x1, GALLERY_TOP, z, B.IRON_RIVETED.block)
    for dy, half in ((0, "lower"), (1, "upper")):
        c.set(door_x, walk + dy, z, st(B.IRON_DOOR, facing="north", half=half, hinge="left"))
    c.box(door_x - 2, walk + 2, z, door_x + 2, walk + 2, z, B.IRON_CAST)
    c.box(door_x + 2, walk, z, door_x + 3, walk + 1, z, st(B.IRON_BARS, east="true", west="true"))
    c.set(x + 2, 0, z, B.IRON_GRATE)                    # the vent, at the wall's foot
    # the floor of gratings, the railing on its outer blocks
    fx0, fx1, fz1 = x + 1, x1 - 1, z + GALLERY_DEEP
    c.box(fx0, GALLERY_Y, z + 1, fx1, GALLERY_Y, fz1, B.IRON_GRATE)
    c.box(fx0 + 1, walk, fz1, fx1 - 1, walk, fz1, st(B.IRON_BARS, east="true", west="true"))
    c.set(fx0, walk, fz1, st(B.IRON_BARS, east="true", north="true"))
    c.set(fx1, walk, fz1, st(B.IRON_BARS, west="true", north="true"))
    for bx in (fx0, fx1):
        c.box(bx, walk, z + 1, bx, walk, fz1 - 1, st(B.IRON_BARS, north="true", south="true"))
        c.box(bx, 0, fz1, bx, GALLERY_Y - 1, fz1, st(B.IRON_PIPE, axis="y"))    # what the floor stands on
    c.box(x, 0, z + 1, x, GALLERY_TOP, z + 1, st(B.IRON_PIPE, axis="y"))
    for bx in (fx0, fx1):
        c.box(bx, GALLERY_TOP + 1, z, bx, GALLERY_TOP + 2, z, st(B.IRON_ROD, facing="up"))
    return x1 + 2


RAIL_WIDE = 8           # the balustrade: so many hatches on edge, x .. x + 7
BLADES = 4              # the louvre beside it: so many lying hatches one above the other, two wide


def balustrade(c, x, z):
    """Eight hatches on edge in a row along the far side of a course of riveted plate, seen across
    its top the way the panels of the ring stair are seen from the treads; and beside it a louvre
    as the belfry has it, lying hatches one above the other between two posts."""
    x1 = x + RAIL_WIDE - 1
    c.box(x, 0, z, x1, 0, z, B.IRON_RIVETED.block)
    # a standing hatch stands on the side it turns its back to: these on the north, away from the viewer
    c.box(x, 1, z, x1, 1, z, st(B.IRON_HATCH, facing="south", half="bottom", open="true"))
    post0, post1 = x1 + 2, x1 + 5
    for px in (post0, post1):
        c.box(px, 0, z, px, BLADES - 1, z, B.IRON_RIVETED.block)
    c.box(post0 + 1, 0, z, post1 - 1, BLADES - 1, z, st(B.IRON_HATCH, facing="south", half="bottom", open="false"))
    _board.stage(c, x, post1, z)
    return post1 + 2


STATIONS = [("plates", _board.twins_plates), ("shapes", _board.twins_shapes), ("walls", walls),
            ("gallery", gallery), ("balustrade", balustrade)]


def layout(c=None):
    """Where each station stands: {name: (first x, x after it)}. Builds into `c` when given one."""
    c = c or Canvas()
    spans, x = {}, 0
    for name, station in STATIONS:
        end = station(c, x, Z)
        spans[name] = (x, end)
        x = end + 2
    return spans


def build():
    c = Canvas()
    layout(c)
    return c


def build_models():
    return {}           # blocks only


def write_pack(pack_dir):
    # the sky's pack with the blocks': the scene stands in the map's hour, and without it the game's own sun is in the sky
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])


def shots():
    """Camera positions from the layout: the two twin rows in halves at reading distance (the split
    and the lamp glow), each eight-by-eight wall close (rivets, seams, brushing), the riveted treads
    from above, and both walls from twenty blocks (stripes); the gallery from the front, from the
    eye of someone standing before its door, from above down through the gratings, and from twenty
    blocks; the balustrade and its louvre at reading distance."""
    spans = layout()
    out = []

    def front(name, x0, x1, y=1.6):
        """Looking north at x0..x1 from as near as shows all of it."""
        d = max(5.0, (x1 - x0 + 2) / 2.6)
        out.append({"name": name, "pos": [(x0 + x1) / 2.0, y + 1.2, round(Z + 1 + d, 1)], "look_at": [(x0 + x1) / 2.0, y, Z], "time": TIME})

    for name in ("plates", "shapes"):                   # each row is wide: read it in halves
        x0, x1 = spans[name]
        x1 -= 2                                          # the station's own last x, without the gap
        mid = (x0 + x1) // 2
        front(f"{name}_a", x0, mid)
        front(f"{name}_b", mid, x1)
    xs = spans["shapes"][0]                              # the caged bulb (lit over unlit) and the lantern
    front("shapes_lamps", xs + 25, xs + 34)
    xw = spans["walls"][0]
    out.append({"name": "wall_riveted", "pos": [xw + 3.5, 4.6, Z + 8.5], "look_at": [xw + 3.5, 4.0, Z], "time": TIME})
    out.append({"name": "wall_plate", "pos": [xw + 13.5, 4.6, Z + 8.5], "look_at": [xw + 13.5, 4.0, Z], "time": TIME})
    out.append({"name": "wall_treads", "pos": [xw + 3.5, 4.2, Z + 4.6], "look_at": [xw + 3.5, 0.2, Z + 1.0], "time": TIME})
    out.append({"name": "walls_far", "pos": [xw + 8.5, 5.0, Z + 20.0], "look_at": [xw + 8.5, 4.0, Z], "time": TIME})
    mid = spans["gallery"][0] + GALLERY_WIDE / 2.0      # the middle of the door
    eye = round(GALLERY_Y + 1 + EYE, 2)
    out.append({"name": "gallery_front", "pos": [mid, 4.6, Z + 13.0], "look_at": [mid, 3.4, Z + 1.0], "time": TIME})
    out.append({"name": "gallery_door", "pos": [mid, eye, Z + 3.7], "look_at": [mid, eye, Z + 1.0], "time": TIME})
    out.append({"name": "gallery_floor", "pos": [mid, 8.0, Z + 8.0], "look_at": [mid, 2.5, Z + 2.5], "time": TIME})
    out.append({"name": "gallery_far", "pos": [mid, 5.0, Z + 21.0], "look_at": [mid, 4.0, Z + 1.0], "time": TIME})
    x0, x1 = spans["balustrade"]
    front("balustrade", x0, x1 - 2)
    return out
