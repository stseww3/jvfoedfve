"""Sky observatory: an original floating-island scene used to test how far scripted art can go.

Seen from the south the story reads left to right: airship and dock at the west tip, a path past
the cherry tree and the keeper's house, then the stair up the crag to the observatory. A pond in
front of the crag drains over the southern rim.
"""
from artkit import respack
from artkit.canvas import Canvas

from . import flora, house, instruments, props, site, sky, terrain, tower

TOWER = (20.0, -12.0)
HOUSE = (-19, -7, 3, 11)   # x0, x1, z0, z1
GARDEN = (-3, 3, 4, 9)     # x0, z0, x1, z1
POND = (22.0, 24.0, 5.2, 4.0)
BIOME = "skyobs"           # one of mood.BIOMES
BIOME_MARGIN = 40          # the look has to reach every camera position, not only the blocks
BIOME_MARGIN_Y = 110
GROUND = 1                 # y of the ground blocks on the levelled parts


def write_pack(pack_dir):
    """Resource pack pieces besides the prop models: the sky, and blocks painted for this scene."""
    out = sky.write_pack(pack_dir)
    out.append(respack.cube_variants(pack_dir, instruments.VAULT, instruments.vault_tiles(), name="star_vault"))
    return out

TREES = [
    {"kind": "cherry", "x": -33, "z": -5, "height": 13, "spread": 9, "thick": True},
    {"kind": "cherry", "x": -27, "z": 24, "height": 8, "spread": 5},
    {"kind": "spruce", "x": -44, "z": -14, "height": 18},
    {"kind": "spruce", "x": -24, "z": -23, "height": 24},
    {"kind": "spruce", "x": -15, "z": -27, "height": 19},
    {"kind": "spruce", "x": -6, "z": -29, "height": 27},
    {"kind": "spruce", "x": 3, "z": -24, "height": 16},
    {"kind": "spruce", "x": 41, "z": -4, "height": 22},
    {"kind": "spruce", "x": 38, "z": 6, "height": 15},
    {"kind": "spruce", "x": 45, "z": 12, "height": 12},
    {"kind": "birch", "x": 32, "z": 17, "height": 10, "spread": 4},
    {"kind": "birch", "x": 14, "z": 34, "height": 8, "spread": 3},
    {"kind": "oak", "x": 2, "z": 32, "height": 14, "spread": 8, "thick": True},
    {"kind": "oak", "x": -40, "z": 16, "height": 9, "spread": 5},
]


def build():
    c = Canvas()
    hx0, hx1, hz0, hz1 = HOUSE
    gx0, gz0, gx1, gz1 = GARDEN
    px, pz, prx, prz = POND
    pads = [
        (hx0 - 3, hz0 - 3, hx1 + 3, hz1 + 5, GROUND, 5.0),
        (gx0 - 1, gz0 - 1, gx1 + 1, gz1 + 1, GROUND, 3.0),
        (px - prx - 2, pz - prz - 2, px + prx + 2, pz + prz + 2, GROUND, 5.0),
        (16, 8, 24, 16, GROUND, 4.0),
        (-56, -3, -40, 5, GROUND, 4.0),
    ]
    land = terrain.build(c, pads)
    flora.underside(c, land)

    tower.build(c, land, TOWER[0], TOWER[1], terrain.KNOLL_H + 1)
    foot_z = site.grand_stair(c, land, 18, 21, -1, terrain.KNOLL_H, GROUND)
    roof = house.build(c, land, hx0, hx1, hz0, hz1, GROUND + 1)
    site.garden(c, land, gx0, gz0, gx1, gz1, GROUND)

    # the rim at the west tip decides where the dock goes
    rim_x = min(x for (x, z) in land.top if -1 <= z <= 3)
    dock_out = rim_x - 7
    site.dock(c, land, rim_x + 9, dock_out, 1, 2, GROUND)
    site.airship(c, dock_out - 6, GROUND, 1)
    c.set(dock_out - 1, GROUND, 1, "spruce_slab[type=top]")
    # mooring lines from the two outer dock posts to the after rail of the car
    for side in (-1, 1):
        props.stretch(c, "rope", (dock_out + 0.5, GROUND + 2.6, 1.5 + 2 * side),
                      (dock_out - 2.5, GROUND + 3.0, 1.5 + side), thick=1.5)

    site.pond(c, land, px, pz, prx, prz, GROUND, [(25.0, 26.5), (28.0, 29.5), (34.0, 35.5)])

    door_x = hx0 + 4
    main = [(rim_x + 9, 1.5), (-34, 6), (-24, 14), (door_x + 0.5, 15), (-4, 15.5), (8, 14.5),
            (17, foot_z + 2.5), (19.5, foot_z + 0.5)]
    site.path(c, land, main, width=3.2, seed=1)
    site.path(c, land, [(door_x + 0.5, 15), (door_x + 0.5, hz1 + 1)], width=2.0, seed=2)
    site.path(c, land, [(19.5, foot_z + 1), (20.5, 18.5)], width=2.0, seed=3)
    site.path(c, land, [(0, 15), (0, 10.5)], width=1.6, seed=4)
    for x, z in ((-40, 6), (-27, 10), (-9, 18), (6, 12), (13, 18)):
        site.lamp(c, land, x, z, toward=site.nearest_on(main, x + 0.5, z + 0.5))
    site.lamp(c, land, 25, 16, toward=(21.0, 16.5))

    # custom-model dressing: fingerpost at the fork, shop sign and weathervane on the house,
    # armillary sphere where the stair starts
    site.reserve(c, land, -12, 17)
    props.place(c, "signpost", -11.5, GROUND + 1, 17.5)
    props.place(c, "sign_board", hx1 + 1.0, GROUND + 4.9, hz1 - 0.5)
    props.place(c, "weathervane", hx1 - 1.5, roof["ridge_y"], roof["ridge_z"], brightness=(15, 0))
    top = site.pedestal(c, land, 25, 11)
    props.place(c, "armillary", 25.5, top, 11.5)
    props.place(c, "armillary_core", 25.5, top + 2.0, 11.5, turns=(("z", 23.5),))
    site.woodpile(c, hx1 + 1, GROUND + 1, hz0 + 2)
    c.set(door_x + 2, GROUND + 1, hz1 + 1, "barrel[facing=up]")
    c.set(door_x + 3, GROUND + 1, hz1 + 1, "barrel[facing=up]")
    c.set(door_x + 3, GROUND + 2, hz1 + 1, "barrel[facing=south]")
    by = land.y(-30, 4)
    if by is not None:
        site.bench(c, -31, by + 1, 4, 3, "north")
        for x in (-31, -30, -29):
            land.kind[(x, 4)] = "built"

    flora.plant_trees(c, land, TREES)
    site.boulders(c, land, seed=5)
    flora.petals(c, land, -33, -5, 10, 5)
    flora.petals(c, land, -27, 24, 6, 6)
    flora.rim_shrubs(c, land)
    flora.ground_cover(c, land)

    site.islet(c, -72, -4, -34, 6.5, 13, 801, tree=("spruce", 13))
    site.islet(c, 66, -12, 34, 5.0, 10, 802, tree=("birch", 7))
    site.islet(c, 74, 4, -24, 3.6, 7, 803)
    site.islet(c, -50, -22, 44, 3.0, 6, 804)

    sky.build(c)
    return c
