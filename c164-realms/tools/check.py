#!/usr/bin/env python3
"""Technical checks for a scene (plan/PIPELINE.md section 6).

    check.py --scene obs                the master scene
    check.py --scene obs_mat_stone      a work package's test scene

    --shots <file>   shot list for the per-view entity counts (default: the scene's shots.json)
    --jar <file>     the game jar, to see which other blocks a replaced vanilla file changes
                     (default: MC_JAR, else <MC_ROOT>/client26/versions/26.3/26.3.jar)
    --json <file>    also write the report as JSON
    --keep <dir>     keep the generated packs there instead of a temporary folder

In the shared workspace it goes through the job runner like every script, from the part's copy
of the code (the path is relative to build/):

    python bin/job.py <part> -- ../tools/check.py --scene <scene>

It needs neither a server nor the game window and draws nothing: seconds for a test scene.

Each check prints PASS, WARN or FAIL; the exit code is 1 when one fails.

  regen      the scene, its models, resource pack, data pack and look generate from nothing
  strays     no generated picture has a colour outside the palette
  conflicts  no resource-pack file is written by two packages; files lie in their category's
             folders; model names carry their category's prefix (plan/roles/INTERFACE.md 4)
  repaint    only blocks of the occupancy table are repainted, and no replaced vanilla model or
             picture changes a block outside it
  blocks     the blocks placed are in the occupancy table
  entities   every display entity shows a model of the pack; counts against the budget;
             16 pixels to the block
  views      display entities inside each shot's view, against the per-view budget

What a script cannot judge (doors a player fits through, storey heights, the wording of signs,
whether a repainted block is used for what it was repainted as) is read off the pictures and the
code by whoever does the technical check.
"""
import argparse
import importlib
import json
import math
import os
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


class Report:
    def __init__(self, scene):
        self.scene, self.rows = scene, []

    def add(self, check, status, summary, details=()):
        details = list(details)
        self.rows.append({"check": check, "status": status, "summary": summary, "details": details})
        print(f"[{status}] {check:9s} {summary}")
        for line in details:
            print(f"                 {line}")
        sys.stdout.flush()

    def count(self, status):
        return sum(1 for r in self.rows if r["status"] == status)


def clip(lines, shown=SHOWN):
    lines = list(lines)
    return lines if len(lines) <= shown else lines[:shown] + [f"... and {len(lines) - shown} more"]


def files_under(root):
    out = []
    for d, _, names in os.walk(root):
        for n in names:
            out.append(os.path.relpath(os.path.join(d, n), root).replace(os.sep, "/"))
    return sorted(out)


def builder_of(scene, name):
    """The scene's build_models(): its own, else its props module's, else none at all."""
    f = getattr(scene, "build_models", None)
    if f is not None:
        return f
    try:
        return importlib.import_module(f"scenes.{name}.props").build_models
    except ModuleNotFoundError as e:
        if e.name != f"scenes.{name}.props":
            raise
        return dict


def look_of(name):
    try:
        return importlib.import_module(f"scenes.{name}.mood")
    except ModuleNotFoundError as e:
        if e.name != f"scenes.{name}.mood":
            raise
        return None


# ---- regen -------------------------------------------------------------------------------------
def regen(rep, name, work):
    """Generate what the drivers generate, from nothing. Returns what the other checks read."""
    t0 = time.time()
    try:
        scene = importlib.import_module(f"scenes.{name}")
        builder = builder_of(scene, name)
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
    return {"scene": scene, "builder": builder, "canvas": canvas, "models": models, "pack": pack}


# ---- conflicts ---------------------------------------------------------------------------------
def writers(scene, name, builder):
    """[(owner, category or None, "models" | "pack", function)]: who writes into the resource pack.

    The master scene has one writer per work package (a module of a category subpackage); any
    other scene has its models and its write_pack().
    """
    out = []
    if hasattr(scene, "LINES") and hasattr(scene, "_line"):
        for cat in scene.LINES:
            for part in scene._line(cat)._cat.parts():
                owner = f"{cat}/{part.__name__.rsplit('.', 1)[1]}"
                if hasattr(part, "models"):
                    out.append((owner, cat, "models", part.models))
                if hasattr(part, "pack"):
                    out.append((owner, cat, "pack", part.pack))
    else:
        out.append((name, None, "models", builder))
        if hasattr(scene, "write_pack"):
            out.append((name, None, "pack", scene.write_pack))
    return out


def owner_of(path):
    best, who = -1, None
    for cat, roots in OWNED.items():
        for root in roots:
            if path.startswith(root) and len(root) > best:
                best, who = len(root), cat
    return who


def conflicts(rep, got, name, work):
    """Every writer fills a folder of its own; a path that turns up in two of them is a conflict."""
    scene = got["scene"]
    by_path, fails, warns, attributed, standing = {}, [], [], {}, {}
    ws = writers(scene, name, got["builder"])
    for i, (owner, cat, kind, fn) in enumerate(ws):
        d = os.path.join(work, f"writer-{i}")
        os.makedirs(d, exist_ok=True)
        prefix = getattr(scene._line(cat), "PREFIX", None) if cat else None
        if kind == "models":
            built = fn() or {}
            M.write_pack(d, list(built.values()))
            for key, model in built.items():
                if key != model.name:
                    fails.append(f"{owner}: models() key {key!r} is not the model's name {model.name!r}")
                if prefix and not model.name.startswith(prefix):
                    fails.append(f"{owner}: model {model.name!r} lacks the category prefix {prefix!r}")
        else:
            fn(d)
        for path in files_under(d):
            if path == "pack.mcmeta":
                continue
            by_path.setdefault(path, []).append(f"{owner} ({kind})")
            attributed[path] = owner
            if kind != "pack" or cat is None:
                continue
            own = owner_of(path)
            if own is not None and own != cat:
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
    stray_files = [p for p in files_under(got["pack"]) if p != "pack.mcmeta" and p not in by_path]
    if stray_files:
        warns += [f"{p} is in the pack but no package's models() or pack() wrote it" for p in stray_files]
    packages = sorted({w[0] for w in ws})
    summary = f"{len(packages)} packages write {len(by_path)} files"
    for own, paths in sorted(standing.items()):
        summary += f"; {len(paths)} files of {own} are placeholders of the stand-ins"
    if fails:
        rep.add("conflicts", "FAIL", summary + f": {len(fails)} problems", clip(fails) + clip(warns, 4))
    elif warns:
        rep.add("conflicts", "WARN", summary + ", no file written twice", clip(warns))
    else:
        rep.add("conflicts", "PASS", summary + ", no file written twice, every file in its owner's folders")


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


# ---- repaint -----------------------------------------------------------------------------------
def _model_refs(node, out):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "model" and isinstance(v, str):
                out.add(v.split(":", 1)[-1])
            else:
                _model_refs(v, out)
    elif isinstance(node, list):
        for v in node:
            _model_refs(v, out)
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
                    for tex in (data.get("textures") or {}).values():
                        if isinstance(tex, str) and not tex.startswith("#"):
                            self.painted.setdefault(tex.split(":", 1)[-1], set()).add(ref)

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
            for kind, refs in (("model", models), ("picture", pictures)):
                for ref in refs:
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
    table = set(B.ids(B.REPAINTED + B.VANILLA))
    used = {k.split(":", 1)[-1]: v for k, v in got["canvas"].count().items()}
    outside = sorted(((n, b) for b, n in used.items() if b not in table), reverse=True)
    if outside:
        rep.add("blocks", "WARN", f"{len(used)} kinds of block placed, {len(outside)} not in the occupancy table "
                f"(add them to the table through S2, or use a block of the table)",
                clip(f"{b} x{n}" for n, b in outside))
    else:
        rep.add("blocks", "PASS", f"{len(used)} kinds of block placed, all in the occupancy table")


# ---- entities ----------------------------------------------------------------------------------
def _displays(canvas):
    return [(x, y, z, nbt) for x, y, z, nbt in canvas.entities if nbt.get("id") in DISPLAYS]


def _model_of(nbt):
    return ((nbt.get("item") or {}).get("components") or {}).get("minecraft:item_model")


def entities(rep, got, is_master):
    canvas, models = got["canvas"], got["models"]
    shown = _displays(canvas)
    others = len(canvas.entities) - len(shown)
    fails, warns, used, missing, dense, stretched = [], [], set(), {}, {}, 0
    for x, y, z, nbt in shown:
        if nbt["id"] != "minecraft:item_display":
            continue
        ref = _model_of(nbt)
        name = (ref or "").split(":", 1)[-1]
        if ref is None or not ref.startswith(MODEL_NS + ":") or name not in models:
            missing[ref] = missing.get(ref, 0) + 1
            continue
        used.add(name)
        scale = [float(v) for v in (nbt.get("transformation") or {}).get("scale", (1.0, 1.0, 1.0))]
        density = [16.0 * models[name].px / abs(s) if s else 0.0 for s in scale]
        off = [d for d in density if abs(d - 16.0) > 0.05]
        if len(off) == 1:
            stretched += 1      # a piece drawn out along one axis (pipes, cables: models.between)
        elif off:
            key = (name, tuple(round(d, 2) for d in density))
            dense[key] = dense.get(key, 0) + 1
    for ref, n in sorted(missing.items(), key=lambda kv: str(kv[0])):
        fails.append(f"{n} display entities show {ref!r}, which the pack does not have")
    for (name, d), n in sorted(dense.items()):
        warns.append(f"{name} x{n}: {d[0]:g}/{d[1]:g}/{d[2]:g} pixels to the block along x/y/z, not 16")
    idle = sorted(set(models) - used)
    total = len(shown)
    words = [f"{total} display entities"]
    if is_master:
        words[0] += f" of {S.ENTITY_TOTAL}"
        if total > S.ENTITY_TOTAL:
            fails.append(f"{total} display entities, the whole map may have {S.ENTITY_TOTAL}")
        counts = getattr(canvas, "entity_counts", None) or {}
        if counts:
            words.append("by category: " + ", ".join(f"{k} {v}" for k, v in counts.items() if v))
            if sum(counts.values()) != len(canvas.entities):
                warns.append(f"build() returned {sum(counts.values())} entities in all, the canvas holds "
                             f"{len(canvas.entities)}: a package returns the wrong count")
            if counts.get("machines", 0) > S.BUDGET["machines"]:
                fails.append(f"machines: {counts['machines']} entities, budget {S.BUDGET['machines']}")
            if counts.get("props", 0) > S.BUDGET["props_outdoor"]:
                fails.append(f"props: {counts['props']} entities, budget {S.BUDGET['props_outdoor']}")
            if counts.get("interiors", 0) > S.BUDGET["props_indoor"]:
                fails.append(f"interiors: {counts['interiors']} entities, budget {S.BUDGET['props_indoor']}")
    if stretched:
        words.append(f"{stretched} drawn out along one axis")
    if others:
        words.append(f"{others} other entities")
    if idle:
        words.append(f"{len(idle)} models never placed")
    status = "FAIL" if fails else "WARN" if warns else "PASS"
    rep.add("entities", status, ", ".join(words), clip(fails) + clip(warns))


# ---- views -------------------------------------------------------------------------------------
def views(rep, got, shots_path):
    if not shots_path or not os.path.exists(shots_path):
        rep.add("views", "SKIP", "no shot list, so no per-view counts")
        return
    with open(shots_path, encoding="utf-8") as fh:
        shots = json.load(fh)
    pts = np.array([[x, y, z] for x, y, z, _ in _displays(got["canvas"])], dtype=float).reshape(-1, 3)
    reach = np.array([float(nbt.get("view_range", 1.0)) * 64.0 for _, _, _, nbt in _displays(got["canvas"])])
    ty = math.tan(math.radians(FOV) / 2.0)
    rows, over = [], []
    for shot in shots:
        pos = np.array(shot["pos"], dtype=float)
        if shot.get("look_at") is not None:
            f = np.array(shot["look_at"], dtype=float) - pos
        else:
            yaw, pitch = math.radians(shot.get("yaw", 0.0)), math.radians(shot.get("pitch", 0.0))
            f = np.array([-math.sin(yaw) * math.cos(pitch), -math.sin(pitch), math.cos(yaw) * math.cos(pitch)])
        f /= np.linalg.norm(f)
        r = np.cross(f, (0.0, 1.0, 0.0))
        r /= np.linalg.norm(r)
        u = np.cross(r, f)
        n = 0
        if len(pts):
            v = pts - pos
            depth = v @ f
            # two blocks of slack: a model reaches beyond the point it stands on
            inside = ((depth > -2.0) & (np.abs(v @ r) <= depth * ty * ASPECT + 2.0)
                      & (np.abs(v @ u) <= depth * ty + 2.0) & (np.linalg.norm(v, axis=1) <= reach))
            n = int(inside.sum())
        rows.append((n, shot["name"]))
        if n > S.ENTITY_PER_VIEW:
            over.append(f"{shot['name']}: {n} display entities in view, a view may have {S.ENTITY_PER_VIEW}")
    most = max(rows) if rows else (0, "-")
    summary = (f"{len(rows)} shots, most display entities in view: {most[0]} ({most[1]}), "
               f"limit {S.ENTITY_PER_VIEW}; counted without what walls hide")
    rep.add("views", "WARN" if over else "PASS", summary, clip(over))


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


def main():
    ap = argparse.ArgumentParser(description="technical checks for a scene (plan/PIPELINE.md 6)")
    ap.add_argument("--scene", required=True)
    ap.add_argument("--shots")
    ap.add_argument("--jar", default=os.environ.get("MC_JAR") or os.path.join(
        os.environ.get("MC_ROOT", "/agent/realms-study"), "client26", "versions", "26.3", "26.3.jar"))
    ap.add_argument("--json")
    ap.add_argument("--keep")
    args = ap.parse_args()

    rep = Report(args.scene)
    print(f"check {args.scene} at {commit()}")
    work = args.keep or tempfile.mkdtemp(prefix="c164-check-")
    if args.keep:
        shutil.rmtree(work, ignore_errors=True)
        os.makedirs(work)
    try:
        got = regen(rep, args.scene, work)
        if got is not None:
            checks = [lambda: conflicts(rep, got, args.scene, work),
                      lambda: strays(rep, got),
                      lambda: repaint(rep, got, args.jar)]
            if got["canvas"] is not None:
                checks += [lambda: blocks(rep, got),
                           lambda: entities(rep, got, hasattr(got["scene"], "LINES")),
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
