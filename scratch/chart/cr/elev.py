"""A front elevation of box models, drawn without the renderer: every part's face that looks along
+z (the side a wall-mounted model shows the room), painted back to front. For looking at a model's
pixels while there is no machine to draw on; turned parts are left out.

    PYTHONPATH=build python /tmp/c164_chart/f3/cr/elev.py wall out.png [scale]
"""
import sys

import numpy as np
from PIL import Image

from artkit import models as M


def front(model, face="s"):
    """(picture RGBA, x0, y0): the model seen from +z, one pixel to the texel; x0, y0 the model
    coordinates of the picture's lower left corner."""
    lo, hi = model.bounds()
    x0, y0 = int(np.floor(lo[0])), int(np.floor(lo[1]))
    w, h = int(np.ceil(hi[0])) - x0, int(np.ceil(hi[1])) - y0
    out = np.zeros((h, w, 4), dtype=np.uint8)
    faces = {}
    for pi, f, mat, fw, fh, grain, seed in model.faces():
        if f == face:
            faces[pi] = (mat, fw, fh, grain, seed)
    order = sorted(faces, key=lambda pi: model.parts[pi]["hi"][2])
    for pi in order:
        p = model.parts[pi]
        if p["rot"]:
            continue
        mat, fw, fh, grain, seed = faces[pi]
        tex = mat.paint(fw, fh, grain, seed)
        px0 = int(round(p["lo"][0])) - x0
        top = h - (int(round(p["hi"][1])) - y0)
        th, tw = tex.shape[:2]
        ys, xs = max(0, top), max(0, px0)
        ye, xe = min(h, top + th), min(w, px0 + tw)
        if ye <= ys or xe <= xs:
            continue
        piece = tex[ys - top:ye - top, xs - px0:xe - px0]
        solid = piece[..., 3] > 0
        out[ys:ye, xs:xe][solid] = piece[solid]
    return out, x0, y0


def paste(sheet, picture, left, bottom):
    """Put a picture on the sheet with its lower left corner at (left, bottom), y up."""
    h, w = picture.shape[:2]
    top = sheet.shape[0] - bottom - h
    ys, xs = max(0, top), max(0, left)
    ye, xe = min(sheet.shape[0], top + h), min(sheet.shape[1], left + w)
    piece = picture[ys - top:ye - top, xs - left:xe - left]
    solid = piece[..., 3] > 0
    sheet[ys:ye, xs:xe][solid] = piece[solid]


def wall():
    from scenes.obs.interiors import chartroom as T
    own = T.models()
    bays = len(T.SHELF_WALL)
    sheet = np.zeros((112, 48 * bays, 4), dtype=np.uint8)
    sheet[..., :3] = (8, 8, 10)
    sheet[..., 3] = 255
    for i, tiers in enumerate(T.SHELF_WALL):
        for name, y in zip(tiers, (0, 48, 96)):
            pic, x0, y0 = front(own[T.PREFIX + name])
            paste(sheet, pic, 48 * i + 24 + x0, y + y0)
    return sheet


def main():
    what, out = sys.argv[1], sys.argv[2]
    scale = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    if what == "wall":
        sheet = wall()
    else:
        from scenes.obs.interiors import chartroom as T
        pic, _, _ = front(T.models()[T.PREFIX + what])
        sheet = np.zeros_like(pic)
        sheet[..., :3] = (8, 8, 10)
        sheet[..., 3] = 255
        paste(sheet, pic, 0, 0)
    img = Image.fromarray(sheet[..., :3], "RGB")
    img = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
    img.save(out)
    print(out, img.size)


if __name__ == "__main__":
    main()
