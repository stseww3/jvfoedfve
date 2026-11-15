"""A contact sheet of the comet: the three versions (rows a, b, c) under the three lights (columns
blue, deep, glow), each added onto the colour the western sky has behind it.

Not a picture of the scene and not a render: the sprites as comet.comet() paints them, on a flat
sky worked out from mood.LOOKS the way comet.sky_behind() does (facing west the horizon colour is
stained by the afterglow). No stars, no clouds, no buildings. It is there to look at the drawing
as pixels while no pictures can be made and to see the versions side by side; what the comet looks
like in the game is judged on the pictures from the game.

    python -m scenes.obs_sky_comet.sheet <folder>      (in build/; a second or two)

writes into the folder, which is not one of the repository's:

    comet_1080p.png   the moon's whole square in every tile, as large as in the middle of a 1080p
                      picture at fov 70 (towards the edges the wide angle enlarges it a little)
    comet_zoom.png    the comet alone, three times enlarged: every pixel of the drawing
    comet_stamp.png   the whole square at a quarter: is it still a comet at the size of a stamp
"""
import math
import os
import sys

import numpy as np
from PIL import Image

from scenes.obs.sky import comet, mood

WEST = 0.9                       # how far the afterglow stains the horizon colour for someone facing west
ZOOM = (20, 220, 68, 198)        # rows and columns of the square that hold the comet in every light
GAP = 6
# screen pixels to one pixel of the drawing: the square is 0.4 wide at distance 1, the picture's
# half height is tan(35 degrees)
AS_SEEN = 0.4 * 540.0 / math.tan(math.radians(35.0)) / comet.SIZE


def _rgb(text):
    return np.array([int(text[i:i + 2], 16) for i in (1, 3, 5)], dtype=float) / 255.0


def sky(look, n=comet.SIZE):
    """The colour of the sky behind every row of the moon's square, (n, n, 3)."""
    v = mood.LOOKS[look]
    zenith, horizon = _rgb(v["zenith"]), _rgb(v["horizon"])
    horizon = horizon + (_rgb(v["glow"]) - horizon) * WEST * v["glow_alpha"]
    z = 16.0 / v["sky_fog_end"]
    out = np.zeros((n, n, 3))
    for row in range(n):
        up = math.degrees(math.atan((n * 0.5 - (row + 0.5)) / (n * 0.5) * 0.2))
        reach = 16.0 / math.tan(math.radians(90.0 - mood.MOON_ANGLE + up))
        f = min(1.0, (16.0 + 496.25 * reach / 512.0) / v["sky_fog_end"])
        out[row, :] = zenith + (horizon - zenith) * (f - z) / (1.0 - z)
    return out


def tile(style, look, scale, crop=None):
    """One version under one light on its sky, as a picture."""
    px = np.clip(sky(look) + comet.comet(style, comet.STRENGTH[look], comet.TAIL[look]), 0.0, 1.0)
    if crop:
        r0, r1, c0, c1 = crop
        px = px[r0:r1, c0:c1]
    im = Image.fromarray((px * 255.0 + 0.5).astype(np.uint8))
    size = (max(1, int(round(im.width * scale))), max(1, int(round(im.height * scale))))
    return im.resize(size, Image.NEAREST if scale >= 1.0 else Image.BOX)


def sheet(path, scale, crop=None):
    tiles = [[tile(style, look, scale, crop) for look in mood.LOOKS] for style in comet.STYLES]
    w, h = tiles[0][0].size
    out = Image.new("RGB", (len(tiles[0]) * (w + GAP) + GAP, len(tiles) * (h + GAP) + GAP), (60, 60, 60))
    for i, row in enumerate(tiles):
        for j, t in enumerate(row):
            out.paste(t, (GAP + j * (w + GAP), GAP + i * (h + GAP)))
    out.save(path)
    return out.size


def main(folder):
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(here, "..", "..", "..", ".."))     # the checkout: c164-realms/ is in it
    if os.path.commonpath([root, os.path.abspath(folder)]) == root:
        sys.exit("the sheet is not kept in the repository: give a folder outside it")
    os.makedirs(folder, exist_ok=True)
    print(f"rows {', '.join(comet.STYLES)}; columns {', '.join(mood.LOOKS)}; not a render, no stars or clouds")
    for name, scale, crop in (("comet_1080p.png", AS_SEEN, None), ("comet_zoom.png", 3.0, ZOOM),
                              ("comet_stamp.png", 0.25, None)):
        path = os.path.join(folder, name)
        print(path, "%d x %d" % sheet(path, scale, crop))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
