"""What the fixed views see of the roofs' package (main/roof): nothing, if the roofs keep to their
rule. The director's condition for the six lamps under the gratings and for the walkways as a
whole (A0 #34510): V1, V2 and V11 show the fronts with the outline main/facade.py gave them.

No picture is drawn. Rays go from each view's eye to every cell main/roof lays and are stepped
through the blocks of the main line with tools/sightline.py, the library tools/check.py uses for
its check "sight". A cell is seen when a ray meets it before it meets anything that hides; glass
and gratings are seen through. The main line alone is built: what else stands in the scene (the
court, the props) could only hide more.

Also told, for whoever wants to stand something on a roof later: from which height a point over
each wing's ridge comes into each view.

    python -m scenes.obs_main_smalldome.hidden      # from c164-realms/build; exit code 1 if anything is seen
"""
import os
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "..", "tools")))

import sightline as SL  # noqa: E402
from artkit.canvas import Canvas  # noqa: E402
from artkit.gameassets import Assets  # noqa: E402
from scenes.obs import main, materials  # noqa: E402
from scenes.obs.common import skeleton as S  # noqa: E402
from scenes.obs.main import roof  # noqa: E402

VIEWS = {"V1": S.V1["pos"], "V2": S.V2["pos"], "V11": S.V11["pos"]}        # the eyes of the three views
GRID = (0.1, 0.3, 0.5, 0.7, 0.9)        # the points a cell is tried at: these along each axis, 125 in all
PROBE_UP = 4.0                          # how far over the ridge the probe looks for the views' lower edge
PROBE_STEP = 1 / 16.0


def jar_path():
    return os.environ.get("MC_JAR") or os.path.join(
        os.environ.get("MC_ROOT", "/agent/realms-study"), "client26", "versions", "26.3", "26.3.jar")


def laid():
    """{cell: state} of everything main/roof lays, on an empty canvas."""
    c = Canvas()
    roof.build(c)
    return dict(c.b)


def probes():
    """The points over the two ridges: [(wing, x, y, z)], over the middle of the east ridge column,
    row by row, in steps of a pixel upwards from the grating."""
    out = []
    steps = int(round(PROBE_UP / PROBE_STEP))
    for wing, s in roof.WINGS.items():
        for az in range(roof.ROOF_IN, roof.ROOF_OUT + 1):
            for k in range(1, steps + 1):
                out.append((wing, roof.RIDGE[1] + 0.5, roof.RIDGE_TOP + k * PROBE_STEP, s * az + 0.5))
    return out


def look(canvas, shapes, eye, cells):
    """One view. Returns ({cell: rays that meet it}, {wing: the lowest probe point in view, or None})."""
    eye = np.array(eye, dtype=float)
    cells = sorted(cells)
    pts = np.array([(x + a, y + b, z + c) for x, y, z in cells for a in GRID for b in GRID for c in GRID], dtype=float)
    owner = np.repeat(np.arange(len(cells)), len(GRID) ** 3)
    over = probes()
    over_pts = np.array([p[1:] for p in over], dtype=float)
    both = np.vstack([pts, over_pts])
    lo = np.floor(np.minimum(both.min(axis=0), eye)).astype(int) - 2
    hi = np.ceil(np.maximum(both.max(axis=0), eye)).astype(int) + 2
    bl = SL.Blockers(canvas.b, [], shapes, lo, hi)

    v = pts - eye
    dist = np.linalg.norm(v, axis=1)
    out = bl.cast(eye, v / dist[:, None], dist + 2.0)
    want = np.array(cells, dtype=np.int64)[owner]
    met = np.isfinite(out["t"]) & np.all(out["cell"] == want, axis=1)
    met |= (out["thru"] >= 0) & np.all(out["thru_cell"] == want, axis=1)
    seen = {cells[int(i)]: int(met[owner == i].sum()) for i in np.unique(owner[met])}

    v = over_pts - eye
    dist = np.linalg.norm(v, axis=1)
    free = ~np.isfinite(bl.cast(eye, v / dist[:, None], dist)["t"])
    lowest = {}
    for wing in roof.WINGS:
        ys = [p[2] for p, f in zip(over, free) if f and p[0] == wing]
        lowest[wing] = min(ys) if ys else None
    return seen, lowest


def _where(cells):
    out = []
    for axis, vals in zip("xyz", zip(*cells)):
        a, b = min(vals), max(vals)
        out.append(f"{axis} {a}" if a == b else f"{axis} {a}..{b}")
    return ", ".join(out)


def run():
    jar = jar_path()
    if not os.path.exists(jar):
        print(f"no game jar at {jar} (MC_JAR, MC_ROOT): the shapes of the blocks cannot be read")
        return 2
    scene = Canvas()
    main.build(scene)
    cells = laid()
    missing = [cell for cell, state in cells.items() if scene.get(*cell) != state]
    if missing:
        print(f"{len(missing)} of the {len(cells)} cells main/roof lays are not in the main line as it lays them "
              f"(first: {sorted(missing)[0]}): is the package in the tree, has a later one built over it?")
    lamps = {cell for s in roof.WINGS.values() for cell in roof.lamps(s)}
    found = 0
    with tempfile.TemporaryDirectory() as pack:
        materials.pack(pack)
        shapes = SL.Shapes(Assets(jar, packs=(pack,)))
        for name, eye in VIEWS.items():
            seen, lowest = look(scene, shapes, eye, cells)
            found += len(seen)
            print(f"{name}, eye {tuple(eye)}: {len(cells)} cells of main/roof, {len(cells) * len(GRID) ** 3} rays: "
                  + (f"{len(seen)} cells seen" if seen else "none seen"))
            kinds = {}
            for cell in seen:
                kinds.setdefault(cells[cell].partition("[")[0], []).append(cell)
            for kind, at in sorted(kinds.items()):
                print(f"    {kind}: {len(at)} at {_where(at)}")
            lit = sorted(cell for cell in seen if cell in lamps)
            print(f"    lamps under the gratings: {'seen at ' + str(lit) if lit else 'none of the six seen'}")
            for wing, y in lowest.items():
                print(f"    over the {wing} ridge the view begins "
                      + (f"at y {y:g}, {y - roof.RIDGE_TOP:g} over the grating" if y is not None else
                         f"more than {PROBE_UP:g} over the grating"))
    print("nothing of main/roof is seen from V1, V2 or V11" if not found else
          f"{found} sightings: the roofs show in a view that has to keep the fronts' outline")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(run())
