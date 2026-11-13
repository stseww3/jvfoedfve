"""Planting: trees, shrubs and ground cover, plus what hangs off the rim and the underside."""
import numpy as np

from artkit import noise as N
from artkit import trees as T
from artkit.canvas import hash3

from . import terrain

SEED = 7164


def _free_column(c, x, y, z, height=2):
    return all(not c.has(x, y + i, z) for i in range(height))


def plant_trees(c, land, plan):
    """plan: list of dicts {kind, x, z, height, ...}. Trees stand on the terrain at (x, z)."""
    for i, t in enumerate(plan):
        x, z = t["x"], t["z"]
        gy = land.y(x, z)
        if gy is None:
            continue
        y = gy + 1
        seed = SEED + 97 * i
        kind = t["kind"]
        if kind == "spruce":
            T.spruce(c, x, y, z, t["height"], seed, width=t.get("width", 1.0))
            for dx in range(-2, 3):
                for dz in range(-2, 3):
                    if land.kind.get((x + dx, z + dz)) in ("grass", "moss") and hash3(x + dx, 1, z + dz, seed) < 0.55:
                        c.set(x + dx, land.y(x + dx, z + dz), z + dz, "podzol" if hash3(x + dx, 2, z + dz, seed) < 0.7 else "coarse_dirt")
                        land.kind[(x + dx, z + dz)] = "duff"
        elif kind == "cherry":
            T.broadleaf(c, x, y, z, t["height"], t["spread"], seed, log="cherry_log",
                        leaves=T.leaf_mix("cherry_leaves"), squash=0.5, lift=(0.2, 0.55), thick=t.get("thick", False),
                        hang=0.14, clumps=1.12)
        elif kind == "birch":
            T.birch(c, x, y, z, t["height"], seed)
        elif kind == "oak":
            T.broadleaf(c, x, y, z, t["height"], t["spread"], seed, log="oak_log",
                        leaves=T.leaf_mix("oak_leaves", "azalea_leaves", 0.12), squash=0.85, lift=(0.5, 0.95),
                        thick=t.get("thick", False), clumps=1.15)
        for dx in range(-1, 2):
            for dz in range(-1, 2):
                if land.kind.get((x + dx, z + dz)) in ("grass", "moss"):
                    land.kind[(x + dx, z + dz)] = "trunk"


def petals(c, land, x0, z0, radius, seed):
    """Fallen petals under a blossoming tree."""
    for x in range(x0 - radius, x0 + radius + 1):
        for z in range(z0 - radius, z0 + radius + 1):
            d = np.hypot(x - x0, z - z0) / radius
            if d > 1 or land.kind.get((x, z)) not in ("grass", "moss", "path"):
                continue
            y = land.y(x, z) + 1
            h = hash3(x, 5, z, seed)
            if h < 0.5 * (1 - d * 0.8) and _free_column(c, x, y, z, 1):
                amount = 1 + int(hash3(x, 6, z, seed) * 4)
                facing = ("north", "east", "south", "west")[int(hash3(x, 7, z, seed) * 4)]
                c.set(x, y, z, f"pink_petals[flower_amount={amount},facing={facing}]")


FLOWER_ZONES = [
    ["poppy", "poppy", "dandelion"],
    ["oxeye_daisy", "azure_bluet", "oxeye_daisy"],
    ["cornflower", "allium", "cornflower"],
    ["dandelion", "oxeye_daisy", "wildflowers"],
    ["allium", "pink_tulip", "lilac"],
]


def ground_cover(c, land):
    xs = np.arange(terrain.X0, terrain.X1 + 1)
    zs = np.arange(terrain.Z0, terrain.Z1 + 1)
    Xg, Zg = np.meshgrid(xs, zs, indexing="ij")
    dens = 0.5 + 0.5 * N.fbm2(Xg * 0.09, Zg * 0.09, SEED, octaves=2)
    patch = N.perlin2(Xg * 0.12, Zg * 0.12, SEED + 1)
    zone = N.perlin2(Xg * 0.035, Zg * 0.035, SEED + 2)
    for (x, z), kind in list(land.kind.items()):
        y = land.y(x, z) + 1
        if not _free_column(c, x, y, z, 2):
            continue
        i, k = x - terrain.X0, z - terrain.Z0
        h = hash3(x, 11, z, SEED)
        h2 = hash3(x, 12, z, SEED)
        d = float(dens[i, k])
        if kind == "grass":
            if patch[i, k] > 0.22 and h < 0.34:
                zi = min(len(FLOWER_ZONES) - 1, int((float(zone[i, k]) + 1) * 0.5 * len(FLOWER_ZONES)))
                f = FLOWER_ZONES[zi][int(h2 * 3)]
                if f == "wildflowers":
                    c.set(x, y, z, f"wildflowers[flower_amount={1 + int(h2 * 97) % 4}]")
                elif f == "lilac":
                    c.set(x, y, z, "lilac[half=lower]")
                    c.set(x, y + 1, z, "lilac[half=upper]")
                else:
                    c.set(x, y, z, f)
            elif h < 0.34 + 0.30 * d:
                c.set(x, y, z, "short_grass")
            elif h < 0.38 + 0.36 * d:
                c.set(x, y, z, "fern")
            elif h < 0.40 + 0.40 * d:
                c.set(x, y, z, "tall_grass[half=lower]")
                c.set(x, y + 1, z, "tall_grass[half=upper]")
            elif h < 0.415 + 0.40 * d:
                c.set(x, y, z, "bush")
            elif h > 0.992:
                T.bush(c, x, y, z, SEED + x * 31 + z, T.leaf("oak_leaves"), size=1)
        elif kind == "moss":
            if h < 0.16:
                c.set(x, y, z, "short_grass")
            elif h < 0.26:
                c.set(x, y, z, "fern")
            elif h < 0.31:
                c.set(x, y, z, "azalea" if h2 < 0.6 else "flowering_azalea")
            elif h < 0.36:
                c.set(x, y, z, "small_dripleaf[half=lower,facing=north]")
                c.set(x, y + 1, z, "small_dripleaf[half=upper,facing=north]")
            elif h < 0.50:
                c.set(x, y, z, "moss_carpet")
        elif kind == "duff":
            if h < 0.22:
                c.set(x, y, z, "fern")
            elif h < 0.32:
                c.set(x, y, z, f"leaf_litter[segment_amount={1 + int(h2 * 4)}]")
            elif h < 0.36:
                c.set(x, y, z, "sweet_berry_bush[age=3]" if h2 < 0.5 else "large_fern[half=lower]")
                if h2 >= 0.5:
                    c.set(x, y + 1, z, "large_fern[half=upper]")
        elif kind == "rock":
            if h < 0.10:
                c.set(x, y, z, "moss_carpet")


BELLY_LIGHT = 10

WALL_FOR = {
    "stone": "cobblestone_wall", "cobblestone": "cobblestone_wall", "mossy_cobblestone": "mossy_cobblestone_wall",
    "andesite": "andesite_wall", "tuff": "tuff_wall", "deepslate": "cobbled_deepslate_wall",
    "cobbled_deepslate": "cobbled_deepslate_wall",
}


def underside(c, land):
    """Stalactite tips, hanging roots, vines down the flanks and hidden lights under the rock."""
    lows = {}
    for (x, y, z) in c.b:
        if (x, z) in land.top and y <= land.top[(x, z)]:
            cur = lows.get((x, z))
            if cur is None or y < cur:
                lows[(x, z)] = y
    for (x, z), y in lows.items():
        name = c.name(x, y, z)
        e = land.edge.get((x, z), 0)
        h = hash3(x, 21, z, SEED)
        # faint hidden light so the belly of the island is not a black hole; what really lights
        # it is the crystal (under.py)
        if x % 5 == (z // 5) % 2 * 2 and z % 5 == 0 and not c.has(x, y - 1, z):
            c.set(x, y - 1, z, f"light[level={BELLY_LIGHT}]")
            continue
        if name in ("dirt", "coarse_dirt", "rooted_dirt", "grass_block"):
            if h < 0.45 and not c.has(x, y - 1, z):
                c.set(x, y - 1, z, "hanging_roots")
            continue
        if name not in WALL_FOR:
            continue
        # is this column a local low point?
        deeper = sum(1 for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)) if lows.get((x + dx, z + dz), 999) < y)
        if deeper == 0 and h < 0.55:
            n = 1 + int(hash3(x, 22, z, SEED) * 3)
            for i in range(1, n + 1):
                if c.has(x, y - i, z):
                    break
                c.set(x, y - i, z, WALL_FOR[name])
        elif deeper <= 1 and h < 0.10:
            c.set(x, y - 1, z, WALL_FOR[name], keep=True)

    # vines on the upper flanks
    faces = (("north", 0, 1), ("south", 0, -1), ("west", 1, 0), ("east", -1, 0))
    for (x, z), ty in land.top.items():
        e = land.edge.get((x, z), 1)
        if e > 0.16:
            continue
        for face, dx, dz in faces:
            ax, az = x + dx, z + dz  # the air cell next to this column; the vine sticks to `face` there
            if (ax, az) in land.top:
                continue
            if hash3(ax, 31, az, SEED + len(face)) > 0.20:
                continue
            y = ty - 1 - int(hash3(ax, 32, az, SEED) * 3)
            if not c.has(x, y, z) or c.has(ax, y, az):
                continue
            length = 2 + int(hash3(ax, 33, az, SEED) * 7)
            for i in range(length):
                if c.has(ax, y - i, az):
                    break
                c.set(ax, y - i, az, f"vine[{face}=true]")


def rim_shrubs(c, land):
    """Leafy clumps spilling over the edge."""
    for (x, z), e in land.edge.items():
        if e > 0.05 or land.kind.get((x, z)) not in ("grass", "moss"):
            continue
        if hash3(x, 41, z, SEED) > 0.10:
            continue
        y = land.y(x, z) + 1
        if not _free_column(c, x, y, z, 2):
            continue
        leaves = T.leaf("azalea_leaves") if hash3(x, 42, z, SEED) < 0.5 else T.leaf("oak_leaves")
        T.bush(c, x, y, z, SEED + x * 17 + z, leaves, size=1)
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if (x + dx, z + dz) not in land.top and hash3(x + dx, 43, z + dz, SEED) < 0.7:
                c.set(x + dx, y - 1, z + dz, leaves, keep=True)
                if hash3(x + dx, 44, z + dz, SEED) < 0.5:
                    c.set(x + dx, y - 2, z + dz, leaves, keep=True)
