"""The far ridges on the sky, without the game.

    python -m scenes.obs_sky_ridges.preview <folder> [--look blue]

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

Whether the shaders compile with the layer in place is the business of the look's own checks
(python plan/parts/figs/sky_shaders.py, which compiles with the game's own shaderc).

A tool for looking and for the card, not evidence: what the game draws is seen in the game.
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image

from scenes.obs.common import skeleton as S
from scenes.obs.sky import _shaders
from scenes.obs.sky import mood
from scenes.obs.sky import ridges

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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--look", default=mood.DEFAULT)
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
