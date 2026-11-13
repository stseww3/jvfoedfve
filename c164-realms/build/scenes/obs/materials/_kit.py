"""What the material packages share: the game's files, painting into the pack, redirecting a block,
and the audit of what the category has written.

A package (a module of this folder) follows one pattern:

    BLOCKS = K.blocks(B.ASHLAR_FINE)                      # the blocks it paints; nobody else may

    def pack(pack_dir):
        K.paint(pack_dir, "ashlar_fine", [fine(seed) for seed in range(4)])     # ashlar_fine0..3
        K.paint(pack_dir, "ashlar_fine_top", fine_top())
        return [K.redirect(pack_dir, b, {"block/sandstone_top": {"end": "ashlar_fine_top", "side": "ashlar_fine"}})
                for b in BLOCKS]

paint() refuses a picture with a colour that is not in the palette; redirect() refuses a block that is
not in the occupancy table as repainted. Blocks no package has claimed are dressed by placeholder.py.
"""
import fnmatch
import io
import json
import os

import numpy as np
from PIL import Image

from artkit import respack
from artkit.gameassets import Assets

from ..common import blocks as B
from ..common import palette as P

NS = "c164"
TILE = 16                   # one block face is 16 pixels, on blocks and on models alike
# what stays as the game draws it: the vanilla half of the occupancy table, and verdigris in general
PROTECT = ("waxed_oxidized_*", "waxed_weathered_*") + tuple(B.ids(B.VANILLA))

_game = None


def jar():
    """The client jar: MC_JAR, or the one under MC_ROOT (as render.py and the job runner have it)."""
    path = os.environ.get("MC_JAR") or os.path.join(os.environ.get("MC_ROOT", "/agent/realms-study"),
                                                     "client26", "versions", "26.3", "26.3.jar")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"the materials need the game's files to redirect blocks, and there is no client "
                                f"jar at {path}; set MC_JAR or MC_ROOT")
    return path


def game():
    """The game's own files, and only those: what is redirected is always read from the vanilla
    game, never from a pack an earlier run has written."""
    global _game
    if _game is None:
        _game = Assets(jar())
    return _game


def blocks(*roles):
    """Block ids of roles of the occupancy table: families, single ids, tuples of ids."""
    out = []
    for role in roles:
        out += B.ids(role if isinstance(role, (list, tuple)) else [role])
    return out


def vanilla_picture(ref):
    """A picture of the game as (pixels, meta): RGBA with every frame of an animated one, and what
    its .mcmeta says (None without one)."""
    ns, _, path = respack.full_ref(ref).partition(":")
    raw = game().read(f"assets/{ns}/textures/{path}.png")
    if raw is None:
        raise FileNotFoundError(f"the game has no picture {ref}")
    return np.array(Image.open(io.BytesIO(raw)).convert("RGBA")), game().json(f"assets/{ns}/textures/{path}.png.mcmeta")


def paint(pack_dir, name, pictures, meta=None, allow=()):
    """Write block pictures into the pack: one array as <name>, a list of them as <name>0, <name>1, ...
    (the versions redirect() mixes by position). Returns the name.

    Every picture is checked: square with a side of 16 pixels or a multiple of it (a full face is
    always 16; a few of the game's models take theirs from a larger sheet), unless `meta` animates
    it (then frames stacked downwards), and no colour outside the palette. `allow` lists (r, g, b)
    colours let through; a colour the palette lacks is asked for in the group, not allowed here.
    """
    many = isinstance(pictures, (list, tuple))
    folder = os.path.join(pack_dir, "assets", NS, "textures", "block")
    for old in [name] + [f"{name}{i}" for i in range(64)]:           # what an earlier run wrote under this name
        for ext in (".png", ".png.mcmeta"):
            path = os.path.join(folder, *f"{old}{ext}".split("/"))
            if os.path.isfile(path):
                os.remove(path)
    if many and name[-1:].isdigit():
        raise ValueError(f"{name}: a name that ends in a digit cannot take numbered versions")
    for i, px in enumerate(pictures if many else [pictures]):
        label = f"{name}{i}" if many else name
        a = np.asarray(px)
        if a.dtype != np.uint8 or a.ndim != 3 or a.shape[2] not in (3, 4):
            raise ValueError(f"{label}: a picture is uint8 RGB or RGBA, this one is {a.dtype} {a.shape}")
        h, w = a.shape[:2]
        animated = bool(meta and "animation" in meta)
        if w % TILE or (h % w if animated else h != w):
            raise ValueError(f"{label}: {w}x{h}; a block picture is square with a side of {TILE} or a multiple"
                             + (", frames stacked downwards" if animated else ""))
        odd = {c: n for c, n in P.strays(a).items() if c not in allow}
        if odd:
            worst = sorted(odd.items(), key=lambda kv: -kv[1])[:5]
            raise ValueError(f"{label}: {len(odd)} colours are not in the palette, e.g. "
                             + ", ".join("#%02x%02x%02x x%d" % (*c, n) for c, n in worst))
        respack.texture(pack_dir, f"block/{label}", a, NS, meta=meta)
    return name


def redirect(pack_dir, block, textures, **kw):
    """respack.redirect_block for a block of the occupancy table; returns a line for the log."""
    if block not in B.ids(B.REPAINTED):
        raise ValueError(f"{block} is not a repainted block of the occupancy table (common/blocks.py)")
    kw.setdefault("protect", PROTECT)
    got = respack.redirect_block(pack_dir, game(), block, textures, ns=NS, **kw)
    return f"{block}: {got['models']} models x {got['variants']} -> {', '.join(p.rpartition('/')[2] for p in got['pictures'])}"


def drawn_by_code(block):
    """True for a block whose models have no boxes: the game draws it itself (signs), and only the
    particle picture can be redirected."""
    state = game().json(f"assets/minecraft/blockstates/{block}.json")
    return all(respack.flat_model(game(), ref)["elements"] is None for ref in respack.state_models(state)[1])


# ---- footstep and handling sounds ------------------------------------------------------------------
def sounds(pack_dir, events):
    """Point sound events at other sounds of the game: {event: [sound names]}, e.g.
    {"block.bamboo_wood.step": ["block/copper/step1", ...]}. Written into assets/minecraft/sounds.json
    with "replace": true, added to what is already there. Only names of sounds the game ships are
    used: this pack carries no audio."""
    path = os.path.join(pack_dir, "assets", "minecraft", "sounds.json")
    data = {}
    if os.path.isfile(path):
        with open(path) as fh:
            data = json.load(fh)
    for event, names in events.items():
        data[event] = {"replace": True, "sounds": [{"name": n} if isinstance(n, str) else n for n in names]}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(data, fh, separators=(",", ":"), sort_keys=True)
    return f"sounds.json: {len(events)} events redirected"


# ---- the audit ---------------------------------------------------------------------------------------
class _Over:
    """A written pack laid over the game's files, as the game reads them (only what the audit needs:
    the jar is not opened a second time)."""

    def __init__(self, pack_dir):
        self.pack_dir = pack_dir
        self._json = {}

    def read(self, path):
        f = os.path.join(self.pack_dir, *path.split("/"))
        if os.path.isfile(f):
            with open(f, "rb") as fh:
                return fh.read()
        return game().read(path)

    def json(self, path):
        if path not in self._json:
            raw = self.read(path)
            self._json[path] = None if raw is None else json.loads(raw)
        return self._json[path]


def _files(root):
    out = []
    for folder, _, names in os.walk(root):
        out += [os.path.relpath(os.path.join(folder, n), root).replace(os.sep, "/") for n in names]
    return sorted(out)


def audit(pack_dir, replaced=()):
    """The rules of this category, checked on the files of a written pack. Raises with the list of
    what is wrong; returns a line when nothing is.

      - a block state file only for a repainted block of the occupancy table, never for one the
        table keeps vanilla, never for verdigris (waxed_oxidized_*, waxed_weathered_*);
      - no model of the game replaced; no block picture of the game replaced unless listed in
        `replaced` (paths under assets/minecraft/textures/);
      - every model a block state names and every picture a model shows exists, in the pack or in
        the game, so nothing shows the missing-texture checkerboard;
      - every block picture of ours is a square of 16s (or frames of one) in palette colours only.
    """
    wrong = []
    repainted = set(B.ids(B.REPAINTED))
    states = _files(os.path.join(pack_dir, "assets", "minecraft", "blockstates"))
    for rel in states:
        block = rel[:-5]
        if any(fnmatch.fnmatchcase(block, p) for p in PROTECT):
            wrong.append(f"blockstates/{rel}: {block} stays as the game draws it")
        elif block not in repainted:
            wrong.append(f"blockstates/{rel}: {block} is not a repainted block of the occupancy table")
    for rel in _files(os.path.join(pack_dir, "assets", "minecraft", "models")):
        wrong.append(f"minecraft/models/{rel}: a model of the game is replaced; blocks that share it change too")
    for rel in _files(os.path.join(pack_dir, "assets", "minecraft", "textures", "block")):
        if f"block/{rel}" not in replaced:
            wrong.append(f"minecraft/textures/block/{rel}: a block picture of the game is replaced")

    both = _Over(pack_dir)
    n_models = 0
    for rel in states:
        with open(os.path.join(pack_dir, "assets", "minecraft", "blockstates", rel)) as fh:
            state = json.load(fh)
        for ref in respack.state_models(state)[1]:
            n_models += 1
            try:
                flat = respack.flat_model(both, ref)
            except (FileNotFoundError, KeyError, ValueError) as e:
                wrong.append(f"blockstates/{rel}: {e}")
                continue
            shown = {face["texture"] for el in flat["elements"] or [] for face in el["faces"].values()}
            for pic in sorted(shown | ({flat["particle"]} if flat["particle"] else set())):
                ns, _, path = pic.partition(":")
                if both.read(f"assets/{ns}/textures/{path}.png") is None:
                    wrong.append(f"{ref}: shows {pic}, which does not exist")

    ours = [rel for rel in _files(os.path.join(pack_dir, "assets", NS, "textures", "block")) if rel.endswith(".png")]
    for rel in ours:
        a = np.array(Image.open(os.path.join(pack_dir, "assets", NS, "textures", "block", rel)).convert("RGBA"))
        if a.shape[1] % TILE or a.shape[0] % a.shape[1]:
            wrong.append(f"{NS}/textures/block/{rel}: {a.shape[1]}x{a.shape[0]}, not a square of {TILE}s (or frames of one)")
        odd = P.strays(a)
        if odd:
            wrong.append(f"{NS}/textures/block/{rel}: {len(odd)} colours outside the palette")
    if wrong:
        raise AssertionError("materials audit:\n  " + "\n  ".join(wrong))
    return f"materials audit: {len(states)} block states, {n_models} models, {len(ours)} pictures, nothing wrong"
