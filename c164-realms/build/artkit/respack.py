"""Resource pack pieces other than item models: repainted blocks and replaced vanilla textures."""
import copy
import fnmatch
import json
import os
import shutil

import numpy as np
from PIL import Image

FACES = ("down", "up", "north", "south", "west", "east")
SIDES = ("north", "south", "west", "east")


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


# ---- one vanilla block shown with other pictures, nothing it shares touched ---------------------------
# Many vanilla blocks share their model and texture files: every oxidized_* copper block with its
# waxed_ twin, the whole sandstone family through sandstone_top. Replacing such a file repaints all of
# them at once. redirect_block() repaints exactly one block instead: it rewrites that block's
# block-state file, and nothing else of the game's, so that every state shows a copy of its vanilla
# model with the pack's own pictures on it.

def full_ref(ref):
    return ref if ":" in ref else "minecraft:" + ref


def _write_json(pack_dir, rel, data):
    path = os.path.join(pack_dir, *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(json.dumps(data, separators=(",", ":")))      # dumps, not dump: many times faster
    return rel


def flat_model(assets, ref):
    """A model of the game in one piece: what it inherits is folded in, and every face names the
    picture it shows instead of a texture variable.

    Returns {"ref", "elements", "particle", "flags", "ambientocclusion", "display", "gui_light"}.
    "elements" are copies of the file's boxes with each face's "texture" replaced by the full
    reference of the picture ("minecraft:block/sandstone_top"); None for a block the game draws by
    code (signs). "flags" holds what a model says about a picture besides its name, per reference:
    {"minecraft:block/yellow_stained_glass": {"force_translucent": True}}.
    """
    chain, seen, at = [], set(), full_ref(ref)
    while at and not at.partition(":")[2].startswith("builtin/"):
        if at in seen:
            raise ValueError(f"{ref}: the parents of this model form a circle")
        seen.add(at)
        ns, _, path = at.partition(":")
        data = assets.json(f"assets/{ns}/models/{path}.json")
        if data is None:
            raise FileNotFoundError(f"{ref}: the game has no model {at}")
        chain.append(data)
        at = full_ref(data["parent"]) if "parent" in data else None

    textures, display = {}, {}
    for data in reversed(chain):                    # the root first, so that children overrule it
        textures.update(data.get("textures", {}))
        display.update(data.get("display", {}))

    def first(key, default=None):
        return next((data[key] for data in chain if key in data), default)

    flags = {}

    def resolve(name):
        own = {}
        for _ in range(32):
            if isinstance(name, dict):              # 26.x: {"sprite": ..., "force_translucent": true}
                own.update({k: v for k, v in name.items() if k != "sprite"})
                name = name["sprite"]
            if not name.startswith("#"):
                name = full_ref(name)
                if own:
                    flags.setdefault(name, {}).update(own)
                return name
            if name[1:] not in textures:
                raise KeyError(f"{ref}: nothing is assigned to the texture variable {name}")
            name = textures[name[1:]]
        raise ValueError(f"{ref}: its texture variables refer to each other in a circle")

    elements = first("elements")
    if elements is not None:
        elements = copy.deepcopy(elements)
        for el in elements:
            for key in [k for k in el if k.startswith("__")]:       # "__comment"
                del el[key]
            for face in el["faces"].values():
                face["texture"] = resolve(face["texture"])
    return {
        "ref": full_ref(ref), "elements": elements,
        "particle": resolve("#particle") if "particle" in textures else None,
        "flags": flags, "ambientocclusion": bool(first("ambientocclusion", True)),
        "display": display, "gui_light": first("gui_light"),
    }


def state_models(state):
    """Every "apply" of a block-state file, and the models they name, in the file's order."""
    applies = list(state["variants"].values()) if "variants" in state else [p["apply"] for p in state["multipart"]]
    refs = []
    for apply in applies:
        for a in apply if isinstance(apply, list) else [apply]:
            if full_ref(a["model"]) not in refs:
                refs.append(full_ref(a["model"]))
    return applies, refs


def block_pictures(assets, block):
    """The pictures a vanilla block shows: {reference: the faces it is on}, "particle" among them.
    Face names are the model's own (before the block state turns it)."""
    state = assets.json(f"assets/minecraft/blockstates/{block}.json")
    if state is None:
        raise FileNotFoundError(f"the game has no block state file for {block}")
    out = {}
    for ref in state_models(state)[1]:
        flat = flat_model(assets, ref)
        for el in flat["elements"] or []:
            for name, face in el["faces"].items():
                out.setdefault(face["texture"], set()).add(name)
        if flat["particle"]:
            out.setdefault(flat["particle"], set()).add("particle")
    return out


def _rule(rule, face):
    """The picture a mapping names for one face. A plain name stands for every face."""
    if rule is None or isinstance(rule, str):
        return rule
    group = "side" if face in SIDES else "end" if face in ("up", "down") else None
    for key in (face, group, "side" if face == "particle" else None, "*"):
        if key is not None and key in rule:
            return rule[key]
    raise KeyError(face)


def _numbered(pack_dir, ns, name):
    """How many pictures <name>0, <name>1, ... the pack holds; 0 when it holds the one picture <name>."""
    folder = os.path.join(pack_dir, "assets", ns, "textures", "block")
    n = 0
    while os.path.isfile(os.path.join(folder, *f"{name}{n}.png".split("/"))):
        n += 1
    if n == 0 and not os.path.isfile(os.path.join(folder, *f"{name}.png".split("/"))):
        raise FileNotFoundError(f"the pack has no picture {ns}:block/{name} (nor {name}0, {name}1, ...); "
                                "write the pictures before redirecting a block to them")
    return n


def redirect_block(pack_dir, assets, block, textures, *, variants=None, weights=None, ns="c164", emit=0,
                   shade=True, ao=None, edit=None, keep=(), protect=("waxed_*",)):
    """Show one vanilla block with the pack's own pictures and leave everything it shares alone.

    The block's block-state file is rewritten: every state keeps its turns (x, y, uvlock) and its
    conditions, and shows a copy of the vanilla model, written to assets/<ns>/models/block/<block>/,
    whose faces show the pictures named here. No vanilla model or texture file is written, so blocks
    that share them (the waxed_ twin, the rest of the sandstone family) stay as the game draws them.
    All of it is read from the game's files; nothing about a block is assumed.

    assets    artkit.gameassets.Assets of the client jar alone. Not of the pack being written: a
              second run would then read the first run's output as if it were the game's.
    textures  {vanilla texture reference: name}: wherever a model of the block shows that picture
              it shows assets/<ns>/textures/block/<name>.png instead. Instead of a name, a dict
              picks by face: {"up": a, "down": a, "side": b}. Keys are the model's own face names
              (before the block state turns it), "side" for the four around, "end" for up and
              down, "particle", and "*" for the rest. None instead of a name keeps the game's picture.
              A picture of the block that is missing here is an error, not a silent leftover.
    variants  how many versions of each state the game mixes by position. Version v shows
              <name><v> where the pack holds numbered pictures <name>0, <name>1, ... (counted
              round where a name has fewer), else <name>. Default: the most any of the names has.
    weights   one weight per version; default all equal.
    emit      light_emission for every box: a level, or a function of the vanilla model reference
              ("minecraft:block/oxidized_copper_bulb_lit") that returns one. The boxes are drawn
              that bright; they do not light the world.
    shade     False takes the game's fixed shading by direction (top 1.0, north and south 0.8,
              east and west 0.6, bottom 0.5) off every box: each face is lit like the top one.
              For a surface that is a light itself, or that carries its own painted shading.
              (26.x has no "shade": false; the boxes get "shade_direction_override": "up".)
              Like emit, a function of the model reference may decide.
    ao        False turns the darkening of corners off as well; None leaves it as the game's
              model has it.
    edit      edit(reference, model) may change a model before it is mapped, in place or by
              returning another: `model` is what flat_model() gives. A face it points at
              "<ns>:block/<name>" shows that picture of the pack.
    keep      vanilla texture references that stay as they are.
    protect   block ids (shell patterns) this function refuses to touch, and that may not appear in
              any path it writes. The default is the rule of the copper family: waxed_ is verdigris
              and stays vanilla.

    The pictures must already be in the pack. Returns {"block", "variants", "models", "files",
    "pictures"}; "files" are the paths written, relative to the pack.
    """
    if any(fnmatch.fnmatchcase(block, p) for p in protect):
        raise ValueError(f"{block} is protected ({', '.join(protect)}): it stays as the game draws it")
    vanilla = assets.json(f"assets/minecraft/blockstates/{block}.json")
    if vanilla is None:
        raise FileNotFoundError(f"the game has no block state file for {block}")
    state = copy.deepcopy(vanilla)
    rules = {full_ref(k): v for k, v in textures.items()}
    keep = {full_ref(k) for k in keep}
    refs = state_models(state)[1]

    # 1. every model in one piece, its faces sorted into slots: one slot per picture it will show
    models = []
    for ref in refs:
        flat = flat_model(assets, ref)
        if edit is not None:
            flat = edit(ref, flat) or flat
        slots = {}                                  # (ours?, name or reference, flags) -> texture variable

        def slot(face, shown, flat=flat, slots=slots, ref=ref):
            if shown.startswith(f"{ns}:block/"):
                ours, name = True, shown[len(ns) + 7:]
            elif shown in rules:
                try:
                    name = _rule(rules[shown], face)
                except KeyError:
                    raise KeyError(f"{block}: the map for {shown} names no picture for the {face} face "
                                   f"(model {ref})") from None
                ours = name is not None
                name = name if ours else shown
            elif shown in keep:
                ours, name = False, shown
            else:
                raise KeyError(f"{block}: model {ref} shows {shown} on its {face} face, "
                               "and the map does not say what to show instead")
            key = (ours, name, tuple(sorted(flat["flags"].get(shown, {}).items())))
            if key not in slots:
                stem = ("" if ours else "game_") + name.rpartition("/")[2]
                var, n = stem, 1
                while var == "particle" or var in slots.values():
                    n += 1
                    var = f"{stem}_{n}"
                slots[key] = var
            return slots[key]

        level = int(emit(ref) if callable(emit) else emit)
        shaded = bool(shade(ref) if callable(shade) else shade)
        for el in flat["elements"] or []:
            for name, face in el["faces"].items():
                face["texture"] = "#" + slot(name, face["texture"])
            if level:
                el["light_emission"] = level
            if not shaded:
                el.pop("shade", None)
                el["shade_direction_override"] = "up"
        particle = "#" + slot("particle", flat["particle"]) if flat["particle"] else None
        models.append((ref, flat, slots, particle))

    # 2. how many versions: as many as the pictures have
    count = {}
    for _, _, slots, _ in models:
        for ours, name, _ in slots:
            if ours:
                count[name] = _numbered(pack_dir, ns, name)
            else:
                game_ns, _, path = name.partition(":")
                if assets.read(f"assets/{game_ns}/textures/{path}.png") is None:
                    raise FileNotFoundError(f"{block}: the game has no picture {name} to keep")
    n = int(variants) if variants else max([1] + list(count.values()))
    if weights is not None and len(weights) != n:
        raise ValueError(f"{block}: {len(weights)} weights for {n} versions")

    # 3. the copies. The folder is this block's alone; what an earlier run left in it goes.
    folder = f"assets/{ns}/models/block/{block}"
    shutil.rmtree(os.path.join(pack_dir, *folder.split("/")), ignore_errors=True)
    written, copies, pictures, stems = [], {}, set(), set()
    for ref, flat, slots, particle in models:
        stem = ref.partition(":")[2]
        stem = (stem[6:] if stem.startswith("block/") else stem).replace("/", "_")
        while stem in stems:
            stem += "_"
        stems.add(stem)
        copies[ref] = []
        for v in range(n):
            shown = {}
            for (ours, name, flags), var in slots.items():
                pic = name if not ours else f"{ns}:block/{name}{v % count[name]}" if count[name] else f"{ns}:block/{name}"
                if ours:
                    pictures.add(pic)
                shown[var] = dict(flags, sprite=pic) if flags else pic
            if particle:
                shown["particle"] = particle
            data = {}
            if not flat["ambientocclusion"] or ao is False:
                data["ambientocclusion"] = False
            if flat["gui_light"]:
                data["gui_light"] = flat["gui_light"]
            if flat["display"]:
                data["display"] = flat["display"]
            data["textures"] = shown
            if flat["elements"] is not None:
                data["elements"] = flat["elements"]
            name = stem + (f"_v{v}" if n > 1 else "")
            written.append(_write_json(pack_dir, f"{folder}/{name}.json", data))
            copies[ref].append(f"{ns}:block/{block}/{name}")

    # 4. the block state file: the same states, turns and conditions, each showing the copies
    def versions(apply):
        out = []
        for a in apply if isinstance(apply, list) else [apply]:
            for v in range(n):
                b = dict(a, model=copies[full_ref(a["model"])][v])
                if weights is not None:
                    b["weight"] = int(a.get("weight", 1)) * int(weights[v])
                out.append(b)
        return out[0] if len(out) == 1 else out

    if "variants" in state:
        state["variants"] = {key: versions(apply) for key, apply in state["variants"].items()}
    else:
        for part in state["multipart"]:
            part["apply"] = versions(part["apply"])
    written.append(_write_json(pack_dir, f"assets/minecraft/blockstates/{block}.json", state))

    # 5. the promise, checked on what was written rather than on what was meant
    for rel in written:
        if rel != f"assets/minecraft/blockstates/{block}.json" and not rel.startswith(folder + "/"):
            raise AssertionError(f"{block}: wrote {rel}, which is neither its block state nor its own model folder")
        for part in rel.split("/"):
            if any(fnmatch.fnmatchcase(part.partition(".")[0], p) for p in protect):
                raise AssertionError(f"{block}: wrote {rel}, which is protected ({', '.join(protect)})")
    if "variants" in vanilla:
        same = list(vanilla["variants"]) == list(state["variants"])
    else:
        same = [p.get("when") for p in vanilla["multipart"]] == [p.get("when") for p in state["multipart"]]
    if not same:
        raise AssertionError(f"{block}: the rewritten block state file does not have the game's states")
    for old, new in zip(state_models(vanilla)[0], state_models(state)[0]):
        old = old if isinstance(old, list) else [old]
        new = new if isinstance(new, list) else [new]
        turns = [{k: v for k, v in a.items() if k not in ("model", "weight")} for a in old for _ in range(n)]
        if turns != [{k: v for k, v in b.items() if k not in ("model", "weight")} for b in new]:
            raise AssertionError(f"{block}: a state lost its turn (x, y, uvlock)")
    return {"block": block, "variants": n, "models": len(models), "files": written, "pictures": sorted(pictures)}
