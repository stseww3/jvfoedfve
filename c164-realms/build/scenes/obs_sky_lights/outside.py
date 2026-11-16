"""python -m scenes.obs_sky_lights.outside (in build/): has a change of sky/lights left the fronts as
they were? The block light of this scene's four stations (_lightkit.levels), once under the code of
another commit and once under this tree's, compared cell by cell.

    against <commit>        the whole comparison: <commit>'s build folder is taken out of git into a
                            scratch folder and surveyed there, this tree is surveyed here, and the
                            report is printed
    dump <file>             survey the tree this is run in and write the survey to a file
    compare <file> <file>   the report for two such files, the older one first

Where a cell stands is told by the window nearest to it (main's table at each station's origin; the
windows of the levels board): before its glass, in the glass column or behind it, counted along
the window's `inward`. What a front shows is what stands before the glass; the cells before the
glass of a window's own opening are its recess.

This is the proof the director asked for when the windows' sources moved before the glass (STATUS,
"亮窗的光源挪到玻璃外侧": allowed if the levels are the same cell by cell). The report says where they
are not the same, by how much, and which of the sources that changed reach there.
"""
import io
import os
import pickle
import shutil
import subprocess
import sys
import tarfile
import tempfile

BOX = ((-62, 100), (-8, 60), (-62, 62))     # round a station's origin: both terraces, the building to its top
SIDES = ("before the glass", "in the glass column", "behind the glass")
TIERS = ("dark", "dim", "lit", "bright")
LISTED = 12                                 # single cells are written out up to this many


# ---- the survey ------------------------------------------------------------------------------------------
def survey():
    """Build the scene with the tree's own sky/lights. Returns what was placed and, for each station,
    the block light round it and its windows with the glass that stands in them."""
    from scenes.obs.main import _plan
    from scenes.obs.sky import _lightkit as L
    from scenes.obs.sky import lights

    from . import BOARD, STATIONS, board_windows, build

    canvas = build()
    r = lights.report(canvas)
    out = {"placed": {cell: (level, why) for cell, (level, why) in r["placed"].items()},
           "summary": lights.summary(canvas), "stations": {}}
    table = [w for w in _plan.windows() if not w.get("blind")]
    for name, o, windows in [(n, o, table) for n, o in STATIONS.items()] + [("levels", BOARD, board_windows())]:
        lv = L.levels(canvas, tuple(o[i] + BOX[i][0] for i in range(3)), tuple(o[i] + BOX[i][1] for i in range(3)))
        records = []
        for w in windows:
            cells = [(x + o[0], z + o[2]) for x, z in w["cells"]]
            y = (w["y"][0] + o[1], w["y"][1] + o[1])
            tiers = [L.tier_of(canvas.name(x, row, z)) for x, z in cells for row in range(y[0], y[1] + 1)]
            tiers = [t for t in tiers if t is not None]
            records.append(dict(name=f"{w['front']} {w['bay']} {w['storey']}", cells=cells, y=y,
                                inward=tuple(w["inward"]), tier=max(tiers) if tiers else None))
        out["stations"][name] = dict(origin=tuple(o), levels=lv, windows=records)
    return out


# ---- the comparison --------------------------------------------------------------------------------------
def _nearest(cell, windows):
    """The window nearest to a cell: (cells between them, the window, how far the cell stands
    behind its glass; negative: before it)."""
    x, y, z = cell
    best = None
    for w in windows:
        dy = max(w["y"][0] - y, 0, y - w["y"][1])
        for gx, gz in w["cells"]:
            d = abs(x - gx) + abs(z - gz) + dy
            if best is None or d < best[0]:
                best = (d, w, (x - gx) * w["inward"][0] + (z - gz) * w["inward"][1])
    return best


def _kind(why):
    """What threw a source, without the window it belongs to: "sky/lights:window", "props/lamps:uplight"."""
    return why.split(" ")[0]


def _spread(pairs):
    """[(before, after)] as "5>1 x4, 4>0 x2", the brightest first."""
    count = {}
    for pair in pairs:
        count[pair] = count.get(pair, 0) + 1
    return ", ".join(f"{a}>{b} x{n}" for (a, b), n in sorted(count.items(), reverse=True))


def _levels(values):
    count = {}
    for v in values:
        count[v] = count.get(v, 0) + 1
    return ", ".join(f"{lv}x{n}" for lv, n in sorted(count.items(), reverse=True)) or "none"


def _tier(w):
    return "not glazed" if w["tier"] is None else TIERS[w["tier"]]


def compare(before, after, names=("before", "after")):
    """The report as lines of text."""
    out = [f"block light, cell by cell: {names[0]} -> {names[1]}",
           f"before: {before['summary'][0]}", f"after:  {after['summary'][0]}"]
    a, b = before["placed"], after["placed"]
    went = {c: v for c, v in a.items() if b.get(c) != v}
    came = {c: v for c, v in b.items() if a.get(c) != v}
    out.append(f"sources of sky/lights: {len(a)} -> {len(b)}; {len(a) - len(went)} stand as they stood, "
               f"{len(went)} went, {len(came)} came (a source whose level changed is counted in both)")
    for kind in sorted({_kind(v[1]) for v in list(went.values()) + list(came.values())}):
        out.append(f"  {kind}: went {_levels(v[0] for v in went.values() if _kind(v[1]) == kind)}; "
                   f"came {_levels(v[0] for v in came.values() if _kind(v[1]) == kind)}")
    changed = [(c, v[0], _kind(v[1])) for c, v in list(went.items()) + list(came.items())]
    total = {"brighter before the glass": 0, "darker before the glass": 0, "in the recess of a lit window": 0}

    for name, s in before["stations"].items():
        t = after["stations"].get(name)
        o = s["origin"]
        out.append("")
        if t is None or [(w["name"], w["cells"], w["y"], w["inward"], w["tier"]) for w in s["windows"]] \
                != [(w["name"], w["cells"], w["y"], w["inward"], w["tier"]) for w in t["windows"]]:
            out.append(f"{name}: the two trees do not have the same windows here; not compared")
            continue
        lv0, lv1, windows = s["levels"], t["levels"], s["windows"]
        cells = set(lv0) | set(lv1)
        differ = sorted(c for c in cells if lv0.get(c, 0) != lv1.get(c, 0))
        out.append(f"{name} (origin {o}; cells are given from it): {len(cells)} cells get light, "
                   f"{len(cells) - len(differ)} the same as before, {len(differ)} not")
        groups = {}
        recess_lit = []
        for c in differ:
            d, w, depth = _nearest(c, windows)
            side = 0 if depth < 0 else 1 if depth == 0 else 2
            sign = "brighter" if lv1.get(c, 0) > lv0.get(c, 0) else "darker"
            reach = tuple(sorted({kind for src, level, kind in changed
                                  if abs(c[0] - src[0]) + abs(c[1] - src[1]) + abs(c[2] - src[2]) < level}))
            recess = side == 0 and d == 1
            if recess and (w["tier"] or 0) > 0:
                recess_lit.append(c)
            groups.setdefault((side, sign, reach), []).append((c, w, recess))
        for (side, sign, reach), found in sorted(groups.items()):
            pairs = [(lv0.get(c, 0), lv1.get(c, 0)) for c, _, _ in found]
            step = max(abs(p - q) for p, q in pairs)
            out.append(f"  {SIDES[side]}, {sign}: {len(found)} cells, by up to {step}; the brightest of them "
                       f"{max(p for p, _ in pairs)} before and {max(q for _, q in pairs)} after; "
                       f"within reach of what changed: {', '.join(reach) or 'nothing'}")
            if side == 0:
                total[f"{sign} before the glass"] += len(found)
            if side == 2:                                   # a room: the sum says it, and where it is brightest now
                c, w, _ = max(found, key=lambda hit: (lv1.get(hit[0], 0), lv0.get(hit[0], 0)))
                out.append(f"      the brightest now: {tuple(c[i] - o[i] for i in range(3))} "
                           f"{lv0.get(c, 0)}>{lv1.get(c, 0)}, behind {w['name']} ({_tier(w)})")
                continue
            by_window = {}
            for c, w, recess in found:
                by_window.setdefault((w["name"], _tier(w)), []).append((c, recess))
            for (wname, tier), hits in sorted(by_window.items()):
                inner = [(lv0.get(c, 0), lv1.get(c, 0)) for c, recess in hits if recess]
                outer = [(lv0.get(c, 0), lv1.get(c, 0)) for c, recess in hits if not recess]
                if side == 1:
                    parts = [f"{len(hits)} cells: {_spread(outer)}"]
                else:
                    parts = [f"{len(inner)} cells in its recess: {_spread(inner)}"] if inner else []
                    parts += [f"{len(outer)} cells further out: {_spread(outer)}"] if outer else []
                    if len(hits) <= LISTED:
                        parts.append("at " + " ".join(str(tuple(c[i] - o[i] for i in range(3))) for c, _ in hits))
                out.append(f"      {wname} ({tier}): " + "; ".join(parts))
        total["in the recess of a lit window"] += len(recess_lit)
        out.append(f"  the recesses of the lit windows: "
                   + (f"{len(recess_lit)} cells differ: "
                      + " ".join(f"{tuple(c[i] - o[i] for i in range(3))} {lv0.get(c, 0)}>{lv1.get(c, 0)}"
                                 for c in recess_lit[:LISTED * 2])
                      if recess_lit else "every cell as before"))
    out.append("")
    out.append("all stations: " + "; ".join(f"{k}: {n} cells" for k, n in total.items()))
    return out


# ---- the commands ----------------------------------------------------------------------------------------
def _git(*args, cwd=None, binary=False):
    done = subprocess.run(("git",) + args, cwd=cwd, stdout=subprocess.PIPE, check=True)
    return done.stdout if binary else done.stdout.decode().strip()


def against(commit):
    """Survey `commit` in a scratch folder and this tree here; the report as lines of text."""
    here = os.path.dirname(os.path.abspath(__file__))
    build = os.path.dirname(os.path.dirname(here))
    top = _git("rev-parse", "--show-toplevel", cwd=build)
    inside = os.path.relpath(build, top).replace(os.sep, "/")
    old = _git("rev-parse", "--short=8", commit + "^{commit}", cwd=top)
    new = _git("rev-parse", "--short=8", "HEAD", cwd=top)
    if _git("status", "--porcelain", "--", inside, cwd=top):
        new += ", with changes that are not committed"
    with tempfile.TemporaryDirectory(prefix="c164_lights_before_") as scratch:
        with tarfile.open(fileobj=io.BytesIO(_git("archive", commit, inside, cwd=top, binary=True))) as tar:
            tar.extractall(scratch, filter="data")
        there = os.path.join(scratch, *inside.split("/"))
        shutil.copy(os.path.abspath(__file__), os.path.join(there, "scenes", "obs_sky_lights", "outside.py"))
        kept = os.path.join(scratch, "before.pickle")
        subprocess.run((sys.executable, "-m", "scenes.obs_sky_lights.outside", "dump", kept), cwd=there, check=True)
        with open(kept, "rb") as fh:
            before = pickle.load(fh)
    return compare(before, survey(), (old, new))


def main(argv):
    if len(argv) == 2 and argv[0] == "against":
        print("\n".join(against(argv[1])))
    elif len(argv) == 2 and argv[0] == "dump":
        with open(argv[1], "wb") as fh:
            pickle.dump(survey(), fh)
    elif len(argv) == 3 and argv[0] == "compare":
        loaded = []
        for path in argv[1:]:
            with open(path, "rb") as fh:
                loaded.append(pickle.load(fh))
        print("\n".join(compare(loaded[0], loaded[1], (argv[1], argv[2]))))
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
