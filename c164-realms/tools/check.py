#!/usr/bin/env python3
"""Technical checks for a scene (plan/PIPELINE.md section 6).

    check.py --scene obs                the master scene
    check.py --scene obs_mat_stone      a work package's test scene

    --shots <file>   shot list for the per-view entity counts (default: the scene's shots.json)
    --jar <file>     the game jar, to see which other blocks a replaced vanilla file changes and
                     whether the game has the models and pictures the pack names
                     (default: MC_JAR, else <MC_ROOT>/client26/versions/26.3/26.3.jar)
    --json <file>    also write the report as JSON: every detail line, and the counts of each shot
    --keep <dir>     keep the generated packs there instead of a temporary folder (the folder is
                     emptied first, so it has to be new, empty or left by an earlier --keep)

In the shared workspace it goes through the job runner like every script, from the part's copy
of the code (the path is relative to build/):

    python bin/job.py <part> -- ../tools/check.py --scene <scene>

It needs neither a server nor the game window and draws nothing: seconds for a test scene.

Each check prints PASS, WARN or FAIL; the exit code is 1 when one fails.

  regen      the scene, its models, resource pack, data pack and look generate from nothing
  conflicts  no resource-pack file is written by two packages; files lie in their category's
             folders and have names the game reads; model names carry their category's prefix
             (plan/roles/INTERFACE.md 4). A package's test scene is held to the same table: the
             packages of its category are run as the master scene runs them
  strays     no generated picture has a colour outside the palette
  refs       every model and picture a file of the pack names exists, in the pack or in the game
  repaint    only blocks of the occupancy table are repainted, and no replaced vanilla model or
             picture changes a block outside it
  blocks     the blocks placed, and those block displays show, are in the occupancy table
  flatwall   no wall face runs flat (one block state, no relief) over more than 5x5
  entities   every display entity shows a model of the pack; counts against the budget;
             16 pixels to the block; a piece drawn out along one axis has an even picture along it
  views      display entities inside each shot's view, against the per-view budget; how many the
             game draws whatever the view; how many stand too far from the camera to be sent

What a script cannot judge (doors a player fits through, storey heights, the wording of signs,
whether a repainted block is used for what it was repainted as) is read off the pictures and the
code by whoever does the technical check.
"""
import argparse
import importlib
import json
import math
import os
import re
import shutil
import sys
import tempfile
import time
import traceback
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.normpath(os.path.join(HERE, "..", "build"))
sys.path.insert(0, BUILD)

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import makepack  # noqa: E402
from artkit import export as X  # noqa: E402
from artkit import models as M  # noqa: E402
from artkit import mood as MOOD  # noqa: E402
from scenes.obs.common import blocks as B  # noqa: E402
from scenes.obs.common import palette as P  # noqa: E402
from scenes.obs.common import skeleton as S  # noqa: E402

MODEL_NS = "c164"            # artkit.models.write_pack's namespace
SHOWN = 12                   # lines of detail per finding before "... and N more"
ASPECT = 16.0 / 9.0          # the billboard pictures
FOV = 77.0                   # vertical, as render.py and tools/shoot.py take them
DISPLAYS = {"minecraft:item_display", "minecraft:block_display", "minecraft:text_display"}
FLAT = 5                     # a wall face may run flat over FLAT x FLAT blocks
KEPT = ".c164-check"         # marks a --keep folder as this script's, so the next run may empty it

# The server sends an entity only to the players within its tracking range: 10 chunks for the
# display entities, measured level. S1 read that off the 26.3 code (EntityType, ChunkMap); it has
# not been seen on the real machine yet, so what stands beyond it is named and still counted.
TRACKED = 160.0

# The game adds the sun, the moon and the stars to the sky behind them and tints the cloud picture:
# a pixel there says how much light to add or where a cloud is, it is not a colour that is seen, so
# those pictures are not held to the palette.
ADDITIVE = ("assets/minecraft/textures/environment/",)

# INTERFACE 4: the resource-pack areas only one category writes. The longest match owns a path.
# The blocks of the cloud sea are the one exception to "only materials paints blocks" (A0, 2026-11-14:
# their colours are tuned with the light of the sky): their block states, their model folders and
# the block pictures named sky_* are the sky's.
OWNED = {
    "materials": ("assets/minecraft/", "assets/c164/textures/block/", "assets/c164/models/block/"),
    "sky": ("assets/minecraft/textures/environment/", "assets/c164/textures/environment/",
            "assets/c164/textures/block/sky_",
            *(f"assets/minecraft/blockstates/{b}.json" for b in B.CLOUD),
            *(f"assets/c164/models/block/{b}/" for b in B.CLOUD)),
    "motion": ("assets/c164/sounds/", "assets/c164/sounds.json", "assets/c164/particles/",
               "assets/c164/textures/particle/"),
}
# Packages that dress the repainted blocks nobody has painted yet. A placeholder may stand in any
# block's files; once the owner writes them too, the path is written twice and that fails.
STANDINS = ("materials/respack_redirect",)

# INTERFACE 5: a package's test scene is called obs_<abbreviation>_<package>.
ABBR = {"mat": "materials", "sky": "sky", "main": "main", "site": "site", "mach": "machines",
        "props": "props", "int": "interiors", "mot": "motion"}
# Categories whose test scenes are boards and backdrops: a sample wall there is meant to be flat.
BOARDS = {"materials", "sky", "props", "motion"}

# The game reads a pack file only if its path is made of these; any other is skipped with an error
# in the log. Pictures are read as .png and nothing else.
NAME_OK = re.compile(r"[a-z0-9_.\-/]+\Z")
NOT_PNG = (".jpg", ".jpeg", ".gif", ".bmp", ".tga", ".webp", ".tif", ".tiff", ".psd", ".xcf")


class Lines(list):
    """Detail lines as they are printed, cut short; .full keeps every line for the JSON report."""

    def __init__(self, shown, full):
        super().__init__(shown)
        self.full = list(full)

    def __add__(self, other):
        return Lines(list(self) + list(other), self.full + list(getattr(other, "full", other)))

    def __radd__(self, other):
        return Lines(list(other) + list(self), list(getattr(other, "full", other)) + self.full)


class Report:
    def __init__(self, scene):
        self.scene, self.rows = scene, []

    def add(self, check, status, summary, details=(), data=None):
        row = {"check": check, "status": status, "summary": summary,
               "details": list(getattr(details, "full", details))}
        if data is not None:
            row["data"] = data
        self.rows.append(row)
        print(f"[{status}] {check:9s} {summary}")
        for line in details:
            print(f"                 {line}")
        sys.stdout.flush()

    def count(self, status):
        return sum(1 for r in self.rows if r["status"] == status)


def clip(lines, shown=SHOWN):
    lines = list(lines)
    return Lines(lines if len(lines) <= shown else lines[:shown] + [f"... and {len(lines) - shown} more"], lines)


def files_under(root):
    out = []
    for d, _, names in os.walk(root):
        for n in names:
            out.append(os.path.relpath(os.path.join(d, n), root).replace(os.sep, "/"))
    return sorted(out)


def look_of(name):
    try:
        return importlib.import_module(f"scenes.{name}.mood")
    except ModuleNotFoundError as e:
        if e.name != f"scenes.{name}.mood":
            raise
        return None


def is_master(scene):
    return hasattr(scene, "LINES") and hasattr(scene, "_line")


def category_of(scene, name):
    """The category a package's test scene belongs to: the scene's CATEGORY if it names one, else
    read off the name obs_<abbreviation>_<package> (INTERFACE 5). None for the master scene and
    for a scene of neither kind."""
    if is_master(scene):
        return None
    declared = getattr(scene, "CATEGORY", None)
    if declared is not None:
        return declared
    parts = name.split("_")
    return ABBR.get(parts[1]) if len(parts) >= 3 and parts[0] == "obs" else None


# ---- regen -------------------------------------------------------------------------------------
def regen(rep, name, work):
    """Generate what the drivers generate, from nothing. Returns what the other checks read."""
    t0 = time.time()
    try:
        scene = importlib.import_module(f"scenes.{name}")
        builder = makepack.builder_of(scene, name)
        # a scene without build() is a model gallery (gallery.py lays it out): models and pack only
        canvas = scene.build() if hasattr(scene, "build") else None
        models = builder()
        pack = os.path.join(work, "resourcepack")
        M.write_pack(pack, list(models.values()))
        if hasattr(scene, "write_pack"):
            scene.write_pack(pack)
        data = os.path.join(work, "datapack")
        os.makedirs(data, exist_ok=True)
        words = []
        if canvas is not None:
            manifest = X.export(canvas, data, "check")
            words += [f"{manifest['blocks']} blocks", f"{manifest['entities']} entities"]
        else:
            words.append("no build(): a model gallery")
        look = look_of(name)
        if look is not None:
            MOOD.write(data, "c164art", look.BIOMES, getattr(look, "TIMELINES", None))
            biome = getattr(scene, "BIOME", None)
            if biome is not None and biome not in look.BIOMES:
                raise ValueError(f"BIOME {biome!r} is not one of the look's biomes {sorted(look.BIOMES)}")
    except Exception:
        tail = traceback.format_exc().rstrip().splitlines()
        rep.add("regen", "FAIL", "does not generate from nothing", tail[-8:])
        return None
    words += [f"{len(models)} models", f"{len(files_under(pack))} resource-pack files",
              f"{len(files_under(data))} data-pack files"]
    if look is not None:
        words.append(f"look: {len(look.BIOMES)} biomes, {len(getattr(look, 'TIMELINES', None) or {})} timelines")
    rep.add("regen", "PASS", ", ".join(words) + f" ({time.time() - t0:.1f} s)")
    return {"scene": scene, "name": name, "category": category_of(scene, name), "builder": builder,
            "canvas": canvas, "models": models, "pack": pack}


# ---- conflicts ---------------------------------------------------------------------------------
def package_writers(master, cats):
    """[(owner, category, "models" | "pack", function)]: the work packages of the categories (the
    modules of the category subpackages) and what each writes into the resource pack."""
    out = []
    for cat in cats:
        for part in master._line(cat)._cat.parts():
            owner = f"{cat}/{part.__name__.rsplit('.', 1)[1]}"
            if hasattr(part, "models"):
                out.append((owner, cat, "models", part.models))
            if hasattr(part, "pack"):
                out.append((owner, cat, "pack", part.pack))
    return out


def owner_of(path):
    best, who = -1, None
    for cat, roots in OWNED.items():
        for root in roots:
            if path.startswith(root) and len(root) > best:
                best, who = len(root), cat
    return who


def conflicts(rep, got, name, work):
    """Every writer fills a folder of its own; a path that turns up in two of them is a conflict.

    The master scene has one writer per work package. Any other scene has two, its models and its
    write_pack(); if it is a package's test scene, the packages of its category are run as well,
    each on its own as in the master scene, so a file in another category's area or a model without
    the prefix shows here and not only after the merge.
    """
    scene, cat = got["scene"], got["category"]
    by_path, fails, warns, attributed, standing = {}, [], [], {}, {}
    if is_master(scene):
        master = scene
        ws = [w + (True,) for w in package_writers(master, master.LINES)]
    else:
        master = importlib.import_module("scenes.obs")
        ws = [(name, None, "models", got["builder"], True)]
        if hasattr(scene, "write_pack"):
            ws.append((name, None, "pack", scene.write_pack, True))
        if cat is not None and cat not in master.LINES:
            fails.append(f"{name}: CATEGORY {cat!r} is not one of {', '.join(master.LINES)}")
            cat = None
        if cat is not None:
            ws += [w + (False,) for w in package_writers(master, [cat])]
    prefixes = {c: getattr(master._line(c), "PREFIX", None) for c in master.LINES}
    known = tuple(sorted(p for p in prefixes.values() if p))
    for i, (owner, wcat, kind, fn, counted) in enumerate(ws):
        d = os.path.join(work, f"writer-{i}")
        os.makedirs(d, exist_ok=True)
        prefix = prefixes.get(wcat)
        if kind == "models":
            built = fn() or {}
            M.write_pack(d, list(built.values()))
            for key, model in built.items():
                if key != model.name:
                    fails.append(f"{owner}: models() key {key!r} is not the model's name {model.name!r}")
                if wcat is not None:
                    if prefix and not model.name.startswith(prefix):
                        fails.append(f"{owner}: model {model.name!r} lacks the category prefix {prefix!r}")
                elif cat is not None and not model.name.startswith(known):
                    # a test scene may show other packages' models beside its own
                    fails.append(f"{owner}: model {model.name!r} carries no category's prefix "
                                 f"({', '.join(known)})")
        else:
            fn(d)
        for path in files_under(d):
            if path == "pack.mcmeta":
                continue
            if counted:
                by_path.setdefault(path, []).append(f"{owner} ({kind})")
                attributed[path] = owner
            elif path in attributed:
                attributed[path] = owner        # the package the scene got the file from
            if kind != "pack" or wcat is None:
                continue
            own = owner_of(path)
            if own is not None and own != wcat:
                if owner in STANDINS:
                    standing.setdefault(own, []).append(path)
                else:
                    fails.append(f"{owner}: {path} lies in the area of {own} (INTERFACE 4)")
            elif own is None and not (path.startswith(f"assets/{MODEL_NS}/")
                                      and os.path.basename(path).startswith(prefix or "\0")):
                warns.append(f"{owner}: {path} is outside the category's folders; tell S2 so the table "
                             f"of areas can name it")
    for path, who in sorted(by_path.items()):
        if len(who) > 1:
            fails.append(f"{path} is written by {' and '.join(who)}")
    got["attributed"] = attributed
    for path in files_under(got["pack"]):
        if path == "pack.mcmeta":
            continue
        who = f"{attributed[path]}: " if path in attributed else ""
        if path not in by_path:
            warns.append(f"{path} is in the pack but no package's models() or pack() wrote it")
        if not NAME_OK.match(path):
            fails.append(f"{who}{path}: the game reads no file whose name has anything but a-z 0-9 _ - . /")
        elif path.endswith(NOT_PNG):
            warns.append(f"{who}{path}: the game reads pictures as .png only; nothing checks this one")
    if is_master(scene):
        summary = f"{len({w[0] for w in ws})} packages write {len(by_path)} files"
        held = "every file in its owner's folders"
    else:
        summary = f"the scene writes {len(by_path)} files"
        n = len({w[0] for w in ws if not w[4]})
        if cat is None:
            held = "not a package's test scene (INTERFACE 5), so folders and prefixes are not checked"
        elif n:
            held = f"the folders and the prefix of {cat} are kept ({n} package{'s' if n > 1 else ''} run alone)"
        else:
            held = f"the packages of {cat} write nothing into the pack"
    for own, paths in sorted(standing.items()):
        summary += f"; {len(paths)} files of {own} are placeholders of the stand-ins"
    if fails:
        rep.add("conflicts", "FAIL", summary + f": {len(fails)} problems", clip(fails) + clip(warns, 4))
    elif warns:
        rep.add("conflicts", "WARN", summary + f", no file written twice; {held}", clip(warns))
    else:
        rep.add("conflicts", "PASS", summary + f", no file written twice, {held}")


# ---- strays ------------------------------------------------------------------------------------
def nearest(rgb):
    best = None
    for ramp, colours in P.RAMPS.items():
        for step, c in enumerate(colours):
            c = P.hx(c)
            d = sum((a - b) ** 2 for a, b in zip(rgb, c))
            if best is None or d < best[0]:
                best = (d, f"{ramp}[{step}] #{c[0]:02x}{c[1]:02x}{c[2]:02x}")
    return best[1]


def strays(rep, got):
    pack, attributed = got["pack"], got.get("attributed", {})
    every = [p for p in files_under(pack) if p.endswith(".png")]
    pictures = [p for p in every if not p.startswith(ADDITIVE)]
    skipped = len(every) - len(pictures)
    note = f"; {skipped} sky pictures not checked (drawn by adding light)" if skipped else ""
    bad = []
    for path in pictures:
        found = P.strays(np.asarray(Image.open(os.path.join(pack, path)).convert("RGBA")))
        if not found:
            continue
        worst = sorted(found.items(), key=lambda kv: -kv[1])
        who = f" [{attributed[path]}]" if path in attributed else ""
        bad.append(f"{path}{who}: {len(found)} colours outside the palette, {sum(found.values())} pixels")
        for (r, g, b), n in worst[:3]:
            bad.append(f"    #{r:02x}{g:02x}{b:02x} x{n}, nearest {nearest((r, g, b))}")
    if bad:
        n_bad = sum(1 for line in bad if not line.startswith("    "))
        rep.add("strays", "FAIL", f"{n_bad} of {len(pictures)} pictures have colours outside the palette{note}",
                clip(bad, 4 * SHOWN))
    else:
        rep.add("strays", "PASS", f"{len(pictures)} pictures, every colour in the palette{note}")


# ---- refs --------------------------------------------------------------------------------------
def _named(node, key, out):
    """Every string found under `key` anywhere in a JSON tree."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k == key and isinstance(v, str):
                out.add(v)
            else:
                _named(v, key, out)
    elif isinstance(node, list):
        for v in node:
            _named(v, key, out)
    return out


def _picture(entry):
    """The picture an entry of a model's "textures" names: a plain name or, since 26.x, an object
    {"sprite": name, "force_translucent": ...}. None where it points at another entry (#name)."""
    if isinstance(entry, dict):
        entry = entry.get("sprite")
    return entry if isinstance(entry, str) and not entry.startswith("#") else None


def _file_of(ref, kind):
    """Pack path of a model ("models", .json) or a picture ("textures", .png) named ns:path."""
    ns, _, path = ref.rpartition(":")
    return f"assets/{ns or 'minecraft'}/{kind}/{path}.{'json' if kind == 'models' else 'png'}"


def refs(rep, got, jar):
    """What the pack's block states, item definitions and models name has to exist: a model or a
    picture that is neither in the pack nor in the game shows as the purple-and-black cube."""
    pack, attributed = got["pack"], got.get("attributed", {})
    files = set(files_under(pack))
    vanilla = None
    if jar and os.path.exists(jar):
        with zipfile.ZipFile(jar) as z:
            vanilla = set(z.namelist())
    fails, warns, used, unchecked, n = [], [], set(), set(), 0

    def need(src, path, what):
        used.add(path)
        if path in files or (vanilla is not None and path in vanilla):
            return
        if vanilla is None and path.startswith("assets/minecraft/"):
            unchecked.add(path)
            return
        who = f" [{attributed[src]}]" if src in attributed else ""
        fails.append(f"{src}{who} names the {what} {path}, which is neither in the pack nor in the game")

    for src in sorted(files):
        parts = src.split("/")
        if not src.endswith(".json") or len(parts) < 4 or parts[0] != "assets":
            continue
        kind = parts[2]
        if kind not in ("blockstates", "items", "models"):
            continue
        try:
            with open(os.path.join(pack, src), encoding="utf-8") as fh:
                node = json.load(fh)
        except ValueError as e:
            fails.append(f"{src} is not JSON the game can read: {e}")
            continue
        n += 1
        if kind != "models":
            # "base" is the model under a special item (a chest, a banner)
            for ref in sorted(_named(node, "model", set()) | (_named(node, "base", set()) if kind == "items" else set())):
                need(src, _file_of(ref, "models"), "model")
            continue
        parent = node.get("parent") if isinstance(node, dict) else None
        if isinstance(parent, str) and not parent.rpartition(":")[2].startswith("builtin/"):
            need(src, _file_of(parent, "models"), "model")
        for entry in ((node.get("textures") or {}) if isinstance(node, dict) else {}).values():
            if _picture(entry) is not None:
                need(src, _file_of(_picture(entry), "textures"), "picture")
    # what nothing shows: the pack's own models and block or item pictures that no file names
    for path in sorted(files):
        own = path.startswith(f"assets/{MODEL_NS}/models/") and path.endswith(".json")
        own = own or (path.startswith((f"assets/{MODEL_NS}/textures/block/", f"assets/{MODEL_NS}/textures/item/"))
                      and path.endswith(".png"))
        if own and path not in used:
            who = f" [{attributed[path]}]" if path in attributed else ""
            warns.append(f"{path}{who} is named by no block state, item definition or model: nothing shows it")
    if unchecked:
        warns.append(f"{len(unchecked)} of the game's own models and pictures are named; without the game jar "
                     f"(--jar or MC_JAR) nothing says they exist")
    summary = f"{n} block states, item definitions and models read"
    if fails:
        rep.add("refs", "FAIL", summary + f": {len(fails)} name something that is not there", clip(fails) + clip(warns, 4))
    elif warns:
        rep.add("refs", "WARN", summary + ", what they name is there", clip(warns))
    else:
        rep.add("refs", "PASS", summary + ", every model and picture they name is there")


# ---- repaint -----------------------------------------------------------------------------------
def _model_refs(node, out):
    for ref in _named(node, "model", set()):
        out.add(ref.split(":", 1)[-1])
    return out


class Vanilla:
    """Which blocks show which vanilla block models and pictures, read from the game jar."""

    def __init__(self, jar):
        self.users, self.children, self.painted = {}, {}, {}
        with zipfile.ZipFile(jar) as z:
            for n in z.namelist():
                if not n.endswith(".json"):
                    continue
                if n.startswith("assets/minecraft/blockstates/"):
                    block = n[len("assets/minecraft/blockstates/"):-5]
                    for ref in _model_refs(json.loads(z.read(n)), set()):
                        self.users.setdefault(ref, set()).add(block)
                elif n.startswith("assets/minecraft/models/block/"):
                    ref = n[len("assets/minecraft/models/"):-5]
                    data = json.loads(z.read(n))
                    if "parent" in data:
                        self.children.setdefault(data["parent"].split(":", 1)[-1], []).append(ref)
                    for entry in (data.get("textures") or {}).values():
                        if _picture(entry) is not None:
                            self.painted.setdefault(_picture(entry).split(":", 1)[-1], set()).add(ref)

    def blocks_showing(self, models):
        """Blocks whose vanilla block state shows one of the models or a model built on one."""
        seen, todo, out = set(), list(models), set()
        while todo:
            m = todo.pop()
            if m in seen:
                continue
            seen.add(m)
            out |= self.users.get(m, set())
            todo += self.children.get(m, [])
        return out


def repaint(rep, got, jar):
    pack = got["pack"]
    table, plain = set(B.ids(B.REPAINTED)), set(B.ids(B.VANILLA))
    files = files_under(pack)
    states = [p[len("assets/minecraft/blockstates/"):-5] for p in files
              if p.startswith("assets/minecraft/blockstates/") and p.endswith(".json")]
    models = [p[len("assets/minecraft/models/"):-5] for p in files
              if p.startswith("assets/minecraft/models/block/") and p.endswith(".json")]
    pictures = [p[len("assets/minecraft/textures/"):-4] for p in files
                if p.startswith("assets/minecraft/textures/block/") and p.endswith(".png")]
    fails, warns = [], []
    for b in states:
        if b not in table:
            what = "is listed as used the vanilla way" if b in plain else "is not in the occupancy table"
            fails.append(f"block state of {b} is replaced, but {b} {what}")
    if models or pictures:
        if jar and os.path.exists(jar):
            vanilla = Vanilla(jar)
            for kind, names in (("model", models), ("picture", pictures)):
                for ref in names:
                    shown = [ref] if kind == "model" else sorted(vanilla.painted.get(ref, ()))
                    hit = vanilla.blocks_showing(shown) - table - set(states)
                    if hit:
                        named = sorted(hit, key=lambda b: (b not in plain, b))
                        fails.append(f"vanilla {kind} {ref} is replaced; that also changes "
                                     f"{', '.join(named[:6])}{' ...' if len(named) > 6 else ''} "
                                     f"({len(hit)} blocks outside the table"
                                     f"{', ' + str(len(hit & plain)) + ' of them used the vanilla way' if hit & plain else ''})")
        else:
            warns.append(f"{len(models)} vanilla block models and {len(pictures)} vanilla block pictures are "
                         f"replaced; without the game jar (--jar or MC_JAR) the blocks they change are not checked")
    summary = (f"{len(states)} block states, {len(models)} vanilla block models, {len(pictures)} vanilla "
               f"block pictures replaced")
    if fails:
        rep.add("repaint", "FAIL", summary + f": {len(fails)} outside the occupancy table", clip(fails) + warns)
    elif warns:
        rep.add("repaint", "WARN", summary, warns)
    else:
        rep.add("repaint", "PASS", summary + ", all within the occupancy table")


# ---- blocks ------------------------------------------------------------------------------------
def blocks(rep, got):
    canvas = got["canvas"]
    table = set(B.ids(B.REPAINTED + B.VANILLA))
    used = {k.split(":", 1)[-1]: v for k, v in canvas.count().items()}
    shown = {}                  # what block displays show is seen like a placed block
    for _, _, _, nbt in canvas.entities:
        if nbt.get("id") == "minecraft:block_display":
            b = str((nbt.get("block_state") or {}).get("Name", "")).split(":", 1)[-1]
            if b:
                shown[b] = shown.get(b, 0) + 1
    outside = [f"{b} x{n}" for n, b in sorted(((n, b) for b, n in used.items() if b not in table), reverse=True)]
    outside += [f"{b} x{n}, shown by block displays"
                for n, b in sorted(((n, b) for b, n in shown.items() if b not in table), reverse=True)]
    words = f"{len(used)} kinds of block placed"
    if shown:
        words += f", {len(shown)} kinds shown by block displays"
    if outside:
        rep.add("blocks", "WARN", f"{words}, {len(outside)} not in the occupancy table "
                f"(add them to the table through S2, or use a block of the table)", clip(outside))
    else:
        rep.add("blocks", "PASS", f"{words}, all in the occupancy table")


# ---- flatwall ----------------------------------------------------------------------------------
def _largest_square(present, h, w):
    """Side of the largest solid square of True cells in an h x w grid, and its last cell."""
    best, at, prev = 0, (0, 0), [0] * w
    for i in range(h):
        cur, left = [0] * w, 0
        for j in range(w):
            if present[i][j]:
                cur[j] = 1 + min(prev[j], left, prev[j - 1] if j else 0)
                if cur[j] > best:
                    best, at = cur[j], (i, j)
            left = cur[j]
        prev = cur
    return best, at


def flatwall(rep, got):
    """A wall reads flat, and its picture is seen to repeat, where one block state runs on without
    relief over more than 5x5 of a face (plan/PIPELINE.md 6). A cell's face is seen when the cell
    in front of it is empty; walls are the upright faces. Only a solid square larger than 5x5 is
    named, so a pilaster strip up to 5 wide or a course up to 5 high is not. A warning: the white
    model is plain on purpose, and a finished elevation is judged on the pictures."""
    cat = got["category"]
    if cat in BOARDS:
        rep.add("flatwall", "SKIP", f"a test scene of {cat}: its sample walls and backdrops are meant to be flat")
        return
    cells = got["canvas"].b
    groups = {}                 # (facing, plane, state) -> {(across, up): cell}
    for (x, y, z), state in cells.items():
        for facing, dx, dz in (("east", 1, 0), ("west", -1, 0), ("south", 0, 1), ("north", 0, -1)):
            if (x + dx, y, z + dz) in cells:
                continue        # covered, not seen
            plane, across = (x, z) if dx else (z, x)
            groups.setdefault((facing, plane, state), {})[(across, y)] = (x, y, z)
    big = []
    for (facing, _plane, state), face in groups.items():
        us, vs = [u for u, _ in face], [v for _, v in face]
        u0, v0 = min(us), min(vs)
        w, h = max(us) - u0 + 1, max(vs) - v0 + 1
        if w <= FLAT or h <= FLAT:
            continue            # too narrow or too low to hold a square larger than the limit
        present = [[False] * w for _ in range(h)]
        for u, v in face:
            present[v - v0][u - u0] = True
        side, (i, j) = _largest_square(present, h, w)
        if side > FLAT:
            big.append((side, state.partition("[")[0].split(":", 1)[-1], facing, face[(u0 + j, v0 + i)]))
    big.sort(key=lambda t: (-t[0], t[1], t[2], t[3]))
    if big:
        lines = [f"{block} facing {facing}: flat over {side}x{side}, the square's top corner at {pos}"
                 for side, block, facing, pos in big]
        rep.add("flatwall", "WARN", f"{len(big)} wall faces run flat over more than {FLAT}x{FLAT} (one block, "
                f"no relief; the white model is plain on purpose, an elevation is not)", clip(lines),
                data={"largest": big[0][0], "faces": len(big)})
    else:
        rep.add("flatwall", "PASS", f"no wall face runs flat over more than {FLAT}x{FLAT}")


# ---- entities ----------------------------------------------------------------------------------
def _displays(canvas):
    return [(x, y, z, nbt) for x, y, z, nbt in canvas.entities if nbt.get("id") in DISPLAYS]


def _model_of(nbt):
    return ((nbt.get("item") or {}).get("components") or {}).get("minecraft:item_model")


def _smear(model, axis):
    """What a stretch along the model's axis (0, 1, 2) does to it: the materials whose pictures
    change along that axis (drawn out, a speckle becomes a streak and the bevel at an end a band),
    and how many boxes are turned away from the axis (the stretch skews those)."""
    e = [0.0, 0.0, 0.0]
    e[axis] = 1.0
    uneven, skewed, even = set(), set(), {}
    for pi, f, mat, w, h, grain, seed in model.faces():
        part, d = model.parts[pi], e
        if part["rot"]:
            x, y, z, qw = part["rot"][0]
            d = M._qrot((-x, -y, -z, qw), e)            # the stretch axis in the box's own frame
        own = max(range(3), key=lambda i: abs(d[i]))
        if abs(abs(d[own]) - 1.0) > 1e-6:
            skewed.add(pi)
            continue
        normal, ua, _va = M.FACE_AXES[f]
        if normal == own:
            continue                                    # an end face is moved, not stretched
        key = (mat.name, w, h, grain, seed, ua == own)
        if key not in even:
            tex = np.asarray(mat.paint(w, h, grain, seed))
            even[key] = bool((tex == (tex[:, :1] if ua == own else tex[:1, :])).all())
        if not even[key]:
            uneven.add(mat.name)
    return sorted(uneven), len(skewed)


def entities(rep, got):
    canvas, models = got["canvas"], got["models"]
    shown = _displays(canvas)
    others = len(canvas.entities) - len(shown)
    fails, warns, used, missing, plain, dense, drawn_out = [], [], set(), {}, {}, {}, {}
    for x, y, z, nbt in shown:
        if nbt["id"] != "minecraft:item_display":
            continue
        ref = _model_of(nbt)
        if ref is None or ref.startswith("minecraft:"):
            item = ref or (nbt.get("item") or {}).get("id")
            plain[item] = plain.get(item, 0) + 1
            continue
        name = ref.split(":", 1)[-1]
        if not ref.startswith(MODEL_NS + ":") or name not in models:
            missing[ref] = missing.get(ref, 0) + 1
            continue
        used.add(name)
        scale = [float(v) for v in (nbt.get("transformation") or {}).get("scale", (1.0, 1.0, 1.0))]
        density = [16.0 * models[name].px / abs(s) if s else 0.0 for s in scale]
        off = [i for i, d in enumerate(density) if abs(d - 16.0) > 0.05]
        if len(off) == 1:       # a piece drawn out along one axis (pipes, cables: models.between)
            drawn_out[(name, off[0])] = drawn_out.get((name, off[0]), 0) + 1
        elif off:
            key = (name, tuple(round(d, 2) for d in density))
            dense[key] = dense.get(key, 0) + 1
    for ref, n in sorted(missing.items()):
        fails.append(f"{n} display entities show {ref!r}, which the pack does not have")
    for item, n in sorted(plain.items(), key=lambda kv: str(kv[0])):
        if item is None:
            warns.append(f"{n} item displays hold no item: they show nothing")
        else:
            warns.append(f"{n} item displays show the game's own {item}, not a model of the pack: its look "
                         f"is the game's, outside the palette")
    for (name, d), n in sorted(dense.items()):
        warns.append(f"{name} x{n}: {d[0]:g}/{d[1]:g}/{d[2]:g} pixels to the block along x/y/z, not 16")
    for (name, axis), n in sorted(drawn_out.items()):
        uneven, skewed = _smear(models[name], axis)
        if uneven:
            warns.append(f"{name} x{n}: drawn out along {M.AXES[axis]}, where the picture of "
                         f"{', '.join(uneven)} is not even: it smears")
        if skewed:
            warns.append(f"{name} x{n}: drawn out along {M.AXES[axis]}, which skews {skewed} boxes turned "
                         f"away from that axis")
    idle = sorted(set(models) - used)
    total = len(shown)
    words = [f"{total} display entities"]
    if is_master(got["scene"]):
        words[0] += f" of {S.ENTITY_TOTAL}"
        if total > S.ENTITY_TOTAL:
            fails.append(f"{total} display entities, the whole map may have {S.ENTITY_TOTAL}")
        counts = getattr(canvas, "entity_counts", None) or {}
        if counts:
            words.append("by category: " + ", ".join(f"{k} {v}" for k, v in counts.items() if v))
            # build() returns the display entities placed (INTERFACE 2); other entities are not counted
            if sum(counts.values()) != total:
                warns.append(f"build() returned {sum(counts.values())} display entities in all, the canvas "
                             f"holds {total}: a package returns the wrong count")
            if counts.get("machines", 0) > S.BUDGET["machines"]:
                fails.append(f"machines: {counts['machines']} entities, budget {S.BUDGET['machines']}")
            if counts.get("props", 0) > S.BUDGET["props_outdoor"]:
                fails.append(f"props: {counts['props']} entities, budget {S.BUDGET['props_outdoor']}")
            if counts.get("interiors", 0) > S.BUDGET["props_indoor"]:
                fails.append(f"interiors: {counts['interiors']} entities, budget {S.BUDGET['props_indoor']}")
    stretched = sum(drawn_out.values())
    if stretched:
        words.append(f"{stretched} drawn out along one axis")
    if others:
        words.append(f"{others} other entities")
    if idle:
        words.append(f"{len(idle)} models never placed")
    status = "FAIL" if fails else "WARN" if warns else "PASS"
    rep.add("entities", status, ", ".join(words), clip(fails) + clip(warns))


# ---- views -------------------------------------------------------------------------------------
def _frame(shot):
    """A shot's camera: eye, forward, right, up. None when the shot gives it no direction."""
    pos = np.array(shot["pos"], dtype=float)
    if shot.get("look_at") is not None:
        f, yaw = np.array(shot["look_at"], dtype=float) - pos, 0.0
    else:
        yaw, pitch = math.radians(shot.get("yaw", 0.0)), math.radians(shot.get("pitch", 0.0))
        f = np.array([-math.sin(yaw) * math.cos(pitch), -math.sin(pitch), math.cos(yaw) * math.cos(pitch)])
    length = float(np.linalg.norm(f))
    if not length > 1e-9:
        return None
    f = f / length
    r = np.cross(f, (0.0, 1.0, 0.0))
    if float(np.linalg.norm(r)) < 1e-6:
        # straight up or down "up" gives no right-hand side; the yaw does, and that is 0 for a
        # look_at: tools/shoot.py turns the game's camera so (build/artkit/gamescene.py likewise)
        r = np.array([-math.cos(yaw), 0.0, -math.sin(yaw)])
    r = r / np.linalg.norm(r)
    return pos, f, r, np.cross(r, f)


def views(rep, got, shots_path):
    if not shots_path or not os.path.exists(shots_path):
        rep.add("views", "SKIP", "no shot list, so no per-view counts")
        return
    with open(shots_path, encoding="utf-8") as fh:
        shots = json.load(fh)
    shown = _displays(got["canvas"])
    pts = np.array([[x, y, z] for x, y, z, _ in shown], dtype=float).reshape(-1, 3)
    reach = np.array([float(nbt.get("view_range", 1.0)) * 64.0 for _, _, _, nbt in shown])
    # the game leaves a display entity out when it is outside the view only if the entity is given
    # a width and a height; without them it is drawn wherever the camera looks
    sized = np.array([float(nbt.get("width", 0.0)) > 0.0 and float(nbt.get("height", 0.0)) > 0.0
                      for _, _, _, nbt in shown], dtype=bool)
    ty = math.tan(math.radians(FOV) / 2.0)
    rows, fails, over, far = [], [], [], []
    for shot in shots:
        frame = _frame(shot)
        if frame is None:
            fails.append(f"{shot['name']}: pos and look_at are the same point, the camera has no direction")
            continue
        pos, f, r, u = frame
        n = drawn = lost = 0
        if len(pts):
            v = pts - pos
            depth = v @ f
            near = np.linalg.norm(v, axis=1) <= reach
            # two blocks of slack: a model reaches beyond the point it stands on
            inside = (near & (depth > -2.0) & (np.abs(v @ r) <= depth * ty * ASPECT + 2.0)
                      & (np.abs(v @ u) <= depth * ty + 2.0))
            n = int(inside.sum())
            drawn = int((near & (inside | ~sized)).sum())
            lost = int((inside & (np.hypot(v[:, 0], v[:, 2]) > TRACKED)).sum())
        rows.append({"name": shot["name"], "in_view": n, "drawn": drawn, "beyond_tracking": lost})
        if n > S.ENTITY_PER_VIEW:
            over.append(f"{shot['name']}: {n} display entities in view, a view may have {S.ENTITY_PER_VIEW}")
        if lost:
            far.append(f"{shot['name']}: {lost} of the {n} in view stand more than {TRACKED:g} blocks from the "
                       f"camera, measured level; the server sends those to no player there")
    if far:
        far.append("(the tracking range is read off the game's code, not yet seen on the real machine)")
    most = max(rows, key=lambda row: row["in_view"]) if rows else {"name": "-", "in_view": 0}
    summary = (f"{len(shots)} shots, most display entities in view: {most['in_view']} ({most['name']}), "
               f"limit {S.ENTITY_PER_VIEW}; counted without what walls hide")
    busiest = max(rows, key=lambda row: row["drawn"]) if rows else None
    if busiest is not None and busiest["drawn"] > busiest["in_view"]:
        summary += (f"; the game draws up to {busiest['drawn']} ({busiest['name']}): a display entity without "
                    f"width and height is drawn outside the view too")
    status = "FAIL" if fails else "WARN" if over or far else "PASS"
    rep.add("views", status, summary, clip(fails) + clip(over) + clip(far), data={"shots": rows})


def commit():
    """Short hash of the checked code, read from .git without running git."""
    try:
        d = HERE
        while not os.path.exists(os.path.join(d, ".git")):
            up = os.path.dirname(d)
            if up == d:
                return "?"
            d = up
        git = os.path.join(d, ".git")
        if os.path.isfile(git):                      # a worktree: "gitdir: <path>"
            with open(git) as fh:
                git = fh.read().split(":", 1)[1].strip()
        with open(os.path.join(git, "HEAD")) as fh:
            head = fh.read().strip()
        if not head.startswith("ref:"):
            return head[:7]
        ref = head.split(" ", 1)[1]
        common = git
        if os.path.exists(os.path.join(git, "commondir")):
            with open(os.path.join(git, "commondir")) as fh:
                common = os.path.normpath(os.path.join(git, fh.read().strip()))
        for base in (git, common):
            path = os.path.join(base, ref)
            if os.path.exists(path):
                with open(path) as fh:
                    return fh.read().strip()[:7]
        with open(os.path.join(common, "packed-refs")) as fh:
            for line in fh:
                if line.strip().endswith(" " + ref):
                    return line[:7]
    except (OSError, IndexError):
        pass
    return "?"


def workdir(ap, keep):
    """The folder the packs are generated in. A --keep folder is emptied first, so it is taken only
    if that loses nothing: new, empty, or marked as left by an earlier --keep."""
    if not keep:
        return tempfile.mkdtemp(prefix="c164-check-")
    if os.path.exists(keep):
        if not os.path.isdir(keep):
            ap.error(f"--keep {keep}: that is a file")
        if os.listdir(keep) and not os.path.exists(os.path.join(keep, KEPT)):
            ap.error(f"--keep {keep}: the folder holds other files and would be emptied; name a new or "
                     f"an empty folder")
        shutil.rmtree(keep)
    os.makedirs(keep)
    with open(os.path.join(keep, KEPT), "w") as fh:
        fh.write("left by tools/check.py --keep; the next run with this folder empties it\n")
    return keep


def main():
    ap = argparse.ArgumentParser(description="technical checks for a scene (plan/PIPELINE.md 6)")
    ap.add_argument("--scene", required=True)
    ap.add_argument("--shots")
    ap.add_argument("--jar", default=os.environ.get("MC_JAR") or os.path.join(
        os.environ.get("MC_ROOT", "/agent/realms-study"), "client26", "versions", "26.3", "26.3.jar"))
    ap.add_argument("--json")
    ap.add_argument("--keep")
    args = ap.parse_args()

    work = workdir(ap, args.keep)
    rep = Report(args.scene)
    print(f"check {args.scene} at {commit()}")
    try:
        got = regen(rep, args.scene, work)
        if got is not None:
            checks = [lambda: conflicts(rep, got, args.scene, work),
                      lambda: strays(rep, got),
                      lambda: refs(rep, got, args.jar),
                      lambda: repaint(rep, got, args.jar)]
            if got["canvas"] is not None:
                checks += [lambda: blocks(rep, got),
                           lambda: flatwall(rep, got),
                           lambda: entities(rep, got),
                           lambda: views(rep, got, args.shots or os.path.join(
                               BUILD, "scenes", args.scene, "shots.json"))]
            for check in checks:
                try:
                    check()
                except Exception:
                    tail = traceback.format_exc().rstrip().splitlines()
                    rep.add("check.py", "FAIL", "a check broke; this is a fault of the script or of what "
                            "the scene hands it", tail[-6:])
    finally:
        if not args.keep:
            shutil.rmtree(work, ignore_errors=True)
    failed, warned = rep.count("FAIL"), rep.count("WARN")
    verdict = "FAIL" if failed else "PASS"
    print(f"result: {verdict} ({failed} failed, {warned} with warnings)")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"scene": args.scene, "commit": commit(), "result": verdict, "checks": rep.rows}, fh,
                      indent=1, ensure_ascii=False)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
