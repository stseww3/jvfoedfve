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


def texture(pack_dir, name, pixels, ns="minecraft"):
    """Write assets/<ns>/textures/<name>.png, e.g. name = "environment/celestial/sun"."""
    _save(os.path.join(pack_dir, "assets", ns, "textures", name + ".png"), pixels)
    return f"{ns}:{name}"


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
