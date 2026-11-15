"""What display entities and blocks lie near a pixel of a shot? Run in build/ with PYTHONPATH=.:/tmp/c164_lamps

    python whatat.py <scene> <shot> <px> <py> [radius]      (pixels of the 1280x720 picture)
"""
import importlib
import math
import sys

from inframe import camera, W, H, FOV


def main():
    scene, shot_name, px0, py0 = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
    rad = float(sys.argv[5]) if len(sys.argv) > 5 else 30.0
    mod = importlib.import_module("scenes." + scene)
    canvas = mod.build()
    shot = next(s for s in mod.shots() if s["name"] == shot_name)
    px = camera(shot["pos"], shot["look_at"])
    print("shot", shot_name, "pos", shot["pos"], "look_at", shot["look_at"])
    ents = getattr(canvas, "e", None) or getattr(canvas, "entities", [])
    for e in ents:
        pos = e.get("pos") if isinstance(e, dict) else getattr(e, "pos", None)
        if pos is None:
            continue
        p = px(pos)
        if p and abs(p[0] - px0) <= rad and abs(p[1] - py0) <= rad:
            ident = e.get("id") if isinstance(e, dict) else getattr(e, "id", "?")
            nbt = e.get("nbt", {}) if isinstance(e, dict) else getattr(e, "nbt", {})
            item = ""
            if isinstance(nbt, dict):
                item = str(nbt.get("item", nbt.get("block_state", "")))[:110]
            print(f"  entity at ({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f}) -> px ({p[0]:.0f}, {p[1]:.0f}), {p[2]:.1f} off: {ident} {item}")
    # the first block along the ray through the pixel
    pos, at = shot["pos"], shot["look_at"]
    f = [at[i] - pos[i] for i in range(3)]
    n = math.sqrt(sum(v * v for v in f)); f = [v / n for v in f]
    r = [-f[2], 0.0, f[0]]; n = math.hypot(r[0], r[2]) or 1.0; r = [v / n for v in r]
    u = [r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0]]
    t = math.tan(math.radians(FOV) / 2)
    sx = (px0 / W * 2 - 1) * t * W / H
    sy = (1 - py0 / H * 2) * t
    d = [f[i] + sx * r[i] + sy * u[i] for i in range(3)]
    n = math.sqrt(sum(v * v for v in d)); d = [v / n for v in d]
    seen = []
    k = 0.0
    while k < 120 and len(seen) < 4:
        k += 0.05
        p = [pos[i] + d[i] * k for i in range(3)]
        cell = tuple(math.floor(v) for v in p)
        state = canvas.b.get(cell)
        if state is not None and (not seen or seen[-1][0] != cell):
            seen.append((cell, state, round(k, 1)))
    for cell, state, k in seen:
        print(f"  ray meets {cell} {state[:70]} at {k}")


if __name__ == "__main__":
    main()
