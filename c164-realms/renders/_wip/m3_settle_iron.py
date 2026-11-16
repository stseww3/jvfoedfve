"""Which models of props/ironwork have faces between two model axes, in which pieces, and what
K.settle does to them.  Run in c164-realms/:  python renders/_wip/m3_settle_iron.py"""
import copy
import os
import sys

sys.path.insert(0, "build")
from scenes.obs.props import _kit as K  # noqa: E402
from scenes.obs.props import ironwork as I  # noqa: E402

out = []
total = 0
for name, spec in I.SPEC.items():
    model = spec["build"]()
    found = K.unsettled(model)
    frame = "+".join(k for k in ("turns", "slide") if spec.get(k)) or "plain"
    seeds = {}
    for i, letters, normal in found:
        part = model.parts[i]
        seeds.setdefault(part["seed"], []).append((i, letters, normal))
    line = f"{name:18s} {len(model.parts):4d} parts, frame {frame:12s} faces between two axes: {len(found):3d} in {len(seeds)} pieces"
    if found:
        total += 1
        kinds = []
        for seed, rows in seeds.items():
            group = [p for p in model.parts if p["seed"] == seed]
            i, letters, n = rows[0]
            lo, hi = model.parts[i]["lo"], model.parts[i]["hi"]
            size = tuple(round(hi[k] - lo[k], 2) for k in range(3))
            kinds.append(f"[{len(group)} boxes, {len(rows)} such; e.g. part {i} faces {letters} normal ({n[0]:.3f}, {n[1]:.3f}, {n[2]:.3f}) box {size}]")
        line += " " + " ".join(kinds[:6]) + (" ..." if len(kinds) > 6 else "")
        try:
            after = K.settle(copy.deepcopy(model))
            left = K.unsettled(after)
            moved = sum(1 for a, b in zip(model.parts, after.parts) if a["rot"] != b["rot"] or a["lo"] != b["lo"])
            line += f" | settled: {len(left)} left, {moved} boxes turned"
        except ValueError as err:
            line += f" | settle FAILS: {err}"
    out.append(line)
out.append(f"{total} of {len(I.SPEC)} models have such faces")
os.makedirs("renders/_wip/settle", exist_ok=True)
open("renders/_wip/settle/iron.txt", "w").write("\n".join(out) + "\n")
print("\n".join(out))
