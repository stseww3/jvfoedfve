"""The far ridges on the sky, without the game.

    python -m scenes.obs_sky_ridges.preview <folder> [--look blue] [--compile]

<folder>: renders/_wip/ridges on a node (tools/nodejob.sh --wip), elsewhere a folder outside the
repository; these pictures are not kept.

The ridges are painted by the sky's shader (scenes/obs/sky/ridges.py hands sky/_shaders.py the
layer). The same arithmetic stands in numpy, the shader's twin (_shaders.Twin, ridges.painted()),
and that is what is drawn here: the sky as the shader paints it from the upper terrace, with the
ridges on it. No stars, no comet, no blocks.

    strip.png    the western half of the horizon: 100 degrees to either side of due west (north
                 to the right), from 4 degrees under the horizon to 12 over it, 10 pixels to the
                 degree
    north.png    the north range from the notch to 60 degrees, 30 pixels to the degree
    south.png    the south range likewise

--compile runs the shaders, the layer in place, through the game's compiler as far as that can be
done outside the game (plan/parts/figs/sky_shaders.py, the look's own checks; the compiler is
found or fetched by plan/parts/figs/sky_glslc.sh).

A tool for looking and for the card, not evidence: what the game draws is seen in the game.
"""
import argparse
import importlib.util
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image

from scenes.obs.common import skeleton as S
from scenes.obs.sky import _shaders
from scenes.obs.sky import mood
from scenes.obs.sky import ridges

PROJECT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
EYE_Y = mood.GROUND_Y + S.GROUND + S.EYE        # world y of an eye on the upper terrace
VIEWS = {
    # name: (bearing at the left edge, at the right edge, degrees up at the lower edge, at the upper edge, pixels to the degree)
    "strip": (-100.0, 100.0, -4.0, 12.0, 10),
    "north": (0.0, 60.0, -2.0, 8.0, 30),
    "south": (-60.0, 0.0, -2.0, 8.0, 30),
}


def directions(bearing, up):
    """Unit vectors (x east, y up, z south) for bearings north of due west and degrees up."""
    a, e = np.radians(bearing), np.radians(up)
    return np.stack([-np.cos(a) * np.cos(e), np.sin(e), -np.sin(a) * np.cos(e)], axis=-1)


def paint(twin, left, right, low, high, scale):
    width, height = int(round((right - left) * scale)), int(round((high - low) * scale))
    bearing = left + (np.arange(width) + 0.5) / scale
    up = high - (np.arange(height) + 0.5) / scale
    d = directions(*np.meshgrid(bearing, up)).reshape(-1, 3)
    colour = ridges.painted(twin.sky_at(d, EYE_Y), d, twin)
    return (np.clip(colour, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8).reshape(height, width, 3)


def compile_check(look):
    """The look's own checks with the layer in place. True when they pass."""
    found = subprocess.run(["bash", os.path.join(PROJECT, "plan", "parts", "figs", "sky_glslc.sh")],
                           capture_output=True, text=True).stdout.strip()
    if not found:
        print("no compiler was found or fetched (plan/parts/figs/sky_glslc.sh): nothing compiled")
        return False
    spec = importlib.util.spec_from_file_location("sky_shaders", os.path.join(PROJECT, "plan", "parts", "figs", "sky_shaders.py"))
    checks = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checks)
    return bool(checks.compiled(found, look, None))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--look", default=mood.DEFAULT)
    ap.add_argument("--compile", action="store_true")
    args = ap.parse_args()
    os.makedirs(args.folder, exist_ok=True)
    twin = _shaders.Twin(args.look)
    for name, view in VIEWS.items():
        path = os.path.join(args.folder, name + ".png")
        Image.fromarray(paint(twin, *view)).save(path)
        print(f"{name}: {view[0]:g} to {view[1]:g} degrees north of west, {view[2]:g} to {view[3]:g} up -> {path}")
    rows = ridges.baked()
    print(f"the layer: {ridges.COLUMNS} columns of {ridges.STEP:g} degrees, a ridge in {int((rows > 0).sum())} of them, "
          f"up to {rows.max() * ridges.STEP:g} degrees; {len(ridges.shader_layer(args.look)['skyline'])} characters of GLSL")
    ok = True
    if args.compile:
        ok = compile_check(args.look)
        print(f"result: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
