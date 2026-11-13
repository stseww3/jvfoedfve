"""Resource pack pieces other than item models: repainted blocks and replaced vanilla textures."""
import json
import os

import numpy as np
from PIL import Image

FACES = ("down", "up", "north", "south", "west", "east")


def _save(path, pixels):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    a = np.asarray(pixels, dtype=np.uint8)
    Image.fromarray(a, "RGBA" if a.shape[2] == 4 else "RGB").save(path)


def texture(pack_dir, name, pixels, ns="minecraft", meta=None):
    """Write assets/<ns>/textures/<name>.png, e.g. name = "environment/celestial/sun".

    meta goes into the .png.mcmeta beside it. A replaced vanilla picture does not keep the vanilla
    one's: the game only reads the file that lies in the same pack as the picture.
    """
    path = os.path.join(pack_dir, "assets", ns, "textures", name + ".png")
    _save(path, pixels)
    if meta:
        with open(path + ".mcmeta", "w") as fh:
            json.dump(meta, fh, separators=(",", ":"))
    return f"{ns}:{name}"


def cube_variants(pack_dir, block, variants, name=None, ns="c164", parent="minecraft:block/cube_all", meta=None):
    """Repaint a vanilla full-cube block with several pictures that the game mixes by position.

    variants: [(pixels, weight), ...]. Only for blocks whose vanilla block state file has a single
    entry for all states: the file is replaced by one that lists a model per picture.
    parent = the vanilla model the pictures go on ("minecraft:block/leaves" for foliage), meta =
    what to write into each picture's .mcmeta.
    """
    name = name or block
    choices = []
    for n, (pixels, weight) in enumerate(variants):
        tex = texture(pack_dir, f"block/{name}{n}", pixels, ns, meta=meta)
        path = os.path.join(pack_dir, "assets", ns, "models", "block", f"{name}{n}.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            json.dump({"parent": parent, "textures": {"all": tex}}, fh, separators=(",", ":"))
        choices.append({"model": f"{ns}:block/{name}{n}", "weight": weight})
    path = os.path.join(pack_dir, "assets", "minecraft", "blockstates", block + ".json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump({"variants": {"": choices}}, fh, separators=(",", ":"))
    return f"{block} -> {len(choices)} pictures of {name}"


def cube(pack_dir, block, pixels, name=None, ns="c164", shade=True, ao=True):
    """Repaint a vanilla full-cube block: all six faces show `pixels`.

    shade=False drops the engine's fixed face shading (top brightest, sides darker) and ao=False the
    corner darkening, so the block shows exactly the painted colour times the light level. That is
    what lets a generator bake its own shading into a surface made of several such blocks.
    (26.x has no "shade": false any more; every face is told to shade like the top face instead.)
    """
    name = name or block
    tex = texture(pack_dir, "block/" + name, pixels, ns)
    element = {"from": [0, 0, 0], "to": [16, 16, 16],
               "faces": {f: {"texture": "#all", "cullface": f} for f in FACES}}
    if not shade:
        element["shade_direction_override"] = "up"
    model = {"textures": {"all": tex, "particle": tex}, "elements": [element]}
    if not ao:
        model["ambientocclusion"] = False
    path = os.path.join(pack_dir, "assets", "minecraft", "models", "block", block + ".json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(model, fh, separators=(",", ":"))
    return f"{block} -> {tex}"
