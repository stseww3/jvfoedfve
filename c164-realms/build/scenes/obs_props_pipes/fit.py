"""obs_props_pipes: what the pictures cannot be trusted to show.

    python -m scenes.obs_props_pipes.fit            (in build/)
    python -m scenes.obs_props_pipes.fit --master   what the family places in the master scene
                                                    (builds the whole of obs: on a node only)

The game lights a face of an item model by the model axis nearest to its normal, and of two axes
that are equally near the last bit of a float decides. A picture drawn here and the game may then
disagree, and two sister models may be lit differently. props/pipes leans such faces half a degree
(pipes._settle); this holds every model of the family to it, and says how each face is filed by the
renderer's single-precision copy of the game's code against the exact rule.
"""
import json
import os
import sys
import tempfile

from artkit import gameassets as G
from artkit import models as M
from scenes.obs.props import pipes

FILED = ("down", "up", "north", "south", "west", "east")       # the order the game tries them in
LETTER = {"d": 0, "u": 1, "n": 2, "s": 3, "w": 4, "e": 5}


def _exact(normal):
    along = (-normal[1], normal[1], -normal[2], normal[2], -normal[0], normal[0])
    best = max(along)
    return next(i for i, v in enumerate(along) if best - v < 1e-9)


def faces():
    """[(model, part, face letter, the axis it is filed under, the axis exact numbers give)] for
    every drawn face that is filed otherwise than exact numbers would, and the count of all faces."""
    out, count = [], 0
    with tempfile.TemporaryDirectory() as tmp:
        for name, model in sorted(pipes.models().items()):
            model.export(tmp)
            with open(os.path.join(tmp, "assets", "c164", "models", "item", name + ".json")) as fh:
                elements = json.load(fh)["elements"]
            for i, (part, element) in enumerate(zip(model.parts, elements)):
                filed = G.quad_directions(element["from"], element["to"], element.get("rotation"))
                q = part["rot"][0] if part["rot"] else M.IDENT
                for letter, k in LETTER.items():
                    if letter in part["skip"]:
                        continue
                    count += 1
                    exact = _exact(M._qrot(q, M.NORMAL[letter]))
                    if filed[k] != exact:
                        out.append((name, i, letter, FILED[filed[k]], FILED[exact]))
    return out, count


def master():
    """What the family places in the master scene (heavy: the whole of obs is built; on a node
    only): the count of each piece, and where the pieces stand that say a line is there."""
    import collections

    from scenes import obs

    canvas = obs.build()
    count = collections.Counter()
    for x, y, z, nbt in canvas.entities:
        name = str(nbt.get("item", {}).get("components", {}).get("minecraft:item_model", ""))
        if pipes.PREFIX not in name:
            continue
        kind = name.split(pipes.PREFIX)[1]
        count[kind] += 1
        if kind.startswith(("down_hopper", "drain_head", "valve", "bonnet", "gauge")):
            print(f"  {kind:18s} at ({x:.2f}, {y:.2f}, {z:.2f})")
    print(f"the master scene: {sum(count.values())} pieces of the family of {len(canvas.entities)} display entities; "
          + ", ".join(f"{k} {n}" for k, n in sorted(count.items())))
    print(f"  the lines' counts: {getattr(canvas, 'entity_counts', None)}")
    return 0


def main():
    if "--master" in sys.argv[1:]:
        return master()
    found = []
    models = pipes.models()
    for name, model in sorted(models.items()):
        for i, letters, normal in pipes.unsettled(model):
            found.append(f"{name}: part {i}, faces {letters} stand between two axes "
                         f"({normal[0]:.4f}, {normal[1]:.4f}, {normal[2]:.4f})")
    wrong, count = faces()
    for name, i, letter, filed, exact in wrong:
        found.append(f"{name}: part {i}, face {letter} is filed under {filed}, exact numbers give {exact}")
    print(f"{len(models)} models, {sum(len(m.parts) for m in models.values())} parts, {count} drawn faces: "
          + ("nothing found" if not found else f"{len(found)} found"))
    for line in found:
        print("  " + line)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
